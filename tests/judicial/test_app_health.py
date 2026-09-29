"""JUR-01 — testes da fundação REST: health check e correlation id."""
from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_api.app import app
from judicial_api.config import get_settings


client = TestClient(app)
HEADER = get_settings().correlation_id_header


def test_health_up():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "UP"
    assert body["service"] == "judicial-api"
    assert body["version"]


def test_health_gera_correlation_id_quando_ausente():
    resp = client.get("/health")
    assert resp.status_code == 200
    # a resposta sempre ecoa um correlation id (gerado quando o cliente não envia).
    assert resp.headers.get(HEADER)


def test_health_reutiliza_correlation_id_do_cliente():
    enviado = "corr-teste-123"
    resp = client.get("/health", headers={HEADER: enviado})
    assert resp.status_code == 200
    assert resp.headers.get(HEADER) == enviado


def test_correlation_ids_sao_distintos_entre_requisicoes():
    a = client.get("/health").headers.get(HEADER)
    b = client.get("/health").headers.get(HEADER)
    assert a and b and a != b
