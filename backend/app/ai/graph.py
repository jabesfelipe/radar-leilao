from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy.orm import Session

from .. import models
from ..logging_config import get_logger
from ..rag.retriever import RetrieverFilters
from ..rag.service import RAGService
from .gateway import LLMGateway, build_gateway
from ..consolidation import consolidate_agent_results

log = get_logger("langgraph")


class AnalysisState(TypedDict, total=False):
    property_id: int
    analysis_id: int | None
    domains: list[str]
    query: str
    context: str
    context_loaded: bool
    retrieved_chunk_ids: list[int]
    retrieval: dict[str, Any]
    agent_results: list[dict[str, Any]]
    llm_runs: list[dict[str, Any]]
    evidence_ids: list[int]
    pending: list[str]
    interpretations: list[str]
    errors: list[str]
    llm_used: bool
    model: str | None
    consolidated: dict[str, Any]


def _gateway_or_none() -> LLMGateway | None:
    try:
        return build_gateway()
    except (RuntimeError, ValueError):
        return None


def _rag_filter(domains: list[str]) -> RetrieverFilters:
    supported = {"documental", "juridico", "financeiro", "mercado", "checklist"}
    category = domains[0] if len(domains) == 1 and domains[0] in supported else None
    return RetrieverFilters(property_id=None, category=category)


def build_analysis_graph(db: Session, gateway_override: LLMGateway | None = None):
    from langgraph.graph import END, START, StateGraph
    from .agents import Supervisor

    gateway = gateway_override or _gateway_or_none()
    supervisor = Supervisor(db, gateway)
    graph = StateGraph(AnalysisState)

    def load_context(state: AnalysisState) -> dict[str, Any]:
        prop = db.get(models.Property, state["property_id"])
        return {"context_loaded": prop is not None, "context": state.get("context", "")}

    def retrieve_rag(state: AnalysisState) -> dict[str, Any]:
        property_id = state["property_id"]
        domains = state.get("domains", [])
        query = state.get("query") or "análise documental do imóvel"
        selected = _rag_filter(domains)
        filters = RetrieverFilters(property_id=property_id, category=selected.category)
        try:
            retrieval = RAGService(db).retrieve_context(query, property_id=property_id, filters=filters)
        except Exception as exc:
            message = f"Falha no RAG: {type(exc).__name__}: {str(exc)[:500]}"
            return {
                "context": "",
                "retrieved_chunk_ids": [],
                "retrieval": {"context_found": False, "count": 0, "vector_search": False, "text_fallback": True, "reason": message, "chunks": []},
                "errors": list(state.get("errors", [])) + [message],
                "pending": list(state.get("pending", [])) + ["Recuperação RAG indisponível"],
            }
        return {
            "context": retrieval.context,
            "retrieved_chunk_ids": retrieval.chunk_ids,
            "retrieval": {
                "context_found": retrieval.context_found,
                "count": retrieval.count,
                "vector_search": retrieval.vector_search,
                "text_fallback": retrieval.text_fallback,
                "reason": retrieval.reason,
                "chunks": retrieval.chunks,
            },
        }

    def run_agents(state: AnalysisState) -> dict[str, Any]:
        property_id = state["property_id"]
        domains = state.get("domains", [])
        analysis_id = state.get("analysis_id")
        log.info("langgraph agentes iniciados: property_id=%s analysis_id=%s dominios=%s chunks=%d llm=%s",
                 property_id, analysis_id, domains, len(state.get("retrieved_chunk_ids", [])), gateway is not None)
        results = supervisor.run(state["property_id"], state.get("domains", []), state.get("context", ""), state.get("retrieved_chunk_ids", []))
        for result in results:
            call = result.llm_call
            log.info("agente executado: agente=%s property_id=%s analysis_id=%s status=%s provider=%s modelo=%s evidencias=%d chunks=%d%s",
                     result.agent, property_id, analysis_id,
                     call.status if call else "SEM_CHAMADA",
                     call.provider if call else "-", call.model if call else "-",
                     len(result.evidence_ids), len(result.retrieved_chunk_ids),
                     f" erro={call.error_message}" if call and call.error_message else "")
        calls = [
            dict(result.llm_call.to_dict(), agent=result.agent, retrieved_chunk_ids=result.retrieved_chunk_ids)
            for result in results
            if result.llm_call
        ]
        errors = list(state.get("errors", [])) + [
            result.llm_call.error_message or "Falha na chamada"
            for result in results
            if result.llm_call and result.llm_call.status == "ERRO"
        ]
        return {
            "agent_results": [result.to_dict() for result in results],
            "llm_runs": calls,
            "evidence_ids": sorted(set(sum((result.evidence_ids for result in results), []))),
            "pending": list(state.get("pending", [])) + [item for result in results for item in result.pending],
            "interpretations": list(state.get("interpretations", [])) + [result.interpretation for result in results if result.interpretation],
            "errors": errors,
            "llm_used": any(result.llm_used for result in results),
            "model": gateway.model if gateway else None,
        }

    def consolidate(state: AnalysisState) -> dict[str, Any]:
        consolidated = consolidate_agent_results(
            property_id=state.get("property_id"),
            analysis_id=state.get("analysis_id"),
            domains=state.get("domains", []),
            agent_results=state.get("agent_results", []),
            evidence_ids=state.get("evidence_ids", []),
            retrieved_chunk_ids=state.get("retrieved_chunk_ids", []),
            pending=state.get("pending", []),
            interpretations=state.get("interpretations", []),
            errors=state.get("errors", []),
            llm_used=state.get("llm_used", False),
            model=state.get("model"),
            llm_runs=state.get("llm_runs", []),
        )
        return {"consolidated": consolidated.to_dict()}

    graph.add_node("LOAD_CONTEXT", load_context)
    graph.add_node("RETRIEVE_RAG", retrieve_rag)
    graph.add_node("RUN_AGENTS", run_agents)
    graph.add_node("CONSOLIDATE", consolidate)
    graph.add_edge(START, "LOAD_CONTEXT")
    graph.add_edge("LOAD_CONTEXT", "RETRIEVE_RAG")
    graph.add_edge("RETRIEVE_RAG", "RUN_AGENTS")
    graph.add_edge("RUN_AGENTS", "CONSOLIDATE")
    graph.add_edge("CONSOLIDATE", END)
    return graph.compile()
