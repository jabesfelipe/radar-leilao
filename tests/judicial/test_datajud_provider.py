"""JUR-02 — testes do DataJudProvider (build de query, paginação, normalização).

Nenhum teste faz rede: usamos um transporte falso (FakeTransport) que devolve
páginas pré-montadas no formato Elasticsearch do DataJud.
"""
from __future__ import annotations

import pytest

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ErrorCode
from judicial_api.errors import JudicialError
from judicial_api.models import SearchRequest
from judicial_api.providers.datajud import DataJudProvider, only_digits


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeTransport:
    """Devolve páginas em sequência e registra as chamadas (url/body/headers)."""

    def __init__(self, pages):
        self._pages = list(pages)
        self.calls = []

    def post(self, url, *, json, headers, timeout):
        self.calls.append({"url": url, "body": json, "headers": headers, "timeout": timeout})
        if self._pages:
            return self._pages.pop(0)
        return FakeResponse({"hits": {"hits": []}})


def _hit(numero, sort, _id="a1", classe=("100", "Execução"), assunto=("5", "Penhora")):
    return {
        "_id": _id,
        "sort": sort,
        "_source": {
            "numeroProcesso": numero,
            "grau": "G1",
            "classe": {"codigo": int(classe[0]), "nome": classe[1]},
            "orgaoJulgador": {"nome": "1ª Vara"},
            "assuntos": [{"codigo": int(assunto[0]), "nome": assunto[1]}],
            "movimentos": [{"dataHora": "2026-09-01", "codigo": 123, "nome": "Penhora realizada"}],
            "dataHoraUltimaAtualizacao": "2026-09-02",
        },
    }


def test_only_digits():
    assert only_digits("0000000-00.0000.0.00.0000") == "00000000000000000000"


def test_capabilities_vem_do_catalogo():
    provider = DataJudProvider()
    cap = provider.get_capabilities("TJPR")
    assert cap.tribunal == "TJPR"
    assert cap.supports.process_number is True
    assert cap.supports.cpf is False


def test_build_query_por_numero_processo():
    provider = DataJudProvider()
    entry = default_catalog().get("TJPR")
    body = provider.build_query(
        SearchRequest(process_number="0000000-00.0000.0.00.0000"), entry, page_size=50,
    )
    assert body["size"] == 50
    must = body["query"]["bool"]["must"]
    assert must == [{"match": {"numeroProcesso": "00000000000000000000"}}]
    assert "search_after" not in body
    # sort por @timestamp (padrão do exemplo oficial de paginação do DataJud).
    assert body["sort"] == [{"@timestamp": {"order": "asc"}}]


def test_build_query_classe_assunto_orgao_grau():
    provider = DataJudProvider()
    entry = default_catalog().get("TJPR")
    body = provider.build_query(
        SearchRequest(class_code=1116, subject_code=10375, court_code=13597, grau="G1"),
        entry, page_size=10,
    )
    must = body["query"]["bool"]["must"]
    assert {"match": {"classe.codigo": 1116}} in must
    assert {"match": {"assuntos.codigo": 10375}} in must
    assert {"match": {"orgaoJulgador.codigo": 13597}} in must
    assert {"match": {"grau": "G1"}} in must


def test_toda_capability_suportada_tem_ramo_de_query():
    """Invariante do review: nenhuma capability é declarada como suportada sem um
    critério/query correspondente no build_query."""
    provider = DataJudProvider()
    entry = default_catalog().get("TJPR")
    cap = entry.capabilities
    # request que preenche exatamente os critérios comprovados
    req = SearchRequest(process_number="1", class_code=2, subject_code=3, court_code=4, grau="G2")
    must = provider.build_query(req, entry, page_size=5)["query"]["bool"]["must"]
    campos = {list(m["match"].keys())[0] for m in must}
    if cap.process_number:
        assert "numeroProcesso" in campos
    if cap.class_:
        assert "classe.codigo" in campos
    if cap.subject:
        assert "assuntos.codigo" in campos
    if cap.court:
        assert "orgaoJulgador.codigo" in campos
    if cap.grau:
        assert "grau" in campos


def test_build_query_com_search_after():
    provider = DataJudProvider()
    entry = default_catalog().get("TJPR")
    body = provider.build_query(
        SearchRequest(process_number="123"), entry, page_size=10, search_after=["x", "y"],
    )
    assert body["search_after"] == ["x", "y"]


def test_build_query_pessoa_nao_suportada_erra():
    provider = DataJudProvider()
    entry = default_catalog().get("TJPR")
    with pytest.raises(JudicialError) as exc:
        provider.build_query(SearchRequest(cpf="12345678900"), entry, page_size=10)
    assert exc.value.code == ErrorCode.UNSUPPORTED_SEARCH_CRITERIA
    assert exc.value.retryable is False


def test_build_query_sem_criterio_suportado_erra():
    provider = DataJudProvider()
    entry = default_catalog().get("TJPR")
    with pytest.raises(JudicialError) as exc:
        provider.build_query(SearchRequest(), entry, page_size=10)
    assert exc.value.code == ErrorCode.UNSUPPORTED_SEARCH_CRITERIA


def test_normalize_mapeia_campos():
    provider = DataJudProvider()
    payload = {"hits": {"hits": [_hit("00000000000000000000", ["s1"])]}}
    processos = provider.normalize(payload, "TJPR")
    assert len(processos) == 1
    p = processos[0]
    assert p.process_number == "00000000000000000000"
    assert p.tribunal == "TJPR"
    assert p.class_name == "Execução"
    assert p.court == "1ª Vara"
    assert p.subjects[0].name == "Penhora"
    assert p.movements[0].description == "Penhora realizada"
    assert p.source_identifier == "a1"


def test_search_encapsula_paginacao_search_after():
    # 2 páginas cheias (size=2) + página vazia encerra.
    page1 = FakeResponse({"hits": {"hits": [_hit("1", ["p1a"], _id="1"), _hit("2", ["p1b"], _id="2")]}})
    page2 = FakeResponse({"hits": {"hits": [_hit("3", ["p2a"], _id="3"), _hit("4", ["p2b"], _id="4")]}})
    page3 = FakeResponse({"hits": {"hits": []}})
    transport = FakeTransport([page1, page2, page3])
    provider = DataJudProvider(api_key="chave-teste", transport=transport)

    processos = provider.search(
        SearchRequest(process_number="123", page_size=2, max_pages_per_source=10), "TJPR",
    )
    assert [p.process_number for p in processos] == ["1", "2", "3", "4"]
    # a 2ª chamada deve usar search_after com o sort do último hit da 1ª página.
    assert transport.calls[1]["body"]["search_after"] == ["p1b"]
    # header de autenticação no formato oficial.
    assert transport.calls[0]["headers"]["Authorization"] == "APIKey chave-teste"


def test_search_para_quando_pagina_incompleta():
    # página com menos que page_size encerra sem nova chamada.
    page1 = FakeResponse({"hits": {"hits": [_hit("1", ["p1a"], _id="1")]}})
    transport = FakeTransport([page1])
    provider = DataJudProvider(api_key="k", transport=transport)
    processos = provider.search(
        SearchRequest(process_number="123", page_size=5, max_pages_per_source=10), "TJPR",
    )
    assert len(processos) == 1
    assert len(transport.calls) == 1


def test_search_sem_transporte_erra_configuracao():
    provider = DataJudProvider(api_key="k")  # sem transport
    with pytest.raises(JudicialError) as exc:
        provider.search(SearchRequest(process_number="1"), "TJPR")
    assert exc.value.code == ErrorCode.CONFIGURATION_ERROR


def test_search_sem_api_key_erra_configuracao():
    transport = FakeTransport([FakeResponse({"hits": {"hits": []}})])
    provider = DataJudProvider(transport=transport)  # sem api_key
    with pytest.raises(JudicialError) as exc:
        provider.search(SearchRequest(process_number="1"), "TJPR")
    assert exc.value.code == ErrorCode.CONFIGURATION_ERROR


def test_search_normaliza_erros_http():
    provider = DataJudProvider(api_key="k", transport=FakeTransport([FakeResponse({}, status_code=401)]))
    with pytest.raises(JudicialError) as exc:
        provider.search(SearchRequest(process_number="1"), "TJPR")
    assert exc.value.code == ErrorCode.AUTHENTICATION_ERROR

    provider2 = DataJudProvider(api_key="k", transport=FakeTransport([FakeResponse({}, status_code=429)]))
    with pytest.raises(JudicialError) as exc2:
        provider2.search(SearchRequest(process_number="1"), "TJPR")
    assert exc2.value.code == ErrorCode.RATE_LIMITED
    assert exc2.value.retryable is True

    provider3 = DataJudProvider(api_key="k", transport=FakeTransport([FakeResponse({}, status_code=503)]))
    with pytest.raises(JudicialError) as exc3:
        provider3.search(SearchRequest(process_number="1"), "TJPR")
    assert exc3.value.code == ErrorCode.PROVIDER_SERVER_ERROR


def test_tribunal_fora_do_catalogo_erra():
    provider = DataJudProvider(api_key="k", transport=FakeTransport([]))
    with pytest.raises(JudicialError) as exc:
        provider.search(SearchRequest(process_number="1"), "TJRJ")
    assert exc.value.code == ErrorCode.CONFIGURATION_ERROR


def test_health_check_reflete_configuracao():
    assert DataJudProvider().health_check().status == "NOT_CONFIGURED"
    ok = DataJudProvider(api_key="k", transport=FakeTransport([]))
    assert ok.health_check().status == "AVAILABLE"
