"""Rate limiting HTTP da Judicial API (JUR-05, SPEC §73).

Implementação em memória, thread-safe, baseada em janela deslizante por
consumidor. Sem dependências externas (não usa Redis/slowapi) — adequado ao
escopo atual (processo único). Para múltiplas réplicas, trocar o backend por um
store compartilhado sem alterar o middleware.

O consumidor é identificado pela API key (quando autenticado) ou pelo IP de
origem (fallback). Ao exceder o limite, o middleware responde 429 com o contrato
de erro normalizado (RATE_LIMITED) — não deixa a exceção vazar.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import get_settings
from .correlation import get_correlation_id
from .enums import ErrorCode
from .errors import ErrorResponse


class SlidingWindowLimiter:
    """Limitador de janela deslizante por chave (thread-safe)."""

    def __init__(self, max_requests: int, window_seconds: float, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._max = max(1, max_requests)
        self._window = max(0.001, float(window_seconds))
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int, float]:
        """Registra uma tentativa. Retorna (permitido, restantes, retry_after_s)."""
        now = self._clock()
        boundary = now - self._window
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= boundary:
                bucket.popleft()
            if len(bucket) >= self._max:
                # Tempo até a requisição mais antiga sair da janela.
                retry_after = max(0.0, bucket[0] + self._window - now)
                return False, 0, retry_after
            bucket.append(now)
            return True, self._max - len(bucket), 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def _client_key(request: Request, header_name: str) -> str:
    api_key = request.headers.get(header_name)
    if api_key and api_key.strip():
        # Não usamos a chave inteira como identificador exposto; o hash mantém o
        # agrupamento por consumidor sem materializar o segredo.
        return f"k:{hash(api_key.strip())}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica rate limiting por consumidor. Ignora rotas isentas (ex.: /health)."""

    def __init__(self, app, *, limiter: SlidingWindowLimiter, api_key_header: str,
                 exempt_paths: frozenset[str] = frozenset({"/health"})) -> None:
        super().__init__(app)
        self._limiter = limiter
        self._api_key_header = api_key_header
        self._exempt = exempt_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._exempt:
            return await call_next(request)

        key = _client_key(request, self._api_key_header)
        allowed, remaining, retry_after = self._limiter.allow(key)
        if not allowed:
            settings = get_settings()
            body = ErrorResponse(
                code=ErrorCode.RATE_LIMITED,
                message="Limite de requisições excedido. Tente novamente mais tarde.",
                retryable=True,
                correlation_id=get_correlation_id(),
            )
            headers = {
                "Retry-After": str(int(retry_after) + 1),
                "X-RateLimit-Limit": str(settings.rate_limit_requests),
                "X-RateLimit-Remaining": "0",
            }
            return JSONResponse(status_code=429, content=body.model_dump(mode="json"), headers=headers)

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
