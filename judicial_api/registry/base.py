"""Interfaces base de Registry (JUR-01).

- TribunalRegistry: cadastro de tribunais/aliases/UF/ramo/capacidades (SPEC §6.2).
- ProviderRegistry: resolução de provider por tribunal/config (SPEC §6.3).

JUR-01 entrega apenas as abstrações. O cadastro efetivo das fontes do escopo
(TJPR, TJSP, TRFs, TRTs, superiores, eleitoral, militar) é escopo da JUR-02 e não
deve ser antecipado aqui.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..enums import JusticeType
from ..models import TribunalInfo
from ..providers.base import JudicialProvider


class TribunalRegistry(ABC):
    """Fonte de verdade dos tribunais habilitados e suas propriedades."""

    @abstractmethod
    def list_tribunals(self) -> list[TribunalInfo]:
        """Lista os tribunais cadastrados/habilitados."""
        raise NotImplementedError

    @abstractmethod
    def get(self, code: str) -> TribunalInfo | None:
        """Retorna um tribunal pelo código (ou alias resolvido), se existir."""
        raise NotImplementedError

    @abstractmethod
    def resolve_alias(self, alias: str) -> str | None:
        """Resolve um alias para o código canônico do tribunal."""
        raise NotImplementedError

    @abstractmethod
    def for_justice_types(self, justice_types: list[JusticeType]) -> list[TribunalInfo]:
        """Filtra os tribunais aplicáveis a um conjunto de ramos da Justiça."""
        raise NotImplementedError


class ProviderRegistry(ABC):
    """Resolve qual provider atende um tribunal e expõe os providers registrados."""

    @abstractmethod
    def get_provider(self, code: str) -> JudicialProvider | None:
        """Retorna o provider pelo código (ex.: "DATAJUD")."""
        raise NotImplementedError

    @abstractmethod
    def provider_for_tribunal(self, tribunal_code: str) -> JudicialProvider | None:
        """Retorna o provider responsável por um tribunal."""
        raise NotImplementedError

    @abstractmethod
    def list_providers(self) -> list[JudicialProvider]:
        """Lista os providers registrados."""
        raise NotImplementedError
