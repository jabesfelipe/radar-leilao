"""DTOs principais da Judicial API (JUR-01).

Modelos de request/response e entidades normalizadas do contrato unificado
(SPEC §7, §17-19, §28-32, §48-55). São contratos estáveis; a lógica de
orquestração, normalização real e persistência vem nas próximas tasks.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import ExecutionMode, JusticeType, SearchStatus, SourceStatus


# --------------------------------------------------------------------------
# Request
# --------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """Critérios de pesquisa (SPEC §7-8). Todos opcionais no formato; a validação
    semântica (ex.: exigir ao menos um critério) é responsabilidade das próximas
    tasks/orchestrator."""

    name: str | None = None
    cpf: str | None = None
    cnpj: str | None = None
    process_number: str | None = None
    # Critérios comprovados na doc oficial do DataJud (glossário): filtros por
    # código da classe processual, do assunto e do órgão julgador, além do grau.
    class_code: int | None = None
    subject_code: int | None = None
    court_code: int | None = None
    grau: str | None = None
    uf: str | None = None
    city: str | None = None
    tribunals: list[str] = Field(default_factory=list)
    justice_types: list[JusticeType] = Field(default_factory=list)
    include_movements: bool = True
    include_parties: bool = True
    include_subjects: bool = True
    page_size: int = 100
    max_pages_per_source: int = 10
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL


# --------------------------------------------------------------------------
# Entidades normalizadas (SPEC §28-32)
# --------------------------------------------------------------------------

class Party(BaseModel):
    name: str
    document: str | None = None
    document_type: str | None = None  # CPF | CNPJ | None
    role: str | None = None           # ex.: DEFENDANT, PLAINTIFF
    party_type: str | None = None     # PERSON | COMPANY
    representation: str | None = None
    source_identifier: str | None = None


class Subject(BaseModel):
    code: str | None = None
    name: str | None = None
    source_identifier: str | None = None


class Movement(BaseModel):
    movement_date: str | None = None
    code: str | None = None
    description: str | None = None
    complement: str | None = None
    source_identifier: str | None = None


class Process(BaseModel):
    process_number: str
    tribunal: str
    justice_type: JusticeType
    jurisdiction: str | None = None
    court: str | None = None
    class_code: str | None = None
    class_name: str | None = None
    subjects: list[Subject] = Field(default_factory=list)
    parties: list[Party] = Field(default_factory=list)
    movements: list[Movement] = Field(default_factory=list)
    priority: list[str] = Field(default_factory=list)
    electronic: bool | None = None
    last_movement_at: str | None = None
    source_identifier: str | None = None


# --------------------------------------------------------------------------
# Resultado por fonte e agregado (SPEC §17-19)
# --------------------------------------------------------------------------

class SourceError(BaseModel):
    code: str
    retryable: bool = False
    message: str | None = None


class SourceResult(BaseModel):
    provider: str
    tribunal: str
    justice_type: JusticeType
    status: SourceStatus
    http_status: int | None = None
    duration_ms: int | None = None
    pages: int = 0
    result_count: int = 0
    attempts: int = 0
    error: SourceError | None = None


class Completeness(BaseModel):
    requested_sources: int = 0
    successful_sources: int = 0
    failed_sources: int = 0
    unsupported_sources: int = 0


class ReanalyzeHint(BaseModel):
    recommended: bool = False
    reason: str | None = None
    sources_affected: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    search_id: str
    status: SearchStatus
    completeness: Completeness = Field(default_factory=Completeness)
    sources: list[SourceResult] = Field(default_factory=list)
    processes: list[Process] = Field(default_factory=list)
    signals: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reanalyze: ReanalyzeHint = Field(default_factory=ReanalyzeHint)


# --------------------------------------------------------------------------
# Metadados de catálogo/provider (SPEC §48-55)
# --------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "UP"
    service: str
    version: str


class TribunalInfo(BaseModel):
    """Identidade de um tribunal no catálogo.

    Um tribunal pode pertencer a mais de um ramo (ex.: o TSE é SUPERIOR e
    ELECTORAL). ``justice_types`` é a lista canônica; ``justice_type`` é mantido
    como o ramo primário para compatibilidade do contrato.
    """

    code: str
    name: str
    justice_type: JusticeType
    justice_types: list[JusticeType] = Field(default_factory=list)
    uf: str | None = None
    enabled: bool = True


class SearchCriteriaSupport(BaseModel):
    """Capacidades de PESQUISA por fonte (SPEC §50). Nunca assumir suporte.

    Cada flag verdadeira corresponde a um critério que o provider sabe traduzir em
    query. ``include_movements`` não é critério de pesquisa (é filtro de conteúdo
    de resposta), por isso não aparece aqui.
    """

    name: bool = False
    cpf: bool = False
    cnpj: bool = False
    process_number: bool = False
    subject: bool = False
    class_: bool = Field(default=False, alias="class")
    court: bool = False
    grau: bool = False

    model_config = {"populate_by_name": True}


class TribunalCapabilities(BaseModel):
    tribunal: str
    supports: SearchCriteriaSupport = Field(default_factory=SearchCriteriaSupport)


class ProviderStatus(BaseModel):
    provider: str
    status: str  # AVAILABLE | UNAVAILABLE | ...
