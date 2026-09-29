"""Correlation ID da Judicial API (JUR-01).

Cada requisição recebe (ou herda, se o cliente enviar) um correlation id, que é
propagado no contexto e devolvido no header de resposta. Permite rastrear uma
pesquisa de ponta a ponta em logs e no contrato de erro (SPEC §23, §71).
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Contexto por-requisição (thread/async-safe) com o correlation id atual.
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def get_correlation_id() -> str | None:
    """Correlation id da requisição atual, se houver."""
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Garante um correlation id por requisição e o ecoa no header de resposta.

    - Usa o valor enviado pelo cliente no header configurado, se presente e não vazio;
    - caso contrário, gera um UUID novo;
    - expõe o valor via ContextVar (get_correlation_id) e no header de resposta.
    """

    def __init__(self, app, header_name: str) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(self.header_name)
        correlation_id = incoming.strip() if incoming and incoming.strip() else new_correlation_id()
        set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response
