"""Registries concretos baseados no catálogo (JUR-02).

- ``CatalogTribunalRegistry`` implementa ``TribunalRegistry`` sobre o catálogo.
- ``SimpleProviderRegistry`` implementa ``ProviderRegistry`` mapeando cada
  tribunal ao seu provider (nesta fase, sempre o DataJud).

São genéricos e dirigidos por dados: nenhum código específico por tribunal.
"""
from __future__ import annotations

from ..catalog.loader import JudicialCatalog, default_catalog
from ..enums import JusticeType
from ..models import TribunalInfo
from ..providers.base import JudicialProvider
from .base import ProviderRegistry, TribunalRegistry


class CatalogTribunalRegistry(TribunalRegistry):
    """TribunalRegistry sustentado pelo catálogo de dados."""

    def __init__(self, catalog: JudicialCatalog | None = None) -> None:
        self._catalog = catalog or default_catalog()

    @property
    def catalog(self) -> JudicialCatalog:
        return self._catalog

    def list_tribunals(self) -> list[TribunalInfo]:
        return [e.to_info() for e in self._catalog.entries() if e.enabled]

    def get(self, code: str) -> TribunalInfo | None:
        canonical = self._catalog.resolve_alias(code) or code
        entry = self._catalog.get(canonical)
        return entry.to_info() if entry else None

    def resolve_alias(self, alias: str) -> str | None:
        return self._catalog.resolve_alias(alias)

    def for_justice_types(self, justice_types: list[JusticeType]) -> list[TribunalInfo]:
        return [e.to_info() for e in self._catalog.for_justice_types(justice_types) if e.enabled]


class SimpleProviderRegistry(ProviderRegistry):
    """Mapeia tribunais a providers. Nesta fase, todos usam o mesmo provider
    (DataJud). A resolução por tribunal usa o catálogo apenas para validar que o
    código existe — mantendo o contrato preparado para múltiplos providers."""

    def __init__(self, providers: list[JudicialProvider], tribunal_registry: TribunalRegistry) -> None:
        self._providers = {p.code: p for p in providers}
        self._tribunals = tribunal_registry
        # Nesta fase há um único provider padrão (o primeiro registrado).
        self._default_provider = providers[0] if providers else None

    def get_provider(self, code: str) -> JudicialProvider | None:
        return self._providers.get(code)

    def provider_for_tribunal(self, tribunal_code: str) -> JudicialProvider | None:
        canonical = self._tribunals.resolve_alias(tribunal_code) or tribunal_code
        if self._tribunals.get(canonical) is None:
            return None
        return self._default_provider

    def list_providers(self) -> list[JudicialProvider]:
        return list(self._providers.values())
