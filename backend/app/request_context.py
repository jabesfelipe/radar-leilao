"""Identificador de correlação por requisição + helpers de erro público.

Cada requisição HTTP recebe um ``correlation_id`` (aceita ``X-Request-ID`` válido do
proxy/cliente ou gera um novo), propagado por ``contextvars`` para os logs e devolvido
no cabeçalho ``X-Request-ID`` e nas respostas de erro. Assim o usuário informa um código
curto e o operador encontra o detalhe técnico (sanitizado) nos logs, sem que o frontend
receba mensagens internas de bibliotecas, stack traces ou segredos.
"""
from __future__ import annotations

import contextvars
import re
import uuid
from typing import NoReturn

from fastapi import HTTPException

from .logging_config import get_logger
from .redaction import redact

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("radar_correlation_id", default="-")
_VALID_ID = re.compile(r"^[A-Za-z0-9._\-]{8,64}$")
HEADER_NAME = "X-Request-ID"

log = get_logger("erro")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str | None = None) -> str:
    cid = value if (value and _VALID_ID.match(value)) else uuid.uuid4().hex[:16]
    _correlation_id.set(cid)
    return cid


class CorrelationIdMiddleware:
    """Middleware ASGI puro (não bufferiza a resposta, compatível com FileResponse)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        cid = set_correlation_id(incoming)

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", cid.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_id)


def public_error(status_code: int, public_message: str, exc: BaseException | None = None, *, context: str = "") -> NoReturn:
    """Registra o detalhe técnico (sanitizado) nos logs e levanta HTTPException com uma
    mensagem amigável + código de referência. Nunca inclui ``str(exc)`` na resposta."""
    cid = get_correlation_id()
    if exc is not None:
        log.error("erro publico ref=%s status=%s contexto=%s tipo=%s detalhe=%s", cid, status_code, context or "-", type(exc).__name__, redact(str(exc), max_len=500))
    raise HTTPException(status_code, f"{public_message} (ref: {cid})") from exc
