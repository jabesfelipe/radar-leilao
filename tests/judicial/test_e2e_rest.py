"""JUR-05 — testes E2E do contrato REST completo.

Exercitam o caminho ponta a ponta pela API HTTP:

    request -> REST -> orchestrator -> provider(mock) -> normalização
            -> persistência -> signals -> response

Sem rede e sem banco. A autenticação é exercitada configurando chaves via
JUDICIAL_API_KEYS e recriando as settings/app.
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from judicial_api.enums import JusticeType
from judicial_api.models import Movement, Party, Process


def _proc_penhora():
    return Process(
        process_number="0001",
        tribunal="TJPR",
        justice_type=JusticeType.STATE,
        parties=[Party(name="JOÃO DA SILVA", document="12345678900", document_type="CPF")],
        movements=[Movement(description="Penhora efetivada nos autos")],
    )


# --------------------------------------------------------------------------
# Fluxo completo de pesquisa (sem auth: modo local/dev)
# --------------------------------------------------------------------------

def test_e2e_search_completo_gera_sinais(make_client):
    client = make_client({"TJPR": [_proc_penhora()]})
    resp = client.post("/api/v1/judicial/search", json={"process_number": "0001", "tribunals": ["TJPR"]})
    assert resp.status_code == 201
    body = resp.json()
    assert body["search_id"]
    assert body["status"] in ("COMPLETED", "PARTIAL", "EMPTY")
    # normalização + persistência: o processo veio do provider mock
    assert any(p["process_number"] == "0001" for p in body["processes"])
    # signals: evidência de penhora + distinção processo x imóvel
    codes = {s["signal_code"] for s in body["signals"]}
    assert "PENHORA" in codes
    assert "PROPERTY_PENHORA_EVIDENCE" in codes


def test_e2e_get_search_recupera_persistido(make_client):
    client = make_client({"TJPR": [_proc_penhora()]})
    created = client.post("/api/v1/judicial/search", json={"process_number": "0001", "tribunals": ["TJPR"]}).json()
    search_id = created["search_id"]

    got = client.get(f"/api/v1/judicial/search/{search_id}")
    assert got.status_code == 200
    assert got.json()["search_id"] == search_id


def test_e2e_sources_endpoint(make_client):
    client = make_client({"TJPR": [_proc_penhora()]})
    search_id = client.post("/api/v1/judicial/search", json={"process_number": "0001", "tribunals": ["TJPR"]}).json()["search_id"]

    resp = client.get(f"/api/v1/judicial/search/{search_id}/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["search_id"] == search_id
    assert any(s["tribunal"] == "TJPR" for s in body["sources"])


def test_e2e_retry_endpoint(make_client):
    client = make_client({"TJPR": [_proc_penhora()]})
    search_id = client.post("/api/v1/judicial/search", json={"process_number": "0001", "tribunals": ["TJPR"]}).json()["search_id"]

    resp = client.post(f"/api/v1/judicial/search/{search_id}/retry")
    assert resp.status_code == 200
    assert resp.json()["search_id"] == search_id


def test_e2e_get_search_inexistente_404(make_client):
    client = make_client({"TJPR": []})
    resp = client.get("/api/v1/judicial/search/nao-existe")
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_e2e_search_sem_criterio_400(make_client):
    client = make_client({"TJPR": []})
    resp = client.post("/api/v1/judicial/search", json={"tribunals": ["TJPR"]})
    assert resp.status_code == 400
    assert resp.json()["code"] == "BAD_REQUEST"


# --------------------------------------------------------------------------
# Metadados / catálogo
# --------------------------------------------------------------------------

def test_e2e_tribunals(make_client):
    client = make_client({})
    resp = client.get("/api/v1/judicial/tribunals")
    assert resp.status_code == 200
    items = resp.json()["items"]
    codes = {t["code"] for t in items}
    assert {"TJPR", "TJSP"}.issubset(codes)


def test_e2e_capabilities(make_client):
    client = make_client({})
    resp = client.get("/api/v1/judicial/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"]
    assert any(t["tribunal"] == "TJPR" for t in body["tribunals"])


def test_e2e_providers_status(make_client):
    client = make_client({})
    resp = client.get("/api/v1/judicial/providers/status")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    assert any(p["provider"] == "DATAJUD" for p in providers)


def test_e2e_metrics_apos_pesquisa(make_client):
    client = make_client({"TJPR": [_proc_penhora()]})
    client.post("/api/v1/judicial/search", json={"process_number": "0001", "tribunals": ["TJPR"]})
    resp = client.get("/metrics")
    assert resp.status_code == 200
    counters = resp.json()["counters"]
    assert counters["searches_total"] >= 1
    assert counters["processes_found"] >= 1


def test_e2e_openapi_tem_endpoints_e_security(make_client):
    client = make_client({})
    schema = client.get("/openapi.json").json()
    assert "/api/v1/judicial/search" in schema["paths"]
    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]


# --------------------------------------------------------------------------
# Autenticação / autorização (recria o app com chaves configuradas)
# --------------------------------------------------------------------------

@pytest.fixture
def auth_client(monkeypatch):
    """App com auth ligada: chave 'k-read' só tem escopo read; 'k-full' tem tudo."""
    monkeypatch.setenv("JUDICIAL_API_KEYS", "k-full, k-read:read")
    monkeypatch.setenv("JUDICIAL_RATE_LIMIT_ENABLED", "false")

    import judicial_api.config as config
    config.get_settings.cache_clear()

    import judicial_api.app as app_module
    importlib.reload(app_module)

    from judicial_api.deps import get_orchestrator

    orch = build_orchestrator_for_auth()
    app_module.app.dependency_overrides[get_orchestrator] = lambda: orch
    client = TestClient(app_module.app)
    yield client

    app_module.app.dependency_overrides.clear()
    monkeypatch.delenv("JUDICIAL_API_KEYS", raising=False)
    monkeypatch.delenv("JUDICIAL_RATE_LIMIT_ENABLED", raising=False)
    config.get_settings.cache_clear()
    importlib.reload(app_module)


def build_orchestrator_for_auth():
    from tests.judicial.conftest import build_orchestrator

    return build_orchestrator({"TJPR": [_proc_penhora()]})


def test_auth_sem_chave_401(auth_client):
    resp = auth_client.post("/api/v1/judicial/search", json={"process_number": "0001", "tribunals": ["TJPR"]})
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTHENTICATION_ERROR"


def test_auth_chave_invalida_401(auth_client):
    resp = auth_client.get("/api/v1/judicial/tribunals", headers={"X-API-Key": "errada"})
    assert resp.status_code == 401


def test_auth_escopo_insuficiente_403(auth_client):
    # k-read não tem escopo 'search': não pode disparar pesquisa.
    resp = auth_client.post(
        "/api/v1/judicial/search",
        json={"process_number": "0001", "tribunals": ["TJPR"]},
        headers={"X-API-Key": "k-read"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "AUTHORIZATION_ERROR"


def test_auth_escopo_read_permite_leitura(auth_client):
    resp = auth_client.get("/api/v1/judicial/tribunals", headers={"X-API-Key": "k-read"})
    assert resp.status_code == 200


def test_auth_chave_full_dispara_pesquisa(auth_client):
    resp = auth_client.post(
        "/api/v1/judicial/search",
        json={"process_number": "0001", "tribunals": ["TJPR"]},
        headers={"X-API-Key": "k-full"},
    )
    assert resp.status_code == 201


def test_health_publico_sem_auth(auth_client):
    assert auth_client.get("/health").status_code == 200
