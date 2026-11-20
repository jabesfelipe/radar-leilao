"""v1.0.14 — pesquisa externa autorizada, pesquisa automática do imóvel, checklist por prioridade, situação documental e
pessoas da matrícula. Dados fictícios; nenhuma chamada de rede real (provedores com transporte simulado ou falsos)."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace as NS

import httpx
import pytest

from backend.app import market_research, models
from backend.app.checklist_priority import prioritized
from backend.app.config import settings
from backend.app.document_status import summarize
from backend.app.investment_summary import summary
from backend.app.registry_timeline import people
from backend.app.search import extract, service
from backend.app.search.providers import BraveProvider, SearchError, SearchHit, SearchResponse, SearchUnavailable, TavilyProvider
from backend.app.viability import market_intelligence
from tests.test_checklist_evidencias import _leilao, _prop
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)


class FakeProvider:
    def __init__(self, name="fake", hits=None, fail=None):
        self.name, self.hits, self.fail, self.calls = name, hits or [], fail, 0

    @property
    def configured(self):
        return True

    def search(self, query, *, max_results, include_domains=None):
        self.calls += 1
        if self.fail:
            raise self.fail
        return SearchResponse(hits=[SearchHit(**h) for h in self.hits], cost_estimate_usd=Decimal("0.001"))


def _sale(i, price, area, condo):
    return {"url": f"https://portal.exemplo/anuncio/{i}?utm=x", "title": f"Apartamento 2 quartos à venda {i}",
            "snippet": f"Apartamento à venda em Cidade Fictícia/PR, {area} m², 2 quartos, 1 vaga. R$ {price}. Condomínio R$ {condo}.",
            "published": "2026-10-01"}


SALES = [_sale(1, "250.000", "50", "400"), _sale(2, "260.000", "52", "420"), _sale(3, "255.000", "51", "410"), _sale(4, "248.000", "50", "405")]
RENTS = [{"url": f"https://portal.exemplo/aluguel/{i}", "title": "Apartamento para alugar",
          "snippet": f"Aluguel de apartamento em Cidade Fictícia, 50 m², 2 quartos. R$ {v} /mês. Condomínio R$ 400."}
         for i, v in enumerate(("1.300", "1.350", "1.400"), 1)]


# ------------------------------------------------------------------ extração

def test_extracao_de_anuncio_de_venda_separa_condominio_do_preco():
    row = extract.extract_listing(SALES[0], "VENDA")
    assert row["utilizavel"] and row["valor"] == Decimal("250000") and row["area_m2"] == Decimal("50")
    assert row["quartos"] == 2 and row["vagas"] == 1 and row["condominio"] == Decimal("400") and row["confianca"] == "MEDIA"
    assert row["url_normalizada"] == "https://portal.exemplo/anuncio/1" and row["fonte"] == "portal.exemplo"


def test_extracao_de_aluguel_mil_e_pagina_de_listagem():
    rent = extract.extract_listing(RENTS[0], "ALUGUEL")
    assert rent["utilizavel"] and rent["valor"] == Decimal("1300")
    mil = extract.extract_listing({"url": "https://x.exemplo/a", "title": "Casa à venda", "snippet": "Casa à venda por R$ 320 mil, 90 m²"}, "VENDA")
    assert mil["valor"] == Decimal("320000")
    page = extract.extract_listing({"url": "https://x.exemplo/l", "title": "350 imóveis à venda em Cidade Fictícia",
                                    "snippet": "R$ 200.000 · R$ 310.000 · R$ 180.000"}, "VENDA")
    assert page["pagina_lista"] and not page["utilizavel"] and page["valor"] is None


def test_numero_com_espaco_do_trecho_de_pesquisa_e_lido_corretamente():
    # formato real observado na validação do imóvel 7 ("R$ 1. 800, 00", "45, 50 m²")
    row = extract.extract_listing({"url": "https://x.exemplo/r", "title": "Apartamento para alugar",
                                   "snippet": "Aluguel mensal de R$ 1. 800, 00, 45, 50 m², 2 quartos, sem taxa de condomínio."}, "ALUGUEL")
    assert extract._SPACED_DECIMAL.sub(r"\1,\2", "R$ 1.800,00, 45 quartos") == "R$ 1.800,00, 45 quartos"
    assert row["valor"] == Decimal("1800.00") and row["area_m2"] == Decimal("45.50") and row["utilizavel"]


def test_texto_sem_preco_nao_inventa_valor():
    row = extract.extract_listing({"url": "https://x.exemplo/b", "title": "Apartamento", "snippet": "Ótima localização, 2 quartos."}, "VENDA")
    assert row["valor"] is None and not row["utilizavel"] and row["confianca"] == "INSUFICIENTE"
    assert any("Preço não encontrado" in m for m in row["motivos"])


def test_deduplicacao_por_url_e_por_preco_area():
    rows = [extract.extract_listing(h, "VENDA") for h in (SALES[0], {**SALES[0], "url": "https://www.portal.exemplo/anuncio/1/"},
                                                           {**SALES[0], "url": "https://outro.exemplo/z"})]
    extract.dedupe(rows)
    assert rows[0]["utilizavel"] and rows[1]["duplicata_de"] == 0 and rows[2]["duplicata_de"] == 0


# ------------------------------------------------------------------ provedores (HTTP simulado)

def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_tavily_monta_requisicao_e_normaliza_resultado():
    seen = {}

    def handler(request):
        seen["auth"], seen["body"] = request.headers.get("authorization"), request.content
        return httpx.Response(200, json={"results": [{"url": "https://a.exemplo", "title": "T", "content": "C", "score": 0.9}]})
    resp = TavilyProvider(api_key="k-teste", client=_client(handler)).search("q", max_results=3, include_domains=["gov.br"])
    assert seen["auth"] == "Bearer k-teste" and b'"include_domains"' in seen["body"]
    assert resp.hits[0].url == "https://a.exemplo" and resp.hits[0].snippet == "C"


def test_brave_normaliza_e_classifica_erros():
    ok = BraveProvider(api_key="k", client=_client(lambda r: httpx.Response(200, json={"web": {"results": [
        {"url": "https://b.exemplo", "title": "B", "description": "D", "page_age": "2026-10-02"}]}})))
    assert ok.search("q", max_results=5).hits[0].published == "2026-10-02"
    with pytest.raises(SearchUnavailable):
        BraveProvider(api_key="k", client=_client(lambda r: httpx.Response(503))).search("q", max_results=5)
    with pytest.raises(SearchError):
        BraveProvider(api_key="k", client=_client(lambda r: httpx.Response(401))).search("q", max_results=5)
    assert not BraveProvider(api_key="").configured and not TavilyProvider(api_key="").configured


# ------------------------------------------------------------------ serviço: cache, retry, fallback, não configurado

def test_sem_provedor_registra_nao_configurado_e_nao_simula(db):
    row = service.search(db, kind="VENDA", query="apartamento", chain=[])
    assert row.status == "NAO_CONFIGURADO" and row.results == [] and row.provider == "nenhum"


def test_cache_evita_nova_chamada(db):
    fake = FakeProvider(hits=[SALES[0]])
    first = service.search(db, kind="VENDA", query="Apartamento  X", chain=[fake])
    second = service.search(db, kind="VENDA", query="apartamento x", chain=[fake])
    assert first.status == "SUCESSO" and second.id == first.id and fake.calls == 1
    expired = service.search(db, kind="VENDA", query="apartamento x", chain=[fake], now=datetime.utcnow() + timedelta(hours=settings.search_cache_hours + 1))
    assert expired.id != first.id and fake.calls == 2


def test_fallback_e_retry(db, monkeypatch):
    monkeypatch.setattr(settings, "search_max_retries", 1)
    down = FakeProvider("principal", fail=SearchUnavailable("timeout"))
    alt = FakeProvider("alternativo", hits=[SALES[1]])
    row = service.search(db, kind="VENDA", query="q fallback", chain=[down, alt])
    assert row.status == "SUCESSO" and row.provider == "alternativo" and down.calls == 2 and row.attempts == 3 and "timeout" in row.error
    bad = service.search(db, kind="VENDA", query="q erro", chain=[FakeProvider("x", fail=SearchError("401"))])
    assert bad.status == "ERRO" and bad.expires_at is None


def test_status_sem_chave_explica_configuracao(monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", None)
    monkeypatch.setattr(settings, "brave_search_api_key", None)
    st = service.status()
    assert st["status"] == "NAO_CONFIGURADO" and "TAVILY_API_KEY" in st["texto"]
    assert {p["variavel"] for p in st["provedores"]} == {"TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY"}


# ------------------------------------------------------------------ pesquisa automática do imóvel → mercado, condomínio, Financeiro

def _searched_prop(db):
    prop = _prop(db)
    prop.title = "Apartamento no Residencial Jardim Fictício"
    _leilao(db, prop)
    db.flush()
    fake = FakeProvider(hits=SALES + RENTS + [{"url": "https://prefeitura.exemplo.gov.br/iptu", "title": "Consulta IPTU", "snippet": "Débitos de IPTU"}])
    out = market_research.run(db, prop, chain=[fake])
    db.flush(); db.expire(prop)
    return prop, out, fake


def test_pesquisa_grava_comparaveis_com_fonte_e_data_e_e_idempotente(db):
    prop, out, fake = _searched_prop(db)
    assert out["status"] == "SUCESSO"
    assert market_research.building_name(prop) == "Residencial Jardim Fictício"
    comps = list(prop.comparables)
    vendas = [c for c in comps if c.kind == "VENDA"]
    assert len(vendas) == 4 and all(c.price_type == "ANUNCIADO" and c.collected_at and c.source.startswith("Pesquisa automática") for c in vendas)
    assert all(c.url.startswith("https://portal.exemplo/") for c in vendas)
    assert out["portais_iptu"] and out["portais_iptu"][0]["dominio"].endswith("gov.br")
    again = market_research.run(db, prop, chain=[fake])
    db.flush(); db.expire(prop)
    assert again["comparaveis_criados"] == [] and len(prop.comparables) == len(comps)     # mesma URL não duplica


def test_comparaveis_pesquisados_alimentam_mercado_condominio_e_resumo_sem_divergir(db):
    prop, _, _ = _searched_prop(db)
    intel = market_intelligence(db, prop)
    assert intel["venda"]["quantidade_usada"] >= 3 and intel["valores"]["valor_mercado_estimado"] is not None
    assert intel["carregamento_mensal"]["valor"] is not None                               # 3+ condomínios → Financeiro
    s = summary(db, prop)
    base = next(c for c in intel["cenarios"] if c["cenario"] == "BASE")
    assert s["numeros"]["valor_venda"]["valor"] == base["valor_venda"]
    assert s["condominio"]["taxa_mensal"]["valor"] == intel["carregamento_mensal"]["valor"]
    assert s["condominio"]["referencias"]["pesquisa_automatica"] >= 3
    assert s["mercado"]["venda"]["origens"]["pesquisa_automatica"] >= 3
    assert s["mercado"]["venda"]["qualidade"]["nivel"] in ("BAIXA", "MEDIA")              # anúncio ≠ transação
    assert [c["cenario"] for c in s["cenarios"]] == ["Conservador", "Provável", "Otimista"]
    assert s["recomendacao"]["codigo"] != "FAVORAVEL"                                       # IPTU e documentos ainda faltam


def test_pesquisa_sem_provedor_nao_grava_nada(db, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", None)
    monkeypatch.setattr(settings, "brave_search_api_key", None)
    prop = _prop(db)
    out = market_research.run(db, prop)
    assert out["status"] == "NAO_CONFIGURADO" and out["comparaveis_criados"] == [] and "TAVILY_API_KEY" in out["texto"]
    assert market_research.run_if_configured(db, prop) is None


# ------------------------------------------------------------------ checklist por prioridade

def _res(key, state, applicable=True):
    return NS(item=NS(canonical_key=key, question=f"{key}?"), state=state, applicable=applicable, answer="", resolution_origin=None, evidences=[])


def test_checklist_ordena_bloqueadores_abertos_primeiro():
    out = prioritized([_res("VAGA_MATRICULA", "PENDENTE"), _res("TERCEIRO_OCUPANTE", "ATENCAO"), _res("EDITAL_LIDO", "PENDENTE"),
                       _res("CONSOLIDACAO_REGISTRADA", "CONFIRMADO")])
    keys = [i["chave"] for i in out["itens"]]
    assert keys == ["EDITAL_LIDO", "TERCEIRO_OCUPANTE", "VAGA_MATRICULA", "CONSOLIDACAO_REGISTRADA"]
    first = out["itens"][0]
    assert first["prioridade"] == "P0" and first["proxima_acao"] and first["responsavel"] and first["explicacao"]
    assert out["abertos_por_prioridade"] == {"P0": 1, "P1": 1, "P2": 0, "P3": 1} and out["bloqueadores_abertos"] == ["Edital lido por completo"]
    assert out["itens"][-1]["proxima_acao"] is None                                        # resolvido não pede ação


# ------------------------------------------------------------------ documentos

def test_situacao_documental_aponta_obrigatorios_e_incompletos():
    docs = [NS(id=1, name="matricula.pdf", document_type="MATRICULA", status="RECEBIDO",
               versions=[NS(id=10, version=1, status="INDEXADO", extraction_metadata={"pages": 3})]),
            NS(id=2, name="fotos.pdf", document_type="OUTRO", status="RECEBIDO", versions=[NS(id=20, version=1, status="OCR_FALHOU", extraction_metadata={})])]
    evs = [NS(document_version_id=10, page=2, confidence="ALTA"), NS(document_version_id=10, page=3, confidence="MEDIA")]
    out = summarize(docs, evidences=evs, iptu_consulted=True)
    assert out["contagem"] == {"recebidos": 2, "analisados": 1, "incompletos": 1, "em_processamento": 0, "evidencias": 2}
    assert out["obrigatorios_faltando"] == ["Edital ou condições da venda"]
    by = {e["chave"]: e for e in out["esperados"]}
    assert by["MATRICULA"]["situacao"] == "ANALISADO" and by["IPTU"]["situacao"] == "ATENDIDO_POR_CONSULTA" and by["LAUDO"]["situacao"] == "INCOMPLETO"
    assert out["documentos"][0]["paginas_citadas"] == [2, 3] and out["documentos"][1]["pendencias"]


# ------------------------------------------------------------------ matrícula: pessoas

def test_pessoas_da_matricula_com_papeis_e_quem_perdeu_o_imovel():
    timeline = {"eventos": [{"ato": "R-2", "tipo": "COMPRA_VENDA", "construtora": "CONSTRUTORA FICTÍCIA LTDA", "data": "2015-01-10"},
                            {"ato": "R-3", "tipo": "ALIENACAO_FIDUCIARIA"}, {"ato": "Av-5", "tipo": "CONSOLIDACAO"}],
                "titularidade": {"partes": [
                    {"nome": "FULANO FICTÍCIO", "papel": "Adquirente (compra e venda)", "ato": "R-2", "status": "HISTORICO", "tipo_pessoa": "FISICA"},
                    {"nome": "FULANO FICTÍCIO", "papel": "Devedor(a) fiduciante", "ato": "R-3", "status": "HISTORICO", "tipo_pessoa": "FISICA"},
                    {"nome": "BANCO FICTÍCIO S.A.", "papel": "Proprietário(a) após a consolidação (credor fiduciário)", "ato": "Av-5", "status": "ATUAL",
                     "tipo_pessoa": "JURIDICA"}]}}
    rows = people(timeline)
    assert rows[0]["nome"] == "BANCO FICTÍCIO S.A." and rows[0]["atual"]
    fulano = next(r for r in rows if r["nome"] == "FULANO FICTÍCIO")
    assert fulano["perdeu_o_imovel"] and fulano["atos"] == ["R-2", "R-3"] and len(fulano["papeis"]) == 2
    assert any(r["papeis"] == ["Construtora / incorporadora"] for r in rows)
    # rótulo genérico lido como nome não vira pessoa; nome truncado da construtora se junta ao nome completo
    timeline["eventos"] += [{"ato": "Av-6", "tipo": "OUTRO", "construtora": "INCORPORADORA/CONSTRUTORA"},
                            {"ato": "Av-7", "tipo": "OUTRO", "construtora": "FICTÍCIA LTDA"}]
    names = [r["nome"] for r in people(timeline)]
    assert "INCORPORADORA/CONSTRUTORA" not in names and "FICTÍCIA LTDA" not in names


# ------------------------------------------------------------------ API

def test_api_pesquisa_checklist_e_documentos(api, monkeypatch):
    monkeypatch.setattr(settings, "tavily_api_key", None)
    monkeypatch.setattr(settings, "brave_search_api_key", None)
    client, db = api
    prop = _prop(db)
    _leilao(db, prop)
    db.flush()
    assert client.get("/api/pesquisa/provedores").json()["status"] == "NAO_CONFIGURADO"
    run = client.post(f"/api/imoveis/{prop.id}/pesquisa-automatica", json={"tipos": ["VENDA"]})
    assert run.status_code == 200 and run.json()["status"] == "NAO_CONFIGURADO"
    hist = client.get(f"/api/imoveis/{prop.id}/pesquisa-automatica").json()
    assert hist["provedores"]["ativo"] is False
    assert "itens" in client.get(f"/api/imoveis/{prop.id}/checklist-prioritario").json()
    sit = client.get(f"/api/imoveis/{prop.id}/documentos/situacao").json()
    assert "Matrícula atualizada" in sit["obrigatorios_faltando"]
    assert client.get(f"/api/imoveis/{prop.id}/documentos").json()["situacao_documental"]["contagem"]["recebidos"] == 0
    body = client.get(f"/api/imoveis/{prop.id}/resumo-investimento").json()
    assert body["mercado"]["pesquisa"]["ativo"] is False and body["documentos"]["obrigatorios_faltando"]
    assert any("documento obrigatório" in p for p in body["pendencias"])
