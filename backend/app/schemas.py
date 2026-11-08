from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
class ScenarioAssumptionInput(BaseModel):
    """Premissas explícitas de um cenário financeiro (base/otimista/pessimista)."""
    nome: Literal["BASE", "OTIMISTA", "PESSIMISTA"]
    valor_venda: Decimal | None = None
    reforma: Decimal | None = None
    desocupacao: Decimal | None = None
    carregamento: Decimal | None = None
    prazo_meses: int | None = None
    justificativa: str = ""

    @field_validator("valor_venda", "reforma", "desocupacao", "carregamento")
    @classmethod
    def _nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("valores não podem ser negativos")
        return v

    @field_validator("prazo_meses")
    @classmethod
    def _prazo_valido(cls, v):
        if v is not None and v < 0:
            raise ValueError("prazo_meses não pode ser negativo")
        return v


class FinanceAssumptions(BaseModel):
    """Premissas financeiras correntes de um imóvel (Task 3).

    Percentuais em FRAÇÃO (0.05 = 5%). Campos opcionais: ausência é tratada como
    dado desconhecido (nunca zero silencioso) pelo motor financeiro.
    """
    goal_kind: Literal["LUCRO_MINIMO", "MARGEM_MINIMA", "ROI_MINIMO"] | None = None
    goal_value: Decimal | None = None
    corretagem_pct: Decimal | None = None
    tributo_pct: Decimal | None = None
    tax_base: Literal["GANHO", "VENDA"] = "GANHO"
    valor_venda_estimado: Decimal | None = None
    prazo_meses: int | None = None
    carregamento_mensal: Decimal | None = None
    cenarios: list[ScenarioAssumptionInput] = Field(default_factory=list)

    @field_validator("corretagem_pct", "tributo_pct")
    @classmethod
    def _percentual_valido(cls, v):
        if v is None:
            return v
        if v < 0 or v > 1:
            raise ValueError("percentual deve estar entre 0 e 1 (fração; 0.05 = 5%)")
        return v

    @field_validator("goal_value", "valor_venda_estimado", "carregamento_mensal")
    @classmethod
    def _nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("valor não pode ser negativo")
        return v

    @field_validator("prazo_meses")
    @classmethod
    def _prazo_valido(cls, v):
        if v is not None and v < 0:
            raise ValueError("prazo_meses não pode ser negativo")
        return v

    @model_validator(mode="after")
    def _meta_consistente(self):
        # Meta exige tipo + valor juntos; margem/ROI em fração (0..1).
        if (self.goal_kind is None) != (self.goal_value is None):
            raise ValueError("goal_kind e goal_value devem ser informados juntos")
        if self.goal_kind in ("MARGEM_MINIMA", "ROI_MINIMO") and self.goal_value is not None:
            if self.goal_value < 0 or self.goal_value > 1:
                raise ValueError("meta de margem/ROI deve ser fração entre 0 e 1")
        return self


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


class PropertySourceUpdate(BaseModel):
    """Edição cadastral de uma fonte do imóvel (TASK 75.2.1). Campos opcionais."""
    source_type: Literal["PAGINA_IMOVEL", "EDITAL", "MATRICULA", "OUTRA"] | None = None
    url: str | None = None
    description: str | None = None
    origin: str | None = None


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


# --- Leiloeiros (TASK 75) ---
class AuctioneerCreate(BaseModel):
    name: str = Field(min_length=2)
    document: str | None = None
    company: str | None = None
    registration: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    observations: str | None = None
    status: str = "ATIVO"


class AuctioneerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    document: str | None = None
    company: str | None = None
    registration: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    observations: str | None = None
    status: str | None = None


class PortalAccessCreate(BaseModel):
    portal: str = Field(min_length=1)
    url: str | None = None
    username: str | None = None
    # Credencial sensível: aceita na escrita, nunca retornada em listagem.
    secret: str | None = None
    access_type: str | None = None
    two_factor_enabled: bool = False
    observations: str | None = None
    status: str = "ATIVO"


class PortalAccessUpdate(BaseModel):
    portal: str | None = None
    url: str | None = None
    username: str | None = None
    # Troca opcional da credencial (sempre cifrada no backend). Nunca retornada.
    secret: str | None = None
    access_type: str | None = None
    two_factor_enabled: bool | None = None
    observations: str | None = None
    status: str | None = None
    last_validated_at: datetime | None = None


class AuctioneerDocumentCreate(BaseModel):
    doc_type: str = "OUTROS"
    name: str = Field(min_length=1)
    file_path: str | None = None
    version: int = 1
    observations: str | None = None


class AuctioneerDocumentUpdate(BaseModel):
    """Edição dos METADADOS do documento do leiloeiro (TASK 75.2.1).
    NÃO altera conteúdo/versionamento: file_path e version são imutáveis aqui."""
    doc_type: str | None = None
    name: str | None = Field(default=None, min_length=1)
    observations: str | None = None


class AuctionAuctioneerLink(BaseModel):
    auctioneer_id: int


# ============================================================================
# TASK 75.2 — Schemas de EDIÇÃO (PATCH) de dados cadastrais/factuais.
# Todos os campos são opcionais (exclude_unset no handler): só altera o que vier.
# Dado cadastral é editável e gera EntityHistory (before/after) + DomainEvent.
# ============================================================================
class CostUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    recurring: bool | None = None

    @field_validator("amount")
    @classmethod
    def _nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("amount não pode ser negativo")
        return v


class DebtUpdate(BaseModel):
    category: str | None = None
    creditor: str | None = None
    amount: Decimal | None = None
    reference_date: date | None = None
    status: str | None = None
    evidence_id: int | None = None

    @field_validator("amount")
    @classmethod
    def _nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("amount não pode ser negativo")
        return v


class ComparableUpdate(BaseModel):
    kind: str | None = None
    price: Decimal | None = None
    rent: Decimal | None = None
    area_m2: Decimal | None = None
    source: str | None = None
    url: str | None = None


class ProcessMovementCreate(BaseModel):
    """Nova movimentação processual (append-only; nunca editada destrutivamente)."""
    movement_date: date | None = None
    description: str = Field(min_length=1)
    source: str = "Cadastro manual"


class ProcessUpdate(BaseModel):
    number: str | None = None
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


class RegistrationUpdate(BaseModel):
    registration_number: str | None = None
    registry_office: str | None = None
    comarca: str | None = None
    consultation_date: date | None = None
    holder: str | None = None
    observations: str | None = None
    document_version_id: int | None = None


class AuctionNoticeUpdate(BaseModel):
    identifier: str | None = None
    item: str | None = None
    notice_date: date | None = None
    auction_stage: str | None = None
    appraisal_value: Decimal | None = None
    minimum_value: Decimal | None = None
    auction_date: date | None = None
    auctioneer: str | None = None
    observations: str | None = None


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2)
    address: str | None = None
    city: str | None = Field(default=None, min_length=1)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    property_type: str | None = None
    neighborhood: str | None = None
    area_m2: Decimal | None = None
    private_area_m2: Decimal | None = None
    bedrooms: int | None = None
    parking_spots: int | None = None
    description: str | None = None
    origin: str | None = None
    origin_property_code: str | None = None
    inscription: str | None = None
    modality: str | None = None
    system: str | None = None
    status: str | None = None


class AuctionUpdate(BaseModel):
    auction_date: date | None = None
    auction_stage: str | None = None
    appraisal_value: Decimal | None = None
    bid_value: Decimal | None = None
    first_auction_date: datetime | None = None
    first_auction_value: Decimal | None = None
    second_auction_date: datetime | None = None
    second_auction_value: Decimal | None = None
    acquisition_value: Decimal | None = None
    commission_percent: Decimal | None = None
    commission_fixed: Decimal | None = None
    auctioneer: str | None = None
    notice_url: str | None = None


# ============================================================================
# PÓS-ARREMATAÇÃO (novo módulo). Create/Update/Out seguindo o padrão do projeto:
# Update com todos os campos opcionais (exclude_unset no handler); Out com
# ConfigDict(from_attributes=True). Valores monetários validam não-negativo.
# ============================================================================


def _non_negative(v):
    if v is not None and v < 0:
        raise ValueError("valor não pode ser negativo")
    return v


class PostAuctionActivate(BaseModel):
    """Ativação do fluxo pós-arrematação (sob demanda). Campos opcionais: o motor
    congela o orçamento inicial a partir do financeiro da análise se não informado."""
    eviction_mode: Literal["PROPRIA", "TERCEIRIZADA"] | None = None
    initial_budget: Decimal | None = None
    expected_sale_value: Decimal | None = None
    observations: str | None = None
    seed_default_stages: bool = True

    @field_validator("initial_budget", "expected_sale_value")
    @classmethod
    def _nn(cls, v):
        return _non_negative(v)


class PostAuctionUpdate(BaseModel):
    status: Literal["NAO_INICIADO", "EM_ANDAMENTO", "CONCLUIDO", "CANCELADO"] | None = None
    current_stage: str | None = None
    eviction_mode: Literal["PROPRIA", "TERCEIRIZADA"] | None = None
    initial_budget: Decimal | None = None
    expected_sale_value: Decimal | None = None
    observations: str | None = None


class StageCreate(BaseModel):
    stage_key: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1)
    sort_order: int = 0
    status: Literal["PENDENTE", "EM_ANDAMENTO", "CONCLUIDA", "NAO_APLICAVEL", "BLOQUEADA"] = "PENDENTE"
    responsible: str | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    observations: str | None = None
    legal_process_id: int | None = None


class StageUpdate(BaseModel):
    title: str | None = None
    sort_order: int | None = None
    status: Literal["PENDENTE", "EM_ANDAMENTO", "CONCLUIDA", "NAO_APLICAVEL", "BLOQUEADA"] | None = None
    responsible: str | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    observations: str | None = None
    legal_process_id: int | None = None


class PostCostCreate(BaseModel):
    category: str = Field(min_length=1)
    description: str | None = None
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    status: Literal["PREVISTO", "PENDENTE", "PAGO", "CANCELADO", "CONTESTADO"] = "PREVISTO"
    competence_date: date | None = None
    payment_date: date | None = None
    supplier: str | None = None
    payment_method: str | None = None
    origin: str | None = None
    document_version_id: int | None = None
    stage_id: int | None = None
    observations: str | None = None

    @field_validator("planned_amount", "actual_amount")
    @classmethod
    def _nn(cls, v):
        return _non_negative(v)


class PostCostUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    planned_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    status: Literal["PREVISTO", "PENDENTE", "PAGO", "CANCELADO", "CONTESTADO"] | None = None
    competence_date: date | None = None
    payment_date: date | None = None
    supplier: str | None = None
    payment_method: str | None = None
    origin: str | None = None
    document_version_id: int | None = None
    stage_id: int | None = None
    observations: str | None = None

    @field_validator("planned_amount", "actual_amount")
    @classmethod
    def _nn(cls, v):
        return _non_negative(v)


class OccupantContactCreate(BaseModel):
    name: str = Field(min_length=1)
    phone: str | None = None
    email: str | None = None
    contact_type: str | None = None
    relationship_label: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    observations: str | None = None


class OccupantContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    email: str | None = None
    contact_type: str | None = None
    relationship_label: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    observations: str | None = None


class ContactAttemptCreate(BaseModel):
    attempt_date: date | None = None
    channel: str | None = None
    result: str | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    observations: str | None = None


class ConsultancyCreate(BaseModel):
    company_name: str = Field(min_length=1)
    cnpj: str | None = None
    responsible: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    services: str | None = None
    status: Literal["EM_AVALIACAO", "CONTRATADA", "DESCARTADA", "ENCERRADA"] = "EM_AVALIACAO"
    observations: str | None = None


class ConsultancyUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1)
    cnpj: str | None = None
    responsible: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    services: str | None = None
    status: Literal["EM_AVALIACAO", "CONTRATADA", "DESCARTADA", "ENCERRADA"] | None = None
    selected: bool | None = None
    observations: str | None = None


class ProposalCreate(BaseModel):
    title: str = "Proposta"
    fixed_fee: Decimal | None = None
    variable_fee: str | None = None
    additional_costs: Decimal | None = None
    payment_schedule: str | None = None
    included_scope: str | None = None
    excluded_scope: str | None = None
    deadline_days: int | None = None
    document_version_id: int | None = None
    observations: str | None = None

    @field_validator("fixed_fee", "additional_costs")
    @classmethod
    def _nn(cls, v):
        return _non_negative(v)


class NotificationDraftCreate(BaseModel):
    template_key: str | None = None
    title: str = Field(min_length=1)
    recipient: str | None = None
    notifier: str | None = None
    body: str = ""


class NotificationDraftUpdate(BaseModel):
    """Edita metadados da minuta + registro de envio/recebimento (com evidência).
    O TEXTO (body) é versionado por endpoint próprio, nunca sobrescrito em silêncio."""
    title: str | None = None
    recipient: str | None = None
    notifier: str | None = None
    status: Literal["RASCUNHO", "REVISADO", "EMITIDO", "ENVIADO", "RECEBIDO", "DEVOLVIDO", "SEM_CONFIRMACAO"] | None = None
    delivery_channel: str | None = None
    sent_at: datetime | None = None
    receipt_status: str | None = None
    receipt_reference: str | None = None
    observations: str | None = None


class NotificationVersionCreate(BaseModel):
    """Nova versão do texto da minuta (append-only). Opcionalmente muda o status."""
    body: str = ""
    status: Literal["RASCUNHO", "REVISADO", "EMITIDO", "ENVIADO", "RECEBIDO", "DEVOLVIDO", "SEM_CONFIRMACAO"] | None = None


# ============================================================================
# DUE DILIGENCE INTEGRADA — schemas (Create/Update/Out). Padrão do projeto:
# Update com campos opcionais (exclude_unset); Out com from_attributes.
# ============================================================================


class LocationUpdate(BaseModel):
    """Atualiza a localização do imóvel: coordenadas, confirmação, observações e
    checklist de localização. Coordenadas informadas manualmente são aceitas; a
    geocodificação automática é acionada por endpoint próprio (/geocodificar)."""
    normalized_address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    coordinates_confirmed: bool | None = None
    observations: str | None = None
    inspected_at: datetime | None = None
    # Checklist de localização: {criterio: BOM|REGULAR|RUIM|NAO_VERIFICADO}.
    location_checklist: dict[str, Literal["BOM", "REGULAR", "RUIM", "NAO_VERIFICADO"]] | None = None

    @field_validator("latitude")
    @classmethod
    def _lat_range(cls, v):
        if v is not None and not (Decimal("-90") <= v <= Decimal("90")):
            raise ValueError("latitude fora do intervalo [-90, 90]")
        return v

    @field_validator("longitude")
    @classmethod
    def _lng_range(cls, v):
        if v is not None and not (Decimal("-180") <= v <= Decimal("180")):
            raise ValueError("longitude fora do intervalo [-180, 180]")
        return v


class GeocodeRequest(BaseModel):
    """Geocodificação opcional: usa o endereço do imóvel se não informado."""
    address: str | None = None


class PrefeituraDebtCreate(BaseModel):
    """Registro MANUAL de débito municipal (IPTU/taxas) rastreável. Reutiliza o
    aggregate Debt (não cria custo duplicado). Preserva data-base e situação."""
    category: str = "IPTU"
    creditor: str = "Prefeitura"
    amount: Decimal = Field(ge=0)
    reference_date: date | None = None                 # data-base / exercício
    status: Literal["INFORMADO", "ESTIMADO", "CONFIRMADO", "CONTESTADO", "PAGO", "CANCELADO", "PENDENTE"] = "INFORMADO"
    source: str | None = None                          # fonte da consulta
    observations: str | None = None


class DueDiligenceFrontReview(BaseModel):
    """Marca uma frente como revisada (ou reabre) + anotação do responsável."""
    reviewed: bool = True
    reviewed_by: str | None = None
    summary: str | None = None


# ============================================================================
# CENTRAL DE DÉBITOS/DESPESAS + PARÂMETROS ADMINISTRÁVEIS (Etapa A)
# ============================================================================

# --- Municípios ---
class MunicipalityCreate(BaseModel):
    name: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    ibge_code: str | None = None
    coverage_active: bool = False
    status: str = "ATIVO"
    observations: str | None = None


class MunicipalityUpdate(BaseModel):
    name: str | None = None
    state: str | None = Field(default=None, max_length=2)
    ibge_code: str | None = None
    coverage_active: bool | None = None
    status: str | None = None
    observations: str | None = None


class MunicipalityOut(BaseModel):
    id: int; name: str; state: str; ibge_code: str | None; coverage_active: bool
    status: str; observations: str | None
    model_config = ConfigDict(from_attributes=True)


# --- Tipos de débito (catálogo) ---
class DebtTypeCreate(BaseModel):
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    group: str = "OUTRO"
    default_nature: str = "DIVIDA_EXISTENTE"
    canonical_cost_key: str | None = None
    impacts_finance: bool = True
    active: bool = True
    description: str | None = None


class DebtTypeUpdate(BaseModel):
    label: str | None = None
    group: str | None = None
    default_nature: str | None = None
    canonical_cost_key: str | None = None
    impacts_finance: bool | None = None
    active: bool | None = None
    description: str | None = None


class DebtTypeOut(BaseModel):
    id: int; code: str; label: str; group: str; default_nature: str
    canonical_cost_key: str | None; impacts_finance: bool; active: bool; description: str | None
    model_config = ConfigDict(from_attributes=True)


# --- Fontes ---
class DebtSourceCreate(BaseModel):
    municipality_id: int
    debt_category: str | None = None
    name: str = Field(min_length=1)
    authority: str | None = None
    official_url: str | None = None
    source_type: str = "CONSULTA_MANUAL"
    method: str | None = None
    situation: str = "NAO_INVESTIGADA"
    access_requirements: str | None = None
    limitations: str | None = None
    observations: str | None = None
    active: bool = True


class DebtSourceUpdate(BaseModel):
    debt_category: str | None = None
    name: str | None = None
    authority: str | None = None
    official_url: str | None = None
    source_type: str | None = None
    method: str | None = None
    situation: str | None = None
    access_requirements: str | None = None
    limitations: str | None = None
    observations: str | None = None
    active: bool | None = None


class DebtSourceOut(BaseModel):
    id: int; municipality_id: int; debt_category: str | None; name: str; authority: str | None
    official_url: str | None; source_type: str; method: str | None; situation: str
    access_requirements: str | None; limitations: str | None; observations: str | None
    last_validated_at: datetime | None; active: bool
    model_config = ConfigDict(from_attributes=True)


# --- Débito normalizado (PropertyDebt) ---
class PropertyDebtCreate(BaseModel):
    """Registro manual normalizado de débito/despesa. Separa valor_original de
    valor_atualizado; marca natureza/status/confiabilidade. ESTIMADO nunca é tratado
    como CONFIRMADO (validado no serviço)."""
    debt_type_code: str = Field(min_length=1)
    opportunity_id: int | None = None
    municipality_id: int | None = None
    subcategory: str | None = None
    nature: str | None = None
    creditor: str | None = None
    external_id: str | None = None
    competence: str | None = None
    fiscal_year: int | None = None
    due_date: date | None = None
    original_amount: Decimal | None = None
    interest: Decimal | None = None
    penalty: Decimal | None = None
    correction: Decimal | None = None
    updated_amount: Decimal | None = None
    reference_date: date | None = None
    status: str = "INFORMADO"
    reliability: str = "INFORMADO"
    origin: str | None = None
    source_id: int | None = None
    acquisition_method: str | None = None
    evidence_id: int | None = None
    observations: str | None = None

    @field_validator("original_amount", "interest", "penalty", "correction", "updated_amount")
    @classmethod
    def _nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("valores não podem ser negativos")
        return v


class PropertyDebtUpdate(BaseModel):
    subcategory: str | None = None
    nature: str | None = None
    creditor: str | None = None
    external_id: str | None = None
    competence: str | None = None
    fiscal_year: int | None = None
    due_date: date | None = None
    original_amount: Decimal | None = None
    interest: Decimal | None = None
    penalty: Decimal | None = None
    correction: Decimal | None = None
    updated_amount: Decimal | None = None
    reference_date: date | None = None
    status: str | None = None
    reliability: str | None = None
    origin: str | None = None
    source_id: int | None = None
    acquisition_method: str | None = None
    evidence_id: int | None = None
    observations: str | None = None


class PropertyDebtOut(BaseModel):
    id: int; property_id: int; opportunity_id: int | None; municipality_id: int | None
    debt_type_code: str; subcategory: str | None; nature: str; creditor: str | None
    external_id: str | None; competence: str | None; fiscal_year: int | None; due_date: date | None
    original_amount: Decimal | None; interest: Decimal | None; penalty: Decimal | None
    correction: Decimal | None; updated_amount: Decimal | None; reference_date: date | None
    status: str; reliability: str; origin: str | None; source_id: int | None
    acquisition_method: str | None; evidence_id: int | None; queried_at: datetime | None
    observations: str | None; created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Parâmetros ---
class ParameterCreate(BaseModel):
    key: str = Field(min_length=1)
    name: str | None = None
    description: str | None = None
    category: str = "geral"
    data_type: Literal["STRING", "INTEGER", "DECIMAL", "BOOLEAN", "JSON"] = "STRING"
    scope: Literal["GLOBAL", "MUNICIPIO", "CATEGORIA", "MUNICIPIO_CATEGORIA"] = "GLOBAL"
    municipality_id: int | None = None
    debt_category: str | None = None
    value: str | None = None
    default_value: str | None = None
    unit: str | None = None
    allowed_values: list | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    status: Literal["ATIVO", "INATIVO"] = "ATIVO"
    justification: str | None = None


class ParameterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    data_type: Literal["STRING", "INTEGER", "DECIMAL", "BOOLEAN", "JSON"] | None = None
    unit: str | None = None
    allowed_values: list | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    value: str | None = None
    default_value: str | None = None
    status: Literal["ATIVO", "INATIVO"] | None = None
    justification: str | None = None


class ParameterOut(BaseModel):
    id: int; key: str; name: str; description: str | None; category: str; data_type: str
    scope: str; municipality_id: int | None; debt_category: str | None; value: str | None
    default_value: str | None; unit: str | None; allowed_values: list | None
    min_value: Decimal | None; max_value: Decimal | None; valid_from: datetime | None
    valid_until: datetime | None; status: str; version: int; updated_by: str
    created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Cobertura municipal (Etapa B) ---
CoverageLevel = Literal[
    "NAO_INVESTIGADA", "MANUAL", "PARCIAL", "AUTOMATIZAVEL", "INTEGRACAO_DISPONIVEL", "INDISPONIVEL",
]
SourceSituation = Literal[
    "NAO_INVESTIGADA", "EM_INVESTIGACAO", "DISPONIVEL", "INDISPONIVEL", "DEPENDE_AUTENTICACAO", "BLOQUEADA",
]
ConsultationMethod = Literal[
    "MANUAL", "PORTAL_PUBLICO", "SERVICO_OFICIAL", "API_OFICIAL", "DOCUMENTO", "INDEFINIDO",
]


class CoverageCreate(BaseModel):
    municipality_id: int
    debt_type_code: str = Field(min_length=1)
    level: CoverageLevel = "NAO_INVESTIGADA"
    situation: SourceSituation = "NAO_INVESTIGADA"
    method: ConsultationMethod = "INDEFINIDO"
    active: bool = True
    source_id: int | None = None
    identifier_required: str | None = None
    limitations: str | None = None
    observations: str | None = None


class CoverageUpdate(BaseModel):
    level: CoverageLevel | None = None
    situation: SourceSituation | None = None
    method: ConsultationMethod | None = None
    active: bool | None = None
    source_id: int | None = None
    identifier_required: str | None = None
    limitations: str | None = None
    observations: str | None = None
    mark_validated: bool | None = None  # registra last_validated_at = agora


class CoverageOut(BaseModel):
    id: int; municipality_id: int; debt_type_code: str; level: str; situation: str
    method: str; active: bool; source_id: int | None; identifier_required: str | None
    limitations: str | None; observations: str | None; last_validated_at: datetime | None
    created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Consulta de débito (Etapa E) ---
class DebtQueryItemIn(BaseModel):
    """Lançamento informado no fluxo de consulta ASSISTIDA (valores lidos da fonte
    oficial pelo operador). ESTIMADO nunca é tratado como OFICIAL (validado no serviço)."""
    debt_type_code: str | None = None
    original_amount: Decimal | None = None
    updated_amount: Decimal | None = None
    reference_date: date | None = None
    competence: str | None = None
    status: str = "INFORMADO"
    reliability: str = "INFORMADO"
    origin: str | None = None
    external_id: str | None = None
    observations: str | None = None


class DebtQueryRequest(BaseModel):
    debt_type_code: str = Field(min_length=1)
    municipality_id: int | None = None
    source_id: int | None = None
    identifier: str | None = None
    max_attempts: int = 1
    sem_ocorrencia: bool = False
    mensagem: str | None = None
    itens: list[DebtQueryItemIn] | None = None


# --- Estimativa condominial (Etapa C) ---
class CondominiumEstimateRequest(BaseModel):
    """Entrada da estimativa. Qualquer parâmetro ausente é resolvido no catálogo
    central. Os campos de idade são CONTEXTO (nunca prova de dívida) e são separados
    rigorosamente; o período de inadimplência é explícito (nunca derivado de idade)."""
    monthly_reference: Decimal | None = None
    months_delinquent: int | None = Field(default=None, ge=0, le=120)
    safety_margin_pct: Decimal | None = Field(default=None, ge=0, le=2)
    municipality_id: int | None = None
    property_age_years: int | None = Field(default=None, ge=0, le=200)
    condominium_age_years: int | None = Field(default=None, ge=0, le=200)
    financing_age_years: int | None = Field(default=None, ge=0, le=200)
    age_known: bool = True
    justification: str | None = None
    evidence_id: int | None = None
    persist: bool = True


# --- Autenticação / usuários (Onda 11) ---
class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: int; email: str; name: str; role: str; active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MeOut(BaseModel):
    user: UserOut
    permissions: list[str]


class UserCreate(BaseModel):
    email: str = Field(min_length=3)
    name: str = ""
    password: str = Field(min_length=8)
    role: Literal["ADMIN", "ANALISTA", "OPERADOR", "CONSULTA"] = "CONSULTA"
    active: bool = True


class UserUpdate(BaseModel):
    name: str | None = None
    role: Literal["ADMIN", "ANALISTA", "OPERADOR", "CONSULTA"] | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


# --- Modalidades / Oportunidade / Workflow (Onda 2) ---
ModalityCode = Literal[
    "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", "EXTRAJUDICIAL_OUTRA_GARANTIA",
    "JUDICIAL", "VENDA_DIRETA", "INDEFINIDO",
]


class OpportunityCreate(BaseModel):
    property_id: int
    codigo: str | None = None
    modality: ModalityCode = "INDEFINIDO"
    origin: str | None = None
    portal: str | None = None
    external_id: str | None = None


class OpportunityOut(BaseModel):
    id: int; property_id: int; codigo: str | None; modality: str; status: str
    origin: str | None; portal: str | None; external_id: str | None
    is_legacy: bool; opened_at: datetime | None; closed_at: datetime | None
    created_at: datetime; updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ModalityClassifyRequest(BaseModel):
    """Classificação determinística a partir de sinais objetivos. Só confirma com
    evidência (evidence_id); sem evidência permanece INDEFINIDO."""
    signals_text: str | None = None
    origin: str | None = None
    evidence_id: int | None = None
    confirm: bool = True  # quando houver evidência, aplica a modalidade proposta


class ModalityCorrectRequest(BaseModel):
    """Correção manual da modalidade por usuário autorizado (auditada)."""
    modality: ModalityCode
    justification: str = Field(min_length=3)
    evidence_id: int | None = None


class TransitionRequest(BaseModel):
    target_phase: str = Field(min_length=2)
    transition_type: str = "AVANCO"
    justification: str | None = None
    decision: Literal["APROVADA", "REPROVADA", "ADIADA"] | None = None


class PhaseStateRequest(BaseModel):
    """Marca o estado de uma fase (ex.: concluir o gate de saída para habilitar o
    AVANÇO). ``phase`` omitido = fase corrente. Não contorna hard stops."""
    state: str = Field(min_length=2)
    phase: str | None = None
    justification: str | None = None
