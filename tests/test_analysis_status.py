"""Status honesto da análise (rodada de correções P0 — homologação v1.0.2).

Antes: ``POST /analisar`` respondia ``status:"concluida"`` mesmo com TODOS os agentes falhando.
Aqui: o status vem das chamadas reais dos agentes e da prontidão dos documentos.
A parte HTTP usa o backend real + PostgreSQL; só a fronteira de IA (orquestrador) é simulada.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.ai.analysis_status import consolidate_status, is_running, runs_for_status
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

from sqlalchemy.orm import Session

AGENTES = ["documental", "juridico", "financeiro", "mercado", "checklist"]
SEM_DOCS = {"total": 0, "prontos": 0, "nao_prontos": []}
DOC_PRONTO = {"total": 1, "prontos": 1, "nao_prontos": []}


def _runs(*statuses):
    return [{"agent": AGENTES[i], "status": s, "error_message": None if s == "CONCLUIDO" else "falha"} for i, s in enumerate(statuses)]


# ---- função pura ------------------------------------------------------------

def test_todos_os_agentes_ok_com_documento_pronto_e_concluida():
    r = consolidate_status(_runs(*["CONCLUIDO"] * 5), DOC_PRONTO)
    assert r["status"] == "concluida" and r["codigo"] == "OK" and r["agentes_ok"] == 5 and r["ia_disponivel"] is True


def test_sem_chave_em_todos_os_agentes_e_falha_ia_indisponivel():
    r = consolidate_status(_runs(*["SEM_CHAVE"] * 5), DOC_PRONTO)
    assert r["status"] == "falha" and r["codigo"] == "IA_INDISPONIVEL" and r["ia_disponivel"] is False
    assert "não está disponível" in r["mensagem"]


def test_todos_com_erro_e_falha_agentes():
    r = consolidate_status(_runs(*["ERRO"] * 5), DOC_PRONTO)
    assert r["status"] == "falha" and r["codigo"] == "FALHA_AGENTES"


def test_orcamento_excedido_e_falha_com_codigo_proprio():
    r = consolidate_status(_runs(*["ORCAMENTO_EXCEDIDO"] * 5), DOC_PRONTO)
    assert r["status"] == "falha" and r["codigo"] == "ORCAMENTO_EXCEDIDO"


def test_parte_dos_agentes_falhando_e_parcial_e_lista_quem_falhou():
    r = consolidate_status(_runs("CONCLUIDO", "ERRO", "CONCLUIDO", "CONCLUIDO", "SEM_CHAVE"), DOC_PRONTO)
    assert r["status"] == "parcial" and r["codigo"] == "AGENTES_PARCIAIS" and r["agentes_ok"] == 3
    assert "juridico" in r["mensagem"] and "checklist" in r["mensagem"]


def test_agentes_ok_mas_nenhum_documento_pronto_e_parcial():
    docs = {"total": 1, "prontos": 0, "nao_prontos": [{"nome": "mat.pdf", "estado": "OCR_NECESSARIO", "mensagem": "sem texto"}]}
    r = consolidate_status(_runs(*["CONCLUIDO"] * 5), docs)
    assert r["status"] == "parcial" and r["codigo"] == "DOCUMENTOS_NAO_PRONTOS"
    assert any("mat.pdf" in aviso and "OCR_NECESSARIO" in aviso for aviso in r["avisos"])


def test_documento_nao_pronto_entre_prontos_vira_aviso_sem_rebaixar():
    docs = {"total": 2, "prontos": 1, "nao_prontos": [{"nome": "scan.pdf", "estado": "SEM_TEXTO", "mensagem": "m"}]}
    r = consolidate_status(_runs(*["CONCLUIDO"] * 5), docs)
    assert r["status"] == "concluida" and len(r["avisos"]) == 1


def test_sem_nenhum_agente_e_falha():
    assert consolidate_status([], SEM_DOCS)["status"] == "falha"


def test_runs_derivados_de_agent_results_quando_llm_runs_vazio():
    orq = {"llm_runs": [], "agent_results": [{"agent": "documental", "llm_used": False}, {"agent": "juridico", "llm_used": True}]}
    statuses = {r["agent"]: r["status"] for r in runs_for_status(orq)}
    assert statuses == {"documental": "SEM_CHAVE", "juridico": "CONCLUIDO"}


# ---- HTTP real (PostgreSQL), IA simulada ------------------------------------

@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _orquestracao(statuses, llm_used):
    return {
        "agent_results": [{"agent": AGENTES[i], "facts": [], "evidence_ids": [], "pending": [], "llm_used": s == "CONCLUIDO", "model": "m", "retrieved_chunk_ids": []} for i, s in enumerate(statuses)],
        "evidence_ids": [], "retrieved_chunk_ids": [], "llm_used": llm_used, "model": "m", "verdict": None,
        "llm_runs": [{"agent": AGENTES[i], "provider": "openai", "model": "m", "status": s, "error_message": None if s == "CONCLUIDO" else "falha"} for i, s in enumerate(statuses)],
    }


def _imovel(client):
    r = client.post("/api/imoveis", json={"title": "Imóvel Status", "address": "Rua A, 1", "city": "São Paulo", "state": "SP"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.mark.parametrize("statuses,esperado,llm_used", [
    (["CONCLUIDO"] * 5, "concluida", True),
    (["CONCLUIDO", "CONCLUIDO", "ERRO", "CONCLUIDO", "CONCLUIDO"], "parcial", True),
    (["SEM_CHAVE"] * 5, "falha", False),
    (["ERRO"] * 5, "falha", False),
])
def test_api_analisar_reflete_falha_dos_agentes_no_status(client, monkeypatch, statuses, esperado, llm_used):
    monkeypatch.setattr("backend.app.main.AnalysisOrchestrator.run", lambda self, property_id, domains, query, analysis_id=None: _orquestracao(statuses, llm_used))
    pid = _imovel(client)
    r = client.post(f"/api/imoveis/{pid}/analisar", json={})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["status"] == esperado
    assert corpo["status_detalhe"]["agentes_total"] == 5
    assert (corpo["status"] == "concluida") == (corpo["status_detalhe"]["agentes_ok"] == 5)


def test_status_persistido_aparece_no_historico_e_no_detalhe(client, monkeypatch):
    monkeypatch.setattr("backend.app.main.AnalysisOrchestrator.run", lambda self, property_id, domains, query, analysis_id=None: _orquestracao(["SEM_CHAVE"] * 5, False))
    pid = _imovel(client)
    client.post(f"/api/imoveis/{pid}/analisar", json={})
    historico = client.get(f"/api/imoveis/{pid}/historico").json()
    assert historico["analises"][0]["token_usage"]["status"] == "falha"
    detalhe = client.get(f"/api/imoveis/{pid}").json()
    assert detalhe["analise_ultima"]["status"] == "falha" and detalhe["analise_ultima"]["versao"] == 1
    assert detalhe["analise_em_processamento"] is False


def test_analise_sem_chave_real_sem_mock_do_orquestrador_nao_e_concluida(client, monkeypatch):
    """Sem chave de verdade (nenhuma simulação do orquestrador): os 5 agentes devolvem SEM_CHAVE."""
    from backend.app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    pid = _imovel(client)
    corpo = client.post(f"/api/imoveis/{pid}/analisar", json={}).json()
    assert corpo["status"] == "falha"
    assert corpo["status_detalhe"]["codigo"] == "IA_INDISPONIVEL"
    assert corpo["llm_usada"] is False
    assert {a["status"] for a in corpo["status_detalhe"]["agentes"]} == {"SEM_CHAVE"}


# ---- em_processamento (lock da operação) ------------------------------------

def test_is_running_detecta_analise_em_andamento_pelo_lock(postgres_engine, db):
    pid = 987654
    assert is_running(db, pid) is False
    with postgres_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as outra:
        outra.execute(text("SELECT pg_advisory_lock(hashtextextended(:k, 0))"), {"k": f"analise:{pid}"})
        try:
            assert is_running(db, pid) is True
            assert is_running(db, pid + 1) is False  # outro imóvel não é afetado
        finally:
            outra.execute(text("SELECT pg_advisory_unlock(hashtextextended(:k, 0))"), {"k": f"analise:{pid}"})
    assert is_running(db, pid) is False
