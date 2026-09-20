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


def create_verdict(db: Session, prop: models.Property, analysis: models.Analysis):
    finance = build_finance(prop); execution = latest_execution(prop); pending = [r.item.question for r in execution.results if r.state == "PENDENTE"] if execution else []
    risks = list(db.scalars(select(models.Risk).where(models.Risk.property_id == prop.id, models.Risk.analysis_version == analysis.version)).all())
    overall = "ATENÇÃO" if risks or pending else "FAVORÁVEL"
    verdict = models.Verdict(property_id=prop.id, analysis_version=analysis.version, overall=overall, summary=f"Análise V{analysis.version}: {len(pending)} pendência(s) e {len(risks)} risco(s) identificados.", what_is_known="Resultados determinísticos e evidências registradas no dossiê.", what_is_unknown="; ".join(pending[:5]), pending_items=pending, financial=serialize(finance), risk_ids=[r.id for r in risks], evidence_ids=analysis.evidence_ids)
    db.add(verdict); db.flush(); return verdict
