"""Integrações externas (Geocoding e Judicial API): o que sai do Radar e o que fica no log.

Transporte HTTP falso (httpx.MockTransport): nenhuma chamada externa real.
"""
from __future__ import annotations

import json
import logging

import httpx

from backend.app.geocoding_client import GeocodingClient
from backend.app.judicial_client import JudicialApiClient
from backend.app.redaction import redact

# Chave FALSA montada em tempo de execução: nenhum literal com formato de chave real fica no repositório.
GOOGLE_KEY = "AI" + "za" + "SyFAKE-chave-de-teste-" + "0123456789abcdef"


def _geo_client(capturado: dict) -> GeocodingClient:
    def handler(request: httpx.Request) -> httpx.Response:
        capturado["params"] = dict(request.url.params)
        return httpx.Response(200, json={"status": "OK", "results": [{"formatted_address": "Rua Ficticia, 123", "place_id": "x",
                                                                       "geometry": {"location": {"lat": -23.5, "lng": -46.6}, "location_type": "ROOFTOP"}}]})
    return GeocodingClient(api_key=GOOGLE_KEY, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_geocoding_envia_somente_o_endereco_e_preserva_endereco_comum():
    capturado: dict = {}
    r = _geo_client(capturado).geocode("Rua das Acácias Fictícias, 123, apto 45, Jardim Teste, São Paulo, SP, 01310-100")
    assert r.found
    assert set(capturado["params"]) == {"address", "key", "language", "region"}
    assert capturado["params"]["address"] == "Rua das Acácias Fictícias, 123, apto 45, Jardim Teste, São Paulo, SP, 01310-100"


def test_geocoding_remove_identificadores_pessoais_digitados_no_endereco():
    capturado: dict = {}
    _geo_client(capturado).geocode("Rua X, 10 - proprietário CPF 111.222.333-96, fone (11) 98888-7777, joao@example.com")
    enviado = capturado["params"]["address"]
    assert "111.222.333-96" not in enviado and "98888-7777" not in enviado and "joao@example.com" not in enviado
    assert enviado.startswith("Rua X, 10")


def test_chave_do_google_e_parametro_key_nao_chegam_ao_log():
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address=Rua+X&key={GOOGLE_KEY}&language=pt-BR"
    texto = redact(f"HTTP Request: GET {url} \"HTTP/1.1 200 OK\"")
    assert GOOGLE_KEY not in texto and "key=[REDACTED]" in texto
    assert GOOGLE_KEY not in redact(f"erro com a chave {GOOGLE_KEY}")


def test_logger_do_httpx_nao_registra_urls_em_info():
    import backend.app.main  # noqa: F401  (configura o logging da aplicação)
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING


def test_judicial_api_recebe_somente_os_criterios_informados_e_nenhum_texto_de_documento():
    capturado: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        capturado["url"] = str(request.url)
        capturado["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"search_id": "s1", "status": "COMPLETED", "processes": []})

    client = JudicialApiClient(base_url="http://judicial_api:8010", api_key=None, client=httpx.Client(transport=httpx.MockTransport(handler)))
    client.search({"process_number": "0001234-56.2020.5.02.0001", "cpf": None, "cnpj": None, "name": None, "uf": "SP", "tribunals": [], "justice_types": []})
    assert capturado["url"] == "http://judicial_api:8010/api/v1/judicial/search"
    assert capturado["payload"] == {"process_number": "0001234-56.2020.5.02.0001", "uf": "SP"}
