"""JUR-01 — testes de enums e DTOs principais."""
from __future__ import annotations

from judicial_api.enums import (
    RETRYABLE_ERROR_CODES,
    ErrorCode,
    ExecutionMode,
    JusticeType,
    SearchStatus,
    SourceStatus,
)
from judicial_api.models import SearchCriteriaSupport, SearchRequest, SearchResult


def test_justice_types_cobrem_os_ramos_da_spec():
    valores = {j.value for j in JusticeType}
    assert valores == {"STATE", "FEDERAL", "LABOR", "SUPERIOR", "ELECTORAL", "MILITARY"}


def test_empty_e_partial_sao_status_distintos():
    assert SearchStatus.EMPTY != SearchStatus.PARTIAL
    assert SearchStatus.EMPTY.value == "EMPTY"
    assert SearchStatus.PARTIAL.value == "PARTIAL"


def test_catalogo_retryable_apenas_transitorios():
    assert ErrorCode.PROVIDER_TIMEOUT in RETRYABLE_ERROR_CODES
    assert ErrorCode.RATE_LIMITED in RETRYABLE_ERROR_CODES
    assert ErrorCode.PROVIDER_UNAVAILABLE in RETRYABLE_ERROR_CODES
    assert ErrorCode.PROVIDER_SERVER_ERROR in RETRYABLE_ERROR_CODES
    # não transitórios ficam de fora
    assert ErrorCode.BAD_REQUEST not in RETRYABLE_ERROR_CODES
    assert ErrorCode.AUTHENTICATION_ERROR not in RETRYABLE_ERROR_CODES
    assert ErrorCode.UNSUPPORTED_SEARCH_CRITERIA not in RETRYABLE_ERROR_CODES


def test_search_request_defaults():
    req = SearchRequest(cpf="12345678900")
    assert req.execution_mode == ExecutionMode.PARALLEL
    assert req.include_movements is True
    assert req.tribunals == []
    assert req.justice_types == []


def test_search_request_aceita_justice_types_tipados():
    req = SearchRequest(cpf="1", justice_types=[JusticeType.FEDERAL, JusticeType.LABOR])
    assert JusticeType.FEDERAL in req.justice_types


def test_search_result_minimo():
    result = SearchResult(search_id="abc", status=SearchStatus.PENDING)
    assert result.completeness.requested_sources == 0
    assert result.processes == []
    assert result.reanalyze.recommended is False


def test_capability_class_alias():
    # 'class' é palavra reservada; o DTO expõe alias.
    cap = SearchCriteriaSupport(**{"class": True})
    assert cap.class_ is True
    assert SourceStatus.UNSUPPORTED.value == "UNSUPPORTED"
