from backend.app import models
from backend.app.ai.agents import AgentResult
from backend.app.ai.gateway import LLMGateway, LLMCall, ProviderResponse
from backend.app.rag.service import RAGResult


class Provider:
    def structured_chat(self, schema, messages, **kwargs):
        return ProviderResponse(content=None, input_tokens=10, output_tokens=5, request_id="graph-run")

    def chat(self, *args, **kwargs):
        return ProviderResponse(content="")

    def embed(self, texts):
        return []


class Db:
    def __init__(self):
        self.property = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")

    def get(self, model, identifier):
        if model is models.Property and identifier == 1:
            return self.property
        return None


def fake_result(agent, status="CONCLUIDO"):
    call = LLMCall(provider="fake", model="modelo", status=status, request_id=f"{agent}-run")
    return AgentResult(agent=agent, facts=[], evidence_ids=[], pending=[] if status == "CONCLUIDO" else [f"falha {agent}"], llm_used=status == "CONCLUIDO", model="modelo", llm_call=call, retrieved_chunk_ids=[7])


def test_grafo_tem_topologia_explicita_e_preserva_estado(monkeypatch):
    from backend.app.ai import graph as graph_module

    calls = []

    class FakeRag:
        def __init__(self, db):
            pass

        def retrieve_context(self, query, property_id=None, filters=None):
            calls.append(("RETRIEVE_RAG", query, property_id, filters))
            return RAGResult("contexto", [{"chunk_id": 7}], [7], 1, True, False, True)

    class FakeSupervisor:
        def __init__(self, db, gateway):
            pass

        def run(self, property_id, domains, context, retrieved_chunk_ids):
            calls.append(("RUN_AGENTS", property_id, domains, context, retrieved_chunk_ids))
            return [fake_result(domain) for domain in domains]

    monkeypatch.setattr(graph_module, "RAGService", FakeRag)
    monkeypatch.setattr("backend.app.ai.agents.Supervisor", FakeSupervisor)
    compiled = graph_module.build_analysis_graph(Db(), LLMGateway(Provider(), "fake", "modelo"))
    nodes = set(compiled.get_graph().nodes)
    assert {"LOAD_CONTEXT", "RETRIEVE_RAG", "RUN_AGENTS", "CONSOLIDATE"}.issubset(nodes)
    result = compiled.invoke({"property_id": 1, "analysis_id": 10, "domains": ["mercado"], "query": "mercado"})
    assert result["context"] == "contexto"
    assert result["retrieved_chunk_ids"] == [7]
    assert [call[0] for call in calls] == ["RETRIEVE_RAG", "RUN_AGENTS"]
    assert calls[0][2] == 1
    assert calls[1][2] == ["mercado"]
    assert {"agent_results", "evidence_ids", "retrieved_chunk_ids", "llm_runs", "pending", "interpretations", "errors", "llm_used", "model"} <= set(result["consolidated"])
    assert "verdict" not in result
    assert "risk_candidates" not in result


def test_grafo_executa_somente_dominios_solicitados(monkeypatch):
    from backend.app.ai import graph as graph_module

    class FakeRag:
        def __init__(self, db):
            pass
        def retrieve_context(self, *args, **kwargs):
            return RAGResult("ctx", [], [], 0, False, False, True)

    executed = []

    class FakeSupervisor:
        def __init__(self, db, gateway):
            pass
        def run(self, property_id, domains, context, retrieved_chunk_ids):
            executed.extend(domains)
            return [fake_result(domain) for domain in domains]

    monkeypatch.setattr(graph_module, "RAGService", FakeRag)
    monkeypatch.setattr("backend.app.ai.agents.Supervisor", FakeSupervisor)
    graph_module.build_analysis_graph(Db(), LLMGateway(Provider(), "fake", "modelo")).invoke({"property_id": 1, "domains": ["juridico", "mercado"], "query": "q"})
    assert executed == ["juridico", "mercado"]


def test_grafo_preserva_falha_de_agente_e_continua(monkeypatch):
    from backend.app.ai import graph as graph_module

    class FakeRag:
        def __init__(self, db):
            pass
        def retrieve_context(self, *args, **kwargs):
            return RAGResult("ctx", [], [], 0, False, False, True)

    class FakeSupervisor:
        def __init__(self, db, gateway):
            pass
        def run(self, property_id, domains, context, retrieved_chunk_ids):
            return [fake_result("juridico", "ERRO"), fake_result("mercado")]

    monkeypatch.setattr(graph_module, "RAGService", FakeRag)
    monkeypatch.setattr("backend.app.ai.agents.Supervisor", FakeSupervisor)
    result = graph_module.build_analysis_graph(Db(), LLMGateway(Provider(), "fake", "modelo")).invoke({"property_id": 1, "domains": ["juridico", "mercado"], "query": "q"})
    assert [item["agent"] for item in result["agent_results"]] == ["juridico", "mercado"]
    assert any("falha juridico" in item for item in result["pending"])
    assert result["consolidated"]["agent_results"]


def test_orquestrador_retorna_retrieval_do_grafo(monkeypatch):
    from backend.app.ai.orchestrator import AnalysisOrchestrator

    invoked = {}

    class FakeGraph:
        def invoke(self, state):
            invoked.update(state)
            return {"agent_results": [], "llm_runs": [], "evidence_ids": [], "retrieved_chunk_ids": [4], "retrieval": {"count": 1}}

    monkeypatch.setattr("backend.app.ai.orchestrator.build_analysis_graph", lambda db, gateway_override=None: FakeGraph())
    result = AnalysisOrchestrator(Db()).run(1, ["financeiro"], "custos", analysis_id=12)
    assert invoked == {"property_id": 1, "analysis_id": 12, "domains": ["financeiro"], "query": "custos"}
    assert result["retrieved_chunk_ids"] == [4]


def test_graph_nao_utiliza_verdict_ou_risk_no_consolidate():
    import inspect
    from backend.app.ai import graph

    source = inspect.getsource(graph)
    assert "VerdictResponse" not in source
    assert "risk_candidates" not in source
    assert "\"verdict\"" not in source
    assert "structured_chat" not in source
