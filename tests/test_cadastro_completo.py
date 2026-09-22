"""Testes do cadastro completo do imóvel de leilão (TASK 62).

Exercitam o endpoint transacional ``POST /api/imoveis/completo`` que reutiliza os
modelos existentes (Property, Auction, AuctionNotice, PropertyRegistration,
PropertySource) e valida a integração cadastro -> dossiê -> análise.

Caso de referência (fixture, NÃO hardcoded no produto): imóvel real
"COND PARQUE ARVOREDO RESIDENCIAL CLUBE". Serve como caso de validação do primeiro
fluxo E2E real — este teste NÃO declara o E2E real da Caixa como concluído, apenas
verifica que o cadastro foi preparado para esse caso.
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


REQUIRED_TABLES = {
    "properties",
    "auctions",
    "auction_notices",
    "property_registrations",
    "property_sources",
    "documents",
    "document_versions",
    "analyses",
}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient (httpx) indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations do Radar (incl. 0009) ainda não aplicadas no banco de testes")

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


# Caso de referência COND PARQUE ARVOREDO — fixture de validação.
CAIXA_PAYLOAD = {
    "imovel": {
        "title": "COND PARQUE ARVOREDO RESIDENCIAL CLUBE",
        "city": "Curitiba",
        "state": "PR",
        "property_type": "Apartamento",
        "area_m2": 102.71,
        "private_area_m2": 109.08,
        "bedrooms": 3,
        "parking_spots": 2,
        "origin": "Caixa Econômica Federal",
        "origin_property_code": "155552876506-4",
        "inscription": "57000970088001",
        "modality": "Extrajudicial",
        "system": "SFI",
    },
    "leilao": {
        "appraisal_value": 370000,
        "first_auction_value": 370000,
        "second_auction_value": 222000,
        "auctioneer": "WERNO KLÖCKNER JÚNIOR",
    },
    "edital": {"identifier": "0044/0226 - CPA/RE", "item": "258"},
    "matricula": {"registration_number": "25278", "registry_office": "07", "comarca": "Curitiba - PR"},
    "fontes": [
        {"source_type": "PAGINA_IMOVEL", "url": "https://venda-imoveis.caixa.gov.br/exemplo", "description": "Página Caixa"},
        {"source_type": "EDITAL", "url": "https://exemplo.gov.br/edital.pdf"},
    ],
}


def _cadastrar(client, payload=None):
    response = client.post("/api/imoveis/completo", json=payload or CAIXA_PAYLOAD)
    assert response.status_code == 201, response.text
    return response.json()


# 1. Cadastro completo cria todas as entidades ----------------------------------

def test_cadastro_completo_persiste_todas_as_entidades(client):
    criado = _cadastrar(client)
    property_id = criado["id"]
    assert property_id > 0
    assert criado["status"] == "EM_ANALISE"

    detalhe = client.get(f"/api/imoveis/{property_id}").json()
    imovel = detalhe["imovel"]
    assert imovel["title"] == "COND PARQUE ARVOREDO RESIDENCIAL CLUBE"
    assert imovel["city"] == "Curitiba" and imovel["state"] == "PR"
    assert float(imovel["area_m2"]) == pytest.approx(102.71)
    assert float(imovel["private_area_m2"]) == pytest.approx(109.08)
    assert imovel["bedrooms"] == 3 and imovel["parking_spots"] == 2
    assert imovel["origin"] == "Caixa Econômica Federal"
    assert imovel["origin_property_code"] == "155552876506-4"
    assert imovel["inscription"] == "57000970088001"
    assert imovel["modality"] == "Extrajudicial" and imovel["system"] == "SFI"

    # leilão preserva avaliação e 1º/2º leilão separadamente
    leilao = detalhe["leilao"]
    assert leilao is not None
    assert float(leilao["appraisal_value"]) == pytest.approx(370000)
    assert float(leilao["first_auction_value"]) == pytest.approx(370000)
    assert float(leilao["second_auction_value"]) == pytest.approx(222000)
    assert leilao["auctioneer"] == "WERNO KLÖCKNER JÚNIOR"

    # edital e matrícula
    assert detalhe["edital"]["identifier"] == "0044/0226 - CPA/RE"
    assert detalhe["edital"]["item"] == "258"
    assert detalhe["matricula"]["registration_number"] == "25278"
    assert detalhe["matricula"]["registry_office"] == "07"

    # fontes
    fontes = detalhe["fontes"]
    assert len(fontes) == 2
    assert {f["source_type"] for f in fontes} == {"PAGINA_IMOVEL", "EDITAL"}

    # cadastro dispara evento e execução inicial de checklist
    assert any(e["event_type"] == "IMOVEL_CADASTRADO" for e in detalhe["eventos"])
    assert len(detalhe["checklist"]) > 0


# 2. Imóvel aparece na listagem ---------------------------------------------------

def test_imovel_cadastrado_aparece_na_lista(client):
    criado = _cadastrar(client)
    listagem = client.get("/api/imoveis").json()
    assert any(item["id"] == criado["id"] for item in listagem)


# 3. Cadastro mínimo (só obrigatórios) --------------------------------------------

def test_cadastro_minimo_sem_dados_opcionais(client):
    payload = {"imovel": {"title": "Imóvel Simples", "city": "Curitiba", "state": "PR", "property_type": "Casa"}}
    criado = _cadastrar(client, payload)
    detalhe = client.get(f"/api/imoveis/{criado['id']}").json()
    assert detalhe["leilao"] is None
    assert detalhe["edital"] is None
    assert detalhe["matricula"] is None
    assert detalhe["fontes"] == []


# 4. Validação: título obrigatório ------------------------------------------------

def test_cadastro_sem_titulo_falha(client):
    payload = {"imovel": {"title": "", "city": "Curitiba", "state": "PR", "property_type": "Casa"}}
    response = client.post("/api/imoveis/completo", json=payload)
    assert response.status_code == 422


# 5. Fontes podem ser adicionadas após o cadastro ---------------------------------

def test_fontes_endpoint_dedicado(client):
    criado = _cadastrar(client, {"imovel": {"title": "Imóvel Fontes", "city": "Curitiba", "state": "PR", "property_type": "Casa"}})
    add = client.post(f"/api/imoveis/{criado['id']}/fontes", json={"source_type": "MATRICULA", "url": "https://exemplo.gov.br/matricula.pdf"})
    assert add.status_code == 201, add.text
    fontes = client.get(f"/api/imoveis/{criado['id']}/fontes").json()
    assert len(fontes) == 1 and fontes[0]["source_type"] == "MATRICULA"


# 6. Integração cadastro -> dossiê -> análise -------------------------------------

def test_cadastro_completo_habilita_analise_e_gera_versao(client):
    criado = _cadastrar(client)
    property_id = criado["id"]

    resposta = client.post(f"/api/imoveis/{property_id}/analisar", json={})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["versao"] >= 1
    assert corpo["status"] == "concluida"

    # o histórico registra a análise
    historico = client.get(f"/api/imoveis/{property_id}/historico").json()
    assert len(historico["analises"]) >= 1
    # o financeiro consome o leilão cadastrado (avaliação preservada)
    detalhe = client.get(f"/api/imoveis/{property_id}").json()
    assert detalhe["financeiro"] is not None
