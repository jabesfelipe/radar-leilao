from decimal import Decimal

from backend.app.ai.agents import DocumentAgent, Supervisor
from backend.app.ai.contracts import AgentResponse
from backend.app.ai.costs import Pricing, calculate_cost
from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app import models
from backend.app.services import aggregate_llm_usage, persist_llm_runs


class FakeDb:
    def __init__(self, pricing=None):
        self.pricing = pricing
        self.added = []
    def get(self, model, identifier): return None
    def scalar(self, statement): return self.pricing
    def add(self, item): self.added.append(item)
    def flush(self): return None


class FakeProvider:
    def __init__(self, error=None, input_tokens=120, output_tokens=80):
        self.error = error
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = 0
    def structured_chat(self, schema, messages, **kwargs):
        self.calls += 1
        if self.error: raise self.error
        return ProviderResponse(content=AgentResponse(summary="ok", findings=[], pending=[]), input_tokens=self.input_tokens, output_tokens=self.output_tokens, request_id=f"req-{self.calls}")
    def chat(self, messages, **kwargs): return ProviderResponse(content="ok", input_tokens=self.input_tokens, output_tokens=self.output_tokens)
    def embed(self, texts): return [[0.0] * 3 for _ in texts]


def test_gateway_preserva_token_usage_e_duracao():
    provider = FakeProvider()
    call = LLMGateway(provider, "fake", "modelo-teste").structured_chat(AgentResponse, [])
    assert call.status == "CONCLUIDO"
    assert call.input_tokens == 120
    assert call.output_tokens == 80
    assert call.total_tokens == 200
    assert call.duration_ms is not None
    assert call.request_id == "req-1"


def test_calculo_de_custo_por_milhao_de_tokens():
    pricing = Pricing("fake", "modelo-teste", Decimal("2.00"), Decimal("4.00"))
    result = calculate_cost(500_000, 250_000, pricing)
    assert result["input_cost"] == Decimal("1.000000")
    assert result["output_cost"] == Decimal("1.000000")
    assert result["total_cost"] == Decimal("2.000000")


def test_erro_do_provider_e_rastreado_sem_segredo():
    call = LLMGateway(FakeProvider(error=RuntimeError("falha transitória")), "fake", "modelo-teste").structured_chat(AgentResponse, [])
    assert call.status == "ERRO"
    assert call.error_type == "RuntimeError"
    assert call.error_message == "falha transitória"
    assert call.input_tokens is None
    assert call.output_tokens is None


def test_agente_fake_retorna_chamada_rastreavel_sem_api_key():
    provider = FakeProvider()
    result = DocumentAgent(FakeDb(), LLMGateway(provider, "fake", "modelo-teste")).run(10, "contexto", [1, 2])
    assert result.llm_used is True
    assert result.llm_call is not None
    assert result.llm_call.total_tokens == 200
    assert result.retrieved_chunk_ids == [1, 2]


def test_multiplos_agentes_geram_chamadas_individuais():
    provider = FakeProvider()
    results = Supervisor(FakeDb(), LLMGateway(provider, "fake", "modelo-teste")).run(10, ["documental", "juridico"], "contexto", [3])
    assert len(results) == 2
    assert provider.calls == 2
    assert {result.agent for result in results} == {"documental", "juridico"}


def test_persistencia_associa_property_analysis_e_calcula_custo():
    pricing = models.LLMPricing(provider="fake", model="modelo-teste", input_price_per_1m=Decimal("2"), output_price_per_1m=Decimal("4"), active=True)
    db = FakeDb(pricing)
    call = LLMGateway(FakeProvider(), "fake", "modelo-teste").structured_chat(AgentResponse, [])
    run_data = dict(call.to_dict(), agent="documental", retrieved_chunk_ids=[4, 5])
    runs = persist_llm_runs(db, type("Property", (), {"id": 7})(), type("Analysis", (), {"id": 11})(), [run_data])
    assert len(runs) == 1
    run = runs[0]
    assert run.property_id == 7
    assert run.analysis_id == 11
    assert run.input_tokens == 120
    assert run.output_tokens == 80
    assert run.total_tokens == 200
    assert run.total_cost == Decimal("0.00056")
    assert run.retrieved_chunk_ids == [4, 5]


def test_agregacao_de_usage_por_analise_preserva_desconhecido():
    runs = [models.LLMRun(input_tokens=100, output_tokens=50, total_tokens=150, total_cost=Decimal("1.25"), status="CONCLUIDO"), models.LLMRun(input_tokens=None, output_tokens=None, total_tokens=None, total_cost=None, status="ERRO")]
    result = aggregate_llm_usage(runs)
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50
    assert result["total_tokens"] == 150
    assert result["total_cost"] == Decimal("1.25")
    assert result["runs"] == 2
    assert result["error_runs"] == 1


def test_pricing_ausente_mantem_custo_nulo():
    result = calculate_cost(100, 50, None)
    assert result == {"input_cost": None, "output_cost": None, "total_cost": None}


def test_erro_com_api_key_nunca_expoe_segredo():
    secret = "sk-projeto-secreto-123"
    call = LLMGateway(FakeProvider(error=RuntimeError(f"request failed api_key={secret} bearer {secret}")), "fake", "modelo-teste").structured_chat(AgentResponse, [])
    assert call.status == "ERRO"
    assert secret not in (call.error_message or "")
    assert "[REDACTED]" in (call.error_message or "")


def test_persistencia_registra_run_com_erro_sem_segredo():
    db = FakeDb()
    call = LLMGateway(FakeProvider(error=RuntimeError("falha sem segredo")), "fake", "modelo-teste").structured_chat(AgentResponse, [])
    run = persist_llm_runs(db, type("Property", (), {"id": 8})(), type("Analysis", (), {"id": 12})(), [dict(call.to_dict(), agent="supervisor", retrieved_chunk_ids=[9])])[0]
    assert run.status == "ERRO"
    assert run.property_id == 8
    assert run.analysis_id == 12
    assert run.error_message == "falha sem segredo"
    assert run.total_cost is None


def test_rag_nao_tenta_embedding_sem_api_key(monkeypatch):
    from backend.app.rag.service import RAGService
    class NoQueryDb:
        def query(self, *args, **kwargs): raise AssertionError("não deve consultar chunks para gerar embedding")
    from backend.app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr("backend.app.rag.service.HybridRetriever.search", lambda self, **kwargs: [])
    service = RAGService(object())
    result = service.retrieve_context("consulta", property_id=1)
    assert result.vector_search is False
    assert result.text_fallback is True


def test_document_embedding_nao_constroi_gateway_sem_api_key(monkeypatch):
    from backend.app.documents.embedding import embed_pending_chunks
    class NoQueryDb:
        def query(self, *args, **kwargs): raise AssertionError("não deve buscar chunks sem API key")
    from backend.app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    assert embed_pending_chunks(NoQueryDb(), 1) == 0
