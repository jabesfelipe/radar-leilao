from sqlalchemy.orm import Session
from . import models
from .checklist import CHECKLIST_QUESTIONS
from .finance import calculate_financial

def seed_checklist(db: Session, prop: models.Property):
    if prop.checklist_results:
        return
    for index, question in enumerate(CHECKLIST_QUESTIONS, 1):
        db.add(models.ChecklistResult(property_id=prop.id, item_number=index, question=question))

def snapshot(db: Session, prop: models.Property, scope="Completa", changes=""):
    version = len(prop.analyses) + 1
    finance = build_finance(db, prop)
    db.add(models.Analysis(property_id=prop.id, version=version, scope=scope, changes=changes))
    pending = sum(1 for item in prop.checklist_results if item.state == "PENDENTE")
    active_risks = len([r for r in prop.risks if r.status == "ATIVO"])
    overall = "ATENÇÃO" if active_risks or pending else "FAVORÁVEL"
    summary = f"Análise V{version}: {pending} pendência(s) no checklist e {active_risks} risco(s) ativo(s)."
    db.add(models.Verdict(property_id=prop.id, analysis_version=version, overall=overall, summary=summary, financial=serialize(finance)))
    return version, finance

def build_finance(db: Session, prop: models.Property):
    auction = prop.auctions[-1] if prop.auctions else None
    return calculate_financial(auction.bid_value if auction else 0, auction.appraisal_value if auction else 0, [{"amount": c.amount} for c in prop.costs], [{"kind": c.kind, "price": c.price} for c in prop.comparables], prop.area_m2)

def serialize(value):
    if isinstance(value, dict): return {k: serialize(v) for k, v in value.items()}
    return float(value) if hasattr(value, "as_tuple") else value

def recalculate_risks(db: Session, prop: models.Property):
    prop.risks.clear()
    pending = sum(1 for item in prop.checklist_results if item.state == "PENDENTE")
    if pending: prop.risks.append(models.Risk(property_id=prop.id, category="Documental", description=f"{pending} item(ns) do checklist ainda pendente(s).", severity="MEDIA"))
    finance = build_finance(db, prop)
    if finance["custo_total"] > finance["valor_mercado"]: prop.risks.append(models.Risk(property_id=prop.id, category="Financeiro", description="O custo total estimado supera o valor de mercado informado.", severity="ALTA"))
    if not prop.documents: prop.risks.append(models.Risk(property_id=prop.id, category="Documental", description="Nenhum documento foi anexado ao dossiê.", severity="ALTA"))
