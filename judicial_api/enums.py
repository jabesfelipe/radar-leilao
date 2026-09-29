"""Enumerações centrais da Judicial API (JUR-01).

Alinhadas à SPEC: ramos da Justiça (justice_type), status da pesquisa, status por
fonte, modo de execução e códigos de erro normalizados.
"""
from __future__ import annotations

from enum import Enum


class JusticeType(str, Enum):
    """Ramos da Justiça suportados pelo contrato (SPEC §4)."""

    STATE = "STATE"          # Justiça Estadual (TJ*)
    FEDERAL = "FEDERAL"      # Justiça Federal (TRF*)
    LABOR = "LABOR"          # Justiça do Trabalho (TRT*)
    SUPERIOR = "SUPERIOR"    # Tribunais Superiores (STJ, TST, TSE, STM)
    ELECTORAL = "ELECTORAL"  # Justiça Eleitoral (TSE, TREs)
    MILITARY = "MILITARY"    # Justiça Militar (STM, TJM*)


class ExecutionMode(str, Enum):
    """Modo de execução da pesquisa (SPEC §7)."""

    PARALLEL = "PARALLEL"
    SEQUENTIAL = "SEQUENTIAL"


class SearchStatus(str, Enum):
    """Status agregado da pesquisa (SPEC §16). EMPTY != PARTIAL."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceStatus(str, Enum):
    """Status de uma fonte/tribunal individual (SPEC §18-19)."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    UNSUPPORTED = "UNSUPPORTED"
    UNAVAILABLE = "UNAVAILABLE"


class ErrorCode(str, Enum):
    """Catálogo de erros normalizados (SPEC §22).

    O consumidor nunca depende de códigos internos do DataJud.
    """

    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_SERVER_ERROR = "PROVIDER_SERVER_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    PARSE_ERROR = "PARSE_ERROR"
    UNSUPPORTED_SEARCH_CRITERIA = "UNSUPPORTED_SEARCH_CRITERIA"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    RESULT_LIMIT_REACHED = "RESULT_LIMIT_REACHED"


# Erros considerados transitórios (retry automático permitido — SPEC §24).
RETRYABLE_ERROR_CODES: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.PROVIDER_TIMEOUT,
        ErrorCode.RATE_LIMITED,
        ErrorCode.PROVIDER_UNAVAILABLE,
        ErrorCode.PROVIDER_SERVER_ERROR,
    }
)


class SearchEventType(str, Enum):
    """Eventos de auditoria de uma pesquisa (SPEC §68)."""

    SEARCH_CREATED = "SEARCH_CREATED"
    SOURCE_SELECTED = "SOURCE_SELECTED"
    SOURCE_STARTED = "SOURCE_STARTED"
    SOURCE_RETRY = "SOURCE_RETRY"
    SOURCE_SUCCESS = "SOURCE_SUCCESS"
    SOURCE_FAILED = "SOURCE_FAILED"
    NORMALIZATION_COMPLETED = "NORMALIZATION_COMPLETED"
    SIGNAL_ANALYSIS_COMPLETED = "SIGNAL_ANALYSIS_COMPLETED"
    SEARCH_COMPLETED = "SEARCH_COMPLETED"
    REANALYSIS_REQUESTED = "REANALYSIS_REQUESTED"
