"""E2E HTTP do fluxo jurídico pela camada FastAPI (TestClient), SEM LLM e SEM
DataJud real: o transporte do JudicialApiClient é substituído por um fake via
monkeypatch. Isolado por transação (savepoint) — não toca dados reais.

Cobre: consulta judicial, exibição no dossiê (seção jurídica), vinculação manual,
endpoints de riscos/evidências jurídicas e validações.
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

REQUIRED_TABLES = {"properties", "legal_processes", "checklist_items", "evidences"}


def _outcome():
    from backend.app.judicial_client import JudicialSearchOutcome
    return JudicialSearchOutcome(
        search_id="http-1",
        status="COMPLETED",
        processes=[{
            "process_number": "0000003-33.2022.8.16.0001",
            "tribunal": "TJPR", "comarca": "Curitiba", "uf": "PR",
            "class_name": "Execução Fiscal",
            "subjects": [{"name": "Penhora"}],
            "parties": [{"name": "JOÃO DA SILVA", "role": "DEFENDANT"}],
            "movements": [{"movement_date": "2026-03-01", "description": "Penhora efetivada"}],
        }],
        signals=[{"signal_code": "PENHORA", "severity": "HIGH", "confidence": 0.85,
                  "evidence_text": "Movimento menciona penhora", "tribunal": "TJPR",
                  "process_number": "0000003-33.2022.8.16.0001"}],
        sources=[{"tribunal": "TJPR", "status": "SUCCESS"}],
    )


@pytest.fixture
def client(postgres_engine, monkeypatch):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations do Radar ainda não aplicadas")
    if "correlation_level" not in {c["name"] for c in inspect(postgres_engine).get_columns("legal_processes")}:
        pytest.skip("Migration 0013 (correlation_level) ainda não aplicada")

    # Substitui a busca HTTP do cliente judicial por um fake (sem rede/DataJud).
    from backend.app import judicial_client
    monkeypatch.setattr(judicial_client.JudicialApiClient, "search", lambda self, criteria: _outcome())

    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _criar_imovel(client):
    resp = client.post("/api/imoveis", json={
        "title": "Imóvel E2E Jur HTTP", "address": "Rua L", "city": "Curitiba",
        "state": "PR", "property_type": "Apartamento", "area_m2": 70,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_consulta_judicial_persiste_e_correlaciona(client):
    pid = _criar_imovel(client)
    resp = client.post(f"/api/imoveis/{pid}/processos/consultar", json={"name": "JOÃO DA SILVA"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["disponivel"] is True
    assert body["processos_criados"] == 1
    assert body["sinais_criados"] == 1
    assert "processos_relevantes" in body
    # fontes consultadas aparecem na resposta
    assert body["fontes"] and body["fontes"][0]["tribunal"] == "TJPR"


def test_dossie_expoe_secao_juridica(client):
    pid = _criar_imovel(client)
    client.post(f"/api/imoveis/{pid}/processos/consultar", json={"name": "JOÃO DA SILVA"})
    dossie = client.get(f"/api/imoveis/{pid}").json()
    assert "juridico" in dossie
    jur = dossie["juridico"]
    assert jur["processos_encontrados"] == 1
    assert jur["situacao_imovel"] == "NAO_CONFIRMADA"
    assert jur["impacto_financeiro"] == "NAO_QUANTIFICADO"


def test_vinculacao_manual_altera_origem(client):
    pid = _criar_imovel(client)
    client.post(f"/api/imoveis/{pid}/processos/consultar", json={"name": "JOÃO DA SILVA"})
    processos = client.get(f"/api/imoveis/{pid}/processos").json()["processos"]
    assert processos, "deve haver processo persistido"
    process_id = processos[0]["id"]

    resp = client.post(f"/api/imoveis/{pid}/juridico/processos/{process_id}/vincular", json={"link_origin": "VALIDADA", "observacao": "Conferido na matrícula"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["processo"]["link_origin"] == "VALIDADA"


def test_endpoints_juridicos_de_leitura(client):
    pid = _criar_imovel(client)
    client.post(f"/api/imoveis/{pid}/processos/consultar", json={"name": "JOÃO DA SILVA"})
    evid = client.get(f"/api/imoveis/{pid}/juridico/evidencias").json()
    assert evid["evidencias"], "deve listar evidências jurídicas"
    riscos = client.get(f"/api/imoveis/{pid}/juridico/riscos")
    assert riscos.status_code == 200


def test_consulta_sem_criterio_retorna_400(client):
    pid = _criar_imovel(client)
    resp = client.post(f"/api/imoveis/{pid}/processos/consultar", json={})
    assert resp.status_code == 400


def test_vincular_processo_inexistente_404(client):
    pid = _criar_imovel(client)
    resp = client.post(f"/api/imoveis/{pid}/juridico/processos/999999/vincular", json={"link_origin": "MANUAL"})
    assert resp.status_code == 404
