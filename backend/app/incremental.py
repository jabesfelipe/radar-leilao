from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from . import models
from .ai.orchestrator import AnalysisOrchestrator
from .impact import ImpactAnalysisResult, ImpactAnalyzer
from .services import (
    aggregate_llm_usage,
    build_finance,
    create_analysis,
    create_execution,
    create_verdict,
    latest_execution,
    persist_agent_findings,
    persist_llm_runs,
    recalculate_risks,
    record_history,
    serialize,
)


class IncrementalAnalysisService:
    """Executa, de forma síncrona, uma análise causada por um DomainEvent."""

    def __init__(self, db: Session, impact_analyzer: ImpactAnalyzer | None = None, orchestrator: AnalysisOrchestrator | None = None):
        self.db = db
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer()
        self.orchestrator = orchestrator or AnalysisOrchestrator(db)

    def run_for_event(self, event: models.DomainEvent, query: str = "") -> dict[str, Any]:
        if not event.property_id:
            return {"status": "IGNORADO", "motivo": "Evento sem imóvel associado", "evento_id": event.id}
        prop = self.db.get(models.Property, event.property_id)
        if not prop:
            raise ValueError("Imóvel do evento não encontrado")
        impact = self.impact_analyzer.analyze(event.property_id, event.event_type, event.aggregate_type, event.aggregate_id, event.payload or {})
        if not impact.requires_reanalysis:
            return {"status": "IGNORADO", "evento_id": event.id, "impacto": impact.to_dict(), "analise_executada": False}
        return self._execute(event, prop, impact, query)

    def _execute(self, event: models.DomainEvent, prop: models.Property, impact: ImpactAnalysisResult, query: str) -> dict[str, Any]:
        domains = list(impact.affected_domains)
        changes = json.dumps({"cause_event_id": event.id, "event_type": event.event_type, "entity_type": event.aggregate_type, "entity_id": event.aggregate_id, "affected_domains": domains, "reason": impact.reason}, ensure_ascii=False, default=str)
        analysis = create_analysis(db=self.db, prop=prop, scope=f"Incremental:{event.event_type}", domains=domains, evidence_ids=[], changes=changes, agents=[])
        previous_execution = None
        execution = None
        if "checklist" in domains:
            previous_execution = latest_execution(prop)
            execution = create_execution(self.db, prop, f"EVENT:{event.event_type}:{event.id}"[:80], analysis.version)
            self.db.flush()
            record_history(self.db, prop, "ChecklistExecution", execution.id, "CREATE", None, {"analysis_version": analysis.version, "cause_event_id": event.id, "previous_execution_id": previous_execution.id if previous_execution else None}, event.id)
        record_history(self.db, prop, "Analysis", analysis.id, "CREATE", None, {"version": analysis.version, "cause_event_id": event.id, "event_type": event.event_type, "affected_domains": domains}, event.id)
        try:
            orchestration = self.orchestrator.run(prop.id, domains, query or event.event_type, analysis_id=analysis.id)
            agents = [item["agent"] for item in orchestration.get("agent_results", [])]
            analysis.agents_executed = agents
            analysis.model = orchestration.get("model")
            analysis.prompt_version = "radar-analysis-v1"
            analysis.token_usage = {"llm_used": orchestration.get("llm_used", False), "chunks_retrieved": len(orchestration.get("retrieved_chunk_ids", []))}
            if execution:
                execution.analysis_version = analysis.version
            evidence_ids = persist_agent_findings(self.db, prop, analysis, execution, orchestration.get("agent_results", []))
            llm_runs = persist_llm_runs(self.db, prop, analysis, orchestration.get("llm_runs", []))
            analysis.token_usage = {**analysis.token_usage, **serialize(aggregate_llm_usage(llm_runs))}
            finance = build_finance(prop)
            self.db.add(models.FinancialAnalysis(property_id=prop.id, analysis_version=analysis.version, inputs={"domains": domains, "cause_event_id": event.id, "chunks": orchestration.get("retrieved_chunk_ids", [])}, outputs=serialize(finance)))
            recalculate_risks(self.db, prop, analysis.version)
            verdict = create_verdict(self.db, prop, analysis, None)
            event.processed = True
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {"status": "CONCLUIDO", "evento_id": event.id, "impacto": impact.to_dict(), "analise_executada": True, "analysis_id": analysis.id, "versao": analysis.version, "execution_id": execution.id if execution else None, "agentes": agents, "evidencias": evidence_ids, "llm_usage": analysis.token_usage, "veredito": verdict.overall, "chunks_recuperados": orchestration.get("retrieved_chunk_ids", [])}
