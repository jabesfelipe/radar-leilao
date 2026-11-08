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

from .. import models, schemas, debts_service, debt_query_service, estimates_service
from ..database import get_db
from ..services import record_event, record_history, serialize, reflect_due_diligence_signals, upsert_due_diligence_front
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


# --- Consulta de débito (Etapa E) — declarada ANTES de /{debt_id} p/ não ser sombreada ---
@router.get("/api/imoveis/{property_id}/debitos/consultas")
def list_debt_queries(property_id: int, db: Session = Depends(get_db)):
    """Histórico de consultas de débito do imóvel (manual/assistida). Leitura pura."""
    property_or_404(db, property_id)
    return {"property_id": property_id, "consultas": serialize(debt_query_service.list_queries(db, property_id))}


@router.post("/api/imoveis/{property_id}/debitos/consultar", status_code=201)
def run_debt_query(property_id: int, data: schemas.DebtQueryRequest, db: Session = Depends(get_db)):
    """Executa uma consulta de débito via provider selecionado por (município × tipo).
    Sem acesso a portal: usa o provider MANUAL/ASSISTIDO (fallback sempre válido),
    estruturando os valores informados pelo operador a partir da fonte oficial.
    Persiste a execução (DebtQuery) + os débitos normalizados + consolidação."""
    prop = property_or_404(db, property_id)
    payload = {
        "itens": [i.model_dump() for i in data.itens] if data.itens else None,
        "sem_ocorrencia": data.sem_ocorrencia, "mensagem": data.mensagem,
    }
    try:
        out = debt_query_service.run_query(
            db, prop, debt_type_code=data.debt_type_code, municipality_id=data.municipality_id,
            source_id=data.source_id, identifier=data.identifier, payload=payload, max_attempts=data.max_attempts,
        )
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    # Reflete a consulta na frente PREFEITURA (rastreabilidade na due diligence) sem
    # criar nova versão de análise. Pendência quando requer intervenção/indisponível.
    status = out["consulta"]["status"]
    pend = [] if status in {"CONCLUIDA", "SEM_OCORRENCIA"} else [f"Consulta {data.debt_type_code} em {status}."]
    upsert_due_diligence_front(db, prop, "PREFEITURA",
                               status="CONSULTADO" if not pend else "CONCLUIDO_COM_PENDENCIAS",
                               source="Consulta assistida", mode="MANUAL", pendencias=pend, consulted=True)
    if pend:
        reflect_due_diligence_signals(db, prop, "PREFEITURA", pend)
    db.commit()
    return out


# --- Estimativa condominial (Etapa C) ---
@router.get("/api/imoveis/{property_id}/debitos/estimativas-condominio")
def list_condominium_estimates(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id)
    rows = db.scalars(
        select(models.CondominiumEstimate).where(models.CondominiumEstimate.property_id == property_id).order_by(models.CondominiumEstimate.id.desc())
    ).all()
    return {"property_id": property_id, "estimativas": [serialize({
        "id": e.id, "monthly_reference": e.monthly_reference, "monthly_source": e.monthly_source,
        "months_delinquent": e.months_delinquent, "safety_margin_pct": e.safety_margin_pct,
        "property_age_years": e.property_age_years, "condominium_age_years": e.condominium_age_years,
        "financing_age_years": e.financing_age_years, "confianca": e.confidence,
        "cenarios": {"conservador": e.scenario_conservador, "provavel": e.scenario_provavel, "otimista": e.scenario_otimista},
        "assumptions": e.assumptions, "justificativa": e.justification, "created_at": e.created_at,
    }) for e in rows]}


@router.post("/api/imoveis/{property_id}/debitos/estimar-condominio", status_code=201)
def estimate_condominium(property_id: int, data: schemas.CondominiumEstimateRequest, db: Session = Depends(get_db)):
    """Calcula (e opcionalmente persiste) a estimativa condominial parametrizada —
    3 cenários, SEMPRE marcada ESTIMADO (nunca passivo confirmado). Idade do imóvel/
    condomínio/financiamento são contexto; inadimplência é parâmetro explícito. Também
    devolve os alertas de idade parametrizáveis (que respeitam a qualidade da info)."""
    prop = property_or_404(db, property_id)
    computed = estimates_service.compute_condominium_estimate(
        db, monthly_reference=data.monthly_reference, months_delinquent=data.months_delinquent,
        safety_margin_pct=data.safety_margin_pct, municipality_id=data.municipality_id,
        property_age_years=data.property_age_years, condominium_age_years=data.condominium_age_years,
        financing_age_years=data.financing_age_years,
    )
    alerts = estimates_service.age_alerts(db, property_age_years=data.property_age_years,
                                          age_known=data.age_known, municipality_id=data.municipality_id)
    estimate_id = None
    if data.persist and computed.get("possivel"):
        item = estimates_service.persist_condominium_estimate(
            db, prop, computed=computed, monthly_reference=data.monthly_reference,
            property_age_years=data.property_age_years, condominium_age_years=data.condominium_age_years,
            financing_age_years=data.financing_age_years, justification=data.justification, evidence_id=data.evidence_id,
        )
        event = record_event(db, prop, "ESTIMATIVA_CONDOMINIAL_REGISTRADA", "CondominiumEstimate", item.id,
                             {"confianca": computed.get("confianca"), "cenarios": serialize(computed.get("cenarios"))}, ["financeiro", "checklist"])
        record_history(db, prop, "CondominiumEstimate", item.id, "CREATE", None, {"confianca": computed.get("confianca")}, event.id)
        estimate_id = item.id
    db.commit()
    return {"property_id": property_id, "estimativa": serialize(computed), "alertas_idade": alerts, "estimativa_id": estimate_id}


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
