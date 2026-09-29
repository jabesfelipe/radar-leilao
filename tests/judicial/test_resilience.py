"""JUR-03 — testes de resiliência (backoff/jitter + retry)."""
from __future__ import annotations

import pytest

from judicial_api.enums import ErrorCode
from judicial_api.errors import JudicialError
from judicial_api.orchestration.resilience import (
    BackoffPolicy,
    RetryPolicy,
    compute_backoff,
    run_with_retry,
)


def test_backoff_primeira_tentativa_e_zero():
    assert compute_backoff(1, BackoffPolicy()) == 0.0


def test_backoff_exponencial_e_limitado():
    pol = BackoffPolicy(base_ms=500, factor=2.0, max_ms=8000, jitter_ms=0)
    assert compute_backoff(2, pol) == 0.5   # 500ms
    assert compute_backoff(3, pol) == 1.0   # 1000ms
    assert compute_backoff(4, pol) == 2.0   # 2000ms
    # cap em 8000ms
    assert compute_backoff(20, pol) == 8.0


def test_backoff_soma_jitter():
    pol = BackoffPolicy(base_ms=500, factor=2.0, max_ms=8000, jitter_ms=250)
    # jitter=1.0 -> soma 250ms
    assert compute_backoff(2, pol, jitter=1.0) == 0.75


def test_retry_reexecuta_erro_transitorio_e_sucede():
    tentativas = {"n": 0}

    def fn():
        tentativas["n"] += 1
        if tentativas["n"] < 3:
            raise JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504)
        return "ok"

    sleeps = []
    out = run_with_retry(fn, RetryPolicy(max_attempts=3), sleep=sleeps.append)
    assert out == "ok"
    assert tentativas["n"] == 3
    assert len(sleeps) == 2  # dormiu antes das 2 reexecuções


def test_retry_nao_reexecuta_erro_definitivo():
    tentativas = {"n": 0}

    def fn():
        tentativas["n"] += 1
        raise JudicialError(ErrorCode.UNSUPPORTED_SEARCH_CRITERIA, "nao suportado", http_status=422)

    with pytest.raises(JudicialError) as exc:
        run_with_retry(fn, RetryPolicy(max_attempts=5), sleep=lambda _: None)
    assert exc.value.code == ErrorCode.UNSUPPORTED_SEARCH_CRITERIA
    assert tentativas["n"] == 1  # não reexecutou


def test_retry_esgota_tentativas_e_reergue():
    tentativas = {"n": 0}

    def fn():
        tentativas["n"] += 1
        raise JudicialError(ErrorCode.RATE_LIMITED, "429", http_status=502)

    with pytest.raises(JudicialError):
        run_with_retry(fn, RetryPolicy(max_attempts=3), sleep=lambda _: None)
    assert tentativas["n"] == 3
