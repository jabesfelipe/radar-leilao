from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from . import models, schemas
from .ai.orchestrator import AnalysisOrchestrator
from .documents.pipeline import DocumentPipeline
from .documents.embedding import embed_pending_chunks
from .services import (build_finance, create_analysis, create_execution, create_verdict, ensure_checklist_master, impacted_domains, latest_execution, persist_agent_findings, recalculate_risks, record_event, record_history, serialize)

app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AnalyzeRequest(BaseModel):
    domains: list[str] | None = None
    query: str = ""


def property_or_404(db: Session, property_id: int) -> models.Property:
    prop = db.get(models.Property, property_id)
    if not prop: raise HTTPException(404, "Imóvel não encontrado")
    return prop

@app.get("/health")
def health(): return {"status": "ok", "servico": "Radar Leilão API", "persistencia": "PostgreSQL + pgvector", "migrations": "Alembic"}

@app.get("/api/imoveis")
def list_properties(db: Session = Depends(get_db)):
    return db.scalars(select(models.Property).order_by(models.Property.updated_at.desc())).all()

@app.post("/api/imoveis", response_model=schemas.PropertyOut)
def create_property(data: schemas.PropertyCreate, db: Session = Depends(get_db)):
    prop = models.Property(**data.model_dump()); db.add(prop); db.flush(); ensure_checklist_master(db); create_execution(db, prop, "CADASTRO"); record_event(db, prop, "IMOVEL_CADASTRADO", "Property", prop.id, data.model_dump(mode="json"), ["documental", "financeiro", "juridico", "mercado", "checklist"]); db.commit(); db.refresh(prop); return prop

@app.get("/api/imoveis/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); execution = latest_execution(prop); latest = prop.verdicts[-1] if prop.verdicts else None
    checklist = [{"id": r.id, "item_number": r.item.priority // 10, "canonical_key": r.item.canonical_key, "question": r.item.question, "category": r.item.category, "origin": r.item.origin, "active": r.item.active, "required": r.item.required, "state": r.state, "answer": r.answer, "confidence": r.confidence, "interpretation": r.interpretation, "risk": r.risk} for r in (execution.results if execution else [])]
    return {"imovel": prop, "leilao": prop.auctions[-1] if prop.auctions else None, "documentos": [{"id": d.id, "name": d.name, "document_type": d.document_type, "status": d.status, "source": d.source, "versions": [{"id": v.id, "version": v.version, "hash": v.content_hash, "status": v.status, "normalized_path": v.normalized_path} for v in d.versions]} for d in prop.documents], "evidencias": prop.evidences, "processos": prop.processes, "custos": prop.costs, "dividas": prop.debts, "comparaveis": prop.comparables, "checklist": checklist, "riscos": prop.risks, "analises": prop.analyses, "eventos": prop.events, "veredito": latest, "financeiro": serialize(build_finance(prop))}

@app.post("/api/imoveis/{property_id}/leilao")
def add_auction(property_id: int, data: schemas.AuctionCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); auction = models.Auction(property_id=property_id, **data.model_dump()); db.add(auction); db.flush(); event = record_event(db, prop, "LEILAO_ATUALIZADO", "Auction", auction.id, data.model_dump(mode="json"), ["financeiro", "checklist"]); record_history(db, prop, "Auction", auction.id, "CREATE", None, data.model_dump(mode="json"), event.id); db.commit(); return auction

@app.post("/api/imoveis/{property_id}/custos")
def add_cost(property_id: int, data: schemas.CostCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); item = models.Cost(property_id=property_id, **data.model_dump()); db.add(item); db.flush(); record_event(db, prop, "CUSTO_ADICIONADO", "Cost", item.id, data.model_dump(mode="json"), ["financeiro", "checklist"]); db.commit(); return item

@app.post("/api/imoveis/{property_id}/dividas")
def add_debt(property_id: int, data: schemas.DebtCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); item = models.Debt(property_id=property_id, **data.model_dump()); db.add(item); db.flush(); record_event(db, prop, "DIVIDA_ADICIONADA", "Debt", item.id, data.model_dump(mode="json"), impacted_domains("DIVIDA_ADICIONADA")); db.commit(); return item

@app.post("/api/imoveis/{property_id}/comparaveis")
def add_comparable(property_id: int, data: schemas.ComparableCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); item = models.MarketComparable(property_id=property_id, **data.model_dump()); db.add(item); db.flush(); record_event(db, prop, "COMPARAVEL_ADICIONADO", "MarketComparable", item.id, data.model_dump(mode="json"), impacted_domains("COMPARAVEL_ADICIONADO")); db.commit(); return item

@app.post("/api/imoveis/{property_id}/processos")
def add_process(property_id: int, data: schemas.ProcessCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); item = models.LegalProcess(property_id=property_id, **data.model_dump()); db.add(item); db.flush(); record_event(db, prop, "PROCESSO_ADICIONADO", "LegalProcess", item.id, data.model_dump(mode="json"), impacted_domains("PROCESSO_ADICIONADO")); db.commit(); return item

@app.patch("/api/imoveis/{property_id}/checklist/{item_id}")
def update_checklist(property_id: int, item_id: int, data: schemas.ChecklistUpdate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); execution = latest_execution(prop); result = db.get(models.ChecklistResult, item_id)
    if not result or not execution or result.execution_id != execution.id: raise HTTPException(404, "Resultado do Checklist Mestre não encontrado")
    before = {"state": result.state, "answer": result.answer, "confidence": result.confidence}; result.state, result.answer, result.confidence, result.interpretation, result.risk = data.state, data.answer, data.confidence, data.interpretation, data.risk; db.flush(); event = record_event(db, prop, "CHECKLIST_ATUALIZADO", "ChecklistResult", result.id, data.model_dump(), ["checklist", "financeiro", "juridico"]); record_history(db, prop, "ChecklistResult", result.id, "UPDATE", before, data.model_dump(), event.id); db.commit(); return result

@app.post("/api/imoveis/{property_id}/documentos")
async def upload_document(property_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); filename = file.filename or "documento"; content = await file.read()
    document = models.Document(property_id=property_id, name=filename, document_type="Edital" if "edital" in filename.lower() else ("Matrícula" if "matr" in filename.lower() else "Outro"), source="Upload manual"); db.add(document); db.flush()
    version = DocumentPipeline(db).ingest(document, content, filename); event = record_event(db, prop, "DOCUMENTO_ADICIONADO", "DocumentVersion", version.id, {"document_id": document.id, "version": version.version, "hash": version.content_hash}, impacted_domains("DOCUMENTO_ADICIONADO")); record_history(db, prop, "DocumentVersion", version.id, "CREATE", None, {"version": version.version, "hash": version.content_hash}, event.id)
    embeddings = 0
    if settings.effective_llm_api_key: embeddings = embed_pending_chunks(db, version.id)
    db.commit(); return {"documento_id": document.id, "versao_id": version.id, "versao": version.version, "chunks": len(version.chunks), "embeddings": embeddings, "status": version.status}

@app.post("/api/imoveis/{property_id}/evidencias")
def create_evidence(property_id: int, data: schemas.EvidenceCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); evidence = models.Evidence(property_id=property_id, **data.model_dump()); db.add(evidence); db.flush(); event = record_event(db, prop, "EVIDENCIA_REGISTRADA", "Evidence", evidence.id, data.model_dump(), ["checklist", "juridico", "documental"]); record_history(db, prop, "Evidence", evidence.id, "CREATE", None, data.model_dump(), event.id, evidence.id); db.commit(); return evidence

@app.get("/api/imoveis/{property_id}/evidencias")
def list_evidence(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id); return db.scalars(select(models.Evidence).where(models.Evidence.property_id == property_id).order_by(models.Evidence.created_at.desc())).all()

@app.post("/api/imoveis/{property_id}/analisar")
def analyze(property_id: int, request: AnalyzeRequest | None = None, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); request = request or AnalyzeRequest(); domains = request.domains or ["documental", "juridico", "financeiro", "mercado", "checklist"]
    execution = create_execution(db, prop, "REANALISE_INCREMENTAL", len(prop.analyses) + 1); db.flush()
    orchestration = AnalysisOrchestrator(db).run(property_id, domains, request.query)
    agents = [item["agent"] for item in orchestration.get("agent_results", [])]
    analysis = create_analysis(db, prop, ",".join(domains), domains, [], f"Domínios afetados: {', '.join(domains)}", agents)
    analysis.model = orchestration.get("model")
    analysis.prompt_version = "radar-analysis-v1"
    analysis.token_usage = {"llm_used": orchestration.get("llm_used", False), "chunks_retrieved": len(orchestration.get("retrieved_chunk_ids", []))}
    execution.analysis_version = analysis.version
    evidence_ids = persist_agent_findings(db, prop, analysis, execution, orchestration.get("agent_results", []))
    finance = build_finance(prop)
    db.add(models.FinancialAnalysis(property_id=prop.id, analysis_version=analysis.version, inputs={"domains": domains, "chunks": orchestration.get("retrieved_chunk_ids", [])}, outputs=serialize(finance)))
    recalculate_risks(db, prop, analysis.version)
    verdict = create_verdict(db, prop, analysis, orchestration.get("verdict"))
    db.commit()
    return {"versao": analysis.version, "agentes": agents, "llm_usada": orchestration.get("llm_used", False), "modelo": analysis.model, "chunks_recuperados": orchestration.get("retrieved_chunk_ids", []), "evidencias": evidence_ids, "financeiro": serialize(verdict.financial), "veredito": verdict.overall, "status": "concluida"}

@app.get("/api/imoveis/{property_id}/historico")
def history(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id); return {"eventos": db.scalars(select(models.DomainEvent).where(models.DomainEvent.property_id == property_id).order_by(models.DomainEvent.created_at.desc())).all(), "alteracoes": db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id).order_by(models.EntityHistory.created_at.desc())).all(), "analises": db.scalars(select(models.Analysis).where(models.Analysis.property_id == property_id).order_by(models.Analysis.version.desc())).all()}
