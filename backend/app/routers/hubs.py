"""Routers dos HUBS globais (M0 — modularização).

Visões agregadas/transversais (dashboard, imóveis-resumo, financeiro, jurídico,
riscos, veredito, mercado, ocupação, documentos, histórico, checklist-global).
Movido de ``main.py`` SEM alterar contrato (mesmos paths/métodos/respostas). Os
números vêm sempre de fontes determinísticas (reutiliza ``build_finance`` etc.).
"""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services import (
    build_finance, current_auction, juridical_overview,
    latest_execution, latest_occupancy, serialize,
)

router = APIRouter()


# ============================================================================
# Helpers determinísticos dos hubs (reaproveitam build_finance/juridical_overview).
# Números nunca são inventados; ausência vira None/0. Mantidos aqui porque são
# usados exclusivamente pelas visões de hub.
# ============================================================================
def _latest_verdict(db: Session, property_id: int):
    return db.scalar(select(models.Verdict).where(models.Verdict.property_id == property_id).order_by(models.Verdict.analysis_version.desc(), models.Verdict.id.desc()))


def _property_summary(db: Session, prop: models.Property) -> dict:
    """Resumo determinístico de um imóvel para os hubs (reutiliza build_finance)."""
    fin = serialize(build_finance(prop))
    auction = current_auction(prop)
    verdict = _latest_verdict(db, prop.id)
    riscos_ativos = [r for r in prop.risks if (r.status or "ATIVO").upper() not in {"INATIVO", "SUPERADO"}]
    risco_alto = any((r.severity or "").upper() in {"ALTA", "CRITICA"} for r in riscos_ativos)
    jur = juridical_overview(db, prop)
    return {
        "id": prop.id, "titulo": prop.title, "cidade": prop.city, "uf": prop.state,
        "origem": prop.origin, "status": prop.status,
        "lance": auction.bid_value if auction else None,
        "avaliacao": auction.appraisal_value if auction else None,
        "preco_maximo": fin.get("preco_maximo"),
        "preco_maximo_definitivo": fin.get("preco_maximo_definitivo"),
        "preco_maximo_provisorio": fin.get("preco_maximo_provisorio"),
        "custo_total": fin.get("custo_total"),
        "break_even": fin.get("break_even"),
        "roi_operacao": fin.get("roi_operacao"),
        "margem_liquida": fin.get("margem_liquida"),
        "pendencias": len(fin.get("pendencias") or []),
        "riscos_ativos": len(riscos_ativos),
        "risco_alto": risco_alto,
        "correlacao_juridica": jur.get("correlacao"),
        "processos": jur.get("processos_encontrados", 0),
        "veredito": verdict.overall if verdict else None,
        "analysis_version": verdict.analysis_version if verdict else None,
    }


@router.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """Painel de decisão: KPIs, pipeline e alertas calculados dos dados reais."""
    props = db.scalars(select(models.Property).order_by(models.Property.updated_at.desc())).all()
    resumos = [_property_summary(db, p) for p in props]
    total = len(resumos)
    em_analise = sum(1 for r in resumos if (r["status"] or "").upper() == "EM_ANALISE")
    com_pendencias = sum(1 for r in resumos if r["pendencias"] > 0)
    riscos_altos = sum(1 for r in resumos if r["risco_alto"])
    oportunidades = sum(1 for r in resumos if (r["veredito"] or "") == "FAVORAVEL")
    # Pipeline usando somente estados existentes (sem inventar).
    pipeline = {
        "cadastrado": sum(1 for r in resumos if (r["status"] or "").upper() == "EM_ANALISE"),
        "com_veredito": sum(1 for r in resumos if r["veredito"]),
        "com_pendencias": com_pendencias,
        "riscos_altos": riscos_altos,
    }
    alertas = []
    for r in resumos:
        if r["risco_alto"]:
            alertas.append({"tipo": "RISCO_ALTO", "property_id": r["id"], "titulo": r["titulo"], "detalhe": f"{r['riscos_ativos']} risco(s) ativo(s)"})
        if r["preco_maximo_provisorio"]:
            alertas.append({"tipo": "PRECO_MAXIMO_PROVISORIO", "property_id": r["id"], "titulo": r["titulo"], "detalhe": "Preço máximo provisório (custos desconhecidos)"})
        if r["pendencias"] > 0:
            alertas.append({"tipo": "PENDENCIAS", "property_id": r["id"], "titulo": r["titulo"], "detalhe": f"{r['pendencias']} pendência(s)"})
    recentes = [{"id": p.id, "titulo": p.title, "updated_at": p.updated_at} for p in props[:8]]
    return {
        "kpis": {"imoveis": total, "em_analise": em_analise, "com_pendencias": com_pendencias,
                 "riscos_altos": riscos_altos, "oportunidades": oportunidades},
        "pipeline": pipeline, "alertas": alertas, "recentes": recentes,
    }


@router.get("/api/imoveis-resumo")
def properties_summary(db: Session = Depends(get_db)):
    """Listagem enriquecida de imóveis (hub Imóveis): preço máximo, ROI, risco, veredito."""
    props = db.scalars(select(models.Property).order_by(models.Property.updated_at.desc())).all()
    return [_property_summary(db, p) for p in props]


@router.get("/api/financeiro")
def financial_hub(db: Session = Depends(get_db)):
    props = db.scalars(select(models.Property).order_by(models.Property.updated_at.desc())).all()
    itens = [_property_summary(db, p) for p in props]
    return {"total": len(itens), "itens": itens}


@router.get("/api/juridico")
def juridical_hub(db: Session = Depends(get_db)):
    props = db.scalars(select(models.Property)).all()
    linhas = []
    for p in props:
        for proc in p.processes:
            linhas.append({
                "property_id": p.id, "imovel": p.title, "numero": proc.number,
                "tribunal": proc.court, "correlacao": proc.correlation_level,
                "vinculo": proc.link_origin, "status": proc.status,
            })
    riscos_juridicos = db.scalars(select(models.Risk).where(models.Risk.category == "juridico")).all()
    return {"processos": linhas, "total_processos": len(linhas), "riscos_juridicos": len(riscos_juridicos)}


@router.get("/api/riscos")
def risks_hub(severity: str | None = None, db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Risk).order_by(models.Risk.analysis_version.desc(), models.Risk.id.desc())).all()
    props = {p.id: p.title for p in db.scalars(select(models.Property)).all()}
    out = []
    for r in rows:
        if severity and (r.severity or "").upper() != severity.upper():
            continue
        if (r.status or "ATIVO").upper() in {"INATIVO", "SUPERADO"}:
            continue
        out.append({"id": r.id, "property_id": r.property_id, "imovel": props.get(r.property_id),
                    "dominio": r.category, "descricao": r.description, "severidade": r.severity,
                    "confianca": r.confidence, "origem": r.origin, "status": r.status,
                    "evidence_id": r.evidence_id, "analysis_version": r.analysis_version})
    return {"total": len(out), "riscos": out}


@router.get("/api/veredito")
def verdicts_hub(db: Session = Depends(get_db)):
    props = db.scalars(select(models.Property).order_by(models.Property.updated_at.desc())).all()
    itens = []
    for p in props:
        v = _latest_verdict(db, p.id)
        if v is None:
            continue
        s = _property_summary(db, p)
        itens.append({"property_id": p.id, "imovel": p.title, "veredito": v.overall,
                      "analysis_version": v.analysis_version, "preco_maximo": s["preco_maximo"],
                      "custo_total": s["custo_total"], "roi_operacao": s["roi_operacao"],
                      "pendencias": len(v.pending_items or []), "riscos": len(v.risk_ids or [])})
    return {"total": len(itens), "vereditos": itens}


@router.get("/api/mercado")
def market_hub(db: Session = Depends(get_db)):
    props = db.scalars(select(models.Property)).all()
    linhas = []
    for p in props:
        for c in p.comparables:
            linhas.append({"property_id": p.id, "imovel": p.title, "tipo": c.kind,
                           "preco": c.price, "aluguel": c.rent, "area_m2": c.area_m2,
                           "fonte": c.source, "url": c.url})
    return {"total": len(linhas), "comparaveis": linhas}


@router.get("/api/ocupacao")
def occupancy_hub(db: Session = Depends(get_db)):
    props = db.scalars(select(models.Property)).all()
    itens = []
    for p in props:
        occ = latest_occupancy(p)
        if occ is None:
            continue
        itens.append({"property_id": p.id, "imovel": p.title, "status": occ.status,
                      "perfil": occ.occupant_profile, "custo_estimado": occ.estimated_cost,
                      "meses_estimados": occ.estimated_months})
    return {"total": len(itens), "ocupacoes": itens}


@router.get("/api/documentos")
def documents_hub(doc_type: str | None = None, db: Session = Depends(get_db)):
    props = {p.id: p.title for p in db.scalars(select(models.Property)).all()}
    docs = db.scalars(select(models.Document).order_by(models.Document.created_at.desc())).all()
    out = []
    for d in docs:
        if doc_type and (d.document_type or "").upper() != doc_type.upper():
            continue
        latest = d.versions[-1] if d.versions else None
        out.append({"id": d.id, "property_id": d.property_id, "imovel": props.get(d.property_id),
                    "nome": d.name, "tipo": d.document_type, "origem": d.source, "status": d.status,
                    "versao": latest.version if latest else None, "created_at": d.created_at})
    return {"total": len(out), "documentos": out}


@router.get("/api/historico")
def history_hub(db: Session = Depends(get_db)):
    props = {p.id: p.title for p in db.scalars(select(models.Property)).all()}
    eventos = db.scalars(select(models.DomainEvent).order_by(models.DomainEvent.created_at.desc()).limit(200)).all()
    out = [{"id": e.id, "property_id": e.property_id, "imovel": props.get(e.property_id),
            "evento": e.event_type, "entidade": e.aggregate_type, "dominios": e.affected_domains,
            "created_at": e.created_at} for e in eventos]
    return {"total": len(out), "eventos": out}


@router.get("/api/checklist-global")
def checklist_hub(db: Session = Depends(get_db)):
    """Agrega os estados do checklist corrente de cada imóvel (hub Checklist)."""
    props = db.scalars(select(models.Property)).all()
    contagem: Counter = Counter()
    itens = []
    for p in props:
        execution = latest_execution(p)
        if execution is None:
            continue
        c = Counter((r.state or "PENDENTE").upper() for r in execution.results)
        contagem.update(c)
        itens.append({"property_id": p.id, "imovel": p.title,
                      "confirmados": c.get("CONFIRMADO", 0),
                      "pendentes": c.get("PENDENTE", 0) + c.get("EM_ANALISE", 0),
                      "atencao": c.get("ATENCAO", 0) + c.get("RISCO_IDENTIFICADO", 0)})
    return {"totais": dict(contagem), "itens": itens}
