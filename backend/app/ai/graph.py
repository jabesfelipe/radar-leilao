from typing import TypedDict
from sqlalchemy.orm import Session

class AnalysisState(TypedDict, total=False):
    property_id: int
    domains: list[str]
    context: str
    agent_results: list[dict]
    evidence_ids: list[int]
    financial: dict
    verdict: dict


def build_analysis_graph(db: Session):
    from langgraph.graph import END, START, StateGraph
    from .agents import Supervisor
    supervisor = Supervisor(db)
    graph = StateGraph(AnalysisState)
    def identify(state): return {"context": state.get("context", "")}
    def specialized_agents(state):
        results = supervisor.run(state["property_id"], state.get("domains", ["documental", "juridico", "financeiro", "mercado", "checklist"]), state.get("context", ""))
        return {"agent_results": [r.__dict__ for r in results], "evidence_ids": sum((r.evidence_ids for r in results), [])}
    def risk_engine(state): return {"verdict": {"status": "EM_ANALISE", "evidence_ids": state.get("evidence_ids", [])}}
    graph.add_node("identificar_imovel", identify)
    graph.add_node("agentes_especializados", specialized_agents)
    graph.add_node("risk_engine", risk_engine)
    graph.add_edge(START, "identificar_imovel")
    graph.add_edge("identificar_imovel", "agentes_especializados")
    graph.add_edge("agentes_especializados", "risk_engine")
    graph.add_edge("risk_engine", END)
    return graph.compile()
