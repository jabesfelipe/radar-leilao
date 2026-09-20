from __future__ import annotations

import json
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from .. import models
from ..rag.retriever import RetrieverFilters
from ..rag.service import RAGService
from .contracts import VerdictResponse
from .gateway import LLMCall, LLMGateway, build_gateway


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
    verdict: dict[str, Any]
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
        property_id = state["property_id"]
        prop = db.get(models.Property, property_id)
        return {"context_loaded": prop is not None, "context": state.get("context", "")}

    def retrieve_rag(state: AnalysisState) -> dict[str, Any]:
        property_id = state["property_id"]
        domains = state.get("domains", [])
        query = state.get("query") or "análise documental do imóvel"
        filters = _rag_filter(domains)
        if filters.property_id is None:
            filters = RetrieverFilters(property_id=property_id, category=filters.category)
        try:
            retrieval = RAGService(db).retrieve_context(query, property_id=property_id, filters=filters)
        except Exception as exc:
            message = f"Falha no RAG: {type(exc).__name__}: {str(exc)[:500]}"
            return {"context": "", "retrieved_chunk_ids": [], "retrieval": {"context_found": False, "count": 0, "vector_search": False, "text_fallback": True, "reason": message, "chunks": []}, "errors": state.get("errors", []) + [message], "pending": state.get("pending", []) + ["Recuperação RAG indisponível"]}
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
        results = supervisor.run(
            state["property_id"],
            state.get("domains", []),
            state.get("context", ""),
            state.get("retrieved_chunk_ids", []),
        )
        calls = [
            dict(result.llm_call.to_dict(), agent=result.agent, retrieved_chunk_ids=result.retrieved_chunk_ids)
            for result in results
            if result.llm_call
        ]
        agent_results = [result.to_dict() for result in results]
        pending = [item for result in results for item in result.pending]
        interpretations = [result.interpretation for result in results if result.interpretation]
        errors = [result.llm_call.error_message or "Falha na chamada" for result in results if result.llm_call and result.llm_call.status == "ERRO"]
        return {
            "agent_results": agent_results,
            "llm_runs": calls,
            "evidence_ids": sorted(set(sum((result.evidence_ids for result in results), []))),
            "pending": pending,
            "interpretations": interpretations,
            "errors": errors,
            "llm_used": any(result.llm_used for result in results),
            "model": gateway.model if gateway else None,
        }

    def consolidate(state: AnalysisState) -> dict[str, Any]:
        results = state.get("agent_results", [])
        llm_runs = list(state.get("llm_runs", []))
        pending = list(state.get("pending", []))
        interpretations = list(state.get("interpretations", []))
        if not gateway:
            call = LLMCall.unavailable("openai", "desconhecido", "LLM não configurada; consolidação não executada")
            verdict = {
                "summary": "Análise determinística concluída; interpretação LLM pendente de OPENAI_API_KEY",
                "known": [],
                "unknown": ["A consolidação interpretativa ainda não foi executada"],
                "pending": ["Configurar OPENAI_API_KEY"],
                "risk_candidates": [],
            }
            llm_runs.append(dict(call.to_dict(), agent="supervisor", retrieved_chunk_ids=state.get("retrieved_chunk_ids", [])))
            pending.extend(verdict["pending"])
            return {
                "verdict": verdict,
                "llm_runs": llm_runs,
                "pending": pending,
                "consolidated": {"agent_results": results, "evidence_ids": state.get("evidence_ids", []), "pending": pending, "interpretations": interpretations},
                "model": call.model,
            }
        messages = [
            {"role": "system", "content": "Você é o Supervisor do Radar Leilão. Sintetize resultados de agentes fundamentados em RAG. Não invente fatos. Separe conhecido, desconhecido, pendências e riscos candidatos."},
            {"role": "user", "content": json.dumps({"resultados_agentes": results, "evidencias_chunk_ids": state.get("evidence_ids", [])}, ensure_ascii=False, default=str)},
        ]
        call = gateway.structured_chat(VerdictResponse, messages)
        llm_runs.append(dict(call.to_dict(), agent="supervisor", retrieved_chunk_ids=state.get("retrieved_chunk_ids", [])))
        if call.status != "CONCLUIDO":
            verdict = {"summary": "A consolidação falhou; resultados parciais foram preservados.", "known": [], "unknown": [], "pending": [call.error_message or "Erro desconhecido na consolidação"], "risk_candidates": []}
            pending.extend(verdict["pending"])
        else:
            try:
                response = call.content if isinstance(call.content, VerdictResponse) else VerdictResponse.model_validate(call.content)
                verdict = response.model_dump()
                pending.extend(verdict.get("pending", []))
            except Exception as exc:
                verdict = {"summary": "A consolidação retornou resposta inválida; resultados parciais foram preservados.", "known": [], "unknown": [], "pending": ["Resposta estruturada inválida na consolidação"], "risk_candidates": []}
                pending.extend(verdict["pending"])
                call.status = "ERRO"
                call.error_type = type(exc).__name__
                call.error_message = str(exc)[:2000]
        return {
            "verdict": verdict,
            "llm_runs": llm_runs,
            "pending": pending,
            "consolidated": {"agent_results": results, "evidence_ids": state.get("evidence_ids", []), "pending": pending, "interpretations": interpretations},
            "llm_used": state.get("llm_used", False) or call.status == "CONCLUIDO",
            "model": call.model,
        }

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
