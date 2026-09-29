"""Interface base do Provider judicial (JUR-01).

Define o contrato conceitual que qualquer fonte (DataJud e futuros providers)
deverá implementar, mantendo o contrato REST externo estável (SPEC §74-75):

    JudicialProvider
      ├── search()
      ├── get_capabilities()
      ├── health_check()
      └── normalize()

JUR-01 entrega apenas a abstração. NENHUMA implementação concreta (DataJud) é
criada aqui — isso é escopo da JUR-02.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Process, ProviderStatus, SearchRequest, SourceResult, TribunalCapabilities


class ProviderCapabilities:
    """Marcador conceitual para o conjunto de capacidades de um provider.

    Nesta fase, as capacidades por tribunal são representadas por
    ``TribunalCapabilities`` (models). Mantido para clareza da interface e
    expansão futura sem quebrar o contrato.
    """


class JudicialProvider(ABC):
    """Contrato mínimo de um provider judicial (SPEC §74).

    Todos os métodos são abstratos: a fundação não fornece comportamento real.
    A implementação concreta (DataJudProvider) e a orquestração multi-fonte serão
    adicionadas nas tasks JUR-02/JUR-03.
    """

    #: Código único do provider (ex.: "DATAJUD"). Definido pela implementação.
    code: str = "BASE"

    @abstractmethod
    def search(self, request: SearchRequest, tribunal: str) -> list[Process]:
        """Executa a consulta em uma fonte/tribunal e devolve processos normalizados."""
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self, tribunal: str) -> TribunalCapabilities:
        """Informa as capacidades de pesquisa suportadas para um tribunal."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> ProviderStatus:
        """Verifica a disponibilidade do provider."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: Any, tribunal: str) -> list[Process]:
        """Converte a resposta bruta específica da fonte no contrato normalizado."""
        raise NotImplementedError
