"""Due Diligence integrada — testes de localização (CRUD/persistência), geocode
sem API key, orquestrador das 4 frentes com falha parcial, sinais no checklist e
não-duplicação de débito. Reusa a fixture `client` (TestClient + savepoint/rollback;
não toca dados reais).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

REQUIRED_TABLES = {"properties", "due_diligence_fronts", "property_locations", "debts", "legal_processes",
                   "checklist_items", "checklist_executions", "checklist_results", "entity_history", "domain_events"}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations da due diligence ainda não aplicadas")
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


def _new_property(client) -> int:
    resp = client.post("/api/imoveis", json={"title": "Imóvel DD", "address": "Rua Teste, 100", "city": "Curitiba", "state": "PR", "property_type": "Apto", "area_m2": 60})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---- Orquestrador: 4 frentes, falha parcial não impede as demais ----
def test_overview_quatro_frentes_estado_inicial(client):
    pid = _new_property(client)
    ov = client.get(f"/api/imoveis/{pid}/due-diligence").json()
    assert set(ov["frentes"].keys()) == {"MATRICULA", "JUDICIAL", "PREFEITURA", "LOCALIZACAO"}
    # Integrações externas sem credencial => NAO_CONFIGURADO (nunca "sem risco").
    assert ov["frentes"]["LOCALIZACAO"]["integracao"] == "NAO_CONFIGURADO"
    assert ov["frentes"]["PREFEITURA"]["integracao"] == "NAO_CONFIGURADO"
    # Nenhuma frente declara ausência de risco por falta de consulta.
    for frente in ov["frentes"].values():
        assert frente["status"] in {"NAO_INICIADO", "NAO_CONFIGURADO"}


# ---- Localização: CRUD + persistência + checklist ----
def test_localizacao_coordenadas_manuais_e_checklist(client):
    pid = _new_property(client)
    r = client.put(f"/api/imoveis/{pid}/localizacao", json={
        "latitude": "-25.4284", "longitude": "-49.2733", "coordinates_confirmed": True,
        "observations": "Rua pavimentada, comércio próximo.",
        "location_checklist": {"acesso_viario": "BOM", "transporte_publico": "REGULAR"},
    })
    assert r.status_code == 200, r.text
    loc = r.json()
    assert float(loc["latitude"]) == -25.4284
    assert loc["coordinates_confirmed"] is True
    ratings = {i["key"]: i["rating"] for i in loc["location_checklist"]}
    assert ratings["acesso_viario"] == "BOM"
    assert ratings["transporte_publico"] == "REGULAR"
    # Critérios não avaliados ficam NAO_VERIFICADO (nunca presumidos).
    assert ratings["escolas_saude"] == "NAO_VERIFICADO"
    # Persistência: relê e confirma.
    again = client.get(f"/api/imoveis/{pid}/localizacao").json()
    assert float(again["latitude"]) == -25.4284
    # Links externos sempre disponíveis (não dependem de API key).
    assert again["maps_url"] and again["street_view_url"]


def test_localizacao_rejeita_coordenadas_invalidas(client):
    pid = _new_property(client)
    r = client.put(f"/api/imoveis/{pid}/localizacao", json={"latitude": "200"})
    assert r.status_code == 422


# ---- Geocode sem API key: NAO_CONFIGURADO, não inventa coordenadas ----
def test_geocode_sem_api_key_nao_inventa_coordenadas(client):
    pid = _new_property(client)
    r = client.post(f"/api/imoveis/{pid}/localizacao/geocodificar", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["integracao"] == "NAO_CONFIGURADO"
    assert body["localizacao"]["latitude"] is None
    # Mesmo sem chave, oferece link externo para registro manual.
    loc = client.get(f"/api/imoveis/{pid}/localizacao").json()
    assert loc["maps_url"]


# ---- Prefeitura/IPTU: reutiliza Debt sem duplicar custo ----
def test_prefeitura_debito_reusa_debt_sem_duplicar_custo(client):
    pid = _new_property(client)
    # custo da análise (base) para comparar o total do financeiro.
    r = client.post(f"/api/imoveis/{pid}/due-diligence/prefeitura/debito", json={"category": "IPTU", "amount": "1200.50", "status": "INFORMADO", "source": "Portal Prefeitura"})
    assert r.status_code == 201, r.text
    # Débito aparece em /dividas (aggregate reutilizado), não em /custos.
    dividas = client.get(f"/api/imoveis/{pid}/dividas").json()["dividas"]
    assert any(Decimal(str(d["amount"])) == Decimal("1200.50") and "IPTU" in d["category"] for d in dividas)
    custos = client.get(f"/api/imoveis/{pid}/custos").json()["custos"]
    assert not any(Decimal(str(c["amount"])) == Decimal("1200.50") for c in custos)  # não duplicou em custos
    # Débito não confirmado gera pendência na frente PREFEITURA.
    ov = client.get(f"/api/imoveis/{pid}/due-diligence").json()
    assert ov["frentes"]["PREFEITURA"]["debitos_municipais"] >= 1
    assert any("não confirmado" in p for p in ov["frentes"]["PREFEITURA"]["pendencias"])


# ---- Sinais determinísticos no checklist (sem LLM, sem nova versão) ----
def test_localizacao_sem_confirmacao_reflete_no_checklist(client):
    pid = _new_property(client)
    # coordenadas sem confirmação => pendência de localização
    client.put(f"/api/imoveis/{pid}/localizacao", json={"latitude": "-25.4", "longitude": "-49.2", "coordinates_confirmed": False})
    checklist = client.get(f"/api/imoveis/{pid}").json()["checklist"]
    regiao = next((c for c in checklist if c["canonical_key"] == "REGIAO_SERVICOS"), None)
    assert regiao is not None
    assert regiao["state"] == "ATENCAO"  # diligência pendente, nunca CONFIRMADO automático


# ---- Linha do tempo: eventos de due diligence entram no histórico ----
def test_eventos_due_diligence_na_linha_do_tempo(client):
    pid = _new_property(client)
    client.put(f"/api/imoveis/{pid}/localizacao", json={"observations": "ok"})
    client.post(f"/api/imoveis/{pid}/due-diligence/prefeitura/debito", json={"category": "IPTU", "amount": "100", "status": "INFORMADO"})
    historico = client.get(f"/api/imoveis/{pid}/historico").json()
    tipos = {e["event_type"] for e in historico["eventos"]}
    assert "LOCALIZACAO_ATUALIZADA" in tipos
    assert "DILIGENCIA_FRENTE_ATUALIZADA" in tipos
    assert any(h["entity_type"] == "PropertyLocation" for h in historico["alteracoes"])


# ---- Revisão humana de uma frente ----
def test_revisao_de_frente(client):
    pid = _new_property(client)
    r = client.post(f"/api/imoveis/{pid}/due-diligence/MATRICULA/revisar", json={"reviewed": True, "reviewed_by": "analista"})
    assert r.status_code == 200, r.text
    assert r.json()["revisado"] is True
    r2 = client.post(f"/api/imoveis/{pid}/due-diligence/INVALIDA/revisar", json={"reviewed": True})
    assert r2.status_code == 400


# ---- Geocode client puro: sem chave levanta NAO_CONFIGURADO ----
def test_geocoding_client_sem_chave():
    from backend.app.geocoding_client import GeocodingClient, GeocodingUnavailable
    client = GeocodingClient(api_key=None)
    assert client.configured is False
    with pytest.raises(GeocodingUnavailable):
        client.geocode("Rua Qualquer, 100")


def test_geocoding_client_com_resposta_simulada():
    """Valida o parsing do cliente de geocodificação com uma resposta httpx
    injetada (sem rede). Comprova que a integração está preparada para uso real."""
    import httpx
    from backend.app.geocoding_client import GeocodingClient

    def handler(request: httpx.Request) -> httpx.Response:
        assert "maps/api/geocode" in str(request.url)
        return httpx.Response(200, json={
            "status": "OK",
            "results": [{
                "formatted_address": "Rua Teste, 100 - Curitiba - PR",
                "geometry": {"location": {"lat": -25.4284, "lng": -49.2733}, "location_type": "ROOFTOP"},
                "place_id": "abc123", "partial_match": False,
            }],
        })

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    client = GeocodingClient(api_key="fake-key", client=http)
    result = client.geocode("Rua Teste, 100, Curitiba, PR")
    assert result.found is True
    assert result.latitude == -25.4284 and result.longitude == -49.2733
    assert result.location_type == "ROOFTOP"


def test_geocoding_client_zero_results_nao_e_erro():
    import httpx
    from backend.app.geocoding_client import GeocodingClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ZERO_RESULTS", "results": []})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = GeocodingClient(api_key="fake-key", client=http)
    result = client.geocode("Endereço inexistente")
    assert result.found is False
    assert result.raw_status == "ZERO_RESULTS"


def test_geocoding_client_timeout_vira_indisponivel():
    import httpx
    from backend.app.geocoding_client import GeocodingClient, GeocodingUnavailable

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = GeocodingClient(api_key="fake-key", client=http)
    with pytest.raises(GeocodingUnavailable):
        client.geocode("Rua Teste")
