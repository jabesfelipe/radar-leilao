from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Property(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    auctions: Mapped[list["Auction"]] = relationship(cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(cascade="all, delete-orphan")
    processes: Mapped[list["LegalProcess"]] = relationship(cascade="all, delete-orphan")
    costs: Mapped[list["Cost"]] = relationship(cascade="all, delete-orphan")
    comparables: Mapped[list["MarketComparable"]] = relationship(cascade="all, delete-orphan")
    checklist_results: Mapped[list["ChecklistResult"]] = relationship(cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship(cascade="all, delete-orphan")
    verdicts: Mapped[list["Verdict"]] = relationship(cascade="all, delete-orphan")
    analyses: Mapped[list["Analysis"]] = relationship(cascade="all, delete-orphan")


class Auction(Base):
    __tablename__ = "auctions"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    auction_date: Mapped[date | None] = mapped_column(Date)
    auction_stage: Mapped[str] = mapped_column(String(30), default="2º leilão")
    appraisal_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    bid_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    auctioneer: Mapped[str] = mapped_column(String(160), default="")
    notice_url: Mapped[str] = mapped_column(String(500), default="")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    name: Mapped[str] = mapped_column(String(240))
    document_type: Mapped[str] = mapped_column(String(60), default="Outro")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="RECEBIDO")
    source: Mapped[str] = mapped_column(String(240), default="Upload manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LegalProcess(Base):
    __tablename__ = "legal_processes"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    number: Mapped[str] = mapped_column(String(40))
    court: Mapped[str] = mapped_column(String(160), default="")
    subject: Mapped[str] = mapped_column(String(240), default="")
    status: Mapped[str] = mapped_column(String(80), default="Em análise")
    impact: Mapped[str] = mapped_column(Text, default="")


class Cost(Base):
    __tablename__ = "costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(240))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)


class MarketComparable(Base):
    __tablename__ = "market_comparables"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    kind: Mapped[str] = mapped_column(String(20), default="VENDA")
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    source: Mapped[str] = mapped_column(String(240), default="Cadastro manual")
    url: Mapped[str] = mapped_column(String(500), default="")


class ChecklistResult(Base):
    __tablename__ = "checklist_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    item_number: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(40), default="PENDENTE")
    answer: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(20), default="MEDIA")


class Risk(Base):
    __tablename__ = "risks"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    category: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIA")
    status: Mapped[str] = mapped_column(String(30), default="ATIVO")
    source: Mapped[str] = mapped_column(String(120), default="Motor determinístico")


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    version: Mapped[int] = mapped_column(Integer)
    scope: Mapped[str] = mapped_column(String(80), default="Completa")
    changes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Verdict(Base):
    __tablename__ = "verdicts"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    analysis_version: Mapped[int] = mapped_column(Integer)
    overall: Mapped[str] = mapped_column(String(30), default="PENDENTE")
    summary: Mapped[str] = mapped_column(Text)
    financial: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
