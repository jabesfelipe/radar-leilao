"""Observabilidade HTTP da Judicial API (JUR-05, SPEC §69, §71, §73).

Reúne dois middlewares transversais:

- ``RequestAuditMiddleware``: audita cada requisição HTTP (quem, quando, método,
  rota, status, duração) em log estruturado, sempre com o correlation id. Nunca
  registra segredos nem dados sensíveis completos (SPEC §71). Complementa a
  auditoria de domínio da pesquisa (SearchEvent), que continua por busca.

- ``SecurityHeadersMiddleware``: hardening leve — limita o tamanho do corpo da
  requisição (SPEC §73) e adiciona headers de segurança padrão às respostas.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .correlation import get_correlation_id
from .enums import ErrorCode
from .errors import ErrorResponse
from .logging_config import get_logger

_audit_log = get_logger("audit")


def _principal_id(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    return getattr(principal, "key_id", "anonymous") if principal else "anonymous"


class RequestAuditMiddleware(BaseHTTPMiddleware):
    """Registra uma linha de auditoria por requisição concluída."""

    def __init__(self, app, *, exempt_paths: frozenset[str] = frozenset({"/health", "/metrics"})) -> None:
        super().__init__(app)
        self._exempt = exempt_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._exempt:
            return await call_next(request)

        started = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            _audit_log.info(
                "http_request",
                extra={
                    "fields": {
                        "event": "HTTP_REQUEST",
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                        "principal": _principal_id(request),
                        "client": request.client.host if request.client else None,
                    }
                },
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Limita o corpo da requisição e adiciona headers de segurança (hardening)."""

    def __init__(self, app, *, max_request_bytes: int = 1_048_576) -> None:
        super().__init__(app)
        self._max_bytes = max_request_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        # Limite de payload por Content-Length declarado (proteção contra abuso).
        if self._max_bytes > 0:
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit() and int(content_length) > self._max_bytes:
                body = ErrorResponse(
                    code=ErrorCode.BAD_REQUEST,
                    message="Corpo da requisição excede o tamanho máximo permitido.",
                    retryable=False,
                    correlation_id=get_correlation_id(),
                )
                return JSONResponse(status_code=413, content=body.model_dump(mode="json"))

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response
