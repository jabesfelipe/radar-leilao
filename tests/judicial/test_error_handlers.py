"""JUR-01 — testes dos handlers globais de erro (via rotas temporárias)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from judicial_api.app import create_app
from judicial_api.enums import ErrorCode
from judicial_api.errors import JudicialError


def _client_com_rotas():
    app = create_app()

    @app.get("/_boom_domain")
    def _boom_domain():
        raise JudicialError(ErrorCode.PROVIDER_UNAVAILABLE, "fonte fora", http_status=503)

    @app.get("/_boom_unexpected")
    def _boom_unexpected():
        raise RuntimeError("segredo interno: api_key=abc123")

    return TestClient(app, raise_server_exceptions=False)


def test_handler_de_judicial_error_retorna_contrato():
    client = _client_com_rotas()
    resp = client.get("/_boom_domain")
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == ErrorCode.PROVIDER_UNAVAILABLE.value
    assert body["retryable"] is True
    assert body["correlation_id"]


def test_handler_de_erro_inesperado_nao_vaza_detalhes():
    client = _client_com_rotas()
    resp = client.get("/_boom_unexpected")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == ErrorCode.UNKNOWN_ERROR.value
    # a mensagem interna (com "segredo"/api_key) nunca é exposta ao consumidor.
    assert "segredo" not in body["message"]
    assert "api_key" not in body["message"]
    assert body["correlation_id"]
