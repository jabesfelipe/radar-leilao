from datetime import datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models
from .config import settings
from .checklist import CHECKLIST_CONFIDENCES, CHECKLIST_STATES, master_items
from .finance import MaxPriceGoal, SaleAssumptions, ScenarioAssumptions, calculate_financial
from .risk_engine import RiskEngine
from .verdict_engine import VerdictEngine


def serialize(value):
    if isinstance(value, dict): return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, list): return [serialize(v) for v in value]
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, datetime): return value.isoformat()
    return value


# PostgreSQL INTEGER (int4) máximo. chunk_ids vêm da resposta do LLM e podem conter
# números que não são ids reais (ex.: o modelo às vezes cita um número presente no
# conteúdo do documento). Um valor fora do range de int4 quebra o db.get com
# "integer out of range". Aceitamos apenas inteiros positivos dentro do range: um
# id inexistente vira chunk=None (comportamento conservador, evidência não anexada),
# sem derrubar a análise.
_PG_INT4_MAX = 2147483647


def valid_chunk_ids(raw_ids) -> list[int]:
    """Filtra chunk_ids do LLM para inteiros positivos dentro do range do int4."""
    valid: list[int] = []
    for value in raw_ids or []:
        if not str(value).isdigit():
            continue
        number = int(value)
        if 0 < number <= _PG_INT4_MAX:
            valid.append(number)
    return valid


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


def _execution_sort_key(execution: models.ChecklistExecution) -> tuple[int, int]:
    # analysis_version pode ser None; tratamos None como o menor possível para não
    # vencer uma execução versionada. id.desc() é o desempate defensivo (mesma versão).
    version = execution.analysis_version if execution.analysis_version is not None else -1
    return (version, execution.id or -1)


def latest_execution(prop: models.Property):
    """Retorna a ChecklistExecution mais recente de forma determinística.

    Antes usava next(iter(reversed(prop.checklist_executions))), que dependia da
    ordem incidental do relacionamento ORM e podia devolver uma execução antiga.
    Agora seleciona por maior analysis_version e, em empate, maior id.
    """
    executions = list(prop.checklist_executions or [])
    if not executions:
        return None
    return max(executions, key=_execution_sort_key)


def execution_for_version(prop: models.Property, analysis_version: int | None, db: Session | None = None):
    """Retorna a ChecklistExecution correspondente a uma analysis_version específica.

    Usado pelo Veredito para garantir que o cálculo use a execução da própria
    análise (não uma execução antiga/mais recente de outra versão). Em empate de
    versão, escolhe o maior id. Se não houver execução para a versão, cai para a
    execução mais recente (comportamento anterior seguro).

    IMPORTANTE (Task 73): quando `db` é fornecido, a seleção consulta o banco por
    property_id + analysis_version — a fonte de verdade. Isso é necessário porque
    `create_execution` insere a nova execução por FK (property_id) e NÃO a anexa à
    coleção `prop.checklist_executions`. Se essa coleção já foi carregada antes da
    criação, a execução recém-criada não aparece nela (a Session mantém a lista em
    memória sem re-consultar). No mesmo request (create_execution seguido de
    create_verdict) a consulta ao banco encontra deterministicamente a execução da
    versão corrente. Sem `db`, mantemos o caminho anterior sobre a relationship,
    preservando o comportamento dos demais chamadores.
    """
    if analysis_version is not None:
        if db is not None:
            found = db.scalars(
                select(models.ChecklistExecution)
                .where(
                    models.ChecklistExecution.property_id == prop.id,
                    models.ChecklistExecution.analysis_version == analysis_version,
                )
                .order_by(models.ChecklistExecution.id.desc())
            ).first()
            if found is not None:
                return found
        else:
            candidates = [e for e in (prop.checklist_executions or []) if e.analysis_version == analysis_version]
            if candidates:
                return max(candidates, key=lambda e: e.id or -1)
    return latest_execution(prop)


def latest_occupancy(prop: models.Property):
    return next(iter(reversed(prop.occupancy_analyses)), None)


def _build_finance_assumptions(raw: dict | None):
    """Constrói SaleAssumptions / MaxPriceGoal / cenários / valor de venda / prazo /
    carregamento mensal a partir das premissas persistidas em Auction (Task 3).

    Retorna um dict de kwargs a repassar a calculate_financial. Ausência de premissa
    é preservada como None (o motor trata como dado desconhecido, nunca zero)."""
    raw = raw or {}

    def _dec(v):
        return Decimal(str(v)) if v is not None and v != "" else None

    sale = SaleAssumptions(
        corretagem_pct=_dec(raw.get("corretagem_pct")),
        tributo_pct=_dec(raw.get("tributo_pct")),
        tax_base=raw.get("tax_base") or "GANHO",
    )
    goal = None
    if raw.get("goal_kind") and raw.get("goal_value") is not None:
        goal = MaxPriceGoal(kind=raw["goal_kind"], value=_dec(raw.get("goal_value")))
    scenarios = []
    for sc in raw.get("cenarios", []) or []:
        scenarios.append(ScenarioAssumptions(
            nome=sc.get("nome", "BASE"),
            valor_venda=_dec(sc.get("valor_venda")),
            reforma=_dec(sc.get("reforma")),
            desocupacao=_dec(sc.get("desocupacao")),
            carregamento=_dec(sc.get("carregamento")),
            prazo_meses=sc.get("prazo_meses"),
            justificativa=sc.get("justificativa", ""),
        ))
    return {
        "sale": sale,
        "goal": goal,
        "scenarios": scenarios or None,
        "market_value": _dec(raw.get("valor_venda_estimado")),
        "monthly_carrying": _dec(raw.get("carregamento_mensal")),
        "holding_months": int(raw["prazo_meses"]) if raw.get("prazo_meses") not in (None, "") else 0,
    }


def current_auction(prop: models.Property):
    """Seleciona o leilão CORRENTE de forma determinística.

    Um imóvel pode ter mais de um Auction (cada POST /leilao cria um novo registro).
    A relationship ``prop.auctions`` NÃO possui ordenação explícita, então
    ``prop.auctions[-1]`` depende da ordem incidental da coleção ORM e pode variar
    entre sessões/requests — o que fazia premissas gravadas num leilão divergirem do
    leilão lido no cálculo (SPEC §44.2: não usar ordem incidental para estado atual).
    Selecionamos deterministicamente o maior ``id`` (registro mais recente)."""
    if not prop.auctions:
        return None
    return max(prop.auctions, key=lambda a: a.id)


def build_finance(prop: models.Property):
    auction = current_auction(prop)
    acquisition = auction.acquisition_value if auction and auction.acquisition_value is not None else (auction.bid_value if auction else None)
    costs = [{"category": c.category, "amount": c.amount} for c in prop.costs]
    comparables = [{"kind": c.kind, "price": c.price, "rent": c.rent, "area_m2": c.area_m2} for c in prop.comparables]
    debts = [{"amount": d.amount, "status": d.status} for d in prop.debts]
    occupancy = latest_occupancy(prop)
    occupancy_data = {"estimated_cost": occupancy.estimated_cost} if occupancy else {}
    # Premissas financeiras persistidas (Task 3): meta, corretagem, tributo, valor de
    # venda, prazo, carregamento mensal e cenários. Ausência => dado desconhecido.
    assumptions = _build_finance_assumptions(getattr(auction, "financial_assumptions", None) if auction else None)
    return calculate_financial(
        bid=acquisition,
        appraisal=auction.appraisal_value if auction else None,
        costs=costs, comparables=comparables, debts=debts, occupancy=occupancy_data,
        area=prop.area_m2,
        commission_percent=auction.commission_percent if auction else None,
        commission_fixed=auction.commission_fixed if auction else None,
        **assumptions,
    )



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
    # Usa a execução do Checklist da própria versão (fonte de verdade no banco via
    # db), igual ao create_verdict. Antes usava latest_execution(prop), que lê a
    # relationship em memória e pode estar stale: create_execution insere a nova
    # execução por FK e não a anexa à coleção já carregada, fazendo o Risk Engine
    # avaliar uma execução antiga. Reutiliza a seleção da Task 73 (sem nova
    # estratégia nem duplicar a consulta).
    execution = execution_for_version(prop, analysis_version, db=db)
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


def build_verdict_decision(db: Session, prop: models.Property, analysis_version: int, evidence_ids: list[int] | None):
    """Constrói a VerdictDecision determinística de uma versão, sem persistir.

    Fonte de verdade: a ChecklistExecution da própria analysis_version (consultada
    no banco via db) e os Risks daquela versão. Não usa LLM. Extraído para poder
    ser reutilizado tanto pela criação (create_verdict) quanto pela reconciliação
    histórica idempotente (reconcile_verdict), sem duplicar a regra.
    """
    execution = execution_for_version(prop, analysis_version, db=db)
    risks = list(db.scalars(select(models.Risk).where(models.Risk.property_id == prop.id, models.Risk.analysis_version == analysis_version)).all())
    return VerdictEngine().evaluate(
        property_id=prop.id,
        analysis_version=analysis_version,
        risks=risks,
        checklist_results=execution.results if execution else [],
        evidence_ids=evidence_ids or [],
        financial=serialize(build_finance(prop)),
    )


def create_verdict(db: Session, prop: models.Property, analysis: models.Analysis, synthesis: dict | None = None):
    # Usa a execução do Checklist correspondente à versão desta análise, para o
    # Veredito não ser contaminado por uma execução de outra versão. Passamos `db`
    # para que a seleção consulte o banco (fonte de verdade) e encontre a execução
    # recém-criada no mesmo request, mesmo que a relationship esteja desatualizada.
    decision = build_verdict_decision(db, prop, analysis.version, analysis.evidence_ids)
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
            chunk_ids = valid_chunk_ids(finding.get("chunk_ids", []))
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
        chunk_ids = valid_chunk_ids(finding.get("chunk_ids", []))
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


def record_global_event(db: Session, event_type: str, aggregate_type: str, aggregate_id: int | None, payload: dict, domains: list[str]):
    """Evento de domínio NÃO atrelado a um imóvel (ex.: leiloeiro/portal — TASK 75.2).
    property_id=None. NUNCA incluir segredos no payload."""
    event = models.DomainEvent(property_id=None, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id, payload=payload, affected_domains=domains)
    db.add(event); db.flush(); return event


def record_global_history(db: Session, entity_type: str, entity_id: int, action: str, before: dict | None, after: dict | None, event_id: int | None = None):
    """Histórico de alteração NÃO atrelado a um imóvel (property_id=None). before/after
    NUNCA contêm segredos (ex.: credencial de portal → apenas has_secret)."""
    db.add(models.EntityHistory(property_id=None, entity_type=entity_type, entity_id=entity_id, action=action, before_data=before, after_data=after, cause_event_id=event_id))


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


# Códigos de severidade de risco por "peso" para escolher o risco jurídico principal.
_RISK_SEVERITY_ORDER = {"CRITICA": 4, "ALTA": 3, "MEDIA": 2, "BAIXA": 1}


def juridical_overview(db: Session, prop: models.Property) -> dict[str, Any]:
    """Visão jurídica LEGÍVEL para o dossiê/veredito (determinística, sem LLM).

    Distingue explicitamente EVIDÊNCIA/CORRELAÇÃO/SITUAÇÃO: nunca apresenta uma
    hipótese como fato. A situação do imóvel permanece NÃO CONFIRMADA salvo
    confirmação manual (checklist CONFIRMADO). Impacto financeiro = NÃO QUANTIFICADO.
    """
    processos = list(prop.processes or [])
    relevantes = [p for p in processos if (p.correlation_level or "").upper() in {"ALTA", "MEDIA"}]

    execution = latest_execution(prop)
    pendencias: list[str] = []
    confirmados: list[str] = []
    if execution:
        for res in execution.results:
            item = res.item
            if item is None or str(item.category or "").upper() != "JURIDICO":
                continue
            estado = (res.state or "").upper()
            if estado in {"PENDENTE", "EM_ANALISE", "ATENCAO", "RISCO_IDENTIFICADO"}:
                pendencias.append(item.question)
            elif estado == "CONFIRMADO":
                confirmados.append(item.question)

    # Riscos jurídicos persistidos (categoria juridico).
    riscos = [r for r in (prop.risks or []) if str(r.category or "").lower() == "juridico"]
    risco_principal = None
    if riscos:
        risco_principal = max(riscos, key=lambda r: _RISK_SEVERITY_ORDER.get((r.severity or "").upper(), 0))

    # Correlação predominante entre os processos relevantes (maior nível observado).
    correlacao = "NAO_CONFIRMADA"
    for nivel in ("ALTA", "MEDIA", "BAIXA"):
        if any((p.correlation_level or "").upper() == nivel for p in processos):
            correlacao = nivel
            break

    return {
        "processos_encontrados": len(processos),
        "processos_relevantes": len(relevantes),
        "pendencias": pendencias,
        "confirmados": confirmados,
        "correlacao": correlacao,
        # A situação do imóvel só é CONFIRMADA por validação manual/documental.
        "situacao_imovel": "CONFIRMADA" if confirmados and not pendencias else "NAO_CONFIRMADA",
        "risco_principal": (
            {
                "descricao": risco_principal.description,
                "severidade": risco_principal.severity,
                "confianca": risco_principal.confidence,
                "evidencia_id": risco_principal.evidence_id,
            }
            if risco_principal is not None else None
        ),
        "impacto_financeiro": "NAO_QUANTIFICADO",
        "diligencia_recomendada": (
            "Validar matrícula atualizada e documentação processual."
            if pendencias or relevantes else None
        ),
    }


# ============================================================================
# PÓS-ARREMATAÇÃO — helpers de serviço (determinísticos, sem LLM).
# ============================================================================

# As 16 etapas operacionais do fluxo (SPEC §3). São SUGESTÕES configuráveis: cada
# imóvel pode marcar uma etapa como NAO_APLICAVEL (nem toda etapa é obrigatória).
POST_AUCTION_DEFAULT_STAGES: list[tuple[str, str]] = [
    ("ANALISE_DECISAO", "Análise e decisão de investimento"),
    ("ARREMATACAO", "Arrematação"),
    ("PAGAMENTO_LANCE_COMISSAO", "Pagamento do lance e comissão"),
    ("ITBI_TRIBUTOS", "Recolhimento de ITBI e tributos"),
    ("REGISTRO_AQUISICAO", "Registro da aquisição e atualização da matrícula"),
    ("IDENTIFICACAO_OCUPANTE", "Identificação e contato com o ocupante"),
    ("DESOCUPACAO_AMIGAVEL", "Tentativa de desocupação amigável"),
    ("NOTIFICACAO_EXTRAJUDICIAL", "Preparação e envio de notificação extrajudicial"),
    ("DESOCUPACAO_VOLUNTARIA", "Desocupação voluntária ou acordo"),
    ("CONTRATACAO_CONSULTORIA", "Contratação de consultoria (quando aplicável)"),
    ("ACAO_JUDICIAL_IMISSAO", "Ação judicial de imissão na posse"),
    ("REGISTRO_CUSTAS_PROCESSUAIS", "Registro de custas, honorários e despesas processuais"),
    ("IMISSAO_POSSE", "Imissão na posse e confirmação da entrega"),
    ("VISTORIA_REFORMA", "Vistoria, reforma e regularização complementar"),
    ("PREPARACAO_VENDA_LOCACAO", "Preparação para venda ou locação"),
    ("ENCERRAMENTO", "Encerramento operacional e consolidação do resultado"),
]


def get_post_auction(db: Session, property_id: int) -> "models.PostAuction | None":
    return db.scalar(select(models.PostAuction).where(models.PostAuction.property_id == property_id))


def seed_default_stages(db: Session, property_id: int) -> list["models.PostAuctionStage"]:
    """Cria as etapas padrão para um imóvel recém-ativado (idempotente: só cria as
    chaves ausentes, nunca sobrescreve etapas já existentes)."""
    existing = {s.stage_key for s in db.scalars(select(models.PostAuctionStage).where(models.PostAuctionStage.property_id == property_id)).all()}
    created: list[models.PostAuctionStage] = []
    for order, (key, title) in enumerate(POST_AUCTION_DEFAULT_STAGES):
        if key in existing:
            continue
        stage = models.PostAuctionStage(property_id=property_id, stage_key=key, title=title, sort_order=order, status="PENDENTE")
        db.add(stage)
        created.append(stage)
    db.flush()
    return created


def post_auction_cost_summary(db: Session, property_id: int) -> dict[str, Any]:
    """Consolidação financeira determinística do pós-arrematação.

    Preserva a distinção ESTIMATIVA x OBRIGAÇÃO x PAGO e NUNCA sobrescreve o
    financeiro histórico da análise (build_finance permanece a fonte da análise
    inicial). Considera apenas os custos pós-arrematação (tabela própria):
      - previsto_total   = soma dos planned_amount (exceto CANCELADO);
      - realizado_total  = soma dos actual_amount dos itens PAGOS;
      - pendente_total   = soma do que falta pagar (previsto de PREVISTO/PENDENTE/CONTESTADO
                           ainda não pago);
      - variacao         = realizado_total - previsto_total (só itens já pagos).
    Combina com o orçamento inicial congelado (PostAuction.initial_budget) e o
    custo total da análise para expor o custo acumulado do investimento.

    Lucro/ROI usam a MESMA definição do Financeiro (resultado líquido =
    valor de venda - custo de saída - custo total), lendo o custo de saída de
    build_finance. Assim o ROI do pós-arrematação é consistente com o roi_operacao
    do Financeiro quando ainda não há custos de execução lançados."""
    ZERO = Decimal("0")
    costs = db.scalars(select(models.PostAuctionCost).where(models.PostAuctionCost.property_id == property_id)).all()
    pa = get_post_auction(db, property_id)

    previsto_total = ZERO
    realizado_total = ZERO
    pendente_total = ZERO
    for c in costs:
        status = (c.status or "PREVISTO").upper()
        planned = c.planned_amount if c.planned_amount is not None else ZERO
        actual = c.actual_amount if c.actual_amount is not None else ZERO
        if status == "CANCELADO":
            continue
        if status != "CANCELADO":
            previsto_total += planned
        if status == "PAGO":
            realizado_total += actual
        else:
            # Ainda não pago: o que falta é o previsto (ou o realizado já lançado,
            # se maior) deste item; preserva a obrigação pendente.
            restante = planned - actual
            pendente_total += restante if restante > ZERO else ZERO

    initial_budget = pa.initial_budget if pa and pa.initial_budget is not None else None
    expected_sale = pa.expected_sale_value if pa and pa.expected_sale_value is not None else None

    # Custo total acumulado do investimento = base da análise (custo inicial, se
    # congelado) + realizado pós-arrematação. Não mistura com previsto para não
    # inflar o pago. Quando não há orçamento inicial, usa só o pós-arrematação.
    base = initial_budget if initial_budget is not None else ZERO
    custo_acumulado = base + realizado_total

    # Variação entre previsto e realizado (apenas itens já pagos têm realizado).
    variacao = realizado_total - previsto_total

    # Custo de saída da operação (corretagem + tributo da venda). REUSO do motor
    # determinístico: lido de build_finance (NÃO recalculado aqui), para que o
    # lucro/ROI do pós-arrematação usem a MESMA definição do Financeiro (resultado
    # líquido = V - custo_saida - custo_total), evitando ROIs divergentes para o
    # mesmo imóvel. build_finance permanece a fonte, intacto.
    custo_saida = ZERO
    prop = db.get(models.Property, property_id)
    if prop is not None:
        fin = build_finance(prop)
        cs = fin.get("custo_saida")
        if cs is not None:
            custo_saida = cs if isinstance(cs, Decimal) else Decimal(str(cs))

    lucro = None
    roi = None
    if expected_sale is not None and custo_acumulado > ZERO:
        # Alinhado ao Financeiro: lucro = venda - custo de saída - custo acumulado.
        lucro = expected_sale - custo_saida - custo_acumulado
        roi = lucro / custo_acumulado

    return {
        "ativado": pa is not None,
        "status": pa.status if pa else None,
        "orcamento_inicial": initial_budget,
        "valor_venda_estimado": expected_sale,
        "custo_saida_estimado": custo_saida,
        "previsto_total": previsto_total,
        "realizado_total": realizado_total,
        "pendente_total": pendente_total,
        "variacao_previsto_realizado": variacao,
        "custo_total_acumulado": custo_acumulado,
        "lucro_estimado": lucro,
        "roi_estimado": roi,
        "qtd_custos": len(costs),
    }


# ============================================================================
# DUE DILIGENCE INTEGRADA — serviço (determinístico; sem LLM). Reusa os aggregates
# existentes (PropertyRegistration, LegalProcess, Debt, Evidence, PropertyLocation)
# e a linha do tempo (record_event/record_history). A ausência de resultado NUNCA
# vira "sem risco" (SPEC §9). Integrações externas sem credencial => NAO_CONFIGURADO
# (nunca simula sucesso).
# ============================================================================

# Critérios do checklist de localização (SPEC §7.4). Lista canônica, extensível.
LOCATION_CHECKLIST_CRITERIA: tuple[tuple[str, str], ...] = (
    ("acesso_viario", "Acesso viário"),
    ("pavimentacao", "Pavimentação e condição aparente da rua"),
    ("transporte_publico", "Transporte público"),
    ("comercio_servicos", "Comércio e serviços"),
    ("escolas_saude", "Escolas e saúde"),
    ("infraestrutura_entorno", "Infraestrutura do entorno"),
    ("vizinhanca", "Características aparentes da vizinhança"),
    ("facilidade_acesso", "Facilidade de acesso"),
    ("atratividade_locacao", "Atratividade para locação"),
    ("atratividade_revenda", "Atratividade para revenda"),
    ("fatores_liquidez", "Fatores que possam afetar liquidez"),
)
_VALID_LOCATION_RATINGS = {"BOM", "REGULAR", "RUIM", "NAO_VERIFICADO"}


def get_due_diligence_front(db: Session, property_id: int, frente: str) -> "models.DueDiligenceFront | None":
    return db.scalar(
        select(models.DueDiligenceFront).where(
            models.DueDiligenceFront.property_id == property_id,
            models.DueDiligenceFront.frente == frente,
        )
    )


def upsert_due_diligence_front(
    db: Session,
    prop: "models.Property",
    frente: str,
    *,
    status: str,
    source: str | None = None,
    mode: str | None = None,
    summary: str | None = None,
    pendencias: list[str] | None = None,
    findings_count: int | None = None,
    consulted: bool = False,
    emit_event: bool = True,
) -> "models.DueDiligenceFront":
    """Cria/atualiza o estado de uma frente (idempotente por property+frente) e
    registra o evento/histórico na linha do tempo existente. Preserva o controle de
    revisão humana (não zera `reviewed` automaticamente)."""
    front = get_due_diligence_front(db, prop.id, frente)
    before = None
    if front is None:
        front = models.DueDiligenceFront(property_id=prop.id, frente=frente, status="NAO_INICIADO")
        db.add(front)
        db.flush()
    else:
        before = {"status": front.status, "findings_count": front.findings_count, "source": front.source}
    front.status = status
    if source is not None:
        front.source = source
    if mode is not None:
        front.mode = mode
    if summary is not None:
        front.summary = summary
    if pendencias is not None:
        front.pendencias = pendencias
    if findings_count is not None:
        front.findings_count = findings_count
    if consulted:
        front.last_consulted_at = datetime.utcnow()
    db.flush()
    if emit_event:
        after = {"status": front.status, "findings_count": front.findings_count, "source": front.source}
        event = record_event(db, prop, "DILIGENCIA_FRENTE_ATUALIZADA", "DueDiligenceFront", front.id,
                             {"frente": frente, "status": status}, ["documental", "juridico", "financeiro", "checklist"])
        record_history(db, prop, "DueDiligenceFront", front.id, "UPDATE" if before else "CREATE", before, after, event.id)
    return front


def get_property_location(db: Session, property_id: int) -> "models.PropertyLocation | None":
    return db.scalar(select(models.PropertyLocation).where(models.PropertyLocation.property_id == property_id))


def ensure_property_location(db: Session, prop: "models.Property") -> "models.PropertyLocation":
    loc = get_property_location(db, prop.id)
    if loc is None:
        loc = models.PropertyLocation(property_id=prop.id)
        db.add(loc)
        db.flush()
    return loc


def _full_address(prop: "models.Property") -> str:
    parts = [prop.address, prop.neighborhood, prop.city, prop.state]
    return ", ".join(p for p in parts if p)


def location_out(db: Session, prop: "models.Property") -> dict[str, Any]:
    """Visão da frente Localização (coordenadas, links, checklist, status de integração)."""
    from .geocoding_client import maps_link, street_view_link
    loc = get_property_location(db, prop.id)
    address = _full_address(prop)
    # Links externos SEMPRE disponíveis (não dependem de API key).
    lat = float(loc.latitude) if loc and loc.latitude is not None else None
    lng = float(loc.longitude) if loc and loc.longitude is not None else None
    maps_url = (loc.maps_url if loc and loc.maps_url else None) or maps_link(address=address, latitude=lat, longitude=lng)
    sv_url = (loc.street_view_url if loc and loc.street_view_url else None) or street_view_link(address=address, latitude=lat, longitude=lng)
    integration = "CONFIGURADO" if settings.google_maps_api_key else "NAO_CONFIGURADO"
    checklist = dict(loc.location_checklist) if loc and loc.location_checklist else {}
    criteria = [
        {"key": key, "label": label, "rating": checklist.get(key, "NAO_VERIFICADO")}
        for key, label in LOCATION_CHECKLIST_CRITERIA
    ]
    return {
        "property_id": prop.id,
        "endereco": address,
        "normalized_address": loc.normalized_address if loc else None,
        "latitude": lat,
        "longitude": lng,
        "geocode_precision": loc.geocode_precision if loc else None,
        "geocode_source": loc.geocode_source if loc else None,
        "geocoded_at": loc.geocoded_at if loc else None,
        "coordinates_confirmed": bool(loc.coordinates_confirmed) if loc else False,
        "maps_url": maps_url,
        "street_view_url": sv_url,
        "location_checklist": criteria,
        "observations": loc.observations if loc else None,
        "inspected_at": loc.inspected_at if loc else None,
        "integracao_maps": integration,
    }


def validate_location_checklist(checklist: dict[str, str] | None) -> dict[str, str]:
    """Mantém só critérios conhecidos e ratings válidos (defensivo)."""
    if not checklist:
        return {}
    known = {key for key, _ in LOCATION_CHECKLIST_CRITERIA}
    return {k: v for k, v in checklist.items() if k in known and v in _VALID_LOCATION_RATINGS}


def _front_summary_matricula(db: Session, prop: "models.Property") -> dict[str, Any]:
    """Resumo determinístico da frente Matrícula/ônus a partir do que já existe
    (PropertyRegistration + Evidences categoria MATRICULA/JURIDICO vinculadas)."""
    registration = db.scalar(
        select(models.PropertyRegistration)
        .where(models.PropertyRegistration.property_id == prop.id)
        .order_by(models.PropertyRegistration.created_at.desc())
    )
    front = get_due_diligence_front(db, prop.id, "MATRICULA")
    if registration is None:
        status = front.status if front else "NAO_INICIADO"
        return {"frente": "MATRICULA", "status": status if front else "NAO_INICIADO",
                "titular": None, "matricula": None, "fonte": "Registro de Imóveis (RI Digital) — importação manual" if settings.registro_imoveis_base_url is None else None,
                "integracao": "NAO_CONFIGURADO" if settings.registro_imoveis_base_url is None else "CONFIGURADO",
                "ultima_consulta": front.last_consulted_at if front else None,
                "pendencias": ["Matrícula atualizada não importada/consultada."],
                "achados": 0, "revisado": bool(front.reviewed) if front else False}
    return {"frente": "MATRICULA",
            "status": front.status if front else "CONSULTADO",
            "titular": registration.holder,
            "matricula": registration.registration_number,
            "cartorio": registration.registry_office,
            "comarca": registration.comarca,
            "integracao": "NAO_CONFIGURADO" if settings.registro_imoveis_base_url is None else "CONFIGURADO",
            "ultima_consulta": (front.last_consulted_at if front else None) or registration.created_at,
            "pendencias": (front.pendencias if front and front.pendencias else []),
            "achados": 1, "revisado": bool(front.reviewed) if front else False}


def _front_summary_judicial(db: Session, prop: "models.Property") -> dict[str, Any]:
    processes = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == prop.id)).all()
    relevantes = [p for p in processes if (p.correlation_level or "").upper() in {"ALTA", "MEDIA"}]
    homonimos = [p for p in processes if (p.correlation_level or "").upper() == "BAIXA"]
    front = get_due_diligence_front(db, prop.id, "JUDICIAL")
    integ = "CONFIGURADO"  # Judicial API já integrada (consumidor HTTP)
    status = front.status if front else ("CONSULTADO" if processes else "NAO_INICIADO")
    pend = list(front.pendencias) if front and front.pendencias else []
    if homonimos:
        pend.append(f"{len(homonimos)} processo(s) com correlação BAIXA (possível homônimo) — revisar.")
    return {"frente": "JUDICIAL", "status": status, "integracao": integ,
            "processos": len(processes), "relevantes": len(relevantes), "homonimos": len(homonimos),
            "ultima_consulta": front.last_consulted_at if front else None,
            "pendencias": pend, "achados": len(processes),
            "revisado": bool(front.reviewed) if front else False}


def _front_summary_prefeitura(db: Session, prop: "models.Property") -> dict[str, Any]:
    debts = db.scalars(select(models.Debt).where(models.Debt.property_id == prop.id)).all()
    municipais = [d for d in debts if "IPTU" in (d.category or "").upper() or "PREFEITURA" in (d.creditor or "").upper()]
    total = sum((d.amount or Decimal("0")) for d in municipais if (d.status or "").upper() != "QUITADO")
    front = get_due_diligence_front(db, prop.id, "PREFEITURA")
    integ = "NAO_CONFIGURADO" if settings.prefeitura_api_base_url is None else "CONFIGURADO"
    pend = list(front.pendencias) if front and front.pendencias else []
    nao_confirmados = [d for d in municipais if (d.status or "").upper() in {"INFORMADO", "ESTIMADO", "PENDENTE"}]
    if nao_confirmados:
        pend.append(f"{len(nao_confirmados)} débito(s) municipal(is) não confirmado(s) na fonte.")
    status = front.status if front else ("CONSULTADO" if municipais else "NAO_INICIADO")
    return {"frente": "PREFEITURA", "status": status, "integracao": integ,
            "debitos_municipais": len(municipais), "total_em_aberto": total,
            "ultima_consulta": front.last_consulted_at if front else None,
            "pendencias": pend, "achados": len(municipais),
            "revisado": bool(front.reviewed) if front else False}


def _front_summary_localizacao(db: Session, prop: "models.Property") -> dict[str, Any]:
    loc = get_property_location(db, prop.id)
    front = get_due_diligence_front(db, prop.id, "LOCALIZACAO")
    integ = "CONFIGURADO" if settings.google_maps_api_key else "NAO_CONFIGURADO"
    geocoded = bool(loc and loc.latitude is not None and loc.longitude is not None)
    confirmed = bool(loc and loc.coordinates_confirmed)
    pend = list(front.pendencias) if front and front.pendencias else []
    if not geocoded:
        pend.append("Coordenadas não geocodificadas/confirmadas.")
    elif not confirmed:
        pend.append("Ponto no mapa ainda não confirmado como a unidade.")
    status = front.status if front else ("CONSULTADO" if geocoded else "NAO_INICIADO")
    return {"frente": "LOCALIZACAO", "status": status, "integracao": integ,
            "geocodificado": geocoded, "coordenadas_confirmadas": confirmed,
            "ultima_consulta": (front.last_consulted_at if front else None) or (loc.geocoded_at if loc else None),
            "pendencias": pend, "achados": 1 if geocoded else 0,
            "revisado": bool(front.reviewed) if front else False}


def due_diligence_overview(db: Session, prop: "models.Property") -> dict[str, Any]:
    """Visão consolidada das 4 frentes (orquestrador). Reusa os aggregates; não
    dispara consultas (só leitura). Expõe status, fonte, achados e pendências por
    frente, para o dossiê distinguir consultado × sem ocorrência × não consultado ×
    não configurado × falhou × necessita revisão."""
    return {
        "property_id": prop.id,
        "frentes": {
            "MATRICULA": _front_summary_matricula(db, prop),
            "JUDICIAL": _front_summary_judicial(db, prop),
            "PREFEITURA": _front_summary_prefeitura(db, prop),
            "LOCALIZACAO": _front_summary_localizacao(db, prop),
        },
        "localizacao": location_out(db, prop),
    }


# Mapa frente → canonical_key do Checklist Mestre que recebe a diligência pendente.
# Reutiliza itens existentes (checklist.py). Nunca cria conclusão jurídica.
_DD_CHECKLIST_KEYS = {
    "MATRICULA": "CONSOLIDACAO_REGISTRADA",     # registros/averbações da matrícula
    "JUDICIAL": "ACAO_QUESTIONAMENTO",          # ações que questionam o leilão/execução
    "PREFEITURA": "RESPONSABILIDADE_DEBITOS",   # IPTU/condomínio em atraso
    "LOCALIZACAO": "REGIAO_SERVICOS",           # região/serviços/acesso
}
_DD_CHECKLIST_MANUAL_STATES = {"CONFIRMADO", "NAO_APLICAVEL", "RISCO_IDENTIFICADO"}


def reflect_due_diligence_signals(db: Session, prop: "models.Property", frente: str, pendencias: list[str], evidence: "models.Evidence | None" = None) -> bool:
    """Reflete uma pendência de due diligence como NECESSIDADE DE DILIGÊNCIA (ATENCAO)
    no item de checklist correspondente da execução CORRENTE — sem LLM e sem criar
    nova versão de análise. Reusa o padrão do judicial_integration (nunca CONFIRMADO;
    preserva estados manuais). A ausência de resultado não vira "sem risco".

    Retorna True se marcou o item (para o chamador acionar recálculo de risco/veredito
    da versão corrente, se desejar)."""
    if not pendencias:
        return False
    target_key = _DD_CHECKLIST_KEYS.get(frente)
    if not target_key:
        return False
    execution = latest_execution(prop)
    if execution is None:
        return False
    for res in execution.results:
        item = res.item
        if item is None or item.canonical_key != target_key:
            continue
        if res.state in _DD_CHECKLIST_MANUAL_STATES:
            return False
        res.state = "ATENCAO"
        res.risk = "; ".join(pendencias)[:2000]
        if not (res.answer or "").strip():
            res.answer = "Diligência recomendada a partir da investigação de due diligence."
        db.flush()
        if evidence is not None:
            exists = db.scalar(
                select(models.ChecklistEvidence).where(
                    models.ChecklistEvidence.checklist_result_id == res.id,
                    models.ChecklistEvidence.evidence_id == evidence.id,
                )
            )
            if exists is None:
                db.add(models.ChecklistEvidence(checklist_result_id=res.id, evidence_id=evidence.id))
                db.flush()
        return True
    return False
