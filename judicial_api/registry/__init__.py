"""Registries da Judicial API.

- JUR-01: interfaces base ``TribunalRegistry`` / ``ProviderRegistry``.
- JUR-02: implementações concretas baseadas no catálogo.
"""

from .base import ProviderRegistry, TribunalRegistry
from .catalog_registry import CatalogTribunalRegistry, SimpleProviderRegistry

__all__ = [
    "ProviderRegistry",
    "TribunalRegistry",
    "CatalogTribunalRegistry",
    "SimpleProviderRegistry",
]
