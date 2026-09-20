import json
from decimal import Decimal

import pytest
from fastapi import HTTPException

from backend.app import models
from backend.app.ai.agents import MarketAgent
from backend.app.ai.contracts import AgentResponse, Finding
from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app.market import calculate_market


class Provider:
    def __init__(self, content):
        self.content = content
        self.messages = []

    def structured_chat(self, schema, messages, **kwargs):
        self.messages = messages
        return ProviderResponse(content=self.content, input_tokens=24, output_tokens=9, request_id="market-run")

    def chat(self, *args, **kwargs):
        return ProviderResponse(content="")

    def embed(self, texts):
        return []


class Db:
    def __init__(self, prop=None):
        self.prop = prop

    def get(self, model, identifier):
        if model is models.Property:
            return self.prop
        return None


def deterministic_market():
    return {
        "venda": {"quantidade": 2, "preco_medio": 200000.0, "preco_mediano": 200000.0, "preco_m2_medio": 2000.0, "preco_m2_mediano": 2000.0, "quantidade_com_area": 2},
        "aluguel": {"quantidade": 2, "aluguel_medio": 2000.0, "aluguel_mediano": 2000.0, "aluguel_m2_medio": 20.0, "aluguel_m2_mediano": 20.0, "quantidade_com_area": 2},
    }


def test_market_agent_interpreta_comparaveis_sem_alterar_engine():
    deterministic = deterministic_market()
    response = AgentResponse(findings=[Finding(kind="interpretacao", statement="O preço médio é 999000", confidence="ALTA")])
    provider = Provider(response)
    result = MarketAgent(Db(), LLMGateway(provider, "fake", "market-model")).run(1, "", [], deterministic)
    payload = json.loads(provider.messages[1]["content"])
    assert result.agent == "mercado"
    assert result.facts[0]["kind"] == "interpretacao"
    assert payload["mercado_deterministico"]["venda"]["preco_medio"] == 200000.0
    assert deterministic["venda"]["preco_medio"] == 200000.0
    assert result.llm_call.total_tokens == 33


def test_market_agent_prompt_proibe_recalculo_valuation_e_liquidez_inventada():
    provider = Provider(AgentResponse(findings=[Finding(kind="ausencia", statement="Comparáveis insuficientes", confidence="BAIXA")]))
    MarketAgent(Db(), LLMGateway(provider, "fake", "modelo")).run(1, "contexto de mercado", [7], deterministic_market())
    prompt = provider.messages[0]["content"].lower()
    for expected in ("não recalcule", "não altere", "não invente comparáveis", "valuation", "score de liquidez", "veredito", "chunk_ids"):
        assert expected in prompt


def test_market_agent_sem_comparaveis_registra_ausencia():
    result = MarketAgent(Db(), LLMGateway(Provider(AgentResponse(findings=[Finding(kind="ausencia", statement="Não há comparáveis suficientes")])), "fake", "modelo")).run(1, "", [], calculate_market([]))
    assert result.facts[0]["kind"] == "ausencia"


def test_market_agent_sem_gateway_retorna_erro_controlado():
    result = MarketAgent(Db(), None).run(1, "", [], deterministic_market())
    assert result.llm_call.status == "SEM_CHAVE"
    assert result.llm_used is False
    assert result.facts[0]["kind"] == "ausencia"


def test_market_agent_resposta_invalida_retorna_erro():
    result = MarketAgent(Db(), LLMGateway(Provider({"findings": [{"statement": {"invalido": True}}]}), "fake", "modelo")).run(1, "", [], deterministic_market())
    assert result.llm_used is False
    assert result.llm_call.status == "ERRO"


def test_endpoint_market_isola_rag_preserva_engine_e_analysis(monkeypatch):
    from backend.app.main import run_market_agent

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    prop.comparables = [models.MarketComparable(id=4, kind="VENDA", price=Decimal("200000"), area_m2=Decimal("100"))]
    analysis = models.Analysis(id=10, property_id=1, version=3, scope="Mercado", agents_executed=[])
    deterministic = calculate_market([{"kind": "VENDA", "price": Decimal("200000"), "rent": None, "area_m2": Decimal("100")}])

    class FakeDb:
        def __init__(self):
            self.added = []

        def get(self, model, identifier):
            if model is models.Property:
                return prop
            if model is models.Analysis:
                return analysis
            return None

        def add(self, item):
            self.added.append(item)

        def flush(self):
            pass

        def commit(self):
            pass

    class Retrieval:
        context = "documento de mercado"
        chunk_ids = [8]

    class FakeRag:
        def __init__(self, db):
            pass

        def retrieve_context(self, *args, **kwargs):
            assert kwargs["filters"].property_id == 1
            assert kwargs["filters"].category == "mercado"
            return Retrieval()

    response = AgentResponse(findings=[Finding(kind="fato", statement="Há um comparável cadastrado", chunk_ids=[8], page=2, section="Mercado", evidence_excerpt="comparável")])
    run = models.LLMRun(id=90)
    monkeypatch.setattr("backend.app.main.calculate_market", lambda comparables: deterministic)
    monkeypatch.setattr("backend.app.main.RAGService", FakeRag)
    monkeypatch.setattr("backend.app.main.build_gateway", lambda: LLMGateway(Provider(response), "fake", "modelo"))
    monkeypatch.setattr("backend.app.main.persist_llm_runs", lambda *args: [run])
    monkeypatch.setattr("backend.app.main.persist_agent_findings", lambda *args: [31])
    monkeypatch.setattr("backend.app.main.latest_execution", lambda prop: None)
    result = run_market_agent(1, 10, FakeDb())
    assert result["status"] == "CONCLUIDO"
    assert result["agente"] == "mercado"
    assert result["mercado"] == deterministic
    assert result["evidence_ids"] == [31]
    assert analysis.agents_executed == ["mercado"]


def test_endpoint_market_rejeita_analysis_de_outro_imovel():
    from backend.app.main import run_market_agent

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    other_analysis = models.Analysis(id=10, property_id=2, version=1)

    class FakeDb:
        def get(self, model, identifier):
            if model is models.Property:
                return prop
            if model is models.Analysis:
                return other_analysis
            return None

    with pytest.raises(HTTPException) as error:
        run_market_agent(1, 10, FakeDb())
    assert error.value.status_code == 404
