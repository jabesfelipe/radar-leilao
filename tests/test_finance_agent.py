import json
from decimal import Decimal

import pytest
from fastapi import HTTPException

from backend.app import models
from backend.app.ai.agents import FinancialAgent
from backend.app.ai.contracts import AgentResponse, Finding
from backend.app.ai.gateway import LLMGateway, ProviderResponse


class Provider:
    def __init__(self, content):
        self.content = content
        self.messages = []

    def structured_chat(self, schema, messages, **kwargs):
        self.messages = messages
        return ProviderResponse(content=self.content, input_tokens=30, output_tokens=12, request_id="finance-run")

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


def deterministic_result():
    return {
        "custo_total": 250000.0,
        "valor_aquisicao": 200000.0,
        "desconto_percentual": 0.2,
        "margem_percentual": 0.375,
        "yield_mensal": 0.01,
        "yield_anual": 0.12,
        "valor_mercado": 320000.0,
        "aluguel_mensal": 2200.0,
        "preco_maximo": None,
        "pendencias": ["Fórmula canônica de preço máximo não está definida"],
    }


def test_financial_agent_interpreta_sem_alterar_resultado_deterministico():
    deterministic = deterministic_result()
    response = AgentResponse(findings=[Finding(kind="interpretacao", statement="O custo total informado é R$ 270.000", confidence="ALTA")])
    provider = Provider(response)
    result = FinancialAgent(Db(), LLMGateway(provider, "fake", "finance-model")).run(1, "", [], deterministic)
    payload = json.loads(provider.messages[1]["content"])
    assert result.agent == "financeiro"
    assert result.facts[0]["kind"] == "interpretacao"
    assert payload["financeiro_deterministico"]["custo_total"] == 250000.0
    assert deterministic["custo_total"] == 250000.0
    assert result.llm_call.total_tokens == 42


def test_financial_agent_prompt_proibe_recalculo_e_veredito():
    provider = Provider(AgentResponse(findings=[Finding(kind="ausencia", statement="Não há dados suficientes", confidence="BAIXA")]))
    FinancialAgent(Db(), LLMGateway(provider, "fake", "modelo")).run(1, "contexto financeiro", [9], deterministic_result())
    prompt = provider.messages[0]["content"].lower()
    for expected in ("não recalcule", "não altere", "não invente custos", "preço máximo", "não crie score", "veredito", "chunk_ids"):
        assert expected in prompt


def test_financial_agent_sem_dados_registra_ausencia():
    result = FinancialAgent(Db(), LLMGateway(Provider(AgentResponse(findings=[Finding(kind="ausencia", statement="Aluguel mensal ausente")])), "fake", "modelo")).run(1, "", [], {"custo_total": 0, "aluguel_mensal": None, "pendencias": ["aluguel ausente"]})
    assert result.facts[0]["kind"] == "ausencia"


def test_financial_agent_sem_gateway_retorna_erro_controlado():
    result = FinancialAgent(Db(), None).run(1, "", [], deterministic_result())
    assert result.llm_call.status == "SEM_CHAVE"
    assert result.llm_used is False
    assert result.facts[0]["kind"] == "ausencia"


def test_financial_agent_resposta_invalida_retorna_erro():
    result = FinancialAgent(Db(), LLMGateway(Provider({"findings": [{"statement": {"invalido": True}}]}), "fake", "modelo")).run(1, "", [], deterministic_result())
    assert result.llm_used is False
    assert result.llm_call.status == "ERRO"


def test_endpoint_financeiro_isola_rag_preserva_engine_e_analysis(monkeypatch):
    from backend.app.main import run_financial_agent

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    analysis = models.Analysis(id=10, property_id=1, version=3, scope="Financeiro", agents_executed=[])
    deterministic = deterministic_result()

    class FakeDb:
        def __init__(self):
            self.added = []

        def get(self, model, identifier):
            if model is models.Property:
                return prop
            if model is models.Analysis:
                return analysis
            return None

        def scalar(self, statement):
            return None

        def add(self, item):
            self.added.append(item)
            if isinstance(item, models.FinancialAnalysis):
                item.id = 70

        def flush(self):
            pass

        def commit(self):
            pass

    class Retrieval:
        context = "documento financeiro"
        chunk_ids = [8]

    class FakeRag:
        def __init__(self, db):
            pass

        def retrieve_context(self, *args, **kwargs):
            assert kwargs["filters"].property_id == 1
            assert kwargs["filters"].category == "financeiro"
            return Retrieval()

    response = AgentResponse(findings=[Finding(kind="fato", statement="Custo total calculado pelo motor", chunk_ids=[8], page=2, section="Custos", evidence_excerpt="custo total")])
    run = models.LLMRun(id=90)
    monkeypatch.setattr("backend.app.main.build_finance", lambda prop: deterministic)
    monkeypatch.setattr("backend.app.main.RAGService", FakeRag)
    monkeypatch.setattr("backend.app.main.build_gateway", lambda: LLMGateway(Provider(response), "fake", "modelo"))
    monkeypatch.setattr("backend.app.main.persist_llm_runs", lambda *args: [run])
    monkeypatch.setattr("backend.app.main.persist_agent_findings", lambda *args: [31])
    monkeypatch.setattr("backend.app.main.latest_execution", lambda prop: None)
    result = run_financial_agent(1, 10, FakeDb())
    assert result["status"] == "CONCLUIDO"
    assert result["agente"] == "financeiro"
    assert result["financeiro"] == deterministic
    assert result["financial_analysis_id"] == 70
    assert result["evidence_ids"] == [31]
    assert analysis.agents_executed == ["financeiro"]


def test_endpoint_financeiro_rejeita_analysis_de_outro_imovel():
    from backend.app.main import run_financial_agent

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
        run_financial_agent(1, 10, FakeDb())
    assert error.value.status_code == 404
