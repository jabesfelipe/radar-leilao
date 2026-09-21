"""Testes de integração ponta-a-ponta do Radar Leilão.

Exercitam os contratos HTTP reais (FastAPI) contra o banco PostgreSQL/pgvector
já usado pelos demais testes de integração. Reutilizam a fixture ``postgres_engine``
do ``conftest.py`` e sobrescrevem apenas a dependência ``get_db`` do app para
apontar para a sessão de teste, garantindo isolamento por transação (rollback).

A única fronteira externa simulada é a orquestração de IA (LangGraph + Agents +
LLM + RAG), que não roda de forma determinística sem chave de API. Toda a
persistência, os relacionamentos entre entidades e os motores determinísticos
(financeiro, Risk Engine, Verdict Engine) são exercitados de verdade.
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.main import app

try:  # TestClient depende de httpx; se ausente, os testes são ignorados
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - ambiente sem httpx
    TestClient = None


REQUIRED_TABLES = {
    "properties",
    "documents",
    "document_versions",
    "checklist_items",
    "checklist_executions",
    "checklist_results",
    "property_registrations",
    "auction_notices",
    "legal_processes",
    "costs",
    "debts",
    "market_comparables",
    "occupancy_analyses",
    "analyses",
    "risks",
    "verdicts",
    "domain_events",
    "entity_history",
}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient (httpx) indisponível")
    if not REQUIRED_TABLES.issubset(set(inspect(postgres_engine).get_table_names())):
        pytest.skip("Migrations do Radar ainda não aplicadas no banco de testes")

    connection = postgres_engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint" faz cada commit do endpoint liberar
    # apenas um SAVEPOINT, preservando a transação externa para rollback ao final —
    # isolando os dados de cada teste sem tocar no banco real.
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


def _criar_imovel(client, **overrides):
    payload = {
        "title": "Imóvel Integração",
        "address": "Rua da Integração, 100",
        "city": "São Paulo",
        "state": "SP",
        "property_type": "Apartamento",
    }
    payload.update(overrides)
    response = client.post("/api/imoveis", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


# 1. Cadastro e consulta de imóvel ------------------------------------------------

def test_cadastro_e_consulta_de_imovel(client):
    criado = _criar_imovel(client, title="Apartamento Centro")
    assert criado["id"] > 0
    assert criado["title"] == "Apartamento Centro"
    assert criado["status"] == "EM_ANALISE"  # default real do backend

    listagem = client.get("/api/imoveis")
    assert listagem.status_code == 200
    assert any(item["id"] == criado["id"] for item in listagem.json())

    detalhe = client.get(f"/api/imoveis/{criado['id']}")
    assert detalhe.status_code == 200
    corpo = detalhe.json()
    # contrato do Hub: chaves reais retornadas pelo get_property
    assert corpo["imovel"]["id"] == criado["id"]
    for chave in ("documentos", "processos", "custos", "dividas", "comparaveis", "checklist", "riscos", "analises", "eventos", "financeiro"):
        assert chave in corpo
    # cadastro gera evento IMOVEL_CADASTRADO e uma execução de checklist inicial
    assert any(evento["event_type"] == "IMOVEL_CADASTRADO" for evento in corpo["eventos"])
    assert len(corpo["checklist"]) > 0


def test_consulta_de_imovel_inexistente_retorna_404(client):
    assert client.get("/api/imoveis/99999999").status_code == 404


# 2. Documentos -------------------------------------------------------------------

def test_upload_e_listagem_de_documentos(client):
    imovel = _criar_imovel(client)
    arquivo = ("matricula.txt", io.BytesIO(b"# Matricula\nConteudo textual do documento."), "text/plain")
    upload = client.post(
        f"/api/imoveis/{imovel['id']}/documentos",
        files={"file": arquivo},
        data={"document_type": "Matrícula", "source": "Upload manual"},
    )
    assert upload.status_code == 200, upload.text
    documento = upload.json()
    assert documento["document_type"] == "Matrícula"
    assert len(documento["versions"]) == 1
    assert documento["versions"][0]["version"] == 1
    assert len(documento["versions"][0]["content_hash"]) == 64

    listagem = client.get(f"/api/imoveis/{imovel['id']}/documentos")
    assert listagem.status_code == 200
    corpo = listagem.json()
    assert corpo["property_id"] == imovel["id"]
    assert len(corpo["documentos"]) == 1


# 3. Matrícula e edital -----------------------------------------------------------

def test_matricula_persistencia_e_contrato(client):
    imovel = _criar_imovel(client)
    criar = client.post(
        f"/api/imoveis/{imovel['id']}/matricula",
        json={"registration_number": "12345", "registry_office": "1º RI", "comarca": "São Paulo", "holder": "Titular"},
    )
    assert criar.status_code == 200, criar.text
    assert criar.json()["registration_number"] == "12345"

    consulta = client.get(f"/api/imoveis/{imovel['id']}/matricula")
    assert consulta.status_code == 200
    corpo = consulta.json()
    assert corpo["atual"]["registration_number"] == "12345"
    assert len(corpo["historico"]) == 1
    assert "alteracoes" in corpo


def test_edital_persistencia_e_contrato(client):
    imovel = _criar_imovel(client)
    criar = client.post(
        f"/api/imoveis/{imovel['id']}/edital",
        json={"identifier": "EDITAL-1", "auction_stage": "2º leilão", "minimum_value": 180000.25},
    )
    assert criar.status_code == 200, criar.text
    assert criar.json()["identifier"] == "EDITAL-1"

    consulta = client.get(f"/api/imoveis/{imovel['id']}/edital")
    assert consulta.status_code == 200
    corpo = consulta.json()
    assert corpo["atual"]["identifier"] == "EDITAL-1"
    assert len(corpo["historico"]) == 1
    assert "alteracoes" in corpo


# 4. Processos jurídicos ----------------------------------------------------------

def test_processos_juridicos_persistencia(client):
    imovel = _criar_imovel(client)
    criar = client.post(
        f"/api/imoveis/{imovel['id']}/processos",
        json={"number": "0001234-56.2026.8.26.0100", "court": "TJSP", "nature": "Execução"},
    )
    assert criar.status_code == 200, criar.text
    assert criar.json()["number"] == "0001234-56.2026.8.26.0100"

    consulta = client.get(f"/api/imoveis/{imovel['id']}/processos")
    assert consulta.status_code == 200
    corpo = consulta.json()
    assert corpo["property_id"] == imovel["id"]
    assert [p["number"] for p in corpo["processos"]] == ["0001234-56.2026.8.26.0100"]
    assert "historico" in corpo


# 5. Financeiro (custos e dívidas) -----------------------------------------------

def test_financeiro_custos_dividas_e_consolidacao(client):
    imovel = _criar_imovel(client)
    custo = client.post(
        f"/api/imoveis/{imovel['id']}/custos",
        json={"category": "REFORMA", "description": "Obra", "amount": 1200.5, "recurring": True},
    )
    assert custo.status_code == 200, custo.text
    assert custo.json()["recurring"] is True

    divida = client.post(
        f"/api/imoveis/{imovel['id']}/dividas",
        json={"category": "IPTU", "creditor": "Município", "amount": 500.25},
    )
    assert divida.status_code == 200, divida.text

    custos = client.get(f"/api/imoveis/{imovel['id']}/custos")
    dividas = client.get(f"/api/imoveis/{imovel['id']}/dividas")
    assert len(custos.json()["custos"]) == 1
    assert len(dividas.json()["dividas"]) == 1

    # motor financeiro determinístico consome custos e dívidas informados
    financeiro = client.get(f"/api/imoveis/{imovel['id']}/financeiro")
    assert financeiro.status_code == 200
    corpo = financeiro.json()
    assert "financeiro" in corpo
    # serialize() converte Decimal em float, então comparamos numericamente
    assert float(corpo["financeiro"]["custos"]["reforma"]) == pytest.approx(1200.5)
    assert float(corpo["financeiro"]["custos"]["debitos"]) == pytest.approx(500.25)


# 6. Mercado e ocupação -----------------------------------------------------------

def test_mercado_comparaveis_e_calculo(client):
    imovel = _criar_imovel(client)
    criar = client.post(
        f"/api/imoveis/{imovel['id']}/comparaveis",
        json={"kind": "VENDA", "price": 300000, "area_m2": 60},
    )
    assert criar.status_code == 200, criar.text

    mercado = client.get(f"/api/imoveis/{imovel['id']}/mercado")
    assert mercado.status_code == 200
    assert "mercado" in mercado.json()

    # comparável persistido aparece no dossiê consolidado
    detalhe = client.get(f"/api/imoveis/{imovel['id']}")
    assert len(detalhe.json()["comparaveis"]) == 1


def test_ocupacao_registro_e_situacao_atual(client):
    imovel = _criar_imovel(client)
    vazio = client.get(f"/api/imoveis/{imovel['id']}/ocupacao")
    assert vazio.status_code == 200
    assert vazio.json()["situacao_atual"] is None

    registro = client.post(
        f"/api/imoveis/{imovel['id']}/ocupacao",
        json={"status": "OCUPADO", "occupant_profile": "Antigo proprietário", "estimated_months": 6},
    )
    assert registro.status_code == 200, registro.text
    assert registro.json()["status"] == "OCUPADO"

    atual = client.get(f"/api/imoveis/{imovel['id']}/ocupacao")
    corpo = atual.json()
    assert corpo["situacao_atual"]["status"] == "OCUPADO"
    assert len(corpo["historico"]) == 1


def test_ocupacao_rejeita_status_fora_do_contrato(client):
    imovel = _criar_imovel(client)
    resposta = client.post(f"/api/imoveis/{imovel['id']}/ocupacao", json={"status": "INVENTADO"})
    assert resposta.status_code == 422  # Literal do backend não aceita valores fora do contrato


# 7. Checklist --------------------------------------------------------------------

def test_checklist_lista_e_atualizacao_preserva_contrato(client):
    imovel = _criar_imovel(client)
    execucoes = client.get(f"/api/imoveis/{imovel['id']}/checklist")
    assert execucoes.status_code == 200
    execucao = execucoes.json()[-1]
    assert len(execucao["results"]) > 0
    item = execucao["results"][0]

    atualizado = client.patch(
        f"/api/imoveis/{imovel['id']}/checklist/{item['id']}",
        json={"state": "CONFIRMADO", "answer": "Verificado em cartório", "confidence": "ALTA"},
    )
    assert atualizado.status_code == 200, atualizado.text
    corpo = atualizado.json()
    assert corpo["state"] == "CONFIRMADO"
    assert corpo["confidence"] == "ALTA"


def test_checklist_rejeita_estado_invalido(client):
    imovel = _criar_imovel(client)
    execucao = client.get(f"/api/imoveis/{imovel['id']}/checklist").json()[-1]
    item = execucao["results"][0]
    resposta = client.patch(
        f"/api/imoveis/{imovel['id']}/checklist/{item['id']}",
        json={"state": "ESTADO_INEXISTENTE"},
    )
    assert resposta.status_code == 422


# 8, 9, 10, 11. Análise completa + riscos/veredito + histórico + atualização ------

def _fake_orchestration():
    """Payload realista do orquestrador (fronteira de IA), sem chave de LLM."""
    return {
        "agent_results": [
            {
                "agent": "documental",
                "status": "CONCLUIDO",
                "facts": [],
                "evidence_ids": [],
                "pending": [],
                "llm_used": False,
                "model": "modelo-teste",
                "retrieved_chunk_ids": [],
            }
        ],
        "evidence_ids": [],
        "retrieved_chunk_ids": [],
        "llm_runs": [],
        "llm_used": False,
        "model": "modelo-teste",
        "verdict": None,
    }


def test_execucao_analise_completa_atualiza_dossie(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.AnalysisOrchestrator.run",
        lambda self, property_id, domains, query, analysis_id=None: _fake_orchestration(),
    )
    imovel = _criar_imovel(client)

    resposta = client.post(f"/api/imoveis/{imovel['id']}/analisar", json={})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    # contrato real da análise completa
    assert corpo["status"] == "concluida"
    assert corpo["versao"] == 1
    assert corpo["agentes"] == ["documental"]
    for chave in ("llm_usada", "modelo", "chunks_recuperados", "evidencias", "financeiro", "veredito"):
        assert chave in corpo

    # 11. dossiê atualizado após análise: análise, risco/veredito e histórico persistidos
    detalhe = client.get(f"/api/imoveis/{imovel['id']}").json()
    assert len(detalhe["analises"]) == 1
    assert detalhe["analises"][0]["version"] == 1
    assert detalhe["veredito"] is not None  # Verdict Engine determinístico persistiu
    # riscos são recalculados pelo Risk Engine (lista existe, mesmo que vazia)
    assert isinstance(detalhe["riscos"], list)


def test_riscos_e_veredito_expostos_no_dossie(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.AnalysisOrchestrator.run",
        lambda self, property_id, domains, query, analysis_id=None: _fake_orchestration(),
    )
    imovel = _criar_imovel(client)
    client.post(f"/api/imoveis/{imovel['id']}/analisar", json={})

    detalhe = client.get(f"/api/imoveis/{imovel['id']}").json()
    veredito = detalhe["veredito"]
    assert veredito is not None
    assert veredito["analysis_version"] == 1
    assert "overall" in veredito


def test_historico_expoe_eventos_alteracoes_e_analises(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.AnalysisOrchestrator.run",
        lambda self, property_id, domains, query, analysis_id=None: _fake_orchestration(),
    )
    imovel = _criar_imovel(client)
    # gera alteração/histórico com um custo antes da análise
    client.post(f"/api/imoveis/{imovel['id']}/custos", json={"category": "ITBI", "description": "x", "amount": 10})
    client.post(f"/api/imoveis/{imovel['id']}/analisar", json={})

    historico = client.get(f"/api/imoveis/{imovel['id']}/historico")
    assert historico.status_code == 200
    corpo = historico.json()
    # contrato do histórico: três coleções reais
    assert set(("eventos", "alteracoes", "analises")).issubset(corpo.keys())
    assert any(e["event_type"] == "IMOVEL_CADASTRADO" for e in corpo["eventos"])
    assert any(e["event_type"] == "CUSTO_ADICIONADO" for e in corpo["eventos"])
    assert len(corpo["analises"]) == 1
    assert len(corpo["alteracoes"]) >= 1


def test_analise_incremental_gera_nova_versao(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.main.AnalysisOrchestrator.run",
        lambda self, property_id, domains, query, analysis_id=None: _fake_orchestration(),
    )
    imovel = _criar_imovel(client)
    primeira = client.post(f"/api/imoveis/{imovel['id']}/analisar", json={}).json()
    segunda = client.post(f"/api/imoveis/{imovel['id']}/analisar", json={}).json()
    assert primeira["versao"] == 1
    assert segunda["versao"] == 2

    detalhe = client.get(f"/api/imoveis/{imovel['id']}").json()
    assert [a["version"] for a in detalhe["analises"]] == [1, 2]
