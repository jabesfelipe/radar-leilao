"""Resiliência: retry com backoff exponencial + jitter (JUR-03).

Retry automático SOMENTE para erros transitórios (SPEC §24): PROVIDER_TIMEOUT,
RATE_LIMITED, PROVIDER_UNAVAILABLE, PROVIDER_SERVER_ERROR. Erros definitivos
(401/403/400, UNSUPPORTED_SEARCH_CRITERIA, CONFIGURATION_ERROR) não são
reexecutados.

O backoff é exponencial com jitter (SPEC §25). Tudo é injetável (``sleep`` e
``jitter``) para testes determinísticos, sem esperas reais.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from ..enums import RETRYABLE_ERROR_CODES
from ..errors import JudicialError

T = TypeVar("T")


@dataclass(frozen=True)
class BackoffPolicy:
    """Parâmetros configuráveis do backoff exponencial com jitter."""

    base_ms: int = 500
    factor: float = 2.0
    max_ms: int = 8000
    jitter_ms: int = 250


@dataclass(frozen=True)
class RetryPolicy:
    """Política de retry. ``max_attempts`` inclui a tentativa inicial."""

    max_attempts: int = 3
    backoff: BackoffPolicy = BackoffPolicy()


def compute_backoff(attempt: int, policy: BackoffPolicy, jitter: float = 0.0) -> float:
    """Retorna o atraso (em segundos) antes da tentativa ``attempt`` (1-based).

    attempt=1 é a primeira execução (sem espera anterior) e retorna 0. Para
    attempt>=2, aplica base * factor^(attempt-2), limitado por max, somando o
    jitter (0..jitter_ms) — determinístico quando ``jitter`` é fixo.
    """
    if attempt <= 1:
        return 0.0
    raw_ms = policy.base_ms * (policy.factor ** (attempt - 2))
    capped_ms = min(raw_ms, policy.max_ms)
    jitter_ms = max(0.0, min(jitter, 1.0)) * policy.jitter_ms
    return (capped_ms + jitter_ms) / 1000.0


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, JudicialError):
        return exc.retryable or exc.code in RETRYABLE_ERROR_CODES
    return False


def run_with_retry(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = lambda: 0.0,
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Executa ``fn`` com retry para erros transitórios.

    - Reexecuta apenas se a exceção for um JudicialError transitório.
    - Aguarda ``compute_backoff`` entre tentativas (via ``sleep`` injetável).
    - ``on_retry(attempt, exc)`` é chamado antes de cada reexecução (auditoria).
    - Reergue a última exceção quando esgota as tentativas.
    """
    attempts = max(1, policy.max_attempts)
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001 - decidimos retry pela natureza do erro
            last_exc = exc
            if not _is_retryable(exc) or attempt == attempts:
                raise
            if on_retry is not None:
                on_retry(attempt, exc)
            delay = compute_backoff(attempt + 1, policy.backoff, jitter())
            if delay > 0:
                sleep(delay)
    # Inalcançável (o loop sempre retorna ou reergue), mas mantém o tipo explícito.
    assert last_exc is not None
    raise last_exc
