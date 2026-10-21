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
    neighborhood: Mapped[str | None] = mapped_column(String(120))
    property_type: Mapped[str] = mapped_column(String(80), default="Apartamento")
    area_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    private_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    bedrooms: Mapped[int] = mapped_column(Integer, default=0)
    parking_spots: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    # Identificação na origem (ex.: Caixa Econômica Federal). Extensível: sem enum rígido.
    origin: Mapped[str | None] = mapped_column(String(120))
    origin_property_code: Mapped[str | None] = mapped_column(String(80))
    inscription: Mapped[str | None] = mapped_column(String(80))
    modality: Mapped[str | None] = mapped_column(String(80))
    system: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="EM_ANALISE")
    auctions: Mapped[list["Auction"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    sources: Mapped[list["PropertySource"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    registrations: Mapped[list["PropertyRegistration"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    notices: Mapped[list["AuctionNotice"]] = relationship(back_populates="property", cascade="all, delete-orphan")
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
    # 1º e 2º leilão preservados separadamente (não sobrescrevem avaliação/lance atual).
    # DateTime para preservar data + hora do leilão (ex.: 28/09/2026 10:00).
    first_auction_date: Mapped[datetime | None] = mapped_column(DateTime)
    first_auction_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    second_auction_date: Mapped[datetime | None] = mapped_column(DateTime)
    second_auction_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    acquisition_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    commission_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    commission_fixed: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    auctioneer: Mapped[str] = mapped_column(String(160), default="")
    # Vínculo opcional ao cadastro estruturado de Leiloeiro (TASK 75). O texto
    # `auctioneer` é preservado como histórico; a FK permite associar sem duplicar.
    auctioneer_id: Mapped[int | None] = mapped_column(ForeignKey("auctioneers.id"))
    notice_url: Mapped[str] = mapped_column(String(500), default="")
    # Premissas financeiras correntes (Task 3): meta de preço máximo, corretagem,
    # tributo na venda, valor de venda estimado, prazo e carregamento mensal, além
    # das premissas dos cenários. JSON reutilizado no build_finance; recuperável ao
    # reabrir o imóvel. Nunca contém segredo. Ausente por padrão (dados desconhecidos).
    financial_assumptions: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    property: Mapped[Property] = relationship(back_populates="auctions")


class PropertySource(TimestampMixin, Base):
    __tablename__ = "property_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="OUTRA")
    url: Mapped[str | None] = mapped_column(String(600))
    description: Mapped[str | None] = mapped_column(String(240))
    origin: Mapped[str | None] = mapped_column(String(120))
    property: Mapped[Property] = relationship(back_populates="sources")


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


class PropertyRegistration(TimestampMixin, Base):
    __tablename__ = "property_registrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    registration_number: Mapped[str | None] = mapped_column(String(80))
    registry_office: Mapped[str | None] = mapped_column(String(160))
    comarca: Mapped[str | None] = mapped_column(String(160))
    consultation_date: Mapped[date | None] = mapped_column(Date)
    holder: Mapped[str | None] = mapped_column(String(240))
    observations: Mapped[str | None] = mapped_column(Text)
    document_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    property: Mapped[Property] = relationship(back_populates="registrations")


class AuctionNotice(TimestampMixin, Base):
    __tablename__ = "auction_notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    identifier: Mapped[str | None] = mapped_column(String(160))
    item: Mapped[str | None] = mapped_column(String(40))
    notice_date: Mapped[date | None] = mapped_column(Date)
    auction_stage: Mapped[str | None] = mapped_column(String(80))
    appraisal_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    minimum_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    auction_date: Mapped[date | None] = mapped_column(Date)
    auctioneer: Mapped[str | None] = mapped_column(String(160))
    observations: Mapped[str | None] = mapped_column(Text)
    document_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    property: Mapped[Property] = relationship(back_populates="notices")


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
    # Classificação do vínculo processo×imóvel (migration 0013).
    # link_origin: AUTOMATICA | MANUAL | VALIDADA | NAO_CONFIRMADA
    # correlation_level: ALTA | MEDIA | BAIXA | NAO_CONFIRMADA (determinístico)
    link_origin: Mapped[str | None] = mapped_column(String(30))
    correlation_level: Mapped[str | None] = mapped_column(String(20))
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


class Auctioneer(TimestampMixin, Base):
    """Cadastro estruturado de leiloeiro (TASK 75). Um leiloeiro pode ter vários
    portais/acessos e ser referenciado por vários leilões."""
    __tablename__ = "auctioneers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    document: Mapped[str | None] = mapped_column(String(40))  # CPF/CNPJ quando aplicável
    company: Mapped[str | None] = mapped_column(String(200))
    registration: Mapped[str | None] = mapped_column(String(120))  # registro/identificação profissional
    phone: Mapped[str | None] = mapped_column(String(60))
    email: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(300))
    address: Mapped[str | None] = mapped_column(String(300))
    observations: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ATIVO")
    portals: Mapped[list["PortalAccess"]] = relationship(back_populates="auctioneer", cascade="all, delete-orphan")
    documents: Mapped[list["AuctioneerDocument"]] = relationship(back_populates="auctioneer", cascade="all, delete-orphan")


class PortalAccess(TimestampMixin, Base):
    """Portal/acesso de um leiloeiro. A credencial (``secret``) é mantida numa
    COLUNA SEPARADA e NUNCA é retornada em listagens/histórico/logs/evidências nem
    enviada a LLM/RAG (TASK 75 §19/§23). A recuperação exige endpoint dedicado."""
    __tablename__ = "portal_accesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    auctioneer_id: Mapped[int] = mapped_column(ForeignKey("auctioneers.id"), index=True)
    portal: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    username: Mapped[str | None] = mapped_column(String(200))
    # Credencial sensível — nunca serializada em respostas comuns.
    secret: Mapped[str | None] = mapped_column(Text)
    access_type: Mapped[str | None] = mapped_column(String(80))
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    observations: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ATIVO")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    auctioneer: Mapped[Auctioneer] = relationship(back_populates="portals")


class AuctioneerDocument(TimestampMixin, Base):
    """Documento do leiloeiro (contrato, credenciamento, termos, comprovantes...)."""
    __tablename__ = "auctioneer_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    auctioneer_id: Mapped[int] = mapped_column(ForeignKey("auctioneers.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(80), default="OUTROS")
    name: Mapped[str] = mapped_column(String(240))
    file_path: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)
    observations: Mapped[str | None] = mapped_column(Text)
    auctioneer: Mapped[Auctioneer] = relationship(back_populates="documents")


# ============================================================================
# PÓS-ARREMATAÇÃO (novo módulo). Acompanha a EXECUÇÃO real do investimento após a
# arrematação. Tudo vinculado ao imóvel existente (FK properties.id) — não duplica
# o cadastro do imóvel. REUSO explícito: a ação judicial referencia LegalProcess
# (legal_process_id); o estado de ocupação/desocupação continua em OccupancyAnalysis;
# a linha do tempo usa DomainEvent/EntityHistory; os custos da análise inicial
# (Cost/build_finance) permanecem intactos — o custo pós-arrematação é um registro
# SEPARADO com semântica previsto/realizado/pago. Seguindo o padrão do projeto,
# estas entidades são consultadas por property_id (sem relationship em Property),
# igual a EntityHistory, mantendo a mudança aditiva e de baixo risco.
# ============================================================================

# Situação da execução do fluxo pós-arrematação.
POST_AUCTION_STATUS = ("NAO_INICIADO", "EM_ANDAMENTO", "CONCLUIDO", "CANCELADO")

# Situação de uma etapa operacional.
STAGE_STATUS = ("PENDENTE", "EM_ANDAMENTO", "CONCLUIDA", "NAO_APLICAVEL", "BLOQUEADA")

# Situação de um custo pós-arrematação (preserva estimativa x obrigação x pago).
POST_COST_STATUS = ("PREVISTO", "PENDENTE", "PAGO", "CANCELADO", "CONTESTADO")

# Situação de uma minuta de notificação extrajudicial (conforme evidências).
NOTIFICATION_STATUS = ("RASCUNHO", "REVISADO", "EMITIDO", "ENVIADO", "RECEBIDO", "DEVOLVIDO", "SEM_CONFIRMACAO")


class PostAuction(TimestampMixin, Base):
    """Estado/ativação do fluxo de pós-arrematação de UM imóvel (1 por imóvel).

    O módulo só é ativado sob demanda (quando o imóvel entra no fluxo pós-arrematação);
    imóveis apenas analisados não possuem este registro e seguem o fluxo atual."""
    __tablename__ = "post_auctions"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True, unique=True)
    status: Mapped[str] = mapped_column(String(30), default="EM_ANDAMENTO")
    current_stage: Mapped[str | None] = mapped_column(String(120))
    # Modalidade de condução da desocupação: PROPRIA | TERCEIRIZADA | None (indefinida).
    eviction_mode: Mapped[str | None] = mapped_column(String(30))
    # Orçamento inicial congelado na ativação (snapshot do custo total da análise),
    # preservado para comparação com o realizado. Nunca sobrescreve a análise.
    initial_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    expected_sale_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    observations: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)


class PostAuctionStage(TimestampMixin, Base):
    """Etapa operacional configurável da linha do tempo pós-arrematação. Nem toda
    etapa é obrigatória para todo imóvel (``status=NAO_APLICAVEL`` quando não se
    aplica). Pode referenciar um processo jurídico existente (reuso), nunca duplica."""
    __tablename__ = "post_auction_stages"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    stage_key: Mapped[str] = mapped_column(String(60), index=True)   # chave canônica da etapa
    title: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="PENDENTE")
    responsible: Mapped[str | None] = mapped_column(String(160))
    planned_date: Mapped[date | None] = mapped_column(Date)
    actual_date: Mapped[date | None] = mapped_column(Date)
    observations: Mapped[str | None] = mapped_column(Text)
    # Reuso do domínio jurídico: etapa de ação judicial aponta para LegalProcess.
    legal_process_id: Mapped[int | None] = mapped_column(ForeignKey("legal_processes.id"))


class PostAuctionCost(TimestampMixin, Base):
    """Custo da fase pós-arrematação com semântica PREVISTO/REALIZADO/PAGO (que o
    modelo Cost atual NÃO possui). Mantém SEPARADO do Cost da análise inicial para
    não sobrescrever o financeiro histórico. Pode vincular-se a uma etapa."""
    __tablename__ = "post_auction_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(240))
    planned_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))   # previsto
    actual_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))    # realizado
    status: Mapped[str] = mapped_column(String(30), default="PREVISTO")
    competence_date: Mapped[date | None] = mapped_column(Date)               # competência
    payment_date: Mapped[date | None] = mapped_column(Date)                  # pagamento
    supplier: Mapped[str | None] = mapped_column(String(200))                # fornecedor/beneficiário
    payment_method: Mapped[str | None] = mapped_column(String(80))
    origin: Mapped[str | None] = mapped_column(String(120))
    document_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"))
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("post_auction_stages.id"))
    observations: Mapped[str | None] = mapped_column(Text)


class OccupantContact(TimestampMixin, Base):
    """Contato relacionado à ocupação. NÃO presume que o ocupante seja o antigo
    proprietário nem qualquer condição jurídica sem evidência (campos descritivos)."""
    __tablename__ = "occupant_contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(60))
    email: Mapped[str | None] = mapped_column(String(200))
    contact_type: Mapped[str | None] = mapped_column(String(80))      # tipo de contato
    relationship_label: Mapped[str | None] = mapped_column(String(120))  # relação com o imóvel (sem presumir)
    next_action: Mapped[str | None] = mapped_column(String(240))
    next_action_date: Mapped[date | None] = mapped_column(Date)
    observations: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[list["ContactAttempt"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class ContactAttempt(TimestampMixin, Base):
    """Tentativa de contato (append-only): data, canal, resultado e próxima ação."""
    __tablename__ = "contact_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("occupant_contacts.id"), index=True)
    attempt_date: Mapped[date | None] = mapped_column(Date)
    channel: Mapped[str | None] = mapped_column(String(60))           # canal utilizado
    result: Mapped[str | None] = mapped_column(String(240))           # resultado da tentativa
    next_action: Mapped[str | None] = mapped_column(String(240))
    next_action_date: Mapped[date | None] = mapped_column(Date)
    observations: Mapped[str | None] = mapped_column(Text)
    contact: Mapped[OccupantContact] = relationship(back_populates="attempts")


class Consultancy(TimestampMixin, Base):
    """Consultoria de desocupação terceirizada. Deixa explícito o que está incluído
    e o que é cobrado à parte — não presume honorários advocatícios/custas."""
    __tablename__ = "consultancies"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    cnpj: Mapped[str | None] = mapped_column(String(40))
    responsible: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(60))
    email: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    services: Mapped[str | None] = mapped_column(Text)                # serviços oferecidos
    status: Mapped[str] = mapped_column(String(30), default="EM_AVALIACAO")  # EM_AVALIACAO|CONTRATADA|DESCARTADA|ENCERRADA
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    observations: Mapped[str | None] = mapped_column(Text)
    proposals: Mapped[list["ConsultancyProposal"]] = relationship(back_populates="consultancy", cascade="all, delete-orphan")


class ConsultancyProposal(TimestampMixin, Base):
    """Proposta/contrato de uma consultoria. Permite comparar valores e escopo antes
    de selecionar. ``included_scope``/``excluded_scope`` deixam claro o que é à parte."""
    __tablename__ = "consultancy_proposals"
    id: Mapped[int] = mapped_column(primary_key=True)
    consultancy_id: Mapped[int] = mapped_column(ForeignKey("consultancies.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Proposta")
    fixed_fee: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))       # honorários fixos
    variable_fee: Mapped[str | None] = mapped_column(String(240))           # honorários variáveis (descrição)
    additional_costs: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # despesas adicionais
    payment_schedule: Mapped[str | None] = mapped_column(Text)              # forma/calendário de pagamento
    included_scope: Mapped[str | None] = mapped_column(Text)
    excluded_scope: Mapped[str | None] = mapped_column(Text)
    deadline_days: Mapped[int | None] = mapped_column(Integer)
    document_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"))
    observations: Mapped[str | None] = mapped_column(Text)
    consultancy: Mapped[Consultancy] = relationship(back_populates="proposals")


class NotificationDraft(TimestampMixin, Base):
    """Minuta de notificação extrajudicial a partir de modelo editável. É uma MINUTA,
    não um parecer jurídico — o sistema não afirma validade/recebimento/cumprimento
    de prazo sem comprovação. Mantém histórico de versões editáveis."""
    __tablename__ = "notification_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    template_key: Mapped[str | None] = mapped_column(String(80))      # modelo de origem
    title: Mapped[str] = mapped_column(String(200))
    recipient: Mapped[str | None] = mapped_column(String(200))        # destinatário
    notifier: Mapped[str | None] = mapped_column(String(200))         # notificante
    status: Mapped[str] = mapped_column(String(30), default="RASCUNHO")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    # Registro de envio/recebimento — só preenchido com evidência (sem presumir).
    delivery_channel: Mapped[str | None] = mapped_column(String(80))  # meio de envio
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    receipt_status: Mapped[str | None] = mapped_column(String(60))    # recebido/devolvido/sem confirmação
    receipt_reference: Mapped[str | None] = mapped_column(String(240))  # comprovante (código/observação)
    observations: Mapped[str | None] = mapped_column(Text)
    versions: Mapped[list["NotificationDraftVersion"]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class NotificationDraftVersion(TimestampMixin, Base):
    """Versão imutável do texto de uma minuta (append-only a cada salvamento/edição
    relevante), permitindo manter o histórico de versões do documento."""
    __tablename__ = "notification_draft_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("notification_drafts.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="RASCUNHO")
    draft: Mapped[NotificationDraft] = relationship(back_populates="versions")
    __table_args__ = (UniqueConstraint("draft_id", "version", name="uq_notification_draft_version"),)


# ============================================================================
# DUE DILIGENCE INTEGRADA (4 frentes: MATRICULA, JUDICIAL, PREFEITURA, LOCALIZACAO).
# Evolução reuse-first: NÃO duplica matrícula (PropertyRegistration), processos
# (LegalProcess), débitos (Debt) nem eventos (DomainEvent/EntityHistory). Estas
# tabelas só guardam (1) o ESTADO/rastreabilidade da investigação por frente e
# (2) a geolocalização + checklist de localização (que não têm casa hoje).
# Consultadas por property_id (padrão EntityHistory), sem relationship em Property.
# ============================================================================

# Frentes canônicas da due diligence.
DD_FRENTE_MATRICULA = "MATRICULA"
DD_FRENTE_JUDICIAL = "JUDICIAL"
DD_FRENTE_PREFEITURA = "PREFEITURA"
DD_FRENTE_LOCALIZACAO = "LOCALIZACAO"
DD_FRENTES = (DD_FRENTE_MATRICULA, DD_FRENTE_JUDICIAL, DD_FRENTE_PREFEITURA, DD_FRENTE_LOCALIZACAO)

# Estados de execução de uma frente. Distinguem explicitamente "sem ocorrência"
# (consulta feita, nada encontrado) de "não consultado" e de "não configurado" —
# ausência de resultado NUNCA é tratada como prova de ausência de risco (SPEC §9).
DD_STATUS = (
    "NAO_INICIADO",        # nenhuma consulta/registro ainda
    "NAO_CONFIGURADO",     # integração externa sem credencial/endpoint
    "AGUARDANDO_ACAO",     # depende de ação manual do usuário (import/consulta assistida)
    "EM_EXECUCAO",
    "CONSULTADO",          # consulta realizada com resultado
    "SEM_OCORRENCIA",      # consulta realizada, nada encontrado (≠ certidão negativa)
    "CONCLUIDO_COM_PENDENCIAS",
    "FALHOU",
    "INDISPONIVEL",
    "NECESSITA_REVISAO",
)

# Modalidade de obtenção dos dados de uma frente.
DD_MODO_MANUAL = "MANUAL"
DD_MODO_AUTOMATICO = "AUTOMATICO"

# Avaliações do checklist de localização (SPEC §7.4).
LOCATION_RATINGS = ("BOM", "REGULAR", "RUIM", "NAO_VERIFICADO")


class DueDiligenceFront(TimestampMixin, Base):
    """Estado/rastreabilidade de UMA frente de due diligence de um imóvel.

    Um registro por (property_id, frente). NÃO guarda os achados em si (esses vivem
    nos aggregates reutilizados: PropertyRegistration, LegalProcess, Debt, Evidence,
    PropertyLocation); guarda apenas o STATUS, a fonte, a data da consulta, o modo
    (manual/automático), as pendências e o controle de revisão humana."""
    __tablename__ = "due_diligence_fronts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    frente: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(40), default="NAO_INICIADO")
    source: Mapped[str | None] = mapped_column(String(240))          # fonte consultada/registrada
    mode: Mapped[str | None] = mapped_column(String(20))             # MANUAL | AUTOMATICO
    last_consulted_at: Mapped[datetime | None] = mapped_column(DateTime)
    summary: Mapped[str | None] = mapped_column(Text)                # resumo dos achados (humano/determinístico)
    pendencias: Mapped[list[str]] = mapped_column(JSON, default=list)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)  # nº de achados (processos/ônus/débitos)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("property_id", "frente", name="uq_dd_front_property_frente"),)


class PropertyLocation(TimestampMixin, Base):
    """Avaliação geográfica do imóvel (frente Localização). 1 por imóvel. Guarda
    coordenadas (quando geocodificadas), precisão/fonte, links externos e o checklist
    de localização (avaliações observáveis do entorno). NUNCA infere coordenadas sem
    geocodificação, nem características sensíveis a partir de imagens."""
    __tablename__ = "property_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True, unique=True)
    normalized_address: Mapped[str | None] = mapped_column(String(400))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    geocode_precision: Mapped[str | None] = mapped_column(String(40))   # ROOFTOP/APPROXIMATE/...
    geocode_source: Mapped[str | None] = mapped_column(String(120))     # Google Maps / Manual
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime)
    coordinates_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # usuário confirmou que o ponto é a unidade
    maps_url: Mapped[str | None] = mapped_column(String(600))
    street_view_url: Mapped[str | None] = mapped_column(String(600))
    # Checklist de localização: cada critério recebe BOM/REGULAR/RUIM/NAO_VERIFICADO.
    # Armazenado como JSON (chave→rating) para extensibilidade sem nova migration.
    location_checklist: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    observations: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime)     # data da inspeção visual
