"""Router operacional de Oportunidades + Workflow (Onda 2).

Expõe o ciclo de vida F0–F13 (motor puro reusado) e a classificação de modalidade.
Leitura exige usuário autenticado; escrita (criar/transição/modalidade) exige a
permissão ``analysis:write`` (ADMIN/ANALISTA/OPERADOR) — validado no backend. Hard
stop ativo NUNCA é contornável pelo cliente.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, workflow_service as wf, modality_rules
from ..auth import get_current_user
from ..authz import require_permission, PERM_ANALYSIS_WRITE
from ..database import get_db
from ..services import serialize

router = APIRouter(prefix="/api/oportunidades", tags=["oportunidades"])


def _opp_or_404(db: Session, opportunity_id: int) -> models.Opportunity:
    try:
        return wf.get_opportunity(db, opportunity_id)
    except wf.WorkflowError as exc:
        raise HTTPException(404, str(exc)) from exc


def authorized_writer(
    user: models.User = Depends(get_current_user),
    _role: str = Depends(require_permission(PERM_ANALYSIS_WRITE)),
) -> models.User:
    """Escrita operacional: resolve o usuário autenticado real (ator da auditoria) E
    valida a permissão ``analysis:write`` (backend). ``get_current_user`` roda primeiro:
    sem Bearer → 401 (não 503). Papel sem a permissão → 403. ``require_permission``
    retorna o PAPEL (string); o ator precisa do usuário."""
    return user


# --- Catálogo de modalidades (leitura autenticada) ---
@router.get("/modalidades")
def list_modalities(_: models.User = Depends(get_current_user)):
    return {"ruleset_version": modality_rules.MODALITY_RULESET_VERSION,
            "modalidades": [{"code": c, **modality_rules.MODALITY_CATALOG[c]} for c in modality_rules.MODALITIES]}


# --- CRUD/listagem de oportunidades ---
@router.get("")
def list_opportunities(
    municipality: str | None = Query(default=None),
    modality: str | None = Query(default=None),
    status: str | None = Query(default=None),
    phase: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), _: models.User = Depends(get_current_user),
):
    stmt = select(models.Opportunity).join(models.Property, models.Opportunity.property_id == models.Property.id)
    if modality:
        stmt = stmt.where(models.Opportunity.modality == modality)
    if status:
        stmt = stmt.where(models.Opportunity.status == status)
    if municipality:
        stmt = stmt.where(models.Property.city == municipality)
    rows = db.scalars(stmt.order_by(models.Opportunity.id.desc())).all()
    if phase:
        rows = [o for o in rows if (o.workflow and o.workflow.current_phase == phase)]
    total = len(rows)
    page = rows[offset:offset + limit]
    itens = []
    for o in page:
        prop = db.get(models.Property, o.property_id)
        itens.append({
            **schemas.OpportunityOut.model_validate(o).model_dump(mode="json"),
            "municipio": prop.city if prop else None,
            "current_phase": o.workflow.current_phase if o.workflow else "F0_INTAKE",
            "blocked": bool(o.workflow.blocked) if o.workflow else False,
        })
    return {"total": total, "limit": limit, "offset": offset, "itens": itens}


@router.post("", status_code=201)
def create_opportunity(data: schemas.OpportunityCreate, db: Session = Depends(get_db), user: models.User = Depends(authorized_writer)):
    try:
        opp = wf.create_opportunity(db, data.model_dump(), actor=_actor(user))
    except wf.WorkflowError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit(); db.refresh(opp)
    return {"oportunidade": schemas.OpportunityOut.model_validate(opp).model_dump(mode="json"), "workflow": wf.workflow_out(db, opp)}


@router.get("/{opportunity_id}")
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    prop = db.get(models.Property, opp.property_id)
    return {
        "oportunidade": schemas.OpportunityOut.model_validate(opp).model_dump(mode="json"),
        "imovel": {"id": prop.id, "title": prop.title, "city": prop.city, "state": prop.state} if prop else None,
        "workflow": wf.workflow_out(db, opp),
        "fase": serialize(wf.phase_evaluation(db, opp)),
    }


@router.get("/{opportunity_id}/estado")
def get_state(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    return serialize(wf.phase_evaluation(db, opp))


@router.get("/{opportunity_id}/transicoes")
def list_transitions(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    return {"opportunity_id": opp.id, "transicoes": serialize(wf.available_transitions(db, opp))}


@router.get("/{opportunity_id}/hard-stops")
def get_hard_stops(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    return {"opportunity_id": opp.id, "hard_stops": serialize(wf.hard_stops(db, opp))}


@router.get("/{opportunity_id}/pendencias")
def get_pending(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    return serialize(wf.pending_items(db, opp))


@router.get("/{opportunity_id}/historico")
def get_history(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    return {"opportunity_id": opp.id, "historico": serialize(wf.transition_history(db, opp))}


@router.get("/{opportunity_id}/checklist-aplicavel")
def get_checklist_applicability(opportunity_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opp = _opp_or_404(db, opportunity_id)
    return serialize(wf.checklist_applicability_view(db, opp))


@router.post("/{opportunity_id}/transicao")
def request_transition(opportunity_id: int, data: schemas.TransitionRequest, db: Session = Depends(get_db), user: models.User = Depends(authorized_writer)):
    opp = _opp_or_404(db, opportunity_id)
    try:
        out = wf.request_transition(
            db, opp, target_phase=data.target_phase, transition_type=data.transition_type,
            justification=data.justification, decision=data.decision, actor=_actor(user),
        )
    except wf.WorkflowError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit()
    return serialize(out)


@router.post("/{opportunity_id}/fase/estado")
def set_phase_state(opportunity_id: int, data: schemas.PhaseStateRequest, db: Session = Depends(get_db), user: models.User = Depends(authorized_writer)):
    opp = _opp_or_404(db, opportunity_id)
    try:
        out = wf.set_phase_state(db, opp, phase=data.phase, state=data.state, justification=data.justification, actor=_actor(user))
    except wf.WorkflowError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit()
    return serialize(out)


@router.post("/{opportunity_id}/reavaliar")
def reevaluate(opportunity_id: int, db: Session = Depends(get_db), user: models.User = Depends(authorized_writer)):
    opp = _opp_or_404(db, opportunity_id)
    out = {"fase": serialize(wf.phase_evaluation(db, opp)), "hard_stops": serialize(wf.hard_stops(db, opp))}
    db.commit()
    return out


@router.post("/{opportunity_id}/modalidade/classificar")
def classify_modality(opportunity_id: int, data: schemas.ModalityClassifyRequest, db: Session = Depends(get_db), user: models.User = Depends(authorized_writer)):
    opp = _opp_or_404(db, opportunity_id)
    out = wf.classify_and_apply_modality(
        db, opp, signals_text=data.signals_text, origin=data.origin,
        evidence_id=data.evidence_id, confirm=data.confirm, actor=_actor(user),
    )
    db.commit()
    return serialize(out)


@router.post("/{opportunity_id}/modalidade/corrigir")
def correct_modality(opportunity_id: int, data: schemas.ModalityCorrectRequest, db: Session = Depends(get_db), user: models.User = Depends(authorized_writer)):
    opp = _opp_or_404(db, opportunity_id)
    out = wf.correct_modality(db, opp, modality=data.modality, justification=data.justification, evidence_id=data.evidence_id, actor=_actor(user))
    db.commit()
    return serialize(out)


def _actor(user: models.User) -> str:
    return f"user:{user.id}:{user.email}"
