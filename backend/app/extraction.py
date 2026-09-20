from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field

from . import models
from .ai.gateway import LLMCall, LLMGateway, build_gateway
from .rag.retriever import RetrieverFilters
from .rag.service import RAGService
from .services import persist_llm_runs, record_event, record_history

DocumentType = Literal["MATRICULA", "EDITAL"]

class ExtractionReference(BaseModel):
    field: str
    value: str = Field(min_length=1)
    chunk_id: int | None = None
    page: int | None = None
    section: str | None = None
    excerpt: str | None = None
    confidence: Literal["BAIXA", "MEDIA", "ALTA"] = "MEDIA"

class RegistrationExtraction(BaseModel):
    registration_number: str | None = None
    registry_office: str | None = None
    comarca: str | None = None
    consultation_date: date | None = None
    holder: str | None = None
    observations: str | None = None
    references: list[ExtractionReference] = Field(default_factory=list)

class NoticeExtraction(BaseModel):
    identifier: str | None = None
    notice_date: date | None = None
    auction_stage: str | None = None
    appraisal_value: Decimal | None = None
    minimum_value: Decimal | None = None
    auction_date: date | None = None
    auctioneer: str | None = None
    observations: str | None = None
    references: list[ExtractionReference] = Field(default_factory=list)

class ExtractionResult:
    def __init__(self, document_type: str, version_id: int, call: LLMCall, output=None, chunks=None):
        self.document_type = document_type; self.document_version_id = version_id; self.call = call; self.output = output; self.chunks = chunks or []
    @property
    def success(self): return self.call.status == "CONCLUIDO" and self.output is not None


def _prompt(document_type: str, context: str) -> list[dict[str, str]]:
    rules = "Extraia somente fatos literalmente presentes. Use null para ausência. Nunca conclua validade, nulidade, risco, consolidação, evicção, regularidade, dívida ou ocupação. Todo campo preenchido deve ter uma referência com field e value correspondente."
    return [{"role": "system", "content": f"Você é um extrator documental do Radar. Tipo: {document_type}. {rules}"}, {"role": "user", "content": json.dumps({"contexto": context}, ensure_ascii=False)}]


def validate_extraction_references(output: RegistrationExtraction | NoticeExtraction) -> None:
    references = {reference.field: reference.value for reference in output.references}
    for field_name in output.model_fields:
        if field_name == "references": continue
        value = getattr(output, field_name)
        if value is not None and str(value) != references.get(field_name):
            raise ValueError(f"Campo extraído sem referência correspondente: {field_name}")


def extract_document(db, property_id: int, document_version_id: int, document_type: str, gateway_override: LLMGateway | None = None) -> ExtractionResult:
    version = db.get(models.DocumentVersion, document_version_id)
    if not version or version.document.property_id != property_id: raise ValueError("DocumentVersion não pertence ao imóvel")
    document_type = document_type.upper()
    schema = RegistrationExtraction if document_type == "MATRICULA" else NoticeExtraction if document_type == "EDITAL" else None
    if schema is None: raise ValueError("Tipo de documento não suportado")
    retrieval = RAGService(db).retrieve_context(document_type.lower(), property_id, filters=RetrieverFilters(property_id=property_id, document_id=version.document_id, document_version=version.version))
    if gateway_override is not None: gateway = gateway_override
    else:
        try: gateway = build_gateway()
        except RuntimeError as exc: return ExtractionResult(document_type, document_version_id, LLMCall.unavailable("openai", "desconhecido", str(exc)), None, retrieval.chunks)
    call = gateway.structured_chat(schema, _prompt(document_type, retrieval.context))
    if call.status != "CONCLUIDO": return ExtractionResult(document_type, document_version_id, call, None, retrieval.chunks)
    try:
        output = call.content if isinstance(call.content, schema) else schema.model_validate(call.content)
        validate_extraction_references(output)
    except Exception as exc:
        call.status = "ERRO"; call.error_type = type(exc).__name__; call.error_message = str(exc); return ExtractionResult(document_type, document_version_id, call, None, retrieval.chunks)
    return ExtractionResult(document_type, document_version_id, call, output, retrieval.chunks)


def persist_extraction(db, prop: models.Property, result: ExtractionResult):
    if not result.success: raise ValueError("Não é possível persistir uma extração inválida")
    validate_extraction_references(result.output)
    version = db.get(models.DocumentVersion, result.document_version_id); output = result.output
    if result.document_type == "MATRICULA":
        item = models.PropertyRegistration(property_id=prop.id, registration_number=output.registration_number, registry_office=output.registry_office, comarca=output.comarca, consultation_date=output.consultation_date, holder=output.holder, observations=output.observations, document_version_id=version.id)
        target_type = "PropertyRegistration"; event_type = "MATRICULA_EXTRAIDA"; domains = ["juridico", "checklist"]
    else:
        item = models.AuctionNotice(property_id=prop.id, identifier=output.identifier, notice_date=output.notice_date, auction_stage=output.auction_stage, appraisal_value=output.appraisal_value, minimum_value=output.minimum_value, auction_date=output.auction_date, auctioneer=output.auctioneer, observations=output.observations, document_version_id=version.id)
        target_type = "AuctionNotice"; event_type = "EDITAL_EXTRAIDO"; domains = ["documental", "juridico", "financeiro", "checklist"]
    db.add(item); db.flush(); evidence_ids = []
    for reference in output.references:
        chunk = db.get(models.DocumentChunk, reference.chunk_id) if reference.chunk_id else None
        if reference.chunk_id and (not chunk or chunk.document_version_id != version.id): continue
        evidence = models.Evidence(property_id=prop.id, document_version_id=version.id, chunk_id=chunk.id if chunk else None, category=result.document_type, fact=f"{reference.field}: {reference.value}", confidence=reference.confidence, page=reference.page or (chunk.page if chunk else None), section=reference.section or (chunk.section if chunk else None), source_excerpt=reference.excerpt or (chunk.content[:1000] if chunk else None))
        db.add(evidence); db.flush(); evidence_ids.append(evidence.id); db.add(models.EvidenceLink(evidence_id=evidence.id, target_type=target_type, target_id=item.id, relation="SUSTENTA"))
    item.evidence_id = evidence_ids[0] if evidence_ids else None
    payload = {"document_version_id": version.id, "record_id": item.id, "evidence_ids": evidence_ids}
    event = record_event(db, prop, event_type, target_type, item.id, payload, domains); record_history(db, prop, target_type, item.id, "CREATE", None, payload, event.id, item.evidence_id)
    return item, evidence_ids
