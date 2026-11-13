"""Seed da Central Jurídica executado por GET: idempotência, concorrência e ausência de custo.

O catálogo jurídico é inicializado "na primeira leitura". Duas requisições simultâneas num
banco ainda não semeado faziam "consultar e inserir" ao mesmo tempo e uma falhava por
violação de unicidade (HTTP 500). Agora o seed é serializado por um lock consultivo de
transação e tem um caminho rápido (catálogo completo => nenhuma escrita).

Os testes rodam num SCHEMA DESCARTÁVEL do PostgreSQL de teste (apenas as tabelas do catálogo
são criadas nele), de modo que nunca tocam em dados do esquema ``public``. O schema é
removido ao final.
"""
from __future__ import annotations

import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import Session

from backend.app import legal_service, models
from backend.app.checklist import CHECKLIST_MASTER
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.legal_catalog import RULES, SOURCES
from backend.app.main import app

TABELAS = [
    models.KnowledgeItem.__table__, models.LegalSource.__table__, models.LegalProvision.__table__,
    models.LegalRule.__table__, models.LegalRuleChecklistLink.__table__,
]
N_FONTES = len(SOURCES)
N_DISPOSITIVOS = sum(len(s.provisions) for s in SOURCES)
N_REGRAS = len(RULES)


@pytest.fixture
def schema_engine(postgres_engine):
    nome = f"seedtest_{uuid.uuid4().hex[:10]}"
    with postgres_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{nome}"'))
    engine = create_engine(postgres_engine.url, pool_pre_ping=True, connect_args={"options": f"-c search_path={nome},public"})
    try:
        # checkfirst=False: as mesmas tabelas existem em ``public`` e seriam consideradas "visíveis".
        models.Base.metadata.create_all(engine, tables=TABELAS, checkfirst=False)
        yield engine
    finally:
        engine.dispose()
        with postgres_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{nome}" CASCADE'))


def _contagens(session: Session) -> dict[str, int]:
    def total(model):
        return int(session.scalar(select(func.count()).select_from(model)) or 0)
    return {
        "fontes": total(models.LegalSource), "dispositivos": total(models.LegalProvision), "regras": total(models.LegalRule),
        "vinculos": total(models.LegalRuleChecklistLink),
        "biblioteca": int(session.scalar(select(func.count()).select_from(models.KnowledgeItem).where(models.KnowledgeItem.kind == models.LEGAL_LIBRARY_KIND)) or 0),
    }


def test_catalogo_nao_vazio_para_o_teste_ser_significativo():
    assert N_FONTES > 0 and N_DISPOSITIVOS > 0 and N_REGRAS > 0


def test_seed_juridico_concorrente_nao_gera_erro_nem_duplicata(schema_engine):
    a, b = Session(schema_engine), Session(schema_engine)
    resultado_b: dict = {}
    erros: list[BaseException] = []

    def seed_b():
        try:
            resultado_b["created"] = legal_service.seed_legal_catalog(b, embed=False)  # espera o lock de A
            b.commit()
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)

    try:
        resultado_a = legal_service.seed_legal_catalog(a, embed=False)  # A semeia (ainda sem commit)
        assert resultado_a["sources"] == N_FONTES and resultado_a["provisions"] == N_DISPOSITIVOS
        thread = threading.Thread(target=seed_b)
        thread.start()
        time.sleep(0.8)
        assert thread.is_alive(), "B deveria estar aguardando o lock do seed de A"
        a.commit()
        thread.join(timeout=20)
        assert not thread.is_alive()
        assert erros == [], f"seed concorrente falhou: {erros}"
        assert not any(resultado_b["created"].values()), "B não deve criar nada: A já criou tudo"
        with Session(schema_engine) as check:
            c = _contagens(check)
            assert c["fontes"] == N_FONTES and c["dispositivos"] == N_DISPOSITIVOS and c["regras"] == N_REGRAS
            assert c["biblioteca"] == N_DISPOSITIVOS
            sem_item = check.scalar(select(func.count()).select_from(models.LegalProvision).where(models.LegalProvision.knowledge_item_id.is_(None)))
            assert sem_item == 0
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()


def test_controle_negativo_sem_o_lock_o_seed_concorrente_falha(schema_engine, monkeypatch):
    """Prova que o cenário acima é sensível: desligando o lock, a 2ª sessão viola a unicidade
    (era o HTTP 500 original)."""
    from sqlalchemy.exc import IntegrityError

    monkeypatch.setattr(legal_service, "_acquire_seed_lock", lambda db: None)
    a, b = Session(schema_engine), Session(schema_engine)
    erros: list[BaseException] = []

    def seed_b():
        try:
            legal_service.seed_legal_catalog(b, embed=False)
            b.commit()
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)

    try:
        legal_service.seed_legal_catalog(a, embed=False)
        thread = threading.Thread(target=seed_b)
        thread.start()
        time.sleep(0.8)
        a.commit()
        thread.join(timeout=20)
        assert erros and isinstance(erros[0], IntegrityError)
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()


def test_seed_nao_altera_dados_existentes_e_recompleta_apenas_o_que_falta(schema_engine):
    with Session(schema_engine) as s:
        legal_service.seed_legal_catalog(s, embed=False); s.commit()
        dispositivo = s.scalars(select(models.LegalProvision).order_by(models.LegalProvision.id)).first()
        dispositivo.verification_status = "VERIFICADO"
        dispositivo.practical_note = "orientação editada por humano"
        regra = s.scalars(select(models.LegalRule).order_by(models.LegalRule.id)).first()
        regra.active = False
        regra.title = "título editado"
        slug_dispositivo, slug_regra = dispositivo.slug, regra.slug
        # Remove só o item de biblioteca de OUTRO dispositivo (a seed deve recriá-lo).
        outro = s.scalars(select(models.LegalProvision).where(models.LegalProvision.id != dispositivo.id).order_by(models.LegalProvision.id)).first()
        item_id = outro.knowledge_item_id
        outro.knowledge_item_id = None
        s.flush()
        s.delete(s.get(models.KnowledgeItem, item_id))
        s.commit()

    with Session(schema_engine) as s:
        criado = legal_service.seed_legal_catalog(s, embed=False); s.commit()
        assert criado == {"sources": 0, "provisions": 0, "rules": 0, "links": 0, "library": 1}
        d = s.scalar(select(models.LegalProvision).where(models.LegalProvision.slug == slug_dispositivo))
        r = s.scalar(select(models.LegalRule).where(models.LegalRule.slug == slug_regra))
        assert (d.verification_status, d.practical_note) == ("VERIFICADO", "orientação editada por humano")
        assert (r.active, r.title) == (False, "título editado")  # nada foi sobrescrito/reativado
        assert _contagens(s)["biblioteca"] == N_DISPOSITIVOS


def test_seed_com_catalogo_completo_nao_escreve_nada(schema_engine):
    with Session(schema_engine) as s:
        legal_service.seed_legal_catalog(s, embed=False); s.commit()
    comandos: list[str] = []

    def espiao(conn, cursor, statement, parameters, context, executemany):
        comandos.append(statement.lstrip())

    event.listen(schema_engine, "before_cursor_execute", espiao)
    try:
        with Session(schema_engine) as s:
            assert not any(legal_service.seed_legal_catalog(s, embed=False).values())
            s.commit()
    finally:
        event.remove(schema_engine, "before_cursor_execute", espiao)
    assert not [c for c in comandos if c.split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}]
    assert not [c for c in comandos if "advisory" in c.lower()]  # caminho rápido: nem toma o lock


def test_seed_nunca_gera_embedding_pago(schema_engine, monkeypatch):
    """Mesmo com chave configurada, o seed disparado por GET (embed=False) não chama o provider."""
    from backend.app.rag import embeddings

    chamadas: list[str] = []
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    monkeypatch.setattr(embeddings, "generate_embedding", lambda texto, *a, **k: chamadas.append(texto) or [0.0])
    monkeypatch.setattr(embeddings, "build_gateway", lambda: (_ for _ in ()).throw(AssertionError("provider não deve ser criado")))
    with Session(schema_engine) as s:
        legal_service.seed_legal_catalog(s, embed=False); s.commit()
    assert chamadas == []


def test_gets_juridicos_simultaneos_na_primeira_leitura_respondem_200(schema_engine, monkeypatch):
    """Várias requisições HTTP simultâneas num catálogo ainda vazio: todas 200 e consistentes."""
    from backend.app.rag import embeddings

    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    monkeypatch.setattr(embeddings, "build_gateway", lambda: (_ for _ in ()).throw(AssertionError("sem chamadas pagas no seed")))

    def get_db_isolado():
        session = Session(schema_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = get_db_isolado
    caminhos = ["/api/juridico/biblioteca", "/api/juridico/referencias/contexto/LEILAO",
                f"/api/juridico/referencias/checklist/{CHECKLIST_MASTER[0][0]}", "/api/juridico/biblioteca"] * 2
    respostas: list = [None] * len(caminhos)
    barreira = threading.Barrier(len(caminhos))

    def chamar(i: int):
        client = TestClient(app, raise_server_exceptions=False)
        barreira.wait(timeout=10)
        respostas[i] = client.get(caminhos[i])

    try:
        threads = [threading.Thread(target=chamar, args=(i,)) for i in range(len(caminhos))]
        [t.start() for t in threads]
        [t.join(timeout=60) for t in threads]
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert all(r is not None for r in respostas), "alguma requisição não terminou"
    assert [r.status_code for r in respostas] == [200] * len(caminhos), [(c, r.status_code, r.text[:200]) for c, r in zip(caminhos, respostas) if r.status_code != 200]
    with Session(schema_engine) as check:
        c = _contagens(check)
    assert c["fontes"] == N_FONTES and c["dispositivos"] == N_DISPOSITIVOS and c["regras"] == N_REGRAS and c["biblioteca"] == N_DISPOSITIVOS
