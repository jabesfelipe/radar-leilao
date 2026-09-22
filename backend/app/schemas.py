from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class PropertyCreate(BaseModel):
    title: str = Field(min_length=2)
    address: str = ""
    city: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    property_type: str = "Apartamento"
    neighborhood: str | None = None
    area_m2: Decimal = 0
    private_area_m2: Decimal | None = None
    bedrooms: int = 0
    parking_spots: int | None = None
    description: str | None = None
    origin: str | None = None
    origin_property_code: str | None = None
    inscription: str | None = None
    modality: str | None = None
    system: str | None = None
class PropertyOut(PropertyCreate):
    id: int; status: str; created_at: datetime; model_config = ConfigDict(from_attributes=True)
class AuctionCreate(BaseModel):
    auction_date: date | None = None; auction_stage: str = "2º leilão"; appraisal_value: Decimal = 0; bid_value: Decimal = 0; first_auction_date: datetime | None = None; first_auction_value: Decimal | None = None; second_auction_date: datetime | None = None; second_auction_value: Decimal | None = None; acquisition_value: Decimal | None = None; commission_percent: Decimal | None = None; commission_fixed: Decimal | None = None; auctioneer: str = ""; notice_url: str = ""
class CostCreate(BaseModel):
    category: str; description: str; amount: Decimal = 0; recurring: bool = False
class DebtCreate(BaseModel):
    category: str; creditor: str = ""; amount: Decimal = 0; reference_date: date | None = None; status: str = "PENDENTE"; evidence_id: int | None = None
class ComparableCreate(BaseModel):
    kind: str = "VENDA"; price: Decimal = 0; rent: Decimal | None = None; area_m2: Decimal = 0; source: str = "Cadastro manual"; url: str = ""
class ProcessCreate(BaseModel):
    number: str
    court: str | None = None
    comarca: str | None = None
    nature: str | None = None
    subject: str | None = None
    status: str | None = None
    polo_active: str | None = None
    polo_passive: str | None = None
    distribution_date: date | None = None
    observations: str | None = None
    source: str | None = None
    impact: str | None = None
    evidence_id: int | None = None
class ChecklistUpdate(BaseModel):
    state: Literal["PENDENTE", "EM_ANALISE", "CONFIRMADO", "RISCO_IDENTIFICADO", "ATENCAO", "NAO_IDENTIFICADO", "NAO_APLICAVEL"]
    answer: str = ""
    confidence: Literal["BAIXA", "MEDIA", "ALTA"] = "MEDIA"
    interpretation: str | None = None
    risk: str | None = None

class RegistrationCreate(BaseModel):
    registration_number: str
    registry_office: str | None = None
    comarca: str | None = None
    consultation_date: date | None = None
    holder: str | None = None
    observations: str | None = None
    document_version_id: int | None = None
    evidence_id: int | None = None

class AuctionNoticeCreate(BaseModel):
    identifier: str
    item: str | None = None
    notice_date: date | None = None
    auction_stage: str | None = None
    appraisal_value: Decimal | None = None
    minimum_value: Decimal | None = None
    auction_date: date | None = None
    auctioneer: str | None = None
    observations: str | None = None
    document_version_id: int | None = None
    evidence_id: int | None = None

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


class DocumentExtractionRequest(BaseModel):
    document_type: Literal["MATRICULA", "EDITAL"]


class EvidenceLinkCreate(BaseModel):
    target_type: str
    target_id: int
    relation: str = "SUSTENTA"


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


class PropertySourceCreate(BaseModel):
    source_type: Literal["PAGINA_IMOVEL", "EDITAL", "MATRICULA", "OUTRA"] = "OUTRA"
    url: str | None = None
    description: str | None = None
    origin: str | None = None


class PropertySourceOut(PropertySourceCreate):
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Sub-blocos opcionais do cadastro completo. Sem campos obrigatórios além do
# essencial, para não impedir cadastro com dados ainda desconhecidos.
class AuctionFull(BaseModel):
    auction_date: date | None = None
    auction_stage: str = "2º leilão"
    appraisal_value: Decimal | None = None
    bid_value: Decimal | None = None
    first_auction_date: datetime | None = None
    first_auction_value: Decimal | None = None
    second_auction_date: datetime | None = None
    second_auction_value: Decimal | None = None
    acquisition_value: Decimal | None = None
    commission_percent: Decimal | None = None
    commission_fixed: Decimal | None = None
    auctioneer: str = ""
    notice_url: str = ""


class AuctionNoticeFull(BaseModel):
    identifier: str | None = None
    item: str | None = None
    notice_date: date | None = None
    auction_stage: str | None = None
    appraisal_value: Decimal | None = None
    minimum_value: Decimal | None = None
    auction_date: date | None = None
    auctioneer: str | None = None
    observations: str | None = None


class RegistrationFull(BaseModel):
    registration_number: str | None = None
    registry_office: str | None = None
    comarca: str | None = None
    consultation_date: date | None = None
    holder: str | None = None
    observations: str | None = None


class PropertyFullCreate(BaseModel):
    """Cadastro completo transacional de um imóvel de leilão.

    Reutiliza os modelos existentes (Property, Auction, AuctionNotice,
    PropertyRegistration, PropertySource). Documentos NÃO entram aqui: são
    enviados por upload separado para não bloquear o cadastro.
    """
    imovel: PropertyCreate
    leilao: AuctionFull | None = None
    edital: AuctionNoticeFull | None = None
    matricula: RegistrationFull | None = None
    fontes: list[PropertySourceCreate] = Field(default_factory=list)
