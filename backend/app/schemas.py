from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class PropertyCreate(BaseModel):
    title: str = Field(min_length=2); address: str; city: str; state: str = Field(min_length=2, max_length=2); property_type: str = "Apartamento"; area_m2: Decimal = 0; bedrooms: int = 0
class PropertyOut(PropertyCreate):
    id: int; status: str; created_at: datetime; model_config = ConfigDict(from_attributes=True)
class AuctionCreate(BaseModel):
    auction_date: date | None = None; auction_stage: str = "2º leilão"; appraisal_value: Decimal = 0; bid_value: Decimal = 0; auctioneer: str = ""; notice_url: str = ""
class CostCreate(BaseModel):
    category: str; description: str; amount: Decimal = 0; recurring: bool = False
class DebtCreate(BaseModel):
    category: str; creditor: str = ""; amount: Decimal = 0; reference_date: date | None = None; status: str = "PENDENTE"; evidence_id: int | None = None
class ComparableCreate(BaseModel):
    kind: str = "VENDA"; price: Decimal = 0; rent: Decimal | None = None; area_m2: Decimal = 0; source: str = "Cadastro manual"; url: str = ""
class ProcessCreate(BaseModel):
    number: str; court: str = ""; subject: str = ""; status: str = "Em análise"; source: str = "Cadastro manual"; impact: str = ""
class ChecklistUpdate(BaseModel):
    state: str; answer: str = ""; confidence: str = "MEDIA"; interpretation: str | None = None; risk: str | None = None
class EvidenceCreate(BaseModel):
    category: str = "DOCUMENTAL"; fact: str; interpretation: str | None = None; hypothesis: str | None = None; confidence: str = "MEDIA"; document_version_id: int | None = None; chunk_id: int | None = None; page: int | None = None; section: str | None = None; source_excerpt: str | None = None
