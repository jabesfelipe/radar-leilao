"""Contrato de erro unificado da Judicial API (JUR-01).

Estrutura de erro estável e independente do provider (SPEC §22-23). Nunca expõe
stack trace, API key, senha ou detalhes internos ao consumidor.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .enums import RETRYABLE_ERROR_CODES, ErrorCode


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ErrorResponse(BaseModel):
    """Corpo de erro devolvido ao consumidor (SPEC §23)."""

    code: ErrorCode
    message: str
    retryable: bool = False
    provider: str | None = None
    tribunal: str | None = None
    timestamp: str = Field(default_factory=_utc_now_iso)
    correlation_id: str | None = None


class JudicialError(Exception):
    """Erro de domínio da Judicial API, mapeável ao contrato externo.

    Carrega um ErrorCode normalizado e um status HTTP sugerido. O flag
    ``retryable`` deriva do catálogo (SPEC §24) quando não informado
    explicitamente.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        http_status: int = 500,
        retryable: bool | None = None,
        provider: str | None = None,
        tribunal: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = code in RETRYABLE_ERROR_CODES if retryable is None else retryable
        self.provider = provider
        self.tribunal = tribunal

    def to_response(self, correlation_id: str | None = None) -> ErrorResponse:
        return ErrorResponse(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            provider=self.provider,
            tribunal=self.tribunal,
            correlation_id=correlation_id,
        )
