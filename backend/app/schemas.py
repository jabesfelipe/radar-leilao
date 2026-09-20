from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class PropertyCreate(BaseModel):
    title: str = Field(min_length=2); address: str; city: str; state: str = Field(min_length=2, max_length=2); property_type: str = "Apartamento"; area_m2: Decimal = 0; bedrooms: int = 0
class PropertyOut(PropertyCreate):
    id: int; status: str; created_at: datetime; model_config = ConfigDict(from_attributes=True)
class AuctionCreate(BaseModel):
    auction_date: date | None = None; auction_stage: str = "2º leilão"; appraisal_value: Decimal = 0; bid_value: Decimal = 0; acquisition_value: Decimal | None = None; commission_percent: Decimal | None = None; commission_fixed: Decimal | None = None; auctioneer: str = ""; notice_url: str = ""
class CostCreate(BaseModel):
    category: str; description: str; amount: Decimal = 0; recurring: bool = False
class DebtCreate(BaseModel):
    category: str; creditor: str = ""; amount: Decimal = 0; reference_date: date | None = None; status: str = "PENDENTE"; evidence_id: int | None = None
class ComparableCreate(BaseModel):
    kind: str = "VENDA"; price: Decimal = 0; rent: Decimal | None = None; area_m2: Decimal = 0; source: str = "Cadastro manual"; url: str = ""
class ProcessCreate(BaseModel):
    number: str; court: str = ""; subject: str = ""; status: str = "Em análise"; source: str = "Cadastro manual"; impact: str = ""
class ChecklistUpdate(BaseModel):
    state: Literal["PENDENTE", "EM_ANALISE", "CONFIRMADO", "RISCO_IDENTIFICADO", "ATENCAO", "NAO_IDENTIFICADO", "NAO_APLICAVEL"]
    answer: str = ""
    confidence: Literal["BAIXA", "MEDIA", "ALTA"] = "MEDIA"
    interpretation: str | None = None
    risk: str | None = None

class ChecklistItemCreate(BaseModel):
    canonical_key: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1)
    description: str | None = None
    category: str = "DUE_DILIGENCE"
    domain: list[str] = Field(default_factory=lambda: ["CHECKLIST"])
    origin: str = "REGRA_OPERACIONAL"
    priority: int = Field(default=3, ge=1)
    required: bool = False
    applicable: bool = True
    active: bool = True
    expected_evidence: list[str] = Field(default_factory=list)
    potential_impact: str | None = None
    related_rules: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    risk_categories: list[str] = Field(default_factory=list)

class ChecklistItemPatch(BaseModel):
    question: str | None = None
    description: str | None = None
    category: str | None = None
    domain: list[str] | None = None
    origin: str | None = None
    priority: int | None = Field(default=None, ge=1)
    required: bool | None = None
    applicable: bool | None = None
    active: bool | None = None
    expected_evidence: list[str] | None = None
    potential_impact: str | None = None
    related_rules: list[str] | None = None
    agents: list[str] | None = None
    risk_categories: list[str] | None = None
class OccupancyCreate(BaseModel):
    status: Literal["OCUPADO", "DESOCUPADO", "DESCONHECIDO"]
    occupant_profile: str | None = None
    estimated_cost: Decimal | None = None
    estimated_months: int | None = Field(default=None, ge=0)
    evidence_id: int | None = None


class EvidenceCreate(BaseModel):
    category: str = "DOCUMENTAL"
    fact: str
    interpretation: str | None = None
    hypothesis: str | None = None
    confidence: str = "MEDIA"
    document_version_id: int | None = None
    chunk_id: int | None = None
    page: int | None = None
    section: str | None = None
    source_excerpt: str | None = None
