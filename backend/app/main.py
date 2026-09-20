from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .database import Base, engine, get_db
from . import models, schemas
from .services import seed_checklist, snapshot, build_finance, recalculate_risks, serialize

Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"status": "ok", "servico": "Radar Leilão API"}

@app.get("/api/imoveis")
def list_properties(db: Session = Depends(get_db)):
    return db.scalars(select(models.Property).order_by(models.Property.updated_at.desc())).all()

@app.post("/api/imoveis", response_model=schemas.PropertyOut)
def create_property(data: schemas.PropertyCreate, db: Session = Depends(get_db)):
    prop = models.Property(**data.model_dump())
    db.add(prop); db.commit(); db.refresh(prop); seed_checklist(db, prop); db.commit()
    return prop

@app.get("/api/imoveis/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.get(models.Property, property_id)
    if not prop: raise HTTPException(404, "Imóvel não encontrado")
    finance = build_finance(db, prop)
    latest = prop.verdicts[-1] if prop.verdicts else None
    return {"imovel": prop, "leilao": prop.auctions[-1] if prop.auctions else None, "documentos": prop.documents, "processos": prop.processes, "custos": prop.costs, "comparaveis": prop.comparables, "checklist": prop.checklist_results, "riscos": prop.risks, "analises": prop.analyses, "veredito": latest, "financeiro": serialize(finance)}

@app.post("/api/imoveis/{property_id}/leilao")
def add_auction(property_id: int, data: schemas.AuctionCreate, db: Session = Depends(get_db)):
    prop = db.get(models.Property, property_id)
    if not prop: raise HTTPException(404, "Imóvel não encontrado")
    auction = models.Auction(property_id=property_id, **data.model_dump()); db.add(auction); db.commit(); return auction

@app.post("/api/imoveis/{property_id}/custos")
def add_cost(property_id: int, data: schemas.CostCreate, db: Session = Depends(get_db)):
    if not db.get(models.Property, property_id): raise HTTPException(404, "Imóvel não encontrado")
    item = models.Cost(property_id=property_id, **data.model_dump()); db.add(item); db.commit(); return item

@app.post("/api/imoveis/{property_id}/comparaveis")
def add_comparable(property_id: int, data: schemas.ComparableCreate, db: Session = Depends(get_db)):
    if not db.get(models.Property, property_id): raise HTTPException(404, "Imóvel não encontrado")
    item = models.MarketComparable(property_id=property_id, **data.model_dump()); db.add(item); db.commit(); return item

@app.post("/api/imoveis/{property_id}/processos")
def add_process(property_id: int, data: schemas.ProcessCreate, db: Session = Depends(get_db)):
    if not db.get(models.Property, property_id): raise HTTPException(404, "Imóvel não encontrado")
    item = models.LegalProcess(property_id=property_id, **data.model_dump()); db.add(item); db.commit(); return item

@app.patch("/api/imoveis/{property_id}/checklist/{item_id}")
def update_checklist(property_id: int, item_id: int, data: schemas.ChecklistUpdate, db: Session = Depends(get_db)):
    item = db.scalar(select(models.ChecklistResult).where(models.ChecklistResult.property_id == property_id, models.ChecklistResult.item_number == item_id))
    if not item: raise HTTPException(404, "Item do checklist não encontrado")
    item.state, item.answer, item.confidence = data.state, data.answer, data.confidence; db.commit(); return item

@app.post("/api/imoveis/{property_id}/documentos")
def upload_document(property_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(models.Property, property_id): raise HTTPException(404, "Imóvel não encontrado")
    document = models.Document(property_id=property_id, name=file.filename or "documento", document_type="Edital" if "edital" in (file.filename or "").lower() else "Outro")
    db.add(document); db.commit(); return document

@app.post("/api/imoveis/{property_id}/analisar")
def analyze(property_id: int, db: Session = Depends(get_db)):
    prop = db.get(models.Property, property_id)
    if not prop: raise HTTPException(404, "Imóvel não encontrado")
    recalculate_risks(db, prop); version, finance = snapshot(db, prop); db.commit()
    return {"versao": version, "financeiro": serialize(finance), "status": "concluida"}
