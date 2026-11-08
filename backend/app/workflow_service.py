"""Serviço de workflow operacional (Onda 2) — liga o motor puro F0–F13 aos domínios.

Responsabilidades (o engine permanece PURO; aqui mora o I/O):
  - criar/obter a ``Opportunity`` + ``OpportunityWorkflow`` (cache do estado);
  - montar o ``OpportunityContext`` AGREGANDO os domínios reais (checklist, riscos,
    due diligence, financeiro, modalidade) — este é o "serviço de leitura" previsto
    na SPEC-WORKFLOW-ENGINE;
  - listar transições disponíveis, decidir e PERSISTIR a transição de forma
    APPEND-ONLY (`WorkflowTransition`), atualizando o cache `OpportunityWorkflow`;
  - invalidação por evento (marca fases reabertas) e isolamento por oportunidade;
  - auditoria (actor + justificativa + snapshot de gates/hard stops).

Reuso-first: `workflow_engine`/`workflow_rules` (regras), `modality_rules`
(aplicabilidade/hard stops por modalidade), `record_event`/`record_history` (trilha).
Determinístico; sem LLM. Nunca altera resultados históricos nem o imóvel 633.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, workflow_engine as engine, workflow_rules as rules, modality_rules
from .services import (
    latest_execution, build_finance, due_diligence_overview, record_event, record_history, serialize,
)


class WorkflowError(ValueError):
    """Erro de operação de workflow (oportunidade inexistente, transição inválida)."""


# ---------------------------------------------------------------------------
# Oportunidade + cache de workflow
# ---------------------------------------------------------------------------

def create_opportunity(db: Session, data: dict[str, Any], *, actor: str = "sistema") -> models.Opportunity:
    prop = db.get(models.Property, data["property_id"])
    if prop is None:
        raise WorkflowError("property_id inexistente")
    modality = modality_rules.normalize(data.get("modality"))
    opp = models.Opportunity(
        property_id=prop.id, codigo=data.get("codigo"), modality=modality,
        origin=data.get("origin"), portal=data.get("portal"), external_id=data.get("external_id"),
        status="EM_PROSPECCAO", opened_at=datetime.utcnow(), actor=actor,
    )
    db.add(opp); db.flush()
    wf = models.OpportunityWorkflow(
        opportunity_id=opp.id, current_phase="F0_INTAKE", phase_states={}, active_hard_stops=[],
        ruleset_version=rules.WORKFLOW_RULESET_VERSION, blocked=False, updated_by=actor,
    )
    db.add(wf); db.flush()
    record_event(db, prop, "OPORTUNIDADE_CRIADA", "Opportunity", opp.id,
                 {"modality": modality, "codigo": opp.codigo}, ["workflow"])
    return opp


def get_opportunity(db: Session, opportunity_id: int) -> models.Opportunity:
    opp = db.get(models.Opportunity, opportunity_id)
    if opp is None:
        raise WorkflowError("Oportunidade não encontrada")
    return opp


def _ensure_workflow(db: Session, opp: models.Opportunity) -> models.OpportunityWorkflow:
    if opp.workflow is not None:
        return opp.workflow
    wf = models.OpportunityWorkflow(
        opportunity_id=opp.id, current_phase="F0_INTAKE", phase_states={}, active_hard_stops=[],
        ruleset_version=rules.WORKFLOW_RULESET_VERSION, blocked=False,
    )
    db.add(wf); db.flush()
    return wf


# ---------------------------------------------------------------------------
# Montagem do contexto a partir dos domínios reais (serviço de leitura)
# ---------------------------------------------------------------------------

def _collect_hard_stop_signals(db: Session, opp: models.Opportunity) -> list[engine.HardStopSignal]:
    """Deriva os sinais de hard stop dos domínios (determinístico). Hard stops
    específicos de modalidade são suprimidos conforme o ruleset de modalidade."""
    prop = db.get(models.Property, opp.property_id)
    signals: list[engine.HardStopSignal] = []
    suppressed = set(modality_rules.suppressed_hard_stops(opp.modality))

    # Risco jurídico crítico ativo.
    risco_critico = db.scalar(
        select(models.Risk).where(
            models.Risk.property_id == opp.property_id,
            models.Risk.category == "juridico",
            models.Risk.severity == "CRITICA",
            models.Risk.status == "ATIVO",
        )
    )
    if risco_critico is not None:
        signals.append(engine.HardStopSignal("RISCO_JURIDICO_CRITICO", "CONFIRMADO", "Risco jurídico crítico ativo."))

    # Checklist CONSOLIDACAO_REGISTRADA != CONFIRMADO (só extrajudicial AF).
    execution = latest_execution(prop) if prop else None
    if execution is not None:
        for res in execution.results:
            item = res.item
            if item is None:
                continue
            if item.canonical_key == "CONSOLIDACAO_REGISTRADA" and res.state != "CONFIRMADO":
                if "CONSOLIDACAO_NAO_REGISTRADA" not in suppressed:
                    signals.append(engine.HardStopSignal("CONSOLIDACAO_NAO_REGISTRADA", "CONFIRMADO", "Consolidação não registrada na matrícula."))
            if item.canonical_key in {"INTIMACAO_PESSOAL", "INTIMACAO_EDITAL"} and res.state == "RISCO_IDENTIFICADO":
                if "INTIMACAO_MORA_AUSENTE" not in suppressed:
                    signals.append(engine.HardStopSignal("INTIMACAO_MORA_AUSENTE", "CONFIRMADO", "Intimação de mora ausente/insuficiente."))

    # Financeiro: lance acima do preço máximo aprovado.
    if prop is not None:
        try:
            fin = build_finance(prop)
            preco_max = fin.get("preco_maximo")
            aquisicao = fin.get("valor_aquisicao")
            if preco_max is not None and aquisicao is not None and aquisicao > preco_max:
                signals.append(engine.HardStopSignal("PRECO_ACIMA_MAXIMO", "CONFIRMADO", "Lance acima do preço máximo."))
        except Exception:
            pass  # financeiro incompleto não é hard stop; apenas não sinaliza

    # Remove duplicatas preservando ordem.
    seen: set[str] = set()
    unique: list[engine.HardStopSignal] = []
    for s in signals:
        if s.code not in seen and s.code not in suppressed:
            unique.append(s); seen.add(s.code)
    return unique


def _satisfied_gates(db: Session, opp: models.Opportunity, wf: models.OpportunityWorkflow) -> frozenset[str]:
    """Gates satisfeitos a partir do cache de ``phase_states`` + marcações manuais."""
    satisfied = set()
    for phase, state in (wf.phase_states or {}).items():
        if str(state).upper() in rules.PHASE_STATES_SATISFEITOS:
            satisfied.add(phase)
    return frozenset(satisfied)


def build_context(db: Session, opp: models.Opportunity) -> engine.OpportunityContext:
    wf = _ensure_workflow(db, opp)
    signals = _collect_hard_stop_signals(db, opp)
    return engine.OpportunityContext(
        opportunity_id=opp.id,
        current_phase=wf.current_phase,
        phase_state=str((wf.phase_states or {}).get(wf.current_phase, "NAO_INICIADA")),
        modality=opp.modality,
        status=opp.status,
        hard_stop_signals=tuple(signals),
        satisfied_gates=_satisfied_gates(db, opp, wf),
        committee_decision=_latest_committee_decision(opp),
        ruleset_version=rules.WORKFLOW_RULESET_VERSION,
    )


def _latest_committee_decision(opp: models.Opportunity) -> str | None:
    for t in reversed(opp.transitions):
        if t.decision:
            return t.decision
    return None


# ---------------------------------------------------------------------------
# Leitura: estado, transições disponíveis, hard stops, pendências
# ---------------------------------------------------------------------------

def phase_evaluation(db: Session, opp: models.Opportunity) -> dict[str, Any]:
    return engine.evaluate_phase(build_context(db, opp)).to_dict()


def available_transitions(db: Session, opp: models.Opportunity) -> list[dict[str, Any]]:
    """Lista transições candidatas (AVANÇO a partir da matriz + DESCARTE) com a
    decisão do engine para cada uma (permitida/bloqueada + motivo)."""
    ctx = build_context(db, opp)
    out: list[dict[str, Any]] = []
    for target in sorted(rules.forward_targets(ctx.current_phase)):
        out.append(engine.can_transition(ctx, target, "AVANCO").to_dict())
    # DESCARTE sempre ofertado (exige justificativa no serviço).
    out.append(engine.can_transition(ctx, ctx.current_phase, "DESCARTE").to_dict())
    return out


def hard_stops(db: Session, opp: models.Opportunity) -> list[dict[str, Any]]:
    ctx = build_context(db, opp)
    active = engine.compute_hard_stops(ctx)
    return [
        {
            "code": code,
            "description": rules.HARD_STOPS.get(code, {}).get("origin", ""),
            "blocks_phase": rules.HARD_STOPS.get(code, {}).get("blocks_phase"),
            "gravidade": "IMPEDITIVO",
            "acao_necessaria": f"Resolver {code} com evidência antes de avançar.",
        }
        for code in active
    ]


def pending_items(db: Session, opp: models.Opportunity) -> dict[str, Any]:
    """Pendências que afetam o avanço: hard stops ativos + fases não satisfeitas +
    checklist aplicável pendente (por modalidade)."""
    ev = phase_evaluation(db, opp)
    prop = db.get(models.Property, opp.property_id)
    execution = latest_execution(prop) if prop else None
    all_keys = tuple(r.item.canonical_key for r in execution.results if r.item) if execution else ()
    aplicaveis = modality_rules.applicable_checklist_keys(opp.modality, all_keys)
    pendentes = []
    if execution:
        for res in execution.results:
            item = res.item
            if item and item.canonical_key in aplicaveis and res.state in {"PENDENTE", "EM_ANALISE", "ATENCAO", "RISCO_IDENTIFICADO"}:
                pendentes.append({"canonical_key": item.canonical_key, "state": res.state})
    return {
        "fase": ev["phase"], "bloqueado": ev["blocked"],
        "hard_stops": ev["active_hard_stops"],
        "checklist_pendente": pendentes,
        "proxima_acao": ev["next_action"],
    }


# ---------------------------------------------------------------------------
# Escrita: executar transição (append-only) + auditoria
# ---------------------------------------------------------------------------

def request_transition(
    db: Session, opp: models.Opportunity, *, target_phase: str, transition_type: str = "AVANCO",
    justification: str | None = None, decision: str | None = None, actor: str = "sistema",
) -> dict[str, Any]:
    """Avalia e, se permitida, aplica a transição. Persiste SEMPRE um
    ``WorkflowTransition`` (append-only) — inclusive quando BLOQUEADA, para auditoria.
    Atualiza o cache ``OpportunityWorkflow``. Hard stop ativo nunca é contornável."""
    wf = _ensure_workflow(db, opp)
    ctx = build_context(db, opp)
    ttype = (transition_type or "AVANCO").upper()

    # DESCARTE/RETROCESSO exigem justificativa (regra do serviço — SPEC §4).
    if ttype in {"DESCARTE", "RETROCESSO"} and not (justification and justification.strip()):
        raise WorkflowError(f"{ttype} exige justificativa.")
    # Decisão de comitê (F8): registra a decisão no contexto para o engine avaliar F8->F9.
    if decision:
        ctx = engine.OpportunityContext(
            **{**ctx.__dict__, "committee_decision": decision}
        )

    verdict = engine.can_transition(ctx, target_phase, ttype)
    prop = db.get(models.Property, opp.property_id)
    evaluation = engine.evaluate_phase(ctx)

    transition = models.WorkflowTransition(
        opportunity_id=opp.id, from_phase=ctx.current_phase, to_phase=target_phase,
        transition_type=ttype, result=verdict.result, phase_state=evaluation.phase_state,
        hard_stops=list(verdict.active_hard_stops), gate_snapshot={"gate_satisfied": evaluation.gate_satisfied},
        score_snapshot={}, decision=decision, justification=justification,
        actor=actor, ruleset_version=rules.WORKFLOW_RULESET_VERSION,
    )
    db.add(transition); db.flush()

    if verdict.allowed:
        # Aplica a transição ao cache. Marca a fase de origem como satisfeita no avanço.
        states = dict(wf.phase_states or {})
        if ttype == "AVANCO":
            states[ctx.current_phase] = "CONCLUIDA"
            wf.current_phase = target_phase
        elif ttype in {"RETROCESSO", "REABERTURA"}:
            states[target_phase] = "REABERTA"
            wf.current_phase = target_phase
        elif ttype == "DESCARTE":
            opp.status = "DESCARTADA"; opp.closed_at = datetime.utcnow(); opp.close_reason = justification
        elif ttype == "PERDA":
            opp.status = "PERDIDA"; opp.closed_at = datetime.utcnow()
        wf.phase_states = states
        wf.active_hard_stops = list(verdict.active_hard_stops)
        wf.blocked = bool(verdict.active_hard_stops)
        wf.updated_by = actor
        # Status de alto nível coerente com a fase.
        if ttype == "AVANCO":
            opp.status = _status_for_phase(wf.current_phase, opp.status)
        db.flush()

    if prop is not None:
        record_event(db, prop, "WORKFLOW_TRANSICAO", "WorkflowTransition", transition.id,
                     {"from": ctx.current_phase, "to": target_phase, "type": ttype, "result": verdict.result}, ["workflow"])
        record_history(db, prop, "WorkflowTransition", transition.id, "CREATE", None,
                       {"result": verdict.result, "to": target_phase}, None)

    return {
        "decision": verdict.to_dict(),
        "transition_id": transition.id,
        "workflow": _workflow_out(wf, opp),
    }


def set_phase_state(
    db: Session, opp: models.Opportunity, *, phase: str | None = None, state: str,
    justification: str | None = None, actor: str = "sistema",
) -> dict[str, Any]:
    """Marca o estado de uma fase no cache (ex.: concluir o gate de saída para habilitar
    o AVANÇO). O motor permanece puro; aqui apenas persistimos o estado declarado pelo
    operador, com auditoria. Não pula hard stops — o AVANÇO continua sendo avaliado pelo
    engine, que bloqueia se houver hard stop ativo na fase."""
    wf = _ensure_workflow(db, opp)
    target_phase = phase or wf.current_phase
    norm_state = str(state or "").strip().upper()
    if not rules.is_phase(target_phase):
        raise WorkflowError(f"Fase desconhecida: {target_phase}")
    if norm_state not in rules.PHASE_STATES:
        raise WorkflowError(f"Estado de fase inválido: {state}")
    states = dict(wf.phase_states or {})
    before = states.get(target_phase)
    states[target_phase] = norm_state
    wf.phase_states = states
    wf.updated_by = actor
    # Recalcula bloqueio da fase corrente a partir do contexto (hard stops reais).
    ctx = build_context(db, opp)
    wf.active_hard_stops = list(engine.compute_hard_stops(ctx))
    db.flush()
    prop = db.get(models.Property, opp.property_id)
    if prop is not None:
        record_event(db, prop, "WORKFLOW_FASE_ESTADO", "OpportunityWorkflow", wf.id,
                     {"phase": target_phase, "before": before, "after": norm_state}, ["workflow"])
    return {"phase": target_phase, "before": before, "after": norm_state, "workflow": _workflow_out(wf, opp)}


def _status_for_phase(phase: str, current: str) -> str:
    mapping = {
        "F8_COMITE_DECISAO": "EM_DECISAO",
        "F9_LANCE_PAGAMENTO": "APROVADA",
        "F10_TRANSFERENCIA_REGISTRO": "ADQUIRIDA",
        "F13_ENCERRAMENTO": "ENCERRADA",
    }
    if phase in ("F1_TRIAGEM", "F2_DOCUMENTOS") and current == "EM_PROSPECCAO":
        return "EM_ANALISE"
    if rules.phase_index(phase) >= rules.phase_index("F3_JURIDICO_REGISTRAL") and current in ("EM_PROSPECCAO", "EM_ANALISE"):
        current = "EM_ANALISE"
    return mapping.get(phase, current)


def _workflow_out(wf: models.OpportunityWorkflow, opp: models.Opportunity) -> dict[str, Any]:
    return {
        "opportunity_id": opp.id, "current_phase": wf.current_phase,
        "phase_states": wf.phase_states, "active_hard_stops": wf.active_hard_stops,
        "blocked": wf.blocked, "status": opp.status, "modality": opp.modality,
        "ruleset_version": wf.ruleset_version,
    }


def workflow_out(db: Session, opp: models.Opportunity) -> dict[str, Any]:
    return _workflow_out(_ensure_workflow(db, opp), opp)


def transition_history(db: Session, opp: models.Opportunity) -> list[dict[str, Any]]:
    return [
        {
            "id": t.id, "from_phase": t.from_phase, "to_phase": t.to_phase,
            "transition_type": t.transition_type, "result": t.result, "phase_state": t.phase_state,
            "hard_stops": t.hard_stops, "decision": t.decision, "justification": t.justification,
            "actor": t.actor, "ruleset_version": t.ruleset_version, "created_at": t.created_at,
        }
        for t in opp.transitions
    ]


# ---------------------------------------------------------------------------
# Invalidação por evento (marca fases reabertas; NÃO recalcula, NÃO apaga)
# ---------------------------------------------------------------------------

def invalidate_on_event(db: Session, opp: models.Opportunity, event_type: str, *, actor: str = "sistema") -> list[str]:
    """Marca as fases afetadas por ``event_type`` como REABERTA no cache (SPEC §7).
    Append-only: não apaga análises; só sinaliza necessidade de reprocessamento."""
    affected = rules.INVALIDATION_EVENTS.get(event_type, ())
    if not affected:
        return []
    wf = _ensure_workflow(db, opp)
    states = dict(wf.phase_states or {})
    reopened: list[str] = []
    for phase in affected:
        if states.get(phase) in {"CONCLUIDA", "CONCLUIDA_COM_RESSALVA"}:
            states[phase] = "REABERTA"; reopened.append(phase)
    if reopened:
        wf.phase_states = states
        wf.blocked = True if wf.current_phase in reopened else wf.blocked
        db.flush()
        prop = db.get(models.Property, opp.property_id)
        if prop is not None:
            record_event(db, prop, "WORKFLOW_INVALIDACAO", "OpportunityWorkflow", wf.id,
                         {"event": event_type, "reopened": reopened}, ["workflow"])
    return reopened


# ---------------------------------------------------------------------------
# Modalidade: classificação determinística + correção manual auditada
# ---------------------------------------------------------------------------

def classify_and_apply_modality(
    db: Session, opp: models.Opportunity, *, signals_text: str | None, origin: str | None,
    evidence_id: int | None, confirm: bool, actor: str = "sistema",
) -> dict[str, Any]:
    decision = modality_rules.classify_modality(
        signals_text=signals_text, origin=origin, has_evidence=evidence_id is not None,
    )
    applied = False
    if confirm and evidence_id is not None and decision["modality"] != "INDEFINIDO":
        opp.modality = decision["modality"]
        opp.modality_evidence_id = evidence_id
        db.flush()
        applied = True
        prop = db.get(models.Property, opp.property_id)
        if prop is not None:
            record_event(db, prop, "MODALIDADE_CLASSIFICADA", "Opportunity", opp.id,
                         {"modality": opp.modality, "confidence": decision["confidence"]}, ["workflow", "juridico"])
    decision["applied"] = applied
    decision["opportunity_modality"] = opp.modality
    return decision


def correct_modality(
    db: Session, opp: models.Opportunity, *, modality: str, justification: str,
    evidence_id: int | None, actor: str = "sistema",
) -> dict[str, Any]:
    before = opp.modality
    opp.modality = modality_rules.normalize(modality)
    if evidence_id is not None:
        opp.modality_evidence_id = evidence_id
    db.flush()
    prop = db.get(models.Property, opp.property_id)
    if prop is not None:
        event = record_event(db, prop, "MODALIDADE_CORRIGIDA", "Opportunity", opp.id,
                             {"before": before, "after": opp.modality, "actor": actor}, ["workflow", "juridico"])
        record_history(db, prop, "Opportunity", opp.id, "UPDATE", {"modality": before},
                       {"modality": opp.modality, "justification": justification}, event.id)
    return {"before": before, "after": opp.modality, "justification": justification}


def checklist_applicability_view(db: Session, opp: models.Opportunity) -> dict[str, Any]:
    """Aplicabilidade do checklist (27 keys preservadas) sob a modalidade da oportunidade."""
    from .checklist import master_items
    items = master_items()
    out = []
    for it in items:
        key = it["canonical_key"]
        out.append({"canonical_key": key, "aplicabilidade": modality_rules.checklist_applicability(opp.modality, key)})
    return {"modality": opp.modality, "itens": out, "ruleset_version": modality_rules.MODALITY_RULESET_VERSION}
