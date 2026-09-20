from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from . import models, schemas
from .ai.agents import DocumentAgent
from .ai.gateway import build_gateway
from .ai.orchestrator import AnalysisOrchestrator
from .documents.pipeline import DocumentPipeline
from .extraction import extract_document, persist_extraction
from .market import calculate_market
from .rag.service import RAGService
from .services import (aggregate_llm_usage, build_finance, checklist_item_snapshot, create_analysis, create_checklist_item, create_execution, create_verdict, ensure_checklist_master, impacted_domains, latest_execution, persist_agent_findings, persist_llm_runs, recalculate_risks, record_event, record_history, record_checklist_event, record_checklist_history, serialize, update_checklist_item)

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

@app.get("/api/checklist")
def list_checklist(active: bool | None = None, origin: str | None = None, domain: str | None = None, category: str | None = None, priority: int | None = None, required: bool | None = None, db: Session = Depends(get_db)):
    ensure_checklist_master(db)
    db.commit()
    items = db.scalars(select(models.ChecklistItem).order_by(models.ChecklistItem.priority, models.ChecklistItem.canonical_key)).all()
    filtered = [item for item in items if (active is None or item.active == active) and (origin is None or item.origin == origin) and (domain is None or domain in (item.domain or [])) and (category is None or item.category == category) and (priority is None or item.priority == priority) and (required is None or item.required == required)]
    return [checklist_item_snapshot(item) for item in filtered]

@app.get("/api/checklist/{item_id}")
def get_checklist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.ChecklistItem, item_id)
    if not item: raise HTTPException(404, "Regra do Checklist Mestre não encontrada")
    return checklist_item_snapshot(item)

@app.post("/api/checklist", status_code=201)
def create_checklist_rule(data: schemas.ChecklistItemCreate, db: Session = Depends(get_db)):
    try:
        item = create_checklist_item(db, data.model_dump()); db.commit(); db.refresh(item); return checklist_item_snapshot(item)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "canonical_key já existe no Checklist Mestre")

@app.patch("/api/checklist/{item_id}")
def patch_checklist_rule(item_id: int, data: schemas.ChecklistItemPatch, db: Session = Depends(get_db)):
    item = db.get(models.ChecklistItem, item_id)
    if not item: raise HTTPException(404, "Regra do Checklist Mestre não encontrada")
    item = update_checklist_item(db, item, data.model_dump(exclude_unset=True)); db.commit(); db.refresh(item); return checklist_item_snapshot(item)

@app.post("/api/checklist/{item_id}/ativar")
def activate_checklist_rule(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.ChecklistItem, item_id)
    if not item: raise HTTPException(404, "Regra do Checklist Mestre não encontrada")
    item = update_checklist_item(db, item, {"active": True}); db.commit(); db.refresh(item); return checklist_item_snapshot(item)

@app.post("/api/checklist/{item_id}/desativar")
def deactivate_checklist_rule(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.ChecklistItem, item_id)
    if not item: raise HTTPException(404, "Regra do Checklist Mestre não encontrada")
    item = update_checklist_item(db, item, {"active": False}); db.commit(); db.refresh(item); return checklist_item_snapshot(item)

@app.get("/api/checklist/{item_id}/historico")
def checklist_rule_history(item_id: int, db: Session = Depends(get_db)):
    if not db.get(models.ChecklistItem, item_id): raise HTTPException(404, "Regra do Checklist Mestre não encontrada")
    return db.scalars(select(models.EntityHistory).where(models.EntityHistory.entity_type == "ChecklistItem", models.EntityHistory.entity_id == item_id).order_by(models.EntityHistory.created_at)).all()

@app.get("/api/imoveis/{property_id}/checklist")
def property_checklist(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    executions = db.scalars(select(models.ChecklistExecution).where(models.ChecklistExecution.property_id == prop.id).order_by(models.ChecklistExecution.created_at)).all()
    return [{"id": execution.id, "analysis_version": execution.analysis_version, "triggered_by": execution.triggered_by, "created_at": execution.created_at, "results": [{"id": result.id, "checklist_item_id": result.checklist_item_id, "canonical_key": result.item.canonical_key, "item_version": result.item_version, "applicable": result.applicable, "state": result.state, "answer": result.answer, "confidence": result.confidence, "interpretation": result.interpretation, "risk": result.risk, "previous_result_id": result.previous_result_id} for result in execution.results]} for execution in executions]

@app.get("/api/imoveis/{property_id}/checklist/historico")
def property_checklist_history(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id)
    return db.scalars(select(models.ChecklistExecution).where(models.ChecklistExecution.property_id == property_id).order_by(models.ChecklistExecution.created_at)).all()

@app.get("/api/imoveis/{property_id}/financeiro")
def get_financial(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    current = build_finance(prop)
    history = db.scalars(select(models.FinancialAnalysis).where(models.FinancialAnalysis.property_id == property_id).order_by(models.FinancialAnalysis.analysis_version)).all()
    latest = history[-1] if history else None
    return {"property_id": property_id, "analysis_version": latest.analysis_version if latest else None, "financeiro": serialize(current), "historico": [{"id": item.id, "analysis_version": item.analysis_version, "inputs": item.inputs, "outputs": item.outputs, "created_at": item.created_at} for item in history]}

@app.post("/api/imoveis/{property_id}/financeiro/analisar")
def analyze_financial(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    current = build_finance(prop)
    latest = db.scalar(select(models.FinancialAnalysis).where(models.FinancialAnalysis.property_id == property_id).order_by(models.FinancialAnalysis.analysis_version.desc()))
    version = (latest.analysis_version + 1) if latest else 1
    inputs = {"auction_id": prop.auctions[-1].id if prop.auctions else None, "cost_ids": [cost.id for cost in prop.costs], "debt_ids": [debt.id for debt in prop.debts], "comparable_ids": [comparable.id for comparable in prop.comparables]}
    analysis = models.FinancialAnalysis(property_id=property_id, analysis_version=version, inputs=inputs, outputs=serialize(current))
    db.add(analysis); db.commit()
    return {"property_id": property_id, "analysis_version": version, "financeiro": serialize(current)}

@app.get("/api/imoveis/{property_id}/mercado")
def get_market(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    comparables = [{"kind": comparable.kind, "price": comparable.price, "rent": comparable.rent, "area_m2": comparable.area_m2} for comparable in prop.comparables]
    return {"property_id": property_id, "mercado": calculate_market(comparables)}

@app.post("/api/imoveis/{property_id}/ocupacao")
def create_occupancy(property_id: int, data: schemas.OccupancyCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    occupancy = models.OccupancyAnalysis(property_id=property_id, **data.model_dump())
    db.add(occupancy); db.flush()
    payload = data.model_dump(mode="json")
    event = record_event(db, prop, "OCUPACAO_ATUALIZADA", "OccupancyAnalysis", occupancy.id, payload, ["desocupacao", "financeiro", "checklist"])
    record_history(db, prop, "OccupancyAnalysis", occupancy.id, "CREATE", None, payload, event.id, data.evidence_id)
    db.commit(); db.refresh(occupancy)
    return occupancy

@app.get("/api/imoveis/{property_id}/ocupacao")
def get_occupancy(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    history = db.scalars(select(models.OccupancyAnalysis).where(models.OccupancyAnalysis.property_id == property_id).order_by(models.OccupancyAnalysis.created_at)).all()
    def snapshot(item):
        return {"id": item.id, "property_id": item.property_id, "status": item.status, "occupant_profile": item.occupant_profile, "estimated_cost": item.estimated_cost, "estimated_months": item.estimated_months, "evidence_id": item.evidence_id, "created_at": item.created_at, "updated_at": item.updated_at}
    return {"property_id": property_id, "situacao_atual": snapshot(history[-1]) if history else None, "ultimo_registro": snapshot(history[-1]) if history else None, "historico": [snapshot(item) for item in history]}

@app.post("/api/imoveis/{property_id}/matricula")
def create_registration(property_id: int, data: schemas.RegistrationCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    item = models.PropertyRegistration(property_id=property_id, **data.model_dump())
    db.add(item); db.flush(); payload = data.model_dump(mode="json")
    event = record_event(db, prop, "MATRICULA_CADASTRADA", "PropertyRegistration", item.id, payload, ["juridico", "checklist"])
    record_history(db, prop, "PropertyRegistration", item.id, "CREATE", None, payload, event.id, data.evidence_id)
    db.commit(); db.refresh(item); return item

@app.get("/api/imoveis/{property_id}/matricula")
def list_registrations(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    records = db.scalars(select(models.PropertyRegistration).where(models.PropertyRegistration.property_id == property_id).order_by(models.PropertyRegistration.created_at)).all()
    history = db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id, models.EntityHistory.entity_type == "PropertyRegistration").order_by(models.EntityHistory.created_at)).all()
    return {"property_id": prop.id, "atual": records[-1] if records else None, "historico": records, "alteracoes": history}

@app.post("/api/imoveis/{property_id}/edital")
def create_notice(property_id: int, data: schemas.AuctionNoticeCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    item = models.AuctionNotice(property_id=property_id, **data.model_dump())
    db.add(item); db.flush(); payload = data.model_dump(mode="json")
    event = record_event(db, prop, "EDITAL_CADASTRADO", "AuctionNotice", item.id, payload, ["documental", "juridico", "financeiro", "checklist"])
    record_history(db, prop, "AuctionNotice", item.id, "CREATE", None, payload, event.id, data.evidence_id)
    db.commit(); db.refresh(item); return item

@app.get("/api/imoveis/{property_id}/edital")
def list_notices(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    records = db.scalars(select(models.AuctionNotice).where(models.AuctionNotice.property_id == property_id).order_by(models.AuctionNotice.created_at)).all()
    history = db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id, models.EntityHistory.entity_type == "AuctionNotice").order_by(models.EntityHistory.created_at)).all()
    return {"property_id": prop.id, "atual": records[-1] if records else None, "historico": records, "alteracoes": history}

@app.post("/api/imoveis/{property_id}/documentos/{document_version_id}/extrair")
def extract_document_endpoint(property_id: int, document_version_id: int, data: schemas.DocumentExtractionRequest, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    try:
        result = extract_document(db, property_id, document_version_id, data.document_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    run_data = dict(result.call.to_dict(), agent="extracao_documental", retrieved_chunk_ids=[chunk["chunk_id"] for chunk in result.chunks])
    runs = persist_llm_runs(db, prop, None, [run_data])
    if not result.success:
        db.commit()
        return {"status": result.call.status, "erro": result.call.error_message, "llm_run_id": runs[0].id if runs else None, "document_version_id": document_version_id}
    record, evidence_ids = persist_extraction(db, prop, result)
    db.commit(); db.refresh(record)
    return {"status": "PROCESSADO", "document_type": data.document_type, "document_version_id": document_version_id, "registro_id": record.id, "evidence_ids": evidence_ids, "llm_run_id": runs[0].id if runs else None, "dados": record}

@app.get("/api/imoveis/{property_id}/documentos/{document_version_id}/extracao")
def get_document_extraction(property_id: int, document_version_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    version = db.get(models.DocumentVersion, document_version_id)
    if not version or version.document.property_id != property_id: raise HTTPException(404, "DocumentVersion não pertence ao imóvel")
    registrations = db.scalars(select(models.PropertyRegistration).where(models.PropertyRegistration.property_id == property_id, models.PropertyRegistration.document_version_id == document_version_id).order_by(models.PropertyRegistration.created_at)).all()
    notices = db.scalars(select(models.AuctionNotice).where(models.AuctionNotice.property_id == property_id, models.AuctionNotice.document_version_id == document_version_id).order_by(models.AuctionNotice.created_at)).all()
    evidence = db.scalars(select(models.Evidence).where(models.Evidence.property_id == property_id, models.Evidence.document_version_id == document_version_id).order_by(models.Evidence.created_at)).all()
    return {"property_id": prop.id, "document_version_id": document_version_id, "matriculas": registrations, "editais": notices, "evidencias": evidence}

@app.post("/api/imoveis/{property_id}/analises/{analysis_id}/agents/documental")
def run_document_agent(property_id: int, analysis_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    analysis = db.get(models.Analysis, analysis_id)
    if not analysis or analysis.property_id != property_id: raise HTTPException(404, "Análise não encontrada para este imóvel")
    retrieval = RAGService(db).retrieve_context("fatos documentais matrícula edital", property_id)
    try:
        gateway = build_gateway()
    except RuntimeError as exc:
        gateway = None
    result = DocumentAgent(db, gateway).run(property_id, retrieval.context, retrieval.chunk_ids)
    run_data = dict(result.llm_call.to_dict(), agent="documental", retrieved_chunk_ids=retrieval.chunk_ids) if result.llm_call else {"agent": "documental", "status": "ERRO", "error_message": "Chamada não criada", "retrieved_chunk_ids": retrieval.chunk_ids}
    runs = persist_llm_runs(db, prop, analysis, [run_data])
    if not result.llm_call or result.llm_call.status != "CONCLUIDO":
        db.commit()
        return {"status": result.llm_call.status if result.llm_call else "ERRO", "erro": result.llm_call.error_message if result.llm_call else "Chamada não criada", "llm_run_id": runs[0].id if runs else None, "analysis_id": analysis_id, "chunks_recuperados": retrieval.chunk_ids}
    execution = latest_execution(prop)
    evidence_ids = persist_agent_findings(db, prop, analysis, execution, [result.to_dict()])
    analysis.agents_executed = sorted(set((analysis.agents_executed or []) + ["documental"]))
    db.commit()
    return {"status": "CONCLUIDO", "analysis_id": analysis_id, "agente": "documental", "findings": result.facts, "evidence_ids": evidence_ids, "llm_run_id": runs[0].id if runs else None, "chunks_recuperados": retrieval.chunk_ids}

@app.get("/api/imoveis/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); execution = latest_execution(prop); latest = prop.verdicts[-1] if prop.verdicts else None
    checklist = [{"id": r.id, "item_number": r.item.priority, "canonical_key": r.item.canonical_key, "question": r.item.question, "description": r.item.description, "category": r.item.category, "domain": r.item.domain, "origin": r.item.origin, "active": r.item.active, "applicable": r.applicable, "required": r.item.required, "item_version": r.item_version, "state": r.state, "answer": r.answer, "confidence": r.confidence, "interpretation": r.interpretation, "risk": r.risk} for r in (execution.results if execution else [])]
    return {"imovel": prop, "leilao": prop.auctions[-1] if prop.auctions else None, "documentos": [{"id": d.id, "name": d.name, "document_type": d.document_type, "status": d.status, "source": d.source, "versions": [{"id": v.id, "version": v.version, "hash": v.content_hash, "status": v.status, "normalized_path": v.normalized_path} for v in d.versions]} for d in prop.documents], "evidencias": prop.evidences, "processos": prop.processes, "custos": prop.costs, "dividas": prop.debts, "comparaveis": prop.comparables, "checklist": checklist, "riscos": prop.risks, "analises": prop.analyses, "eventos": prop.events, "veredito": latest, "financeiro": serialize(build_finance(prop))}

@app.post("/api/imoveis/{property_id}/leilao")
def add_auction(property_id: int, data: schemas.AuctionCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); auction = models.Auction(property_id=property_id, **data.model_dump()); db.add(auction); db.flush(); event = record_event(db, prop, "LEILAO_ATUALIZADO", "Auction", auction.id, data.model_dump(mode="json"), ["financeiro", "checklist"]); record_history(db, prop, "Auction", auction.id, "CREATE", None, data.model_dump(mode="json"), event.id); db.commit(); return auction

@app.post("/api/imoveis/{property_id}/custos")
def add_cost(property_id: int, data: schemas.CostCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    item = models.Cost(property_id=property_id, **data.model_dump())
    db.add(item); db.flush()
    payload = data.model_dump(mode="json")
    event = record_event(db, prop, "CUSTO_ADICIONADO", "Cost", item.id, payload, ["financeiro", "checklist"])
    record_history(db, prop, "Cost", item.id, "CREATE", None, payload, event.id)
    db.commit(); db.refresh(item)
    return item

@app.get("/api/imoveis/{property_id}/custos")
def list_costs(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    costs = db.scalars(select(models.Cost).where(models.Cost.property_id == property_id).order_by(models.Cost.created_at)).all()
    history = db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id, models.EntityHistory.entity_type == "Cost").order_by(models.EntityHistory.created_at)).all()
    return {"property_id": prop.id, "custos": costs, "historico": history}

@app.post("/api/imoveis/{property_id}/dividas")
def add_debt(property_id: int, data: schemas.DebtCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    item = models.Debt(property_id=property_id, **data.model_dump())
    db.add(item); db.flush()
    payload = data.model_dump(mode="json")
    event = record_event(db, prop, "DIVIDA_ADICIONADA", "Debt", item.id, payload, ["financeiro", "checklist"])
    record_history(db, prop, "Debt", item.id, "CREATE", None, payload, event.id, data.evidence_id)
    db.commit(); db.refresh(item)
    return item

@app.get("/api/imoveis/{property_id}/dividas")
def list_debts(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    debts = db.scalars(select(models.Debt).where(models.Debt.property_id == property_id).order_by(models.Debt.created_at)).all()
    history = db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id, models.EntityHistory.entity_type == "Debt").order_by(models.EntityHistory.created_at)).all()
    return {"property_id": prop.id, "dividas": debts, "historico": history}

@app.post("/api/imoveis/{property_id}/comparaveis")
def add_comparable(property_id: int, data: schemas.ComparableCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); item = models.MarketComparable(property_id=property_id, **data.model_dump()); db.add(item); db.flush(); record_event(db, prop, "COMPARAVEL_ADICIONADO", "MarketComparable", item.id, data.model_dump(mode="json"), impacted_domains("COMPARAVEL_ADICIONADO")); db.commit(); return item

@app.post("/api/imoveis/{property_id}/processos")
def add_process(property_id: int, data: schemas.ProcessCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    item = models.LegalProcess(property_id=property_id, **data.model_dump())
    db.add(item); db.flush()
    payload = data.model_dump(mode="json")
    event = record_event(db, prop, "PROCESSO_ADICIONADO", "LegalProcess", item.id, payload, ["juridico", "checklist", "financeiro"])
    record_history(db, prop, "LegalProcess", item.id, "CREATE", None, payload, event.id, data.evidence_id)
    db.commit(); db.refresh(item)
    return item

@app.get("/api/imoveis/{property_id}/processos")
def list_processes(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    processes = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == property_id).order_by(models.LegalProcess.created_at)).all()
    history = db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id, models.EntityHistory.entity_type == "LegalProcess").order_by(models.EntityHistory.created_at)).all()
    return {"property_id": prop.id, "processos": processes, "historico": history}

@app.patch("/api/imoveis/{property_id}/checklist/{item_id}")
def update_checklist(property_id: int, item_id: int, data: schemas.ChecklistUpdate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id); execution = latest_execution(prop); result = db.get(models.ChecklistResult, item_id)
    if not result or not execution or result.execution_id != execution.id: raise HTTPException(404, "Resultado do Checklist Mestre não encontrado")
    before = {"state": result.state, "answer": result.answer, "confidence": result.confidence}; result.state, result.answer, result.confidence, result.interpretation, result.risk = data.state, data.answer, data.confidence, data.interpretation, data.risk; db.flush(); event = record_event(db, prop, "CHECKLIST_ATUALIZADO", "ChecklistResult", result.id, data.model_dump(), ["checklist", "financeiro", "juridico"]); record_history(db, prop, "ChecklistResult", result.id, "UPDATE", before, data.model_dump(), event.id); db.commit(); return result

def document_or_404(db: Session, document_id: int) -> models.Document:
    document = db.get(models.Document, document_id)
    if not document: raise HTTPException(404, "Documento não encontrado")
    return document


def document_snapshot(document: models.Document) -> dict:
    return {"id": document.id, "property_id": document.property_id, "name": document.name, "document_type": document.document_type, "source": document.source, "status": document.status, "created_at": document.created_at, "updated_at": document.updated_at, "versions": [{"id": version.id, "version": version.version, "content_hash": version.content_hash, "original_path": version.original_path, "normalized_path": version.normalized_path, "extraction_metadata": version.extraction_metadata, "status": version.status, "created_at": version.created_at, "updated_at": version.updated_at} for version in document.versions]}


async def process_document_upload(document: models.Document, file: UploadFile, db: Session):
    try:
        content = await file.read()
        version = DocumentPipeline(db).ingest(document, content, file.filename or "documento")
        return version
    except ValueError as exc:
        document.status = "ERRO"; db.commit(); raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        document.status = "ERRO"; db.commit(); raise HTTPException(422, f"Falha ao processar documento: {exc}") from exc


@app.post("/api/imoveis/{property_id}/documentos")
async def upload_document(property_id: int, file: UploadFile = File(...), document_type: str | None = Form(None), source: str | None = Form(None), db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    filename = file.filename or "documento"
    document = models.Document(property_id=property_id, name=filename, document_type=document_type or "Outro", source=source or "Upload manual")
    db.add(document); db.flush()
    version = await process_document_upload(document, file, db)
    payload = {"document_id": document.id, "version": version.version, "hash": version.content_hash}
    event = record_event(db, prop, "DOCUMENTO_ADICIONADO", "DocumentVersion", version.id, payload, ["documental", "juridico", "checklist"])
    record_history(db, prop, "DocumentVersion", version.id, "CREATE", None, payload, event.id)
    db.commit(); db.refresh(document)
    return document_snapshot(document)

@app.get("/api/imoveis/{property_id}/documentos")
def list_documents(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id)
    documents = db.scalars(select(models.Document).where(models.Document.property_id == property_id).order_by(models.Document.created_at)).all()
    return {"property_id": property_id, "documentos": [document_snapshot(document) for document in documents]}

@app.post("/api/documentos/{document_id}/versoes")
async def add_document_version(document_id: int, file: UploadFile = File(...), document_type: str | None = Form(None), source: str | None = Form(None), db: Session = Depends(get_db)):
    document = document_or_404(db, document_id)
    prop = property_or_404(db, document.property_id)
    if document_type is not None: document.document_type = document_type
    if source is not None: document.source = source
    version = await process_document_upload(document, file, db)
    payload = {"document_id": document.id, "version": version.version, "hash": version.content_hash}
    event = record_event(db, prop, "DOCUMENTO_VERSAO_ADICIONADA", "DocumentVersion", version.id, payload, ["documental", "juridico", "checklist"])
    record_history(db, prop, "DocumentVersion", version.id, "CREATE", None, payload, event.id)
    db.commit(); db.refresh(document)
    return document_snapshot(document)

@app.post("/api/imoveis/{property_id}/evidencias")
def create_evidence(property_id: int, data: schemas.EvidenceCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    if data.document_version_id is not None:
        version = db.get(models.DocumentVersion, data.document_version_id)
        if not version or version.document.property_id != property_id: raise HTTPException(400, "DocumentVersion não pertence ao imóvel")
    if data.chunk_id is not None:
        chunk = db.get(models.DocumentChunk, data.chunk_id)
        if not chunk or chunk.document_version.document.property_id != property_id: raise HTTPException(400, "DocumentChunk não pertence ao imóvel")
    evidence = models.Evidence(property_id=property_id, **data.model_dump())
    db.add(evidence); db.flush(); payload = data.model_dump(mode="json")
    event = record_event(db, prop, "EVIDENCIA_REGISTRADA", "Evidence", evidence.id, payload, ["checklist", "juridico", "documental"])
    record_history(db, prop, "Evidence", evidence.id, "CREATE", None, payload, event.id, evidence.id)
    db.commit(); db.refresh(evidence); return evidence

@app.get("/api/imoveis/{property_id}/evidencias")
def list_evidence(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id); return db.scalars(select(models.Evidence).where(models.Evidence.property_id == property_id).order_by(models.Evidence.created_at.desc())).all()

@app.get("/api/imoveis/{property_id}/evidencias/{evidence_id}")
def get_evidence(property_id: int, evidence_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id)
    evidence = db.get(models.Evidence, evidence_id)
    if not evidence or evidence.property_id != property_id: raise HTTPException(404, "Evidência não encontrada")
    return {"evidencia": evidence, "document_version": evidence.document_version, "chunk": db.get(models.DocumentChunk, evidence.chunk_id) if evidence.chunk_id else None, "links": evidence.links}

@app.post("/api/imoveis/{property_id}/evidencias/{evidence_id}/links")
def link_evidence(property_id: int, evidence_id: int, data: schemas.EvidenceLinkCreate, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    evidence = db.get(models.Evidence, evidence_id)
    if not evidence or evidence.property_id != property_id: raise HTTPException(404, "Evidência não encontrada")
    link = models.EvidenceLink(evidence_id=evidence_id, target_type=data.target_type, target_id=data.target_id, relation=data.relation)
    db.add(link); db.flush(); payload = data.model_dump(mode="json") | {"evidence_id": evidence_id}
    event = record_event(db, prop, "EVIDENCIA_VINCULADA", "EvidenceLink", link.id, payload, ["checklist", "juridico", "documental", "financeiro"])
    record_history(db, prop, "EvidenceLink", link.id, "CREATE", None, payload, event.id, evidence_id)
    db.commit(); db.refresh(link); return link

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
    llm_runs = persist_llm_runs(db, prop, analysis, orchestration.get("llm_runs", []))
    analysis.token_usage = {**analysis.token_usage, **serialize(aggregate_llm_usage(llm_runs))}
    finance = build_finance(prop)
    db.add(models.FinancialAnalysis(property_id=prop.id, analysis_version=analysis.version, inputs={"domains": domains, "chunks": orchestration.get("retrieved_chunk_ids", [])}, outputs=serialize(finance)))
    recalculate_risks(db, prop, analysis.version)
    verdict = create_verdict(db, prop, analysis, orchestration.get("verdict"))
    db.commit()
    return {"versao": analysis.version, "agentes": agents, "llm_usada": orchestration.get("llm_used", False), "modelo": analysis.model, "chunks_recuperados": orchestration.get("retrieved_chunk_ids", []), "evidencias": evidence_ids, "llm_usage": analysis.token_usage, "financeiro": serialize(verdict.financial), "veredito": verdict.overall, "status": "concluida"}

@app.get("/api/imoveis/{property_id}/historico")
def history(property_id: int, db: Session = Depends(get_db)):
    property_or_404(db, property_id); return {"eventos": db.scalars(select(models.DomainEvent).where(models.DomainEvent.property_id == property_id).order_by(models.DomainEvent.created_at.desc())).all(), "alteracoes": db.scalars(select(models.EntityHistory).where(models.EntityHistory.property_id == property_id).order_by(models.EntityHistory.created_at.desc())).all(), "analises": db.scalars(select(models.Analysis).where(models.Analysis.property_id == property_id).order_by(models.Analysis.version.desc())).all()}
