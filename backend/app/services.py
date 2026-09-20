from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models
from .checklist import master_items
from .finance import calculate_financial


def serialize(value):
    if isinstance(value, dict): return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, list): return [serialize(v) for v in value]
    return float(value) if isinstance(value, Decimal) else value


def ensure_checklist_master(db: Session) -> None:
    existing = {item.canonical_key for item in db.scalars(select(models.ChecklistItem)).all()}
    for definition in master_items():
        if definition["canonical_key"] not in existing: db.add(models.ChecklistItem(**definition))
    db.flush()


def create_execution(db: Session, prop: models.Property, triggered_by: str = "MANUAL", analysis_version: int | None = None):
    ensure_checklist_master(db)
    execution = models.ChecklistExecution(property_id=prop.id, triggered_by=triggered_by, analysis_version=analysis_version)
    db.add(execution); db.flush()
    previous = next(iter(reversed(prop.checklist_executions)), None)
    previous_by_item = {r.checklist_item_id: r for r in previous.results} if previous else {}
    for item in db.scalars(select(models.ChecklistItem).where(models.ChecklistItem.active.is_(True)).order_by(models.ChecklistItem.priority)).all():
        old = previous_by_item.get(item.id)
        db.add(models.ChecklistResult(execution_id=execution.id, checklist_item_id=item.id, state=old.state if old else "PENDENTE", answer=old.answer if old else "", confidence=old.confidence if old else "MEDIA", interpretation=old.interpretation if old else None, risk=old.risk if old else None))
    db.flush()
    return execution


def latest_execution(prop: models.Property):
    return next(iter(reversed(prop.checklist_executions)), None)


def build_finance(prop: models.Property):
    auction = prop.auctions[-1] if prop.auctions else None
    occupancy = {}
    return calculate_financial(auction.bid_value if auction else Decimal("0"), auction.appraisal_value if auction else Decimal("0"), [{"amount": c.amount} for c in prop.costs], [{"kind": c.kind, "price": c.price, "rent": c.rent, "area_m2": c.area_m2} for c in prop.comparables], [{"amount": d.amount, "status": d.status} for d in prop.debts], occupancy, prop.area_m2)


def record_event(db: Session, prop: models.Property, event_type: str, aggregate_type: str, aggregate_id: int | None, payload: dict, domains: list[str]):
    event = models.DomainEvent(property_id=prop.id, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id, payload=payload, affected_domains=domains)
    db.add(event); db.flush(); return event


def record_history(db: Session, prop: models.Property, entity_type: str, entity_id: int, action: str, before: dict | None, after: dict | None, event_id: int | None = None, evidence_id: int | None = None):
    db.add(models.EntityHistory(property_id=prop.id, entity_type=entity_type, entity_id=entity_id, action=action, before_data=before, after_data=after, cause_event_id=event_id, evidence_id=evidence_id))


def impacted_domains(event_type: str) -> list[str]:
    return {"DOCUMENTO_ADICIONADO": ["documental", "juridico", "checklist"], "COMPARAVEL_ADICIONADO": ["mercado", "financeiro", "checklist"], "DIVIDA_ADICIONADA": ["financeiro", "checklist"], "PROCESSO_ADICIONADO": ["juridico", "checklist"], "OCUPACAO_ATUALIZADA": ["desocupacao", "financeiro", "checklist"]}.get(event_type, ["documental", "financeiro", "juridico", "mercado", "checklist"])


def create_analysis(db: Session, prop: models.Property, scope: str, domains: list[str], evidence_ids: list[int], changes: str, agents: list[str]):
    version = len(prop.analyses) + 1
    analysis = models.Analysis(property_id=prop.id, version=version, scope=scope, affected_domains=domains, agents_executed=agents, evidence_ids=evidence_ids, changes=changes)
    db.add(analysis); db.flush(); return analysis


def recalculate_risks(db: Session, prop: models.Property, analysis_version: int):
    pending = len([r for r in (latest_execution(prop).results if latest_execution(prop) else []) if r.state == "PENDENTE"])
    finance = build_finance(prop)
    risks = []
    if pending: risks.append(("Documental", f"{pending} item(ns) do Checklist Mestre ainda pendente(s).", "MEDIA"))
    if finance["custo_total"] > finance["valor_mercado"]: risks.append(("Financeiro", "O custo total estimado supera o valor de mercado informado.", "ALTA"))
    if not prop.documents: risks.append(("Documental", "Nenhum documento foi anexado ao dossiê.", "ALTA"))
    for category, description, severity in risks: db.add(models.Risk(property_id=prop.id, category=category, description=description, severity=severity, analysis_version=analysis_version))
    db.flush(); return risks


def create_verdict(db: Session, prop: models.Property, analysis: models.Analysis, synthesis: dict | None = None):
    finance = build_finance(prop); execution = latest_execution(prop); pending = [r.item.question for r in execution.results if r.state == "PENDENTE"] if execution else []
    risks = list(db.scalars(select(models.Risk).where(models.Risk.property_id == prop.id, models.Risk.analysis_version == analysis.version)).all())
    synthesis = synthesis or {}
    known = synthesis.get("known", []) or ["Resultados determinísticos e evidências registradas no dossiê."]
    unknown = synthesis.get("unknown", [])
    llm_pending = synthesis.get("pending", [])
    all_pending = pending + [item for item in llm_pending if item not in pending]
    overall = "ATENÇÃO" if risks or all_pending else "FAVORÁVEL"
    summary = synthesis.get("summary") or f"Análise V{analysis.version}: {len(all_pending)} pendência(s) e {len(risks)} risco(s) identificados."
    verdict = models.Verdict(property_id=prop.id, analysis_version=analysis.version, overall=overall, summary=summary, what_is_known="; ".join(known), what_is_unknown="; ".join(unknown), pending_items=all_pending, financial=serialize(finance), risk_ids=[r.id for r in risks], evidence_ids=analysis.evidence_ids)
    db.add(verdict); db.flush(); return verdict


def persist_agent_findings(db: Session, prop: models.Property, analysis: models.Analysis, execution: models.ChecklistExecution, agent_results: list[dict]) -> list[int]:
    """Converte findings estruturados em evidências rastreáveis e atualiza o checklist da execução."""
    evidence_ids: list[int] = []
    document_ids: set[int] = set()
    result_by_key = {result.item.canonical_key: result for result in execution.results}
    for result in agent_results:
        agent_name = result.get("agent", "IA")
        for finding in result.get("facts", []):
            statement = finding.get("statement") or finding.get("descricao")
            if not statement:
                continue
            chunk_ids = [int(value) for value in finding.get("chunk_ids", []) if str(value).isdigit()]
            chunk = db.get(models.DocumentChunk, chunk_ids[0]) if chunk_ids else None
            version = db.get(models.DocumentVersion, chunk.document_version_id) if chunk else None
            if chunk and version:
                document_ids.add(version.document_id)
            evidence = models.Evidence(property_id=prop.id, document_version_id=version.id if version else None, chunk_id=chunk.id if chunk else None, category=agent_name.upper(), fact=statement, interpretation=statement if finding.get("kind") == "interpretacao" else None, hypothesis=statement if finding.get("kind") == "hipotese" else None, confidence=finding.get("confidence", "MEDIA"), page=finding.get("page") or (chunk.page if chunk else None), section=finding.get("section") or (chunk.section if chunk else None), source_excerpt=finding.get("evidence_excerpt") or (chunk.content[:1000] if chunk else None))
            db.add(evidence); db.flush(); evidence_ids.append(evidence.id)
            db.add(models.EvidenceLink(evidence_id=evidence.id, target_type="Analysis", target_id=analysis.id, relation="SUSTENTA"))
            checklist_key = finding.get("checklist_key")
            if checklist_key and checklist_key in result_by_key:
                checklist_result = result_by_key[checklist_key]
                new_state = finding.get("checklist_state") or checklist_result.state
                checklist_result.state = new_state
                checklist_result.answer = statement
                checklist_result.confidence = finding.get("confidence", checklist_result.confidence)
                checklist_result.interpretation = statement
                db.add(models.ChecklistEvidence(checklist_result_id=checklist_result.id, evidence_id=evidence.id))
            if result.get("llm_used"):
                db.add(models.LLMRun(property_id=prop.id, analysis_id=analysis.id, agent=agent_name, provider="openai", model=analysis.model or "configurado", retrieved_chunk_ids=chunk_ids, status="CONCLUIDO"))
    analysis.evidence_ids = evidence_ids
    analysis.documents_considered = sorted(document_ids)
    db.flush()
    return evidence_ids
