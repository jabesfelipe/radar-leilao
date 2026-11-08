"""Dashboard operacional (Onda 2): agregação REAL de oportunidades.

Indicadores calculados no backend a partir dos dados persistidos (Opportunity +
OpportunityWorkflow + Risk + Analysis). Cada contagem tem origem identificável. Sem
números fictícios: ausência de dado = zero explícito. Leitura exige autenticação.
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/oportunidades")
def opportunities_dashboard(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    opps = db.scalars(select(models.Opportunity)).all()
    workflows = {w.opportunity_id: w for w in db.scalars(select(models.OpportunityWorkflow)).all()}
    props = {p.id: p for p in db.scalars(select(models.Property)).all()}

    por_status: Counter[str] = Counter()
    por_modalidade: Counter[str] = Counter()
    por_fase: Counter[str] = Counter()
    por_municipio: Counter[str] = Counter()
    bloqueadas = 0
    for o in opps:
        por_status[o.status] += 1
        por_modalidade[o.modality] += 1
        w = workflows.get(o.id)
        fase = w.current_phase if w else "F0_INTAKE"
        por_fase[fase] += 1
        if w and w.blocked:
            bloqueadas += 1
        prop = props.get(o.property_id)
        if prop:
            por_municipio[prop.city] += 1

    # Riscos críticos ativos (origem: tabela risks).
    riscos_criticos = db.scalar(
        select(models.Risk).where(models.Risk.severity == "CRITICA", models.Risk.status == "ATIVO").with_only_columns(models.Risk.id)
    )
    riscos_criticos_total = len(db.scalars(
        select(models.Risk.id).where(models.Risk.severity == "CRITICA", models.Risk.status == "ATIVO")
    ).all())

    return {
        "total_oportunidades": len(opps),
        "bloqueadas": bloqueadas,
        "por_status": dict(por_status),
        "por_modalidade": dict(por_modalidade),
        "por_fase": dict(por_fase),
        "por_municipio": dict(por_municipio),
        "riscos_criticos_ativos": riscos_criticos_total,
        "fontes": {
            "por_status/por_modalidade": "opportunities",
            "por_fase/bloqueadas": "opportunity_workflows",
            "por_municipio": "properties.city",
            "riscos_criticos_ativos": "risks(severity=CRITICA,status=ATIVO)",
        },
    }
