"""TASK FINAL — testes do cliente HTTP da Judicial API (Radar → Judicial).

Usa um transporte httpx falso (httpx.MockTransport) para exercitar o cliente sem
rede: resposta de sucesso, timeout, 5xx (indisponível) e 4xx (erro do chamador).
"""
from __future__ import annotations

import httpx
import pytest

from backend.app.judicial_client import (
    JudicialApiClient,
    JudicialApiError,
    JudicialApiUnavailable,
)


def _client(handler) -> JudicialApiClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return JudicialApiClient(base_url="http://judicial-test", api_key="k", client=http)


def test_search_sucesso_parseia_outcome():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("X-API-Key") == "k"
        return httpx.Response(201, json={
            "search_id": "abc",
            "status": "COMPLETED",
            "processes": [{"process_number": "1"}],
            "signals": [{"signal_code": "PENHORA"}],
            "sources": [{"tribunal": "TJPR", "status": "SUCCESS"}],
            "warnings": [],
            "reanalyze": {"recommended": False},
        })

    outcome = _client(handler).search({"process_number": "1", "tribunals": ["TJPR"]})
    assert outcome.search_id == "abc"
    assert outcome.status == "COMPLETED"
    assert outcome.processes[0]["process_number"] == "1"
    assert outcome.signals[0]["signal_code"] == "PENHORA"


def test_search_timeout_vira_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    with pytest.raises(JudicialApiUnavailable):
        _client(handler).search({"process_number": "1"})


def test_search_5xx_vira_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"code": "PROVIDER_UNAVAILABLE"})

    with pytest.raises(JudicialApiUnavailable):
        _client(handler).search({"process_number": "1"})


def test_search_4xx_vira_erro_do_chamador():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": "BAD_REQUEST"})

    with pytest.raises(JudicialApiError) as exc:
        _client(handler).search({})
    assert not isinstance(exc.value, JudicialApiUnavailable)


def test_search_remove_criterios_vazios():
    capturado = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json as _json
        capturado["body"] = _json.loads(request.content)
        return httpx.Response(201, json={"search_id": "x", "status": "EMPTY"})

    _client(handler).search({"process_number": "1", "cpf": None, "tribunals": []})
    # chaves vazias/None não são enviadas
    assert "cpf" not in capturado["body"]
    assert "tribunals" not in capturado["body"]
    assert capturado["body"]["process_number"] == "1"
