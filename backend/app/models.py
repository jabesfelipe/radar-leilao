from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
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
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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
    __tablename__ = "auction_notices"  # opportunity_id adicionado abaixo (Onda 1)
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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
    # Rastreabilidade (v1.0.4, migration 0025). NULL = registro anterior, origem não registrada.
    # origin: DOCUMENTO | CADASTRO | CALCULO | PESQUISA_JUDICIAL | INFERENCIA_IA | REGRA_DETERMINISTICA
    # strength: FORTE | MODERADA | FRACA | INVALIDA (força da citação de documento; ver app/citations.py)
    origin: Mapped[str | None] = mapped_column(String(30))
    strength: Mapped[str | None] = mapped_column(String(20))
    agent: Mapped[str | None] = mapped_column(String(40))
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
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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
    # Como o item saiu de PENDENTE (v1.0.4): DOCUMENTO (evidência validada) | REGRA_DETERMINISTICA (dados
    # cadastrados) | NULL (pendente, manual ou registro anterior).
    resolution_origin: Mapped[str | None] = mapped_column(String(30))
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
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
    analysis_version: Mapped[int] = mapped_column(Integer)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Risk(TimestampMixin, Base):
    __tablename__ = "risks"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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
    # Integridade do histórico: uma única análise por (imóvel, oportunidade, versão);
    # NULL (legado) conta como 0. Defesa em profundidade contra duas requisições
    # simultâneas calcularem a mesma versão (a serialização principal é o advisory lock
    # de ``/analisar``). Espelha a migration 0024.
    __table_args__ = (Index("uq_analysis_property_opp_version", "property_id", text("(COALESCE(opportunity_id, 0))"), "version", unique=True),)


class Verdict(TimestampMixin, Base):
    __tablename__ = "verdicts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True, unique=True)  # UNIQUE preservado (Gate 1 opção A)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1); rastreabilidade
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
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado (Onda 1)
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


# ============================================================================
# CENTRAL JURÍDICA (camada transversal de conhecimento jurídico).
#
# Objetivo (SPEC Central Jurídica): NÃO é "uma página que lista leis", e sim uma
# BASE de conhecimento jurídico reutilizável que aparece EM CONTEXTO de decisão —
# nos itens do checklist, na desocupação/posse, na due diligence e no veredito.
#
# Reuse-first:
#   - a BUSCA semântica/RAG reaproveita ``KnowledgeItem`` (kind=LEGAL_LIBRARY) +
#     ``RAGService``/embeddings (não cria um segundo mecanismo de embedding);
#   - as EVIDÊNCIAS continuam em ``Evidence``/``EvidenceLink``;
#   - a rastreabilidade continua em ``DomainEvent``/``EntityHistory``;
#   - os 27 ``canonical_key`` do Checklist Mestre NÃO são alterados: a Central
#     apenas os ENRIQUECE com referências legais (via LegalRuleChecklistLink).
#
# Estas tabelas guardam a BASE LEGAL CURADA (fontes, dispositivos, regras práticas e
# o vínculo regra↔checklist). São "catálogo" (não ligadas a um imóvel específico):
# consultadas globalmente e cruzadas com o contexto do imóvel em tempo de leitura.
#
# Princípio de integridade (igual ao resto do projeto): NUNCA fabricar norma. Texto
# oficial (``official_text``) é preservado SEPARADO da paráfrase/orientação prática
# (``practical_note``); vigência é explícita; conteúdo não verificado fica como
# ``verification_status="PENDENTE"`` e jamais é apresentado como confirmado.
# ============================================================================

# Tipos de fonte legal (extensível; sem enum rígido no banco).
LEGAL_SOURCE_TYPES = (
    "LEI",            # lei ordinária/complementar (ex.: Lei 9.514/97)
    "CODIGO",         # código (Código Civil, CPC, CTN...)
    "DECRETO",
    "SUMULA",         # súmula de tribunal superior
    "JURISPRUDENCIA", # acórdão/tese/repetitivo
    "ENUNCIADO",      # enunciado doutrinário/jornada
    "DOUTRINA",
    "OUTRO",
)

# Situação de verificação da curadoria (a fonte foi conferida no texto oficial?).
LEGAL_VERIFICATION_STATUS = (
    "VERIFICADO",   # conferido contra fonte oficial (texto fiel ao vigente)
    "PENDENTE",     # cadastrado, ainda não conferido na fonte oficial
    "DESATUALIZADO" # norma revogada/alterada — manter por histórico, sinalizar
)

# Natureza de uma regra prática (como o conhecimento é aplicado na decisão).
LEGAL_RULE_KINDS = (
    "REQUISITO",     # condição que precisa ser verificada/atendida
    "RISCO",         # alerta de risco jurídico
    "ORIENTACAO",    # orientação prática/procedimental
    "PRAZO",         # prazo relevante
    "RESPONSABILIDADE",
)

# Etapas/contextos transversais onde a regra aparece (reutiliza vocabulário do
# projeto: categorias de checklist + fluxo pós-arrematação/desocupação).
LEGAL_CONTEXTS = (
    "LEILAO",
    "ARREMATACAO",
    "MATRICULA",
    "CONSOLIDACAO",
    "DESOCUPACAO",
    "POSSE",
    "TRIBUTARIO",
    "LOCACAO",
    "GERAL",
)

# Kind reservado no KnowledgeItem para a biblioteca jurídica indexável por RAG.
LEGAL_LIBRARY_KIND = "LEGAL_LIBRARY"


class LegalSource(TimestampMixin, Base):
    """Fonte legal curada (lei, código, súmula, jurisprudência...).

    É o "cabeçalho" da norma: identificação, apelido, link oficial e vigência. Os
    artigos/dispositivos concretos ficam em ``LegalProvision``. Não guarda nada por
    imóvel — é catálogo compartilhado. ``slug`` é único e estável (usado em links
    e seeds idempotentes)."""
    __tablename__ = "legal_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(30), index=True)  # LEGAL_SOURCE_TYPES
    label: Mapped[str] = mapped_column(String(160))                   # apelido curto (ex.: "Lei 9.514/97")
    title: Mapped[str] = mapped_column(String(300))                   # ementa/nome completo
    authority: Mapped[str | None] = mapped_column(String(160))        # órgão/esfera (ex.: "Federal", "STJ")
    official_url: Mapped[str | None] = mapped_column(String(600))     # link para a fonte oficial
    year: Mapped[int | None] = mapped_column(Integer)
    in_force: Mapped[bool] = mapped_column(Boolean, default=True)     # vigente?
    verification_status: Mapped[str] = mapped_column(String(20), default="PENDENTE")  # LEGAL_VERIFICATION_STATUS
    summary: Mapped[str | None] = mapped_column(Text)                 # resumo neutro (paráfrase)
    observations: Mapped[str | None] = mapped_column(Text)
    provisions: Mapped[list["LegalProvision"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class LegalProvision(TimestampMixin, Base):
    """Dispositivo concreto de uma fonte (artigo/§/inciso ou tese/súmula específica).

    Preserva o TEXTO OFICIAL (``official_text``, verbatim do dispositivo vigente)
    SEPARADO da ``practical_note`` (paráfrase/explicação prática do Método Radar).
    Nunca mistura os dois — o usuário sempre distingue o que é lei do que é
    interpretação. ``knowledge_item_id`` liga (opcionalmente) ao KnowledgeItem
    indexado por RAG, reaproveitando a busca semântica existente."""
    __tablename__ = "legal_provisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("legal_sources.id"), index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    reference: Mapped[str] = mapped_column(String(160))     # ex.: "Art. 27, §1º"
    heading: Mapped[str | None] = mapped_column(String(300))  # título/epígrafe do dispositivo
    official_text: Mapped[str | None] = mapped_column(Text)   # texto oficial (verbatim) — pode ser None se PENDENTE
    practical_note: Mapped[str | None] = mapped_column(Text)  # paráfrase/orientação (NUNCA apresentada como texto legal)
    contexts: Mapped[list[str]] = mapped_column(JSON, default=list)  # subset de LEGAL_CONTEXTS
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    verification_status: Mapped[str] = mapped_column(String(20), default="PENDENTE")
    knowledge_item_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_items.id"))
    source: Mapped[LegalSource] = relationship(back_populates="provisions")
    rules: Mapped[list["LegalRule"]] = relationship(back_populates="provision")


class LegalRule(TimestampMixin, Base):
    """Regra prática do Método Radar ancorada em uma base legal.

    É a ponte entre a NORMA e a DECISÃO: descreve o que verificar/observar, de que
    risco se trata e qual a orientação, sempre apontando (quando existe) o
    ``provision_id`` que a fundamenta. Uma regra pode ser vinculada a um ou mais
    itens do checklist (via LegalRuleChecklistLink) sem alterar os 27 canonical_key."""
    __tablename__ = "legal_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    rule_kind: Mapped[str] = mapped_column(String(30), index=True)   # LEGAL_RULE_KINDS
    title: Mapped[str] = mapped_column(String(240))
    statement: Mapped[str] = mapped_column(Text)                     # a regra em si (orientação/risco)
    contexts: Mapped[list[str]] = mapped_column(JSON, default=list)  # subset de LEGAL_CONTEXTS
    severity: Mapped[str | None] = mapped_column(String(20))         # ALTA/MEDIA/BAIXA quando for RISCO
    provision_id: Mapped[int | None] = mapped_column(ForeignKey("legal_provisions.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    provision: Mapped[LegalProvision | None] = relationship(back_populates="rules")
    checklist_links: Mapped[list["LegalRuleChecklistLink"]] = relationship(back_populates="rule", cascade="all, delete-orphan")


class LegalRuleChecklistLink(TimestampMixin, Base):
    """Vínculo regra jurídica ↔ item do Checklist Mestre (por ``canonical_key``).

    Este é o mecanismo que ENRIQUECE os 27 itens do checklist com base legal SEM
    tocar na definição canônica (CHECKLIST_MASTER). Guardamos a ``canonical_key``
    como string (não FK): os itens são recriados por execução, mas a chave canônica
    é estável e é o identificador correto para correlação transversal."""
    __tablename__ = "legal_rule_checklist_links"
    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("legal_rules.id"), index=True)
    canonical_key: Mapped[str] = mapped_column(String(80), index=True)
    relevance: Mapped[str] = mapped_column(String(20), default="PRINCIPAL")  # PRINCIPAL | COMPLEMENTAR
    note: Mapped[str | None] = mapped_column(String(300))
    rule: Mapped[LegalRule] = relationship(back_populates="checklist_links")
    __table_args__ = (UniqueConstraint("rule_id", "canonical_key", name="uq_legal_rule_checklist"),)


# ---------------------------------------------------------------------------
# Domínio de Oportunidade + Workflow (Ciclo 2 — Onda 1)
# Base: SPEC-OPPORTUNITY-DOMAIN, MODEL-DATA-WORKFLOW, SPEC-WORKFLOW-ENGINE.
# Property 1:N Opportunity; Opportunity 1:1 OpportunityWorkflow; Opportunity 1:N
# WorkflowTransition (append-only). opportunity_id é NULLABLE nas 9 tabelas de
# trabalho (NULL = oportunidade legada implícita; sem backfill — Gate 2 bloqueado).
# As novas colunas/relationships NÃO participam do cascade de Property.
# ---------------------------------------------------------------------------


class Opportunity(TimestampMixin, Base):
    """Uma oferta de aquisição específica sobre um imóvel (este leilão/edital/
    preço/data). 1 Imóvel : N Oportunidades. Agrega análise + workflow + decisão;
    não substitui Auction (que é a oferta concreta/edital). Históricos de
    oportunidades diferentes nunca se misturam (ver SPEC-OPPORTUNITY-ISOLATION)."""
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    codigo: Mapped[str | None] = mapped_column(String(120))
    modality: Mapped[str] = mapped_column(String(40), default="INDEFINIDO", index=True)  # F1
    modality_evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    origin: Mapped[str | None] = mapped_column(String(120))
    portal: Mapped[str | None] = mapped_column(String(120))
    external_id: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="EM_PROSPECCAO", index=True)
    is_legacy: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    close_reason: Mapped[str | None] = mapped_column(String(240))
    actor: Mapped[str] = mapped_column(String(120), default="sistema")
    workflow: Mapped["OpportunityWorkflow | None"] = relationship(
        back_populates="opportunity", uselist=False, cascade="all, delete-orphan"
    )
    transitions: Mapped[list["WorkflowTransition"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", order_by="WorkflowTransition.id"
    )
    __table_args__ = (
        Index("ix_opportunities_property_status", "property_id", "status"),
    )


class OpportunityWorkflow(TimestampMixin, Base):
    """Estado vivo do workflow de uma oportunidade (fase corrente + estado por
    fase). 1:1 com Opportunity. phase_states/active_hard_stops são projeção/cache
    recalculável a partir dos domínios; a verdade permanece nos domínios."""
    __tablename__ = "opportunity_workflows"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunities.id"), nullable=False, unique=True, index=True
    )
    current_phase: Mapped[str] = mapped_column(String(40), default="F0_INTAKE", index=True)
    phase_states: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active_hard_stops: Mapped[list[str]] = mapped_column(JSON, default=list)
    ruleset_version: Mapped[str | None] = mapped_column(String(40))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    updated_by: Mapped[str] = mapped_column(String(120), default="sistema")
    opportunity: Mapped[Opportunity] = relationship(back_populates="workflow")


class WorkflowTransition(TimestampMixin, Base):
    """Trilha IMUTÁVEL (append-only) de cada mudança de fase/estado/decisão de uma
    oportunidade. Semântica própria de workflow (fase origem/destino, gates, hard
    stops avaliados, decisão), complementando — não duplicando — EntityHistory.
    Política append-only garantida no serviço (sem UPDATE/DELETE) + teste."""
    __tablename__ = "workflow_transitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    from_phase: Mapped[str | None] = mapped_column(String(40))
    to_phase: Mapped[str] = mapped_column(String(40))
    transition_type: Mapped[str] = mapped_column(String(30), index=True)
    result: Mapped[str] = mapped_column(String(30))
    phase_state: Mapped[str] = mapped_column(String(30))
    hard_stops: Mapped[list[str]] = mapped_column(JSON, default=list)
    gate_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    score_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    decision: Mapped[str | None] = mapped_column(String(30))
    justification: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(120), default="sistema")
    ruleset_version: Mapped[str | None] = mapped_column(String(40))
    cause_event_id: Mapped[int | None] = mapped_column(ForeignKey("domain_events.id"))
    opportunity: Mapped[Opportunity] = relationship(back_populates="transitions")
    __table_args__ = (
        Index("ix_workflow_transitions_opportunity_to_phase", "opportunity_id", "to_phase"),
    )


# ===========================================================================
# CENTRAL DE DÉBITOS/DESPESAS + PARÂMETROS ADMINISTRÁVEIS (Etapa A)
# Base: docs/PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md. Tudo ADITIVO: preserva
# Debt/Cost e os endpoints atuais. Catálogos administráveis (município/tipo/fonte)
# e um catálogo CENTRAL de parâmetros (transversal, não só de débitos), com
# resolução por precedência e histórico imutável. Sem coletores/scraping/consulta
# externa nesta etapa (fontes são apenas cadastradas).
# ===========================================================================

# --- Vocabulários canônicos (constantes de código; estrutura, não valor de negócio) ---
# Grupos de débito/despesa (natureza macro). Catálogo de TIPOS é administrável (debt_types).
DEBT_GROUPS = ("MUNICIPAL", "CONDOMINIO", "CONCESSIONARIA", "AQUISICAO_REGULARIZACAO", "OUTRO")

# Natureza do lançamento: separa o que é passivo do que é custo/estimativa (nunca somar entre si).
DEBT_NATURES = ("DIVIDA_EXISTENTE", "OBRIGACAO_POTENCIAL", "CUSTO_AQUISICAO", "ESTIMATIVA_OPERACIONAL")

# Situação do registro. ESTIMADO nunca é tratado como CONFIRMADO.
DEBT_STATUSES = ("PENDENTE", "CONFIRMADO", "INFORMADO", "ESTIMADO", "QUITADO", "CANCELADO", "INDISPONIVEL", "EM_VALIDACAO")

# Grau de confiabilidade da informação.
DEBT_RELIABILITIES = ("OFICIAL", "DOCUMENTAL", "INFORMADO", "ESTIMADO", "NAO_VERIFICADO")

# Tipos de fonte de informação (cadastro; nenhuma consulta executada nesta etapa).
DEBT_SOURCE_TYPES = ("API_OFICIAL", "SERVICO_OFICIAL", "PORTAL_PUBLICO", "CONSULTA_MANUAL", "DOCUMENTO", "OUTRA_FONTE")

# --- Cobertura municipal (Etapa B) --------------------------------------------
# Situação operacional de uma fonte/cobertura. "NAO_INVESTIGADA" é o estado honesto
# inicial: ausência de investigação ≠ ausência de débito. Nunca declarar
# disponibilidade sem evidência.
DEBT_SOURCE_SITUATIONS = (
    "NAO_INVESTIGADA", "EM_INVESTIGACAO", "DISPONIVEL", "INDISPONIVEL",
    "DEPENDE_AUTENTICACAO", "BLOQUEADA",
)

# Método pelo qual a consulta é (ou será) obtida. Nenhuma automação nesta etapa;
# o método apenas descreve a viabilidade cadastrada.
DEBT_CONSULTATION_METHODS = (
    "MANUAL", "PORTAL_PUBLICO", "SERVICO_OFICIAL", "API_OFICIAL", "DOCUMENTO", "INDEFINIDO",
)

# Nível de cobertura de um município × tipo de débito. Independente por combinação;
# não é derivado de condicional fixa — é DADO, administrável.
COVERAGE_LEVELS = (
    "NAO_INVESTIGADA",       # ainda não analisada (default honesto)
    "MANUAL",                # só consulta manual assistida (fallback sempre válido)
    "PARCIAL",               # alguma via disponível, com limitações
    "AUTOMATIZAVEL",         # portal/serviço potencialmente automatizável (não automatizado)
    "INTEGRACAO_DISPONIVEL", # API/serviço oficial disponível (ainda não integrado nesta etapa)
    "INDISPONIVEL",          # sem via conhecida
)

# --- Consulta de débito / orquestração (Etapa E) ------------------------------
# Status de UMA execução de consulta (manual/assistida ou futura automatizada).
# Alinhado ao padrão de due_diligence_fronts: "sem ocorrência" ≠ "não consultado".
DEBT_QUERY_STATUSES = (
    "PENDENTE",                   # planejada, ainda não executada
    "EM_EXECUCAO",
    "CONCLUIDA",                  # retornou resultado
    "PARCIAL",                    # resultado incompleto
    "SEM_OCORRENCIA",             # consulta feita, nada encontrado (≠ ausência de débito)
    "INDISPONIVEL",               # fonte indisponível no momento
    "REQUER_INTERVENCAO_MANUAL",  # precisa de ação humana (identificador/portal)
    "ERRO",                       # falha técnica
)

# Modo de execução de uma consulta.
DEBT_QUERY_MODES = ("MANUAL", "ASSISTIDA", "AUTOMATICA")

# --- Estimativa condominial (Etapa C) -----------------------------------------
# Grau de confiança da estimativa (NUNCA é passivo confirmado).
ESTIMATE_CONFIDENCE = ("BAIXA", "MEDIA", "ALTA")

# Catálogo central de parâmetros.
PARAMETER_DATA_TYPES = ("STRING", "INTEGER", "DECIMAL", "BOOLEAN", "JSON")
PARAMETER_SCOPES = ("GLOBAL", "MUNICIPIO", "CATEGORIA", "MUNICIPIO_CATEGORIA")
PARAMETER_STATUSES = ("ATIVO", "INATIVO")


class Municipality(TimestampMixin, Base):
    """Município cadastrável com cobertura inicial ativa (Curitiba, SJP, Fazenda Rio
    Grande, Assis). A cobertura NÃO vive em condicionais do backend — é dado. Novos
    municípios entram pelo módulo administrativo."""
    __tablename__ = "municipalities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    ibge_code: Mapped[str | None] = mapped_column(String(7), unique=True)   # confirmado quando disponível
    coverage_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="ATIVO")
    observations: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list["DebtSource"]] = relationship(back_populates="municipality", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("name", "state", name="uq_municipality_name_state"),
    )


class DebtType(TimestampMixin, Base):
    """Catálogo ADMINISTRÁVEL de tipos de débito/despesa (código, grupo, natureza).
    Evita enum rígido espalhado pelo código; novas categorias entram por cadastro.
    ``canonical_cost_key`` mapeia para a chave do breakdown do motor financeiro
    (finance.COST_KEYS) quando o tipo impacta o financeiro — sem dupla contagem."""
    __tablename__ = "debt_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)   # ex.: IPTU, COTA_CONDOMINIAL
    label: Mapped[str] = mapped_column(String(160))
    group: Mapped[str] = mapped_column(String(40), index=True)               # DEBT_GROUPS
    default_nature: Mapped[str] = mapped_column(String(30), default="DIVIDA_EXISTENTE")  # DEBT_NATURES
    canonical_cost_key: Mapped[str | None] = mapped_column(String(40))       # finance.COST_KEYS (opcional)
    impacts_finance: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class DebtSource(TimestampMixin, Base):
    """Fonte de informação por município × tipo de débito. Nesta etapa é apenas
    CADASTRO/administração (nenhuma consulta é executada). Guarda a classificação da
    fonte, situação operacional e a data da última validação."""
    __tablename__ = "debt_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_id: Mapped[int] = mapped_column(ForeignKey("municipalities.id"), nullable=False, index=True)
    debt_category: Mapped[str | None] = mapped_column(String(60), index=True)  # code de DebtType (opcional: fonte geral)
    name: Mapped[str] = mapped_column(String(200))
    authority: Mapped[str | None] = mapped_column(String(200))                 # órgão responsável
    official_url: Mapped[str | None] = mapped_column(String(600))              # só quando conhecida/validada
    source_type: Mapped[str] = mapped_column(String(30), default="CONSULTA_MANUAL")  # DEBT_SOURCE_TYPES
    method: Mapped[str | None] = mapped_column(String(120))                    # método disponível (texto)
    situation: Mapped[str] = mapped_column(String(30), default="NAO_INVESTIGADA")    # situação operacional
    access_requirements: Mapped[str | None] = mapped_column(Text)              # auth/CAPTCHA/certificado (texto)
    limitations: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    municipality: Mapped[Municipality] = relationship(back_populates="sources")


class PropertyDebt(TimestampMixin, Base):
    """Débito/despesa NORMALIZADO de um imóvel/oportunidade (modelo rico da Central).

    Aditivo: NÃO substitui ``Debt``/``Cost`` (que seguem intactos). Representa o
    resultado estruturado de identificação/consulta/estimativa, separando SEMPRE
    ``valor_original`` de ``valor_atualizado`` e marcando natureza/status/
    confiabilidade. ``opportunity_id`` é NULLABLE (NULL = legado; Gate 1)."""
    __tablename__ = "property_debts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey("municipalities.id"), index=True)
    debt_type_code: Mapped[str] = mapped_column(String(60), index=True)        # code de DebtType
    subcategory: Mapped[str | None] = mapped_column(String(80))
    nature: Mapped[str] = mapped_column(String(30), default="DIVIDA_EXISTENTE", index=True)  # DEBT_NATURES
    creditor: Mapped[str | None] = mapped_column(String(200))
    external_id: Mapped[str | None] = mapped_column(String(120))               # identificador do débito na fonte
    competence: Mapped[str | None] = mapped_column(String(20))                 # competência (ex.: 2025/03)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)                   # exercício
    due_date: Mapped[date | None] = mapped_column(Date)
    original_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    interest: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    penalty: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    correction: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    updated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    reference_date: Mapped[date | None] = mapped_column(Date)                  # data-base do valor
    status: Mapped[str] = mapped_column(String(30), default="PENDENTE", index=True)  # DEBT_STATUSES
    reliability: Mapped[str] = mapped_column(String(30), default="NAO_VERIFICADO")   # DEBT_RELIABILITIES
    origin: Mapped[str | None] = mapped_column(String(120))                    # origem da informação (texto)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("debt_sources.id"))
    acquisition_method: Mapped[str | None] = mapped_column(String(120))        # método de obtenção
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    queried_at: Mapped[datetime | None] = mapped_column(DateTime)              # data/hora da consulta (quando houver)
    observations: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        Index("ix_property_debts_property_status", "property_id", "status"),
    )


class Parameter(TimestampMixin, Base):
    """Catálogo CENTRAL de parâmetros administráveis (transversal: financeiro, risco,
    mercado, checklist, débitos, etc.). Resolução por precedência (serviço central).
    Segredos NUNCA entram aqui (continuam em cofre/secrets_crypto). ``value``/
    ``default_value`` são texto serializado conforme ``data_type`` (validado no serviço)."""
    __tablename__ = "parameters"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), index=True)                  # ex.: condominio.margem_seguranca_pct
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), index=True)              # financeiro/mercado/estimativa/...
    data_type: Mapped[str] = mapped_column(String(20), default="STRING")       # PARAMETER_DATA_TYPES
    scope: Mapped[str] = mapped_column(String(30), default="GLOBAL", index=True)  # PARAMETER_SCOPES
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey("municipalities.id"), index=True)
    debt_category: Mapped[str | None] = mapped_column(String(60), index=True)  # code de DebtType (opcional)
    value: Mapped[str | None] = mapped_column(Text)                            # valor atual (serializado)
    default_value: Mapped[str | None] = mapped_column(Text)                    # valor padrão (serializado)
    unit: Mapped[str | None] = mapped_column(String(40))
    allowed_values: Mapped[list | None] = mapped_column(JSON)                  # whitelist opcional
    min_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    max_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="ATIVO", index=True)  # PARAMETER_STATUSES
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str] = mapped_column(String(120), default="sistema")
    history: Mapped[list["ParameterHistory"]] = relationship(back_populates="parameter", cascade="all, delete-orphan", order_by="ParameterHistory.id")
    __table_args__ = (
        # Unicidade por chave + escopo (um valor por combinação de abrangência).
        UniqueConstraint("key", "scope", "municipality_id", "debt_category", name="uq_parameter_scope"),
        Index("ix_parameters_key_scope", "key", "scope"),
    )


class ParameterHistory(TimestampMixin, Base):
    """Trilha IMUTÁVEL (append-only) de alterações de um parâmetro, para auditoria e
    para identificar a versão vigente em uma análise. Nunca sobrescreve versões."""
    __tablename__ = "parameter_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    parameter_id: Mapped[int] = mapped_column(ForeignKey("parameters.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[int] = mapped_column(Integer)
    previous_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(20), default="UPDATE")          # CREATE/UPDATE/ACTIVATE/DEACTIVATE
    actor: Mapped[str] = mapped_column(String(120), default="sistema")
    justification: Mapped[str | None] = mapped_column(Text)
    parameter: Mapped[Parameter] = relationship(back_populates="history")


class MunicipalityCoverage(TimestampMixin, Base):
    """Matriz de cobertura: o que cada MUNICÍPIO cobre para cada TIPO de débito.

    Esta é a estrutura operacional da Etapa B. A cobertura é INDEPENDENTE por
    município × tipo (Curitiba pode cobrir IPTU + dívida ativa; outro, só IPTU) e
    vive como DADO — nunca em condicional fixa no código. Aditivo e reversível;
    não toca ``Debt``/``Cost``/``PropertyDebt`` da Etapa A.

    Nenhuma consulta externa é executada: esta tabela apenas declara disponibilidade
    e viabilidade conhecidas, com situação, método, limitações e data da última
    validação. ``level``/``situation``/``method`` seguem vocabulários canônicos
    (COVERAGE_LEVELS/DEBT_SOURCE_SITUATIONS/DEBT_CONSULTATION_METHODS). A fonte
    preferencial (``source_id``) é opcional e sempre do mesmo município."""
    __tablename__ = "municipality_coverage"
    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_id: Mapped[int] = mapped_column(ForeignKey("municipalities.id"), nullable=False, index=True)
    debt_type_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)  # code de DebtType
    level: Mapped[str] = mapped_column(String(30), default="NAO_INVESTIGADA", index=True)  # COVERAGE_LEVELS
    situation: Mapped[str] = mapped_column(String(30), default="NAO_INVESTIGADA")           # DEBT_SOURCE_SITUATIONS
    method: Mapped[str] = mapped_column(String(30), default="INDEFINIDO")                    # DEBT_CONSULTATION_METHODS
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)                  # cobertura ligada/desligada
    source_id: Mapped[int | None] = mapped_column(ForeignKey("debt_sources.id"))            # fonte preferencial (opcional)
    identifier_required: Mapped[str | None] = mapped_column(String(160))                    # identificador exigido (ex.: Inscrição Imobiliária)
    limitations: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    municipality: Mapped["Municipality"] = relationship()
    __table_args__ = (
        # Uma linha por município × tipo de débito (sem duplicidade).
        UniqueConstraint("municipality_id", "debt_type_code", name="uq_coverage_municipality_type"),
        Index("ix_coverage_municipality_type", "municipality_id", "debt_type_code"),
    )


class DebtQuery(TimestampMixin, Base):
    """Execução de uma consulta de débito (Etapa E), manual/assistida ou futura
    automatizada. Rastreabilidade por consulta: fonte, provider, status, origem do
    resultado e evidência. Separa CONSULTA de normalização/persistência — o resultado
    normalizado vira ``PropertyDebt`` (reusado), e esta tabela guarda o histórico da
    execução. NENHUMA consulta externa é disparada pelo modelo; ele apenas registra.

    ``opportunity_id`` é NULLABLE (NULL = legado; Gate 1). ``debt_id`` liga ao
    ``PropertyDebt`` gerado (quando houver). ``provider`` identifica o adaptador
    determinístico utilizado (ex.: ``manual_assistida``)."""
    __tablename__ = "debt_queries"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey("municipalities.id"), index=True)
    debt_type_code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), default="manual_assistida")  # nome do adaptador
    provider_version: Mapped[str | None] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(20), default="MANUAL")                # DEBT_QUERY_MODES
    status: Mapped[str] = mapped_column(String(30), default="PENDENTE", index=True)  # DEBT_QUERY_STATUSES
    source_id: Mapped[int | None] = mapped_column(ForeignKey("debt_sources.id"))
    identifier: Mapped[str | None] = mapped_column(String(160))                    # identificador usado (ex.: inscrição)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=1)                       # tentativas (retry controlado)
    message: Mapped[str | None] = mapped_column(Text)                              # mensagem/limitação/erro estruturado
    debt_id: Mapped[int | None] = mapped_column(ForeignKey("property_debts.id"))   # PropertyDebt gerado (quando houver)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))
    __table_args__ = (
        Index("ix_debt_queries_property_status", "property_id", "status"),
    )


class CondominiumEstimate(TimestampMixin, Base):
    """Estimativa PARAMETRIZADA de despesa condominial (Etapa C). NUNCA é passivo
    confirmado: é sempre ESTIMADO, com memória de cálculo, premissas, grau de
    confiança e cenários conservador/provável/otimista.

    Distingue rigorosamente (campos de CONTEXTO, nunca prova de dívida):
    idade do imóvel, idade do condomínio, tempo de financiamento e período presumido
    de inadimplência. O período de inadimplência é um PARÂMETRO explícito
    (``months_delinquent``), nunca derivado da idade do imóvel/financiamento.

    Os valores dos cenários são gravados como snapshot do cálculo; os parâmetros
    efetivamente usados ficam em ``assumptions`` (JSON) para auditoria/imutabilidade."""
    __tablename__ = "condominium_estimates"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), nullable=False, index=True)
    opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id"), index=True)  # NULL = legado
    monthly_reference: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))   # valor mensal de referência (informado ou do parâmetro)
    monthly_source: Mapped[str] = mapped_column(String(20), default="ESTIMADO")  # INFORMADO | ESTIMADO
    months_delinquent: Mapped[int | None] = mapped_column(Integer)              # período PRESUMIDO de inadimplência (parâmetro)
    safety_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))    # fração (0.10 = 10%)
    # Contexto (NUNCA passivo): separados explicitamente.
    property_age_years: Mapped[int | None] = mapped_column(Integer)
    condominium_age_years: Mapped[int | None] = mapped_column(Integer)
    financing_age_years: Mapped[int | None] = mapped_column(Integer)
    # Resultado (snapshot do cálculo determinístico).
    scenario_conservador: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    scenario_provavel: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    scenario_otimista: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    confidence: Mapped[str] = mapped_column(String(10), default="BAIXA")        # ESTIMATE_CONFIDENCE
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)     # parâmetros usados + memória de cálculo
    justification: Mapped[str | None] = mapped_column(Text)
    reference_date: Mapped[date | None] = mapped_column(Date)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidences.id"))


# ============================================================================
# AUTENTICAÇÃO / RBAC (Onda 11)
# Identidade local em PostgreSQL. Senha SEMPRE com hash (bcrypt); nunca em claro.
# Papéis com permissões explícitas (ver authz.py). O antigo X-Admin-Token permanece
# apenas como compatibilidade temporária, não como identidade.
# ============================================================================

# Papéis de usuário. Permissões explícitas vivem em authz.ROLE_PERMISSIONS.
USER_ROLES = ("ADMIN", "ANALISTA", "OPERADOR", "CONSULTA")


class User(TimestampMixin, Base):
    """Usuário do Radar. Autenticação por e-mail + senha (hash bcrypt); autorização
    por papel (``role`` em USER_ROLES). ``active=False`` bloqueia o login (falha-
    fechada). Nenhum usuário/senha padrão é criado automaticamente — o bootstrap do
    primeiro admin é opcional e vem do ambiente."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="CONSULTA")  # USER_ROLES
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_email"),
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )
