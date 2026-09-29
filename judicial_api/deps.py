"""Composição de dependências da Judicial API (JUR-05).

Monta o grafo de objetos que serve os endpoints REST — provider, registries,
catálogo, store e orchestrator — e o expõe como singletons de processo via
``Depends`` do FastAPI. O wiring é isolado aqui para manter ``app.py`` enxuto e os
testes livres para injetar overrides (``app.dependency_overrides``).

Persistência: usa o ``InMemorySearchStore`` (JUR-03). PostgreSQL é fase futura da
SPEC e não faz parte desta task.
"""
from __future__ import annotations

from functools import lru_cache

from .catalog.loader import JudicialCatalog, default_catalog
from .config import get_settings
from .logging_config import get_logger
from .metrics import Metrics, get_metrics
from .orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
from .orchestration.store import InMemorySearchStore, SearchStore
from .providers.datajud import DataJudProvider
from .registry.base import ProviderRegistry, TribunalRegistry
from .registry.catalog_registry import CatalogTribunalRegistry, SimpleProviderRegistry

log = get_logger("deps")


@lru_cache
def get_catalog() -> JudicialCatalog:
    return default_catalog()


@lru_cache
def get_tribunal_registry() -> TribunalRegistry:
    return CatalogTribunalRegistry(get_catalog())


@lru_cache
def get_datajud_provider() -> DataJudProvider:
    settings = get_settings()
    # Transporte HTTP real (TASK FINAL — Entrega 2): injetado quando há credencial
    # e o transporte real está habilitado. Sem credencial, o transporte permanece
    # None e a consulta real falha de forma controlada (CONFIGURATION_ERROR) — a
    # suíte padrão roda sem rede e sem credencial. Nunca simula sucesso sem chave.
    transport = None
    if settings.datajud_real_transport and settings.datajud_api_key:
        from .providers.http_transport import HttpxTransport

        transport = HttpxTransport()
        log.info("datajud transporte real habilitado")
    return DataJudProvider(
        catalog=get_catalog(),
        api_key=settings.datajud_api_key,
        transport=transport,
        default_timeout_ms=settings.default_source_timeout_ms,
    )


@lru_cache
def get_provider_registry() -> ProviderRegistry:
    return SimpleProviderRegistry([get_datajud_provider()], get_tribunal_registry())


@lru_cache
def get_store() -> SearchStore:
    """Store de persistência padrão.

    PostgreSQL é o padrão de produção (durável, compartilhado entre instâncias). O
    ``InMemorySearchStore`` só é usado quando explicitamente selecionado
    (``JUDICIAL_PERSISTENCE_BACKEND=memory``) — nunca é fallback silencioso.
    """
    settings = get_settings()
    if settings.use_postgres:
        from .persistence.postgres_store import PostgresSearchStore

        return PostgresSearchStore()
    log.warning("persistencia em memoria selecionada explicitamente (nao-duravel)")
    return InMemorySearchStore()


@lru_cache
def get_orchestrator() -> SearchOrchestrator:
    settings = get_settings()
    config = OrchestratorConfig(
        source_timeout_ms=settings.default_source_timeout_ms,
        global_timeout_ms=settings.global_timeout_ms,
    )
    return SearchOrchestrator(
        get_provider_registry(),
        catalog=get_catalog(),
        store=get_store(),
        config=config,
    )


def get_app_metrics() -> Metrics:
    return get_metrics()


def reset_singletons() -> None:
    """Limpa os singletons cacheados (útil para testes que precisam de estado novo)."""
    for fn in (get_catalog, get_tribunal_registry, get_datajud_provider,
               get_provider_registry, get_store, get_orchestrator):
        fn.cache_clear()
