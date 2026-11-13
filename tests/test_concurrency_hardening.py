"""Concorrência e duplicidade: advisory locks, seed do checklist, versão de análise,
claim do worker (SKIP LOCKED), registro/backoff de erro de embedding e varredura manual.

Usa conexões PostgreSQL reais e independentes (duas sessões = dois processos/workers).
Dados criados com commit são removidos ao final de cada teste.
"""
from __future__ import annotations

import threading
import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app import models, services
from backend.app.config import settings
from backend.app.documents import states, worker
from backend.app.locks import require_operation_lock, try_advisory_xact_lock


def _key() -> str:
    return f"teste-{uuid.uuid4().hex}"


# ------------------------------------------------------------------ advisory locks

def test_advisory_lock_exclui_segunda_sessao_ate_o_fim_da_transacao(postgres_engine):
    key = _key()
    a, b = Session(postgres_engine), Session(postgres_engine)
    try:
        assert try_advisory_xact_lock(a, key) is True
        assert try_advisory_xact_lock(a, key) is True      # reentrante na mesma sessão
        assert try_advisory_xact_lock(b, key) is False     # outra sessão não obtém
        with pytest.raises(HTTPException) as exc:
            require_operation_lock(b, key, "ocupado")
        assert exc.value.status_code == 409 and exc.value.detail == "ocupado"
        a.rollback()                                       # fim da transação libera
        assert try_advisory_xact_lock(b, key) is True
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()


def test_chaves_diferentes_nao_se_bloqueiam(postgres_engine):
    a, b = Session(postgres_engine), Session(postgres_engine)
    try:
        assert try_advisory_xact_lock(a, _key()) and try_advisory_xact_lock(b, _key())
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()


def test_analises_simultaneas_do_mesmo_imovel_geram_409_via_http(postgres_engine, monkeypatch):
    """Duas requisições POST /analisar do mesmo imóvel: a segunda recebe 409 enquanto a
    primeira mantém o lock (aqui simulado por uma conexão independente)."""
    from backend.app.database import get_db
    from backend.app.main import app
    from fastapi.testclient import TestClient

    property_id = 910_000_000 + (uuid.uuid4().int % 1_000_000)
    holder = Session(postgres_engine)
    request_session = Session(postgres_engine)
    def override_get_db():
        yield request_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        assert try_advisory_xact_lock(holder, f"analise:{property_id}") is True
        client = TestClient(app, raise_server_exceptions=False)
        ocupado = client.post(f"/api/imoveis/{property_id}/analisar")
        assert ocupado.status_code == 409 and "análise em andamento" in ocupado.json()["detail"]
        reanalise = client.post(f"/api/imoveis/{property_id}/eventos/1/reanalisar")
        assert reanalise.status_code == 409  # compartilha o lock de análise do imóvel
        holder.rollback()
        request_session.rollback()
        livre = client.post(f"/api/imoveis/{property_id}/analisar")
        assert livre.status_code == 404  # lock liberado: segue para a regra de negócio (imóvel inexistente)
    finally:
        app.dependency_overrides.pop(get_db, None)
        holder.rollback(); request_session.rollback(); holder.close(); request_session.close()


# ------------------------------------------------------------------ seed do checklist

def test_seed_do_checklist_concorrente_nao_gera_erro_nem_duplicata(postgres_engine, monkeypatch, aguardar_bloqueio):
    sufixo = uuid.uuid4().hex[:8].upper()
    definicoes = [
        {"canonical_key": f"RACE_{sufixo}_{i}", "question": f"q{i}", "description": f"q{i}", "category": "JURIDICO",
         "domain": ["JURIDICO", "CHECKLIST"], "origin": "teste", "priority": 900 + i, "required": False, "applicable": True,
         "active": True, "version": 1, "expected_evidence": [], "potential_impact": None, "related_rules": [], "agents": [],
         "risk_categories": ["JURIDICO"]}
        for i in range(2)
    ]
    monkeypatch.setattr(services, "master_items", lambda: definicoes)
    a, b = Session(postgres_engine), Session(postgres_engine)
    pid_b = b.execute(text("SELECT pg_backend_pid()")).scalar()
    erros: list[BaseException] = []

    def seed_b():
        try:
            services.ensure_checklist_master(b)   # bloqueia no índice único até A terminar
            b.commit()
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)

    try:
        services.ensure_checklist_master(a)       # A insere (ainda sem commit)
        thread = threading.Thread(target=seed_b)
        thread.start()
        assert aguardar_bloqueio(pid_b), "B deveria estar bloqueada aguardando o commit de A"
        a.commit()
        thread.join(timeout=15)
        assert not thread.is_alive()
        assert erros == [], f"seed concorrente falhou: {erros}"
        with Session(postgres_engine) as check:
            total = check.scalar(select(text("count(*)")).select_from(models.ChecklistItem).where(models.ChecklistItem.canonical_key.like(f"RACE_{sufixo}_%")))
        assert total == 2
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()
        with Session(postgres_engine) as cleanup:
            cleanup.execute(delete(models.ChecklistItem).where(models.ChecklistItem.canonical_key.like(f"RACE_{sufixo}_%")))
            cleanup.commit()


def test_seed_do_checklist_e_idempotente_com_itens_ja_existentes(db):
    services.ensure_checklist_master(db)
    antes = db.scalar(select(text("count(*)")).select_from(models.ChecklistItem))
    services.ensure_checklist_master(db)
    depois = db.scalar(select(text("count(*)")).select_from(models.ChecklistItem))
    assert antes == depois >= 27


# ------------------------------------------------------------------ versão da análise

def test_versoes_de_analise_sao_sequenciais_e_duplicata_e_recusada(db):
    prop = models.Property(title="Imóvel versões", address="Rua V", city="São Paulo", state="SP")
    db.add(prop); db.flush()
    primeira = services.create_analysis(db, prop, "Completa", ["documental"], [], "", [])
    segunda = services.create_analysis(db, prop, "Completa", ["documental"], [], "", [])
    assert (primeira.version, segunda.version) == (1, 2)
    # Duas requisições que calculassem a mesma versão (legado: opportunity_id NULL) são recusadas pelo banco.
    db.add(models.Analysis(property_id=prop.id, version=1))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# ------------------------------------------------------------------ worker: claim, erro e backoff

@pytest.fixture
def versao_pendente(postgres_engine):
    """Versão de documento com chunks sem vetor, COMMITADA (visível a outras sessões)."""
    with Session(postgres_engine) as s:
        prop = models.Property(title="Imóvel worker", address="Rua W", city="São Paulo", state="SP")
        s.add(prop); s.flush()
        doc = models.Document(property_id=prop.id, name="w.txt", document_type="Matrícula")
        s.add(doc); s.flush()
        ver = models.DocumentVersion(document_id=doc.id, version=1, content_hash=uuid.uuid4().hex + uuid.uuid4().hex, original_path="w.txt", normalized_markdown="# w")
        s.add(ver); s.flush()
        s.add_all([models.DocumentChunk(document_version_id=ver.id, chunk_index=i, content=f"trecho {i}", metadata_json={}, embedding=None) for i in range(2)])
        s.commit()
        ids = SimpleNamespace(prop=prop.id, doc=doc.id, ver=ver.id)
    yield ids
    with Session(postgres_engine) as s:
        s.execute(delete(models.DocumentChunk).where(models.DocumentChunk.document_version_id == ids.ver))
        s.execute(delete(models.DocumentVersion).where(models.DocumentVersion.id == ids.ver))
        s.execute(delete(models.Document).where(models.Document.id == ids.doc))
        s.execute(delete(models.Property).where(models.Property.id == ids.prop))
        s.commit()


def test_worker_nao_processa_versao_travada_por_outra_sessao(postgres_engine, versao_pendente, monkeypatch):
    chamadas = []
    monkeypatch.setattr(worker, "embed_pending_chunks", lambda db, vid: chamadas.append(vid) or {})
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    holder, other = Session(postgres_engine), Session(postgres_engine)
    try:
        # Sessão A (ex.: outro worker) já "reivindicou" a versão.
        holder.execute(select(models.DocumentVersion.id).where(models.DocumentVersion.id == versao_pendente.ver).with_for_update())
        out = worker.process_version(other, versao_pendente.ver)
        assert out["status"] == "EM_PROCESSAMENTO" and chamadas == []   # sem chamada duplicada ao provider
        holder.rollback()
        out = worker.process_version(other, versao_pendente.ver)
        assert chamadas == [versao_pendente.ver] and out["status"] != "EM_PROCESSAMENTO"
    finally:
        holder.rollback(); other.rollback(); holder.close(); other.close()


def test_worker_versao_inexistente(postgres_engine):
    with Session(postgres_engine) as s:
        assert worker.process_version(s, 987_654_321)["status"] == "NAO_ENCONTRADA"


class _ProviderQueFalha:
    def __init__(self, exc):
        self.exc = exc
    def embed(self, texts):
        raise self.exc


class RateLimitError(Exception):
    status_code = 429


class AuthenticationError(Exception):
    status_code = 401


def _com_provider(monkeypatch, exc):
    from backend.app.documents import embedding
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    monkeypatch.setattr(embedding, "build_gateway", lambda: _ProviderQueFalha(exc))


def test_worker_registra_erro_transitorio_sem_consumir_tentativas_e_aplica_backoff(postgres_engine, versao_pendente, monkeypatch):
    _com_provider(monkeypatch, RateLimitError("429 Rate limit key=sk-proj-SEGREDO12345"))
    with Session(postgres_engine) as db:
        out = worker.process_version(db, versao_pendente.ver)
        ver = db.get(models.DocumentVersion, versao_pendente.ver)
        meta = ver.extraction_metadata
        assert out["status"] == states.AGUARDANDO_EMBEDDING
        assert meta["embedding_last_error"].startswith("[RATE_LIMIT]") and "SEGREDO" not in meta["embedding_last_error"]
        assert meta["embedding_attempts"] == 0                     # falha transitória não consome tentativa definitiva
        assert meta["embedding_retry_after"] > time.time()          # backoff aplicado
        assert versao_pendente.ver not in worker.pending_versions(db)   # não insiste a cada ciclo
        db.rollback()


def test_worker_credencial_invalida_nao_queima_as_tentativas(postgres_engine, versao_pendente, monkeypatch):
    _com_provider(monkeypatch, AuthenticationError("Incorrect API key provided"))
    with Session(postgres_engine) as db:
        for _ in range(6):
            worker.process_version(db, versao_pendente.ver)
        meta = db.get(models.DocumentVersion, versao_pendente.ver).extraction_metadata
        assert meta["embedding_attempts"] == 0 and meta["embedding_last_error"].startswith("[AUTENTICACAO]")
        assert meta["embedding_transient_failures"] == 6
        db.rollback()


def test_worker_erro_permanente_consome_tentativas_e_sai_da_fila(postgres_engine, versao_pendente, monkeypatch):
    _com_provider(monkeypatch, ValueError("conteúdo inválido"))
    with Session(postgres_engine) as db:
        for _ in range(5):
            worker.process_version(db, versao_pendente.ver)
        meta = db.get(models.DocumentVersion, versao_pendente.ver).extraction_metadata
        assert meta["embedding_attempts"] == 5 and meta["embedding_last_error"].startswith("[DESCONHECIDO]")
        assert versao_pendente.ver not in worker.pending_versions(db)
        db.rollback()


def test_worker_sucesso_limpa_erro_anterior(postgres_engine, versao_pendente, monkeypatch):
    from backend.app.documents import embedding
    with Session(postgres_engine) as db:
        ver = db.get(models.DocumentVersion, versao_pendente.ver)
        ver.extraction_metadata = {"embedding_last_error": "[RATE_LIMIT] antigo", "embedding_retry_after": 1.0, "embedding_transient_failures": 3}
        db.flush()
        vetor = [0.1] * settings.embedding_dimensions
        monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
        monkeypatch.setattr(embedding, "build_gateway", lambda: SimpleNamespace(embed=lambda textos: [vetor for _ in textos]))
        out = worker.process_version(db, versao_pendente.ver)
        meta = db.get(models.DocumentVersion, versao_pendente.ver).extraction_metadata
        assert out["status"] == states.INDEXADO
        assert "embedding_last_error" not in meta and "embedding_retry_after" not in meta and "embedding_transient_failures" not in meta
        db.rollback()


def test_run_once_faz_commit_por_versao(postgres_engine, versao_pendente, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    with Session(postgres_engine) as db:
        commits = []
        original_commit = db.commit
        db.commit = lambda: (commits.append(1), original_commit())[1]
        out = worker.run_once(db, limit=50)
        assert out["processadas"] >= 1 and len(commits) >= out["processadas"]


# ------------------------------------------------------------------ reprocessamento manual (varredura única)

def test_varredura_manual_nao_executa_se_outra_estiver_em_andamento(postgres_engine, monkeypatch):
    from backend.app.routers import monitoring

    execucoes = []
    monkeypatch.setattr(monitoring.doc_worker, "run_once", lambda db, limit=None: execucoes.append(limit) or {})
    with postgres_engine.connect() as outra:
        assert outra.execute(text("SELECT pg_try_advisory_lock(hashtextextended('rag-reprocess', 0))")).scalar()
        try:
            monitoring._run_reprocess_scan(5)
            assert execucoes == []                                  # varredura anterior em curso: ignora
        finally:
            outra.execute(text("SELECT pg_advisory_unlock(hashtextextended('rag-reprocess', 0))"))
            outra.commit()
    monitoring._run_reprocess_scan(5)
    assert execucoes == [5]
    # e o lock foi liberado ao final (pode ser obtido de novo)
    with postgres_engine.connect() as c:
        assert c.execute(text("SELECT pg_try_advisory_lock(hashtextextended('rag-reprocess', 0))")).scalar()
        c.execute(text("SELECT pg_advisory_unlock(hashtextextended('rag-reprocess', 0))")); c.commit()


# ------------------------------------------------------------------ worker: crash, lease e limite de tentativas

class _Relogio:
    def __init__(self, inicio=1_800_000_000.0):
        self.t = inicio
    def __call__(self):
        return self.t


@pytest.fixture
def relogio(monkeypatch):
    r = _Relogio()
    monkeypatch.setattr(worker, "_now", r)
    return r


def _meta_db(postgres_engine, ver_id):
    with Session(postgres_engine) as s:
        ver = s.get(models.DocumentVersion, ver_id)
        return dict(ver.extraction_metadata or {}), ver.status


def _chunks_sem_vetor(postgres_engine, ver_id):
    with Session(postgres_engine) as s:
        return s.scalar(select(text("count(*)")).select_from(models.DocumentChunk).where(
            models.DocumentChunk.document_version_id == ver_id, models.DocumentChunk.embedding.is_(None)))


def _crash(monkeypatch):
    """Simula a morte do processo durante o embedding (BaseException não é capturada pelo worker)."""
    chamadas: list[int] = []

    def embed(db, vid):
        chamadas.append(vid)
        raise SystemExit("worker morto (kill/OOM)")

    monkeypatch.setattr(worker, "embed_pending_chunks", embed)
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    return chamadas


def test_crash_durante_o_processamento_nao_perde_a_contagem_de_tentativas(postgres_engine, versao_pendente, relogio, monkeypatch):
    chamadas = _crash(monkeypatch)
    with Session(postgres_engine) as db:
        with pytest.raises(SystemExit):
            worker.process_version(db, versao_pendente.ver, lease_seconds=30)
        # o processo morreu: a transação de processamento é desfeita (rollback), como no banco real
        db.rollback()
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert chamadas == [versao_pendente.ver]
    assert meta["embedding_attempts"] == 1                       # a tentativa sobreviveu ao crash
    assert meta["embedding_lease_until"] == relogio.t + 30
    assert status == states.PROCESSANDO_EMBEDDING                # não foi marcada como concluída
    assert _chunks_sem_vetor(postgres_engine, versao_pendente.ver) == 2   # nenhum chunk perdido
    with Session(postgres_engine) as s:
        assert versao_pendente.ver not in worker.pending_versions(s)     # lease ativo: outro worker poderia estar nela


def test_worker_reiniciado_repete_com_backoff_e_para_no_limite_de_tentativas(postgres_engine, versao_pendente, relogio, monkeypatch):
    chamadas = _crash(monkeypatch)
    monkeypatch.setattr(worker, "_pending_ids", lambda db: [versao_pendente.ver])   # isola a varredura da nossa versão
    t0 = relogio.t

    def reiniciar_e_varrer(em, esperar_crash):
        relogio.t = t0 + em
        with Session(postgres_engine) as db:      # processo novo = sessão nova
            if esperar_crash:
                with pytest.raises(SystemExit):
                    worker.run_once(db, limit=5, max_attempts=3, lease_seconds=10)
                db.rollback()
                return None
            return worker.run_once(db, limit=5, max_attempts=3, lease_seconds=10)

    reiniciar_e_varrer(0, esperar_crash=True)                       # tentativa 1 -> crash
    assert reiniciar_e_varrer(1, False)["processadas"] == 0         # lease ainda válido: ninguém repete
    out = reiniciar_e_varrer(11, False)                             # lease expirou: interrupção registrada + backoff
    assert out["interrompidas"] == [versao_pendente.ver] and out["processadas"] == 0
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert meta["embedding_last_error"].startswith("[INTERROMPIDO]") and meta["embedding_interruptions"] == 1
    assert meta["embedding_retry_after"] == t0 + 11 + 60 and "embedding_lease_until" not in meta
    assert status == states.AGUARDANDO_EMBEDDING and meta["embedding_attempts"] == 1

    assert reiniciar_e_varrer(40, False)["processadas"] == 0        # ainda em backoff
    reiniciar_e_varrer(80, esperar_crash=True)                      # tentativa 2 -> crash
    assert reiniciar_e_varrer(100, False)["interrompidas"] == [versao_pendente.ver]
    meta, _ = _meta_db(postgres_engine, versao_pendente.ver)
    assert meta["embedding_attempts"] == 2 and meta["embedding_interruptions"] == 2
    assert meta["embedding_retry_after"] == t0 + 100 + 120          # backoff exponencial
    reiniciar_e_varrer(300, esperar_crash=True)                     # tentativa 3 -> crash
    out = reiniciar_e_varrer(400, False)                            # limite atingido: sai da fila com ERRO
    assert out["interrompidas"] == [versao_pendente.ver]
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert status == states.ERRO and meta["embedding_attempts"] == 3
    assert "limite de 3 tentativas" in meta["embedding_last_error"]

    # Daqui em diante, nenhum reinício volta a processar: sem loop ilimitado.
    for depois in (10_000, 100_000):
        assert reiniciar_e_varrer(depois, False)["processadas"] == 0
    assert len(chamadas) == 3                                       # exatamente WORKER_MAX_ATTEMPTS chamadas
    assert _chunks_sem_vetor(postgres_engine, versao_pendente.ver) == 2   # documento/trechos preservados, não "concluído"
    assert status != states.INDEXADO


def test_recuperacao_nao_mexe_em_versao_de_worker_vivo(postgres_engine, versao_pendente, relogio, monkeypatch):
    monkeypatch.setattr(worker, "_pending_ids", lambda db: [versao_pendente.ver])
    with Session(postgres_engine) as s:
        ver = s.get(models.DocumentVersion, versao_pendente.ver)
        ver.extraction_metadata = {"embedding_attempts": 1, "embedding_lease_until": relogio.t - 5}   # lease vencido
        s.commit()
    vivo, outro = Session(postgres_engine), Session(postgres_engine)
    try:
        vivo.execute(select(models.DocumentVersion.id).where(models.DocumentVersion.id == versao_pendente.ver).with_for_update())  # ainda processando
        assert worker.recover_interrupted(outro) == []          # linha travada por worker vivo: não é "crash"
        vivo.rollback()
        assert worker.recover_interrupted(outro) == [versao_pendente.ver]   # liberada e lease vencido: interrompida
    finally:
        vivo.rollback(); outro.rollback(); vivo.close(); outro.close()


def test_apos_crash_uma_nova_tentativa_bem_sucedida_conclui_e_limpa_o_historico(postgres_engine, versao_pendente, relogio, monkeypatch):
    from backend.app.documents import embedding
    _crash(monkeypatch)
    monkeypatch.setattr(worker, "_pending_ids", lambda db: [versao_pendente.ver])
    with Session(postgres_engine) as db:
        with pytest.raises(SystemExit):
            worker.run_once(db, lease_seconds=10)
        db.rollback()
    relogio.t += 11
    with Session(postgres_engine) as db:
        assert worker.run_once(db)["interrompidas"] == [versao_pendente.ver]
    relogio.t += 61                                              # backoff cumprido
    monkeypatch.undo()                                           # remove o crash simulado
    vetor = [0.1] * settings.embedding_dimensions
    monkeypatch.setattr(worker, "_now", relogio)
    monkeypatch.setattr(worker, "_pending_ids", lambda db: [versao_pendente.ver])
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    monkeypatch.setattr(embedding, "build_gateway", lambda: SimpleNamespace(embed=lambda textos: [vetor for _ in textos]))
    with Session(postgres_engine) as db:
        out = worker.run_once(db)
        assert out["processadas"] == 1
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert status == states.INDEXADO and meta["embedding_attempts"] == 2
    for chave in ("embedding_lease_until", "embedding_interruptions", "embedding_last_error", "embedding_retry_after"):
        assert chave not in meta
    assert _chunks_sem_vetor(postgres_engine, versao_pendente.ver) == 0


def test_sem_chave_nao_conta_tentativa_nem_cria_lease(postgres_engine, versao_pendente, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    with Session(postgres_engine) as db:
        out = worker.process_version(db, versao_pendente.ver)
        db.commit()
    meta, _ = _meta_db(postgres_engine, versao_pendente.ver)
    assert out["status"] == states.AGUARDANDO_EMBEDDING
    assert "embedding_attempts" not in meta and "embedding_lease_until" not in meta


def test_falha_comum_continua_registrando_motivo_e_encerrando_o_lease(postgres_engine, versao_pendente, relogio, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)

    def quebra(db, vid):
        raise RuntimeError("falha com key=sk-proj-SEGREDO999")

    monkeypatch.setattr(worker, "embed_pending_chunks", quebra)
    with Session(postgres_engine) as db:
        out = worker.process_version(db, versao_pendente.ver)
        db.commit()
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert out["status"] == states.ERRO == status and meta["embedding_attempts"] == 1
    assert "SEGREDO999" not in meta["embedding_last_error"] and "embedding_lease_until" not in meta


# ------------------------------------------------------------------ worker: corrida entre as etapas 1 e 2, lock e dono do lease

def _com_chave(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)


def _provider_falso(monkeypatch, retorno=None):
    chamadas: list[int] = []
    monkeypatch.setattr(worker, "embed_pending_chunks", lambda db, vid: chamadas.append(vid) or (retorno if retorno is not None else {}))
    return chamadas


def _travar_linha(session, ver_id):
    session.execute(select(models.DocumentVersion.id).where(models.DocumentVersion.id == ver_id).with_for_update())


def test_corrida_entre_etapa_1_e_2_espera_o_lock_e_processa_sem_gastar_tentativa_em_vao(postgres_engine, versao_pendente, monkeypatch, aguardar_bloqueio):
    """Outro executor segura a linha logo depois do commit da etapa 1. A etapa 2 deve ESPERAR (e não
    desistir com a tentativa consumida): ao liberar, processa. Uma tentativa, uma chamada ao provider."""
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch)
    w1, outro = Session(postgres_engine), Session(postgres_engine)
    pid_w1 = w1.execute(text("SELECT pg_backend_pid()")).scalar()
    esperou: list[bool] = []
    threads: list[threading.Thread] = []
    commit_original = w1.commit

    def commit_e_outro_segura_a_linha():
        commit_original()                                   # fim da etapa 1 (tentativa + lease gravados)
        _travar_linha(outro, versao_pendente.ver)           # o outro executor passa a segurar a linha

        def liberar():
            esperou.append(aguardar_bloqueio(pid_w1))       # só libera quando W1 estiver de fato bloqueada
            outro.rollback()
        t = threading.Thread(target=liberar); t.start(); threads.append(t)

    w1.commit = commit_e_outro_segura_a_linha
    try:
        out = worker.process_version(w1, versao_pendente.ver)
        w1.commit = commit_original
        commit_original()
        [t.join(timeout=15) for t in threads]
    finally:
        w1.commit = commit_original
        w1.rollback(); outro.rollback(); w1.close(); outro.close()
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert esperou == [True], "a etapa 2 deveria ter ficado bloqueada esperando o lock"
    assert chamadas == [versao_pendente.ver] and out["status"] != "EM_PROCESSAMENTO"
    assert meta["embedding_attempts"] == 1 and "embedding_lease_until" not in meta and "embedding_lease_owner" not in meta
    assert status == states.AGUARDANDO_EMBEDDING            # chunks ainda sem vetor (provider falso): segue na fila


def test_timeout_do_lock_mantem_estado_consistente_e_a_tentativa_so_conta_uma_vez(postgres_engine, versao_pendente, relogio, monkeypatch):
    """Lock indisponível durante TODA a chamada (nem a devolução consegue o lock): nada é processado,
    o estado fica consistente (tentativa + lease ativo do dono) e o vencimento do lease a contabiliza UMA vez."""
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch)
    monkeypatch.setattr(worker, "_pending_ids", lambda db: [versao_pendente.ver])
    w1, outro = Session(postgres_engine), Session(postgres_engine)
    commit_original = w1.commit

    def commit_e_outro_segura_a_linha():
        commit_original()
        _travar_linha(outro, versao_pendente.ver)

    w1.commit = commit_e_outro_segura_a_linha
    try:
        inicio = time.monotonic()
        out = worker.process_version(w1, versao_pendente.ver, lease_seconds=30, lock_timeout_ms=200)
        decorrido = time.monotonic() - inicio
    finally:
        w1.commit = commit_original
        w1.rollback(); outro.rollback(); w1.close(); outro.close()
    assert out["status"] == "EM_PROCESSAMENTO" and "lock indisponível" in out["motivo"]
    assert chamadas == [] and decorrido < 5, "o lock_timeout deve impedir espera indefinida"
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert meta["embedding_attempts"] == 1 and meta["embedding_lease_until"] == relogio.t + 30 and meta["embedding_lease_owner"]
    assert status == states.PROCESSANDO_EMBEDDING

    relogio.t += 31                                          # lease vence: a tentativa é tratada como interrompida
    with Session(postgres_engine) as db:
        assert worker.recover_interrupted(db) == [versao_pendente.ver]
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert meta["embedding_attempts"] == 1 and meta["embedding_interruptions"] == 1 and "embedding_lease_owner" not in meta
    assert status == states.AGUARDANDO_EMBEDDING


def test_lock_demora_mas_vem_depois_do_primeiro_timeout_a_tentativa_e_devolvida_sem_processar(postgres_engine, versao_pendente, monkeypatch):
    """Primeiro re-claim estoura o lock_timeout; ao tentar devolver, o lock vem: a tentativa dessa execução é
    devolvida (attempts volta ao valor anterior, lease encerrado) e o provider NÃO é chamado."""
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch)
    real = worker._claim_row_blocking
    estado = {"n": 0}

    def claim_com_primeiro_timeout(db, vid, ms):
        estado["n"] += 1
        if estado["n"] == 1:
            raise worker.LockUnavailable("simulado")
        return real(db, vid, ms)

    monkeypatch.setattr(worker, "_claim_row_blocking", claim_com_primeiro_timeout)
    with Session(postgres_engine) as db:
        out = worker.process_version(db, versao_pendente.ver)
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert out["status"] == "EM_PROCESSAMENTO" and "devolvida" in out["motivo"] and chamadas == []
    assert meta.get("embedding_attempts", 0) == 0 and "embedding_lease_until" not in meta and "embedding_lease_owner" not in meta
    assert status == states.AGUARDANDO_EMBEDDING


def test_lease_de_outra_execucao_nao_e_limpo_nem_a_tentativa_devolvida(postgres_engine, versao_pendente, monkeypatch):
    """Entre as etapas 1 e 2 o lease passa a ser de outra execução: esta não processa e não mexe em nada."""
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch)
    w1 = Session(postgres_engine)
    commit_original = w1.commit

    def commit_e_outra_execucao_assume():
        commit_original()
        with Session(postgres_engine) as outra:
            ver = outra.get(models.DocumentVersion, versao_pendente.ver)
            meta = dict(ver.extraction_metadata or {})
            meta.update({"embedding_lease_owner": "outra-execucao", "embedding_attempts": 2})
            ver.extraction_metadata = meta
            outra.commit()

    w1.commit = commit_e_outra_execucao_assume
    try:
        out = worker.process_version(w1, versao_pendente.ver)
    finally:
        w1.commit = commit_original
        w1.rollback(); w1.close()
    meta, _ = _meta_db(postgres_engine, versao_pendente.ver)
    assert out["status"] == "EM_PROCESSAMENTO" and "outra execução" in out["motivo"] and chamadas == []
    assert meta["embedding_lease_owner"] == "outra-execucao" and meta["embedding_attempts"] == 2 and "embedding_lease_until" in meta


def test_worker_concorrente_segurando_o_lock_nao_consome_tentativa(postgres_engine, versao_pendente, monkeypatch):
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch)
    vivo, outro = Session(postgres_engine), Session(postgres_engine)
    try:
        _travar_linha(vivo, versao_pendente.ver)                        # worker vivo dentro do processamento
        out = worker.process_version(outro, versao_pendente.ver)
        vivo.rollback()
    finally:
        vivo.rollback(); outro.rollback(); vivo.close(); outro.close()
    meta, status = _meta_db(postgres_engine, versao_pendente.ver)
    assert out["status"] == "EM_PROCESSAMENTO" and chamadas == []
    assert meta.get("embedding_attempts", 0) == 0 and "embedding_lease_until" not in meta
    assert status != states.PROCESSANDO_EMBEDDING


def test_lease_vencido_com_worker_ainda_vivo_nao_e_recuperado_nem_reprocessado_nem_consome_tentativa(postgres_engine, versao_pendente, relogio, monkeypatch):
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch)
    monkeypatch.setattr(worker, "_pending_ids", lambda db: [versao_pendente.ver])
    with Session(postgres_engine) as s:
        ver = s.get(models.DocumentVersion, versao_pendente.ver)
        ver.extraction_metadata = {"embedding_attempts": 1, "embedding_lease_until": relogio.t - 5, "embedding_lease_owner": "worker-vivo"}
        s.commit()
    antes, _ = _meta_db(postgres_engine, versao_pendente.ver)
    vivo, outro = Session(postgres_engine), Session(postgres_engine)
    try:
        _travar_linha(vivo, versao_pendente.ver)                        # ainda processando, embora o lease tenha vencido
        assert versao_pendente.ver in worker.pending_versions(outro)    # aparece como elegível...
        assert worker.recover_interrupted(outro) == []                  # ...mas não é "recuperada"
        out = worker.process_version(outro, versao_pendente.ver)        # ...nem reprocessada
        vivo.rollback()
    finally:
        vivo.rollback(); outro.rollback(); vivo.close(); outro.close()
    depois, _ = _meta_db(postgres_engine, versao_pendente.ver)
    assert out["status"] == "EM_PROCESSAMENTO" and chamadas == []
    assert depois == antes, "nada pode ser alterado enquanto o worker vivo segura a linha"


def test_duas_execucoes_simultaneas_da_mesma_versao_processam_uma_unica_vez(postgres_engine, versao_pendente, monkeypatch):
    _com_chave(monkeypatch)
    entrou, liberar = threading.Event(), threading.Event()
    chamadas: list[int] = []

    def embed_lento(db, vid):
        chamadas.append(vid)
        entrou.set()
        assert liberar.wait(timeout=20)
        return {}

    monkeypatch.setattr(worker, "embed_pending_chunks", embed_lento)
    resultado: dict = {}

    def w1():
        with Session(postgres_engine) as db:
            resultado["w1"] = worker.process_version(db, versao_pendente.ver)
            db.commit()

    t = threading.Thread(target=w1); t.start()
    try:
        assert entrou.wait(timeout=20), "W1 deveria ter entrado no processamento"
        with Session(postgres_engine) as db2:
            resultado["w2"] = worker.process_version(db2, versao_pendente.ver)     # W1 está no meio do embedding
            db2.commit()
    finally:
        liberar.set(); t.join(timeout=20)
    meta, _ = _meta_db(postgres_engine, versao_pendente.ver)
    assert resultado["w2"]["status"] == "EM_PROCESSAMENTO"
    assert resultado["w1"]["status"] != "EM_PROCESSAMENTO"
    assert chamadas == [versao_pendente.ver], "o provider só pode ser chamado uma vez"
    assert meta["embedding_attempts"] == 1 and "embedding_lease_until" not in meta


def test_nada_a_processar_nao_consome_tentativa(postgres_engine, versao_pendente, monkeypatch):
    _com_chave(monkeypatch)
    chamadas = _provider_falso(monkeypatch, retorno={"embeddings_pendentes": 0})
    with Session(postgres_engine) as db:
        worker.process_version(db, versao_pendente.ver)
        db.commit()
    meta, _ = _meta_db(postgres_engine, versao_pendente.ver)
    assert chamadas == [versao_pendente.ver] and meta["embedding_attempts"] == 0
