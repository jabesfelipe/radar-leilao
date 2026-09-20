from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .config import settings
from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Property(TimestampMixin, Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(240))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    property_type: Mapped[str] = mapped_column(String(80), default="Apartamento")
    area_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="EM_ANALISE")
    auctions: Mapped[list["Auction"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    processes: Mapped[list["LegalProcess"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    costs: Mapped[list["Cost"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    debts: Mapped[list["Debt"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    comparables: Mapped[list["MarketComparable"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    occupancy_analyses: Mapped[list["OccupancyAnalysis"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    checklist_executions: Mapped[list["ChecklistExecution"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    verdicts: Mapped[list["Verdict"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    events: Mapped[list["DomainEvent"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    llm_runs: Mapped[list["LLMRun"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class Auction(TimestampMixin, Base):
    __tablename__ = "auctions"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    auction_date: Mapped[date | None] = mapped_column(Date)
    auction_stage: Mapped[str] = mapped_column(String(30), default="2º leilão")
    appraisal_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    bid_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    acquisition_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    commission_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    commission_fixed: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    auctioneer: Mapped[str] = mapped_column(String(160), default="")
    notice_url: Mapped[str] = mapped_column(String(500), default="")
    property: Mapped[Property] = relationship(back_populates="auctions")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    document_type: Mapped[str] = mapped_column(String(60), default="Outro")
    source: Mapped[str] = mapped_column(String(240), default="Upload manual")
    status: Mapped[str] = mapped_column(String(40), default="RECEBIDO")
    property: Mapped[Property] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(TimestampMixin, Base):
    __tablename__ = "document_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    original_path: Mapped[str] = mapped_column(String(600))
    normalized_path: Mapped[str | None] = mapped_column(String(600))
    normalized_markdown: Mapped[str | None] = mapped_column(Text)
    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="RECEBIDO")
    document: Mapped[Document] = relationship(back_populates="versions")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document_version", cascade="all, delete-orphan")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="document_version")
    __table_args__ = (UniqueConstraint("document_id", "version", name="uq_document_version"),)


class DocumentChunk(TimestampMixin, Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_version_id: Mapped[int] = mapped_column(ForeignKey("document_versions.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(240))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions))
    document_version: Mapped[DocumentVersion] = relationship(back_populates="chunks")
    __table_args__ = (Index("ix_document_chunks_content_trgm", "content", postgresql_using="gin", postgresql_ops={"content": "gin_trgm_ops"}),)


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidences"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    document_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"))
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id"))
    category: Mapped[str] = mapped_column(String(60), default="DOCUMENTAL")
    fact: Mapped[str] = mapped_column(Text)
    interpretation: Mapped[str | None] = mapped_column(Text)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="MEDIA")
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(240))
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    property: Mapped[Property] = relationship(back_populates="evidences")
    document_version: Mapped[DocumentVersion | None] = relationship(back_populates="evidences")
    links: Mapped[list["EvidenceLink"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidences.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[int] = mapped_column(Integer)
    relation: Mapped[str] = mapped_column(String(60), default="SUSTENTA")
    evidence: Mapped[Evidence] = relationship(back_populates="links")


class ChecklistItem(TimestampMixin, Base):
    __tablename__ = "checklist_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(100), unique=True)
    question: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="DUE_DILIGENCE")
    domain: Mapped[list[str]] = mapped_column(JSON, default=list)
    origin: Mapped[str] = mapped_column(String(160), default="METODO_RADAR")
    priority: Mapped[int] = mapped_column(Integer, default=3)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    expected_evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    potential_impact: Mapped[str | None] = mapped_column(Text)
    related_rules: Mapped[list[str]] = mapped_column(JSON, default=list)
    agents: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    executions: Mapped[list["ChecklistResult"]] = relationship(back_populates="item")


class ChecklistExecution(TimestampMixin, Base):
    __tablename__ = "checklist_executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    analysis_version: Mapped[int | None] = mapped_column(Integer)
    triggered_by: Mapped[str] = mapped_column(String(80), default="MANUAL")
    property: Mapped[Property] = relationship(back_populates="checklist_executions")
    results: Mapped[list["ChecklistResult"]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class ChecklistResult(TimestampMixin, Base):
    __tablename__ = "checklist_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("checklist_executions.id"), index=True)
    checklist_item_id: Mapped[int] = mapped_column(ForeignKey("checklist_items.id"), index=True)
    item_version: Mapped[int] = mapped_column(Integer)
    applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    previous_result_id: Mapped[int | None] = mapped_column(ForeignKey("checklist_results.id"))
    state: Mapped[str] = mapped_column(String(40), default="PENDENTE")
    answer: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(20), default="MEDIA")
    interpretation: Mapped[str | None] = mapped_column(Text)
    risk: Mapped[str | None] = mapped_column(Text)
    execution: Mapped[ChecklistExecution] = relationship(back_populates="results")
    item: Mapped[ChecklistItem] = relationship(back_populates="executions")
    previous_result: Mapped["ChecklistResult | None"] = relationship(remote_side="ChecklistResult.id", uselist=False)
    evidence_links: Mapped[list["ChecklistEvidence"]] = relationship(cascade="all, delete-orphan")
    evidences: Mapped[list["Evidence"]] = relationship("Evidence", secondary="checklist_evidences", viewonly=True)


class ChecklistEvidence(Base):
    __tablename__ = "checklist_evidences"
    checklist_result_id: Mapped[int] = mapped_column(ForeignKey("checklist_results.id"), primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidences.id"), primary_key=True)


class LegalProcess(TimestampMixin, Base):
    __tablename__ = "legal_processes"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    court: Mapped[str | None] = mapped_column(String(160))
    comarca: Mapped[str | None] = mapped_column(String(160))
    nature: Mapped[str | None] = mapped_column(String(120))
    subject: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str | None] = mapped_column(String(80))
    polo_active: Mapped[str | None] = mapped_column(Text)
    polo_passive: Mapped[str | None] = mapped_column(Text)
    distribution_date: Mapped[date | None] = mapped_column(Date)
    observations: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(240))
    consulted_at: Mapped[datetime | None] = mapped_column(DateTime)
    impact: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    property: Mapped[Property] = relationship(back_populates="processes")
    movements: Mapped[list["ProcessMovement"]] = relationship(back_populates="process", cascade="all, delete-orphan")


class ProcessMovement(TimestampMixin, Base):
    __tablename__ = "process_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(ForeignKey("legal_processes.id"), index=True)
    movement_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(240), default="Cadastro manual")
    process: Mapped[LegalProcess] = relationship(back_populates="movements")


class Cost(TimestampMixin, Base):
    __tablename__ = "costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(240))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    property: Mapped[Property] = relationship(back_populates="costs")


class Debt(TimestampMixin, Base):
    __tablename__ = "debts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    creditor: Mapped[str] = mapped_column(String(160), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    reference_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="PENDENTE")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    property: Mapped[Property] = relationship(back_populates="debts")


class MarketComparable(TimestampMixin, Base):
    __tablename__ = "market_comparables"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="VENDA")
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    rent: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    area_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    source: Mapped[str] = mapped_column(String(240), default="Cadastro manual")
    url: Mapped[str] = mapped_column(String(500), default="")
    property: Mapped[Property] = relationship(back_populates="comparables")


class OccupancyAnalysis(TimestampMixin, Base):
    __tablename__ = "occupancy_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="DESCONHECIDO")
    occupant_profile: Mapped[str | None] = mapped_column(String(160))
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    estimated_months: Mapped[int | None] = mapped_column(Integer)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    property: Mapped[Property] = relationship(back_populates="occupancy_analyses")


class FinancialAnalysis(TimestampMixin, Base):
    __tablename__ = "financial_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    analysis_version: Mapped[int] = mapped_column(Integer)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Risk(TimestampMixin, Base):
    __tablename__ = "risks"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIA")
    impact: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="MEDIA")
    status: Mapped[str] = mapped_column(String(30), default="ATIVO")
    origin: Mapped[str] = mapped_column(String(120), default="Motor determinístico")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    analysis_version: Mapped[int | None] = mapped_column(Integer)
    property: Mapped[Property] = relationship(back_populates="risks")


class Analysis(TimestampMixin, Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    scope: Mapped[str] = mapped_column(String(80), default="Completa")
    affected_domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    agents_executed: Mapped[list[str]] = mapped_column(JSON, default=list)
    documents_considered: Mapped[list[int]] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    changes: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    property: Mapped[Property] = relationship(back_populates="analyses")
    llm_runs: Mapped[list["LLMRun"]] = relationship(back_populates="analysis")


class Verdict(TimestampMixin, Base):
    __tablename__ = "verdicts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    analysis_version: Mapped[int] = mapped_column(Integer)
    overall: Mapped[str] = mapped_column(String(30), default="PENDENTE")
    summary: Mapped[str] = mapped_column(Text)
    what_is_known: Mapped[str] = mapped_column(Text, default="")
    what_is_unknown: Mapped[str] = mapped_column(Text, default="")
    pending_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    financial: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    property: Mapped[Property] = relationship(back_populates="verdicts")


class KnowledgeItem(TimestampMixin, Base):
    __tablename__ = "knowledge_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dimensions))


class DomainEvent(TimestampMixin, Base):
    __tablename__ = "domain_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    affected_domains: Mapped[list[str]] = mapped_column(JSON, default=list)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    property: Mapped[Property] = relationship(back_populates="events")


class EntityHistory(TimestampMixin, Base):
    __tablename__ = "entity_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(30))
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    cause_event_id: Mapped[int | None] = mapped_column(ForeignKey("domain_events.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    actor: Mapped[str] = mapped_column(String(120), default="sistema")


class LLMRun(TimestampMixin, Base):
    __tablename__ = "llm_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), index=True)
    analysis_id: Mapped[int | None] = mapped_column(ForeignKey("analyses.id"), index=True)
    agent: Mapped[str] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    input_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 8))
    output_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 8))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 8))
    input_price_per_1m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8))
    output_price_per_1m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8))
    retrieved_chunk_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    request_id: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), default="CONCLUIDO")
    error_type: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    property: Mapped[Property | None] = relationship(back_populates="llm_runs")
    analysis: Mapped[Analysis | None] = relationship(back_populates="llm_runs")


class LLMPricing(Base):
    __tablename__ = "llm_pricing"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    input_price_per_1m: Mapped[Decimal] = mapped_column(Numeric(14, 8), default=0)
    output_price_per_1m: Mapped[Decimal] = mapped_column(Numeric(14, 8), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("provider", "model", name="uq_llm_pricing_provider_model"),)
