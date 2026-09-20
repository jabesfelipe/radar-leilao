import json
from typing import TypedDict
from sqlalchemy.orm import Session
from .contracts import VerdictResponse
from .gateway import LLMCall, LLMGateway, build_gateway

class AnalysisState(TypedDict, total=False):
    property_id: int
    domains: list[str]
    context: str
    retrieved_chunk_ids: list[int]
    agent_results: list[dict]
    llm_runs: list[dict]
    evidence_ids: list[int]
    llm_used: bool
    model: str | None
    verdict: dict


def _gateway_or_none() -> LLMGateway | None:
    try: return build_gateway()
    except RuntimeError: return None


def build_analysis_graph(db: Session, gateway_override: LLMGateway | None = None):
    from langgraph.graph import END, START, StateGraph
    from .agents import Supervisor
    gateway = gateway_override or _gateway_or_none()
    supervisor = Supervisor(db, gateway)
    graph = StateGraph(AnalysisState)

    def identify(state): return {"context": state.get("context", "")}

    def specialized_agents(state):
        results = supervisor.run(state["property_id"], state.get("domains", ["documental", "juridico", "financeiro", "mercado", "checklist"]), state.get("context", ""), state.get("retrieved_chunk_ids", []))
        calls = [dict(r.llm_call.to_dict(), agent=r.agent, retrieved_chunk_ids=r.retrieved_chunk_ids) for r in results if r.llm_call]
        return {"agent_results": [r.to_dict() for r in results], "llm_runs": calls, "evidence_ids": sorted(set(sum((r.evidence_ids for r in results), []))), "llm_used": any(r.llm_used for r in results), "model": gateway.model if gateway else None}

    def synthesize(state):
        results = state.get("agent_results", [])
        if not gateway:
            call = LLMCall.unavailable("openai", "desconhecido", "LLM não configurada; síntese do Supervisor não executada")
            return {"verdict": {"summary": "Análise determinística concluída; interpretação LLM pendente de OPENAI_API_KEY", "known": [], "unknown": ["A análise interpretativa ainda não foi executada"], "pending": ["Configurar OPENAI_API_KEY"], "risk_candidates": []}, "llm_runs": state.get("llm_runs", []) + [dict(call.to_dict(), agent="supervisor", retrieved_chunk_ids=state.get("retrieved_chunk_ids", []))], "model": call.model}
        messages = [{"role": "system", "content": "Você é o Supervisor do Radar Leilão. Sintetize resultados de agentes fundamentados em RAG. Não invente fatos. Separe conhecido, desconhecido, pendências e riscos candidatos."}, {"role": "user", "content": json.dumps({"resultados_agentes": results, "evidencias_chunk_ids": state.get("evidence_ids", [])}, ensure_ascii=False, default=str)}]
        call = gateway.structured_chat(VerdictResponse, messages)
        if call.status != "CONCLUIDO":
            verdict = {"summary": "A síntese do Supervisor falhou; resultados parciais foram preservados.", "known": [], "unknown": [], "pending": [call.error_message or "Erro desconhecido na síntese"], "risk_candidates": []}
            return {"verdict": verdict, "llm_runs": state.get("llm_runs", []) + [dict(call.to_dict(), agent="supervisor", retrieved_chunk_ids=state.get("retrieved_chunk_ids", []))], "model": call.model}
        response = call.content
        verdict = response if isinstance(response, VerdictResponse) else VerdictResponse.model_validate(response)
        return {"verdict": verdict.model_dump(), "llm_runs": state.get("llm_runs", []) + [dict(call.to_dict(), agent="supervisor", retrieved_chunk_ids=state.get("retrieved_chunk_ids", []))], "llm_used": True, "model": call.model}

    graph.add_node("identificar_imovel", identify)
    graph.add_node("agentes_especializados", specialized_agents)
    graph.add_node("sintese_supervisor", synthesize)
    graph.add_edge(START, "identificar_imovel")
    graph.add_edge("identificar_imovel", "agentes_especializados")
    graph.add_edge("agentes_especializados", "sintese_supervisor")
    graph.add_edge("sintese_supervisor", END)
    return graph.compile()
