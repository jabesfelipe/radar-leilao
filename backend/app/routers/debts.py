"""Router da Central de Débitos/Despesas por imóvel (Etapa A).

Registro manual normalizado + leitura/consolidação por natureza (totais separados).
Determinístico, sem consulta externa. Reusa `Evidence`/`DomainEvent`/`EntityHistory`
e NÃO altera `Debt`/`Cost`/`build_finance` (a consolidação é leitura). Preserva o
endpoint legado `/dividas` (intacto em main.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, debts_service
from ..database import get_db
from ..services import record_event, record_history, serialize
from .deps import property_or_404

router = APIRouter(tags=["debitos"])


@router.get("/api/imoveis/{property_id}/debitos")
def list_property_debts(property_id: int, db: Session = Depends(get_db)):
    """Lista os débitos NORMALIZADOS do imóvel + a consolidação por natureza.
    Também expõe o legado (`Debt`) para transparência (sem dupla contagem no total)."""
    property_or_404(db, property_id)
    rows = db.scalars(
        select(models.PropertyDebt).where(models.PropertyDebt.property_id == property_id).order_by(models.PropertyDebt.id)
    ).all()
    legacy = db.scalars(select(models.Debt).where(models.Debt.property_id == property_id).order_by(models.Debt.id)).all()
    return {
        "property_id": property_id,
        "debitos": [schemas.PropertyDebtOut.model_validate(d).model_dump() for d in rows],
        "legado_debts": [{"id": d.id, "category": d.category, "creditor": d.creditor, "amount": d.amount, "status": d.status} for d in legacy],
        "consolidacao": serialize(debts_service.consolidate(db, property_id)),
    }


@router.get("/api/imoveis/{property_id}/debitos/consolidacao")
def get_debts_consolidation(property_id: int, db: Session = Depends(get_db)):
    """Consolidação por natureza (confirmados/informados/estimados/despesas previstas/
    não apurados) + exposição de passivo com ressalva. Leitura pura (não dispara nada)."""
    property_or_404(db, property_id)
    return serialize(debts_service.consolidate(db, property_id))


@router.get("/api/imoveis/{property_id}/debitos/{debt_id}")
def get_property_debt(property_id: int, debt_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id)
    d = db.get(models.PropertyDebt, debt_id)
    if not d or d.property_id != property_id:
        raise HTTPException(404, "Débito não encontrado para o imóvel")
    return schemas.PropertyDebtOut.model_validate(d).model_dump()


@router.post("/api/imoveis/{property_id}/debitos", status_code=201)
def create_property_debt(property_id: int, data: schemas.PropertyDebtCreate, db: Session = Depends(get_db)):
    """Registro MANUAL de débito/despesa normalizado. Valida tipo/natureza/status/
    confiabilidade (ESTIMADO nunca vira CONFIRMADO). Gera evento + histórico."""
    prop = property_or_404(db, property_id)
    try:
        payload = debts_service.normalize_debt_payload(db, data.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    item = models.PropertyDebt(property_id=property_id, **payload)
    db.add(item); db.flush()
    event = record_event(db, prop, "DEBITO_NORMALIZADO_ADICIONADO", "PropertyDebt", item.id,
                         {"debt_type_code": item.debt_type_code, "nature": item.nature, "status": item.status}, ["financeiro", "checklist"])
    record_history(db, prop, "PropertyDebt", item.id, "CREATE", None,
                   {"debt_type_code": item.debt_type_code, "status": item.status}, event.id, item.evidence_id)
    db.commit(); db.refresh(item)
    return {"debito": schemas.PropertyDebtOut.model_validate(item).model_dump(),
            "consolidacao": serialize(debts_service.consolidate(db, property_id)), "evento_id": event.id}


@router.patch("/api/imoveis/{property_id}/debitos/{debt_id}")
def update_property_debt(property_id: int, debt_id: int, data: schemas.PropertyDebtUpdate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    item = db.get(models.PropertyDebt, debt_id)
    if not item or item.property_id != property_id:
        raise HTTPException(404, "Débito não encontrado para o imóvel")
    changes = data.model_dump(exclude_unset=True)
    # Revalida natureza/status/confiabilidade quando alterados (mantém invariantes).
    merged = {**{"debt_type_code": item.debt_type_code, "nature": item.nature, "status": item.status, "reliability": item.reliability}, **changes}
    try:
        normalized = debts_service.normalize_debt_payload(db, merged)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    for field in ("nature", "status", "reliability"):
        changes[field] = normalized[field]
    before = {"status": item.status, "nature": item.nature, "updated_amount": item.updated_amount}
    for k, v in changes.items():
        setattr(item, k, v)
    db.flush()
    event = record_event(db, prop, "DEBITO_NORMALIZADO_ATUALIZADO", "PropertyDebt", item.id, {"changes": list(changes.keys())}, ["financeiro", "checklist"])
    record_history(db, prop, "PropertyDebt", item.id, "UPDATE", before, {"status": item.status, "nature": item.nature}, event.id)
    db.commit(); db.refresh(item)
    return {"debito": schemas.PropertyDebtOut.model_validate(item).model_dump(),
            "consolidacao": serialize(debts_service.consolidate(db, property_id)), "evento_id": event.id}
