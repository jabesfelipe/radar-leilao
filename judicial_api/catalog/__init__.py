"""Catálogo de fontes judiciais (JUR-02).

O catálogo é uma FONTE DE VERDADE em dados (``tribunals.json``), não código por
tribunal. O loader converte o arquivo em objetos de domínio, aplicando as
capacidades padrão do provider e permitindo override por tribunal.
"""

from .loader import (
    CatalogEntry,
    JudicialCatalog,
    build_search_url,
    load_catalog,
)

__all__ = ["CatalogEntry", "JudicialCatalog", "build_search_url", "load_catalog"]
