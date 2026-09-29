"""Endpoints REST de negócio da Judicial API (JUR-05, SPEC §49-55).

Expõe o contrato unificado sob ``/api/v1/judicial``. Toda a lógica pesada vive nas
camadas inferiores (orchestrator, provider, registries): aqui só fazemos wiring,
autenticação/autorização por escopo, contabilização de métricas e a tradução para
o contrato REST. As rotas são síncronas (``def``) de propósito — o orchestrator é
bloqueante (thread pool interno), então o FastAPI as executa em threadpool e não
trava o event loop.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .deps import (
    get_app_metrics,
    get_orchestrator,
    get_provider_registry,
    get_tribunal_registry,
)
from .enums import ErrorCode
from .errors import JudicialError
from .metrics import Metrics
from .models import (
    CapabilitiesResponse,
    ProviderStatus,
    ProvidersStatusResponse,
    SearchRequest,
    SearchResult,
    SourcesResponse,
    TribunalCapabilities,
    TribunalsResponse,
)
from .orchestration.orchestrator import SearchOrchestrator
from .registry.base import ProviderRegistry, TribunalRegistry
from .registry.catalog_registry import CatalogTribunalRegistry
from .security import SCOPE_READ, SCOPE_SEARCH, Principal, require_scope

router = APIRouter(prefix="/api/v1/judicial", tags=["judicial"])


def _require_criteria(request: SearchRequest) -> None:
    """Valida que a pesquisa traz pelo menos um critério utilizável (SPEC §78).

    Uma pesquisa sem nenhum critério não pode ser disparada — seleciona tudo e não
    filtra nada. Falha cedo com BAD_REQUEST em vez de consultar fontes à toa.
    """
    tem_criterio = any(
        [
            request.name,
            request.cpf,
            request.cnpj,
            request.process_number,
            request.class_code is not None,
            request.subject_code is not None,
            request.court_code is not None,
            request.grau,
        ]
    )
    if not tem_criterio:
        raise JudicialError(
            ErrorCode.BAD_REQUEST,
            "Informe ao menos um critério de pesquisa (nome, CPF, CNPJ, número do processo, classe, assunto, órgão ou grau).",
            http_status=400,
            retryable=False,
        )


# --------------------------------------------------------------------------
# Pesquisa (SPEC §51-54)
# --------------------------------------------------------------------------

@router.post("/search", response_model=SearchResult, status_code=201)
def create_search(
    request: SearchRequest,
    principal: Principal = Depends(require_scope(SCOPE_SEARCH)),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
    metrics: Metrics = Depends(get_app_metrics),
) -> SearchResult:
    """Cria e executa uma pesquisa multi-fonte, devolvendo o resultado agregado."""
    _require_criteria(request)
    result = orchestrator.search(request)
    metrics.record_search(result)
    return result


@router.get("/search/{search_id}", response_model=SearchResult)
def get_search(
    search_id: str,
    principal: Principal = Depends(require_scope(SCOPE_READ)),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> SearchResult:
    """Recupera o resultado de uma pesquisa já executada."""
    result = orchestrator.get(search_id)
    if result is None:
        raise JudicialError(
            ErrorCode.NOT_FOUND,
            "Pesquisa não encontrada.",
            http_status=404,
            retryable=False,
        )
    return result


@router.get("/search/{search_id}/sources", response_model=SourcesResponse)
def get_search_sources(
    search_id: str,
    principal: Principal = Depends(require_scope(SCOPE_READ)),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
) -> SourcesResponse:
    """Lista o resultado individual de cada fonte consultada (SPEC §53)."""
    result = orchestrator.get(search_id)
    if result is None:
        raise JudicialError(
            ErrorCode.NOT_FOUND,
            "Pesquisa não encontrada.",
            http_status=404,
            retryable=False,
        )
    return SourcesResponse(search_id=search_id, sources=result.sources)


@router.post("/search/{search_id}/retry", response_model=SearchResult)
def retry_search(
    search_id: str,
    principal: Principal = Depends(require_scope(SCOPE_SEARCH)),
    orchestrator: SearchOrchestrator = Depends(get_orchestrator),
    metrics: Metrics = Depends(get_app_metrics),
) -> SearchResult:
    """Reprocessa somente as fontes com falha recuperável (SPEC §21, §54)."""
    result = orchestrator.retry_failed(search_id)
    if result is None:
        raise JudicialError(
            ErrorCode.NOT_FOUND,
            "Pesquisa não encontrada.",
            http_status=404,
            retryable=False,
        )
    metrics.record_search(result)
    return result


# --------------------------------------------------------------------------
# Catálogo / metadados (SPEC §49-50, §55)
# --------------------------------------------------------------------------

@router.get("/tribunals", response_model=TribunalsResponse)
def list_tribunals(
    principal: Principal = Depends(require_scope(SCOPE_READ)),
    registry: TribunalRegistry = Depends(get_tribunal_registry),
) -> TribunalsResponse:
    """Lista os tribunais habilitados no catálogo (SPEC §49)."""
    return TribunalsResponse(items=registry.list_tribunals())


@router.get("/capabilities", response_model=CapabilitiesResponse)
def list_capabilities(
    principal: Principal = Depends(require_scope(SCOPE_READ)),
    registry: TribunalRegistry = Depends(get_tribunal_registry),
) -> CapabilitiesResponse:
    """Informa as capacidades de pesquisa por tribunal (SPEC §3, §50).

    Nunca assume suporte: as flags vêm do catálogo (fonte de verdade).
    """
    catalog = registry.catalog if isinstance(registry, CatalogTribunalRegistry) else None
    tribunals: list[TribunalCapabilities] = []
    if catalog is not None:
        tribunals = [e.to_capabilities() for e in catalog.entries() if e.enabled]
        provider = catalog.provider
    else:  # pragma: no cover - caminho de segurança para registries alternativos
        provider = "DATAJUD"
    return CapabilitiesResponse(provider=provider, tribunals=tribunals)


@router.get("/providers/status", response_model=ProvidersStatusResponse)
def providers_status(
    principal: Principal = Depends(require_scope(SCOPE_READ)),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> ProvidersStatusResponse:
    """Reporta a saúde de cada provider registrado (SPEC §55)."""
    statuses: list[ProviderStatus] = [p.health_check() for p in registry.list_providers()]
    return ProvidersStatusResponse(providers=statuses)
