"""JUR-01 — testes do contrato de erro unificado."""
from __future__ import annotations

from judicial_api.enums import ErrorCode
from judicial_api.errors import ErrorResponse, JudicialError


def test_retryable_deriva_do_catalogo():
    # PROVIDER_TIMEOUT é transitório (retryable por padrão).
    err = JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504)
    assert err.retryable is True
    # BAD_REQUEST não é transitório.
    err2 = JudicialError(ErrorCode.BAD_REQUEST, "ruim", http_status=400)
    assert err2.retryable is False


def test_retryable_pode_ser_sobrescrito():
    err = JudicialError(ErrorCode.UNKNOWN_ERROR, "x", retryable=True)
    assert err.retryable is True


def test_to_response_inclui_correlation_id_e_campos():
    err = JudicialError(
        ErrorCode.PROVIDER_TIMEOUT, "tribunal nao respondeu",
        http_status=504, provider="DATAJUD", tribunal="TJSP",
    )
    resp = err.to_response(correlation_id="corr-1")
    assert isinstance(resp, ErrorResponse)
    assert resp.code == ErrorCode.PROVIDER_TIMEOUT
    assert resp.retryable is True
    assert resp.provider == "DATAJUD"
    assert resp.tribunal == "TJSP"
    assert resp.correlation_id == "corr-1"
    assert resp.timestamp.endswith("Z")


def test_error_response_nao_expoe_campos_internos():
    resp = ErrorResponse(code=ErrorCode.UNKNOWN_ERROR, message="falha")
    dumped = resp.model_dump()
    # apenas campos do contrato — sem stack trace, api key, etc.
    assert set(dumped.keys()) == {
        "code", "message", "retryable", "provider", "tribunal", "timestamp", "correlation_id",
    }
