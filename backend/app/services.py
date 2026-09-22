from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models
from .checklist import CHECKLIST_CONFIDENCES, CHECKLIST_STATES, master_items
from .finance import calculate_financial
from .risk_engine import RiskEngine
from .verdict_engine import VerdictEngine


def serialize(value):
    if isinstance(value, dict): return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, list): return [serialize(v) for v in value]
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, datetime): return value.isoformat()
    return value


def ensure_checklist_master(db: Session) -> None:
    """Seed controlado: só cria chaves ausentes e nunca reativa/sobrescreve existentes."""
    existing = {item.canonical_key for item in db.scalars(select(models.ChecklistItem)).all()}
    for definition in master_items():
        if definition["canonical_key"] not in existing:
            db.add(models.ChecklistItem(**definition))
    db.flush()


def create_execution(db: Session, prop: models.Property, triggered_by: str = "MANUAL", analysis_version: int | None = None):
    ensure_checklist_master(db)
    # Busca a execução anterior direto no banco (a coleção do relacionamento
    # pode estar desatualizada quando execuções são inseridas por FK), garantindo
    # o vínculo previous_result_id do snapshot.
    previous = db.scalars(
        select(models.ChecklistExecution)
        .where(models.ChecklistExecution.property_id == prop.id)
        .order_by(models.ChecklistExecution.id.desc())
    ).first()
    execution = models.ChecklistExecution(property_id=prop.id, triggered_by=triggered_by, analysis_version=analysis_version)
    db.add(execution); db.flush()
    previous_by_item = {r.checklist_item_id: r for r in previous.results} if previous else {}
    items = db.scalars(select(models.ChecklistItem).where(models.ChecklistItem.active.is_(True)).order_by(models.ChecklistItem.priority, models.ChecklistItem.canonical_key)).all()
    for item in items:
        old = previous_by_item.get(item.id)
        db.add(models.ChecklistResult(execution_id=execution.id, checklist_item_id=item.id, item_version=item.version, applicable=item.applicable, previous_result_id=old.id if old else None, state="PENDENTE", answer="", confidence="MEDIA"))
    db.flush()
    return execution


def latest_execution(prop: models.Property):
    return next(iter(reversed(prop.checklist_executions)), None)


def latest_occupancy(prop: models.Property):
    return next(iter(reversed(prop.occupancy_analyses)), None)


def build_finance(prop: models.Property):
    auction = prop.auctions[-1] if prop.auctions else None
    acquisition = auction.acquisition_value if auction and auction.acquisition_value is not None else (auction.bid_value if auction else None)
    costs = [{"category": c.category, "amount": c.amount} for c in prop.costs]
    comparables = [{"kind": c.kind, "price": c.price, "rent": c.rent, "area_m2": c.area_m2} for c in prop.comparables]
    debts = [{"amount": d.amount, "status": d.status} for d in prop.debts]
    occupancy = latest_occupancy(prop)
    occupancy_data = {"estimated_cost": occupancy.estimated_cost} if occupancy else {}
    return calculate_financial(bid=acquisition, appraisal=auction.appraisal_value if auction else None, costs=costs, comparables=comparables, debts=debts, occupancy=occupancy_data, area=prop.area_m2, commission_percent=auction.commission_percent if auction else None, commission_fixed=auction.commission_fixed if auction else None)



def record_event(db: Session, prop: models.Property, event_type: str, aggregate_type: str, aggregate_id: int | None, payload: dict, domains: list[str]):
    event = models.DomainEvent(property_id=prop.id, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id, payload=payload, affected_domains=domains)
    db.add(event); db.flush(); return event


def record_history(db: Session, prop: models.Property, entity_type: str, entity_id: int, action: str, before: dict | None, after: dict | None, event_id: int | None = None, evidence_id: int | None = None):
    db.add(models.EntityHistory(property_id=prop.id, entity_type=entity_type, entity_id=entity_id, action=action, before_data=before, after_data=after, cause_event_id=event_id, evidence_id=evidence_id))


def impacted_domains(event_type: str) -> list[str]:
    return {"DOCUMENTO_ADICIONADO": ["documental", "juridico", "checklist"], "COMPARAVEL_ADICIONADO": ["mercado", "financeiro", "checklist"], "DIVIDA_ADICIONADA": ["financeiro", "checklist"], "PROCESSO_ADICIONADO": ["juridico", "checklist"], "OCUPACAO_ATUALIZADA": ["desocupacao", "financeiro", "checklist"]}.get(event_type, ["documental", "financeiro", "juridico", "mercado", "checklist"])


def create_analysis(db: Session, prop: models.Property, scope: str, domains: list[str], evidence_ids: list[int], changes: str, agents: list[str]):
    # Próxima versão calculada direto no banco (a coleção prop.analyses pode estar
    # desatualizada dentro da mesma sessão, gerando versões repetidas na reanálise
    # incremental). Preserva o contrato: 1ª análise = v1, 2ª = v2, incremental.
    last_version = db.scalars(
        select(models.Analysis.version)
        .where(models.Analysis.property_id == prop.id)
        .order_by(models.Analysis.version.desc())
    ).first()
    version = (last_version or 0) + 1
    analysis = models.Analysis(property_id=prop.id, version=version, scope=scope, affected_domains=domains, agents_executed=agents, evidence_ids=evidence_ids, changes=changes)
    db.add(analysis); db.flush(); return analysis


def recalculate_risks(db: Session, prop: models.Property, analysis_version: int):
    execution = latest_execution(prop)
    candidates = RiskEngine().evaluate(
        property_id=prop.id,
        checklist_results=execution.results if execution else [],
    )
    persisted: list[models.Risk] = []
    for candidate in candidates:
        risk = models.Risk(
            property_id=prop.id,
            category=candidate.domain,
            description=f"[{candidate.risk_key}] {candidate.title}: {candidate.description}",
            severity=candidate.severity,
            status=candidate.status,
            impact=candidate.impact,
            confidence=candidate.confidence,
            origin=f"{candidate.origin}:{candidate.risk_key}",
            evidence_id=candidate.evidence_ids[0] if candidate.evidence_ids else None,
            analysis_version=analysis_version,
        )
        db.add(risk)
        persisted.append(risk)
    db.flush()
    return persisted


def create_verdict(db: Session, prop: models.Property, analysis: models.Analysis, synthesis: dict | None = None):
    execution = latest_execution(prop)
    risks = list(db.scalars(select(models.Risk).where(models.Risk.property_id == prop.id, models.Risk.analysis_version == analysis.version)).all())
    decision = VerdictEngine().evaluate(
        property_id=prop.id,
        analysis_version=analysis.version,
        risks=risks,
        checklist_results=execution.results if execution else [],
        evidence_ids=analysis.evidence_ids or [],
        financial=serialize(build_finance(prop)),
    )
    verdict = models.Verdict(**decision.to_dict())
    db.add(verdict); db.flush(); return verdict


def persist_agent_findings(db: Session, prop: models.Property, analysis: models.Analysis, execution: models.ChecklistExecution, agent_results: list[dict]) -> list[int]:
    """Converte findings estruturados em evidências rastreáveis e atualiza o checklist da execução."""
    evidence_ids: list[int] = []
    document_ids: set[int] = set()
    result_by_key = {result.item.canonical_key: result for result in execution.results} if execution else {}
    for result in agent_results:
        agent_name = result.get("agent", "IA")
        if agent_name.lower() in {"checklist", "checklist_agent"}:
            evidence_ids.extend(persist_checklist_agent_findings(db, prop, analysis, execution, result.get("facts", [])))
            continue
        for finding in result.get("facts", []):
            statement = finding.get("statement") or finding.get("descricao")
            if not statement:
                continue
            chunk_ids = [int(value) for value in finding.get("chunk_ids", []) if str(value).isdigit()]
            chunk = db.get(models.DocumentChunk, chunk_ids[0]) if chunk_ids else None
            version = db.get(models.DocumentVersion, chunk.document_version_id) if chunk else None
            if chunk and version:
                document_ids.add(version.document_id)
            is_documental = agent_name.lower() in {"documental", "document_agent", "document"}
            is_juridico = agent_name.lower() in {"juridico", "jurídico", "legal", "legal_agent"}
            if is_documental:
                if not chunk or not version:
                    continue
                from .evidence import normalize_documentary_evidence
                evidence = normalize_documentary_evidence(db=db, property_id=prop.id, document_version_id=version.id, chunk_id=chunk.id, category="DOCUMENTAL", fact=statement, confidence=finding.get("confidence", "MEDIA"), page=finding.get("page"), section=finding.get("section"), source_excerpt=finding.get("evidence_excerpt"), target_type="Analysis", target_id=analysis.id)
                evidence_ids.append(evidence.id); document_ids.add(version.document_id)
            elif is_juridico and chunk and version:
                from .evidence import normalize_documentary_evidence
                evidence = normalize_documentary_evidence(db=db, property_id=prop.id, document_version_id=version.id, chunk_id=chunk.id, category="JURIDICO", fact=statement, confidence=finding.get("confidence", "MEDIA"), page=finding.get("page"), section=finding.get("section"), source_excerpt=finding.get("evidence_excerpt"), target_type="Analysis", target_id=analysis.id)
                evidence_ids.append(evidence.id); document_ids.add(version.document_id)
            else:
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
    analysis.evidence_ids = sorted(set((analysis.evidence_ids or []) + evidence_ids))
    analysis.documents_considered = sorted(set((analysis.documents_considered or []) + list(document_ids)))
    db.flush()
    return evidence_ids


def persist_checklist_agent_findings(db: Session, prop: models.Property, analysis: models.Analysis, execution: models.ChecklistExecution, facts: list[dict]) -> list[int]:
    """Valida e aplica somente findings do Checklist Agent em uma nova execução."""
    if not execution:
        return []
    results_by_key = {result.item.canonical_key: result for result in execution.results}
    evidence_ids: list[int] = []
    document_ids: set[int] = set()
    for finding in facts:
        checklist_key = finding.get("checklist_key")
        state = finding.get("checklist_state")
        statement = (finding.get("statement") or "").strip()
        confidence = finding.get("confidence", "MEDIA")
        if not checklist_key or checklist_key not in results_by_key or not state or not statement:
            continue
        if state not in CHECKLIST_STATES or confidence not in CHECKLIST_CONFIDENCES:
            continue
        checklist_result = results_by_key[checklist_key]
        if state == "NAO_APLICAVEL" and checklist_result.applicable:
            continue
        if state != "NAO_APLICAVEL" and not checklist_result.applicable:
            continue
        chunk_ids = [int(value) for value in finding.get("chunk_ids", []) if str(value).isdigit()]
        chunk = db.get(models.DocumentChunk, chunk_ids[0]) if chunk_ids else None
        version = db.get(models.DocumentVersion, chunk.document_version_id) if chunk else None
        if not chunk or not version:
            continue
        document_ids.add(version.document_id)
        from .evidence import normalize_documentary_evidence
        evidence = normalize_documentary_evidence(
            db=db,
            property_id=prop.id,
            document_version_id=version.id,
            chunk_id=chunk.id,
            category="CHECKLIST",
            fact=statement,
            confidence=confidence,
            page=finding.get("page"),
            section=finding.get("section"),
            source_excerpt=finding.get("evidence_excerpt"),
            target_type="Analysis",
            target_id=analysis.id,
        )
        evidence_ids.append(evidence.id)
        checklist_result.state = state
        checklist_result.answer = statement
        checklist_result.confidence = confidence
        checklist_result.interpretation = statement if finding.get("kind") == "interpretacao" else checklist_result.interpretation
        checklist_result.risk = finding.get("risk") or checklist_result.risk
        db.add(models.ChecklistEvidence(checklist_result_id=checklist_result.id, evidence_id=evidence.id))
    analysis.evidence_ids = sorted(set((analysis.evidence_ids or []) + evidence_ids))
    analysis.documents_considered = sorted(set((analysis.documents_considered or []) + list(document_ids)))
    db.flush()
    return evidence_ids


def persist_llm_runs(db: Session, prop: models.Property, analysis: models.Analysis, runs: list[dict]) -> list[models.LLMRun]:
    """Persiste exatamente um registro por chamada real ou tentativa rastreada."""
    from .ai.costs import calculate_cost, resolve_pricing
    persisted: list[models.LLMRun] = []
    for run in runs:
        provider = run.get("provider") or "desconhecido"
        model = run.get("model") or "desconhecido"
        pricing = resolve_pricing(db, provider, model)
        costs = calculate_cost(run.get("input_tokens"), run.get("output_tokens"), pricing)
        llm_run = models.LLMRun(property_id=prop.id, analysis_id=analysis.id if analysis else None, agent=run.get("agent", "desconhecido"), provider=provider, model=model, input_tokens=run.get("input_tokens"), output_tokens=run.get("output_tokens"), total_tokens=run.get("total_tokens"), input_cost=costs["input_cost"], output_cost=costs["output_cost"], total_cost=costs["total_cost"], input_price_per_1m=pricing.input_price_per_1m if pricing else None, output_price_per_1m=pricing.output_price_per_1m if pricing else None, retrieved_chunk_ids=run.get("retrieved_chunk_ids", []), duration_ms=run.get("duration_ms"), request_id=run.get("request_id"), status=run.get("status", "CONCLUIDO"), error_type=run.get("error_type"), error_message=run.get("error_message"))
        db.add(llm_run); persisted.append(llm_run)
    db.flush()
    return persisted


def aggregate_llm_usage(runs: list[models.LLMRun]) -> dict:
    input_tokens = sum((run.input_tokens or 0 for run in runs), 0)
    output_tokens = sum((run.output_tokens or 0 for run in runs), 0)
    total_cost = sum((run.total_cost or Decimal("0") for run in runs), Decimal("0"))
    known_input = any(run.input_tokens is not None for run in runs)
    known_output = any(run.output_tokens is not None for run in runs)
    return {"input_tokens": input_tokens if known_input else None, "output_tokens": output_tokens if known_output else None, "total_tokens": (input_tokens + output_tokens) if known_input and known_output else None, "total_cost": total_cost if any(run.total_cost is not None for run in runs) else None, "runs": len(runs), "successful_runs": len([run for run in runs if run.status == "CONCLUIDO"]), "error_runs": len([run for run in runs if run.status not in {"CONCLUIDO", "IGNORADO"}])}


def checklist_item_snapshot(item: models.ChecklistItem) -> dict:
    return serialize({"id": item.id, "canonical_key": item.canonical_key, "question": item.question, "description": item.description, "category": item.category, "domain": item.domain or [], "origin": item.origin, "priority": item.priority, "required": item.required, "applicable": item.applicable, "active": item.active, "version": item.version, "expected_evidence": item.expected_evidence or [], "potential_impact": item.potential_impact, "related_rules": item.related_rules or [], "agents": item.agents or [], "risk_categories": item.risk_categories or [], "created_at": item.created_at, "updated_at": item.updated_at})


def record_checklist_event(db: Session, item: models.ChecklistItem, event_type: str, payload: dict):
    event = models.DomainEvent(property_id=None, event_type=event_type, aggregate_type="ChecklistItem", aggregate_id=item.id, payload=payload, affected_domains=item.domain or ["CHECKLIST"])
    db.add(event); db.flush(); return event


def record_checklist_history(db: Session, item: models.ChecklistItem, action: str, before: dict | None, after: dict | None, event_id: int | None = None):
    db.add(models.EntityHistory(property_id=None, entity_type="ChecklistItem", entity_id=item.id, action=action, before_data=before, after_data=after, cause_event_id=event_id))


def create_checklist_item(db: Session, data: dict) -> models.ChecklistItem:
    item = models.ChecklistItem(**data, version=1)
    db.add(item); db.flush()
    event = record_checklist_event(db, item, "CHECKLIST_REGRA_CRIADA", checklist_item_snapshot(item))
    record_checklist_history(db, item, "CREATE", None, checklist_item_snapshot(item), event.id)
    return item


def update_checklist_item(db: Session, item: models.ChecklistItem, changes: dict) -> models.ChecklistItem:
    before = checklist_item_snapshot(item)
    relevant = {key: value for key, value in changes.items() if value is not None}
    changed = any(getattr(item, key) != value for key, value in relevant.items())
    if not changed:
        return item
    for key, value in relevant.items():
        setattr(item, key, value)
    item.version += 1
    db.flush()
    event_type = "CHECKLIST_REGRA_ATIVADA" if changes.get("active") is True else ("CHECKLIST_REGRA_DESATIVADA" if changes.get("active") is False else "CHECKLIST_REGRA_ATUALIZADA")
    event = record_checklist_event(db, item, event_type, {"before": before, "after": checklist_item_snapshot(item)})
    record_checklist_history(db, item, "ACTIVATE" if event_type.endswith("ATIVADA") else ("DEACTIVATE" if event_type.endswith("DESATIVADA") else "UPDATE"), before, checklist_item_snapshot(item), event.id)
    return item
