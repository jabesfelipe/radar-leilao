"""JUR-05 — testes unitários de segurança, rate limiting e métricas."""
from __future__ import annotations

from judicial_api.config import JudicialSettings
from judicial_api.metrics import Metrics
from judicial_api.models import Process, SearchResult, SourceResult
from judicial_api.enums import JusticeType, SearchStatus, SourceStatus
from judicial_api.ratelimit import SlidingWindowLimiter
from judicial_api.security import (
    SCOPE_READ,
    SCOPE_SEARCH,
    Principal,
    mask_document,
    masked_criteria,
)


# --------------------------------------------------------------------------
# Parsing de chaves e escopos (config)
# --------------------------------------------------------------------------

def test_parsed_api_keys_com_escopos():
    s = JudicialSettings(api_keys="k-full, k-read:read, k-both:search|read")
    keys = s.parsed_api_keys()
    assert keys["k-full"] == frozenset()          # sem escopo => acesso total
    assert keys["k-read"] == frozenset({"read"})
    assert keys["k-both"] == frozenset({"search", "read"})
    assert s.auth_enabled is True


def test_auth_desligada_sem_chaves():
    s = JudicialSettings(api_keys=None)
    assert s.parsed_api_keys() == {}
    assert s.auth_enabled is False


def test_require_auth_liga_mesmo_sem_chaves():
    s = JudicialSettings(api_keys=None, require_auth=True)
    assert s.auth_enabled is True


# --------------------------------------------------------------------------
# Escopos do Principal
# --------------------------------------------------------------------------

def test_principal_sem_escopo_tem_acesso_total():
    p = Principal(key_id="key:ab***", scopes=frozenset())
    assert p.has_scope(SCOPE_SEARCH)
    assert p.has_scope(SCOPE_READ)


def test_principal_com_escopo_restrito():
    p = Principal(key_id="key:ab***", scopes=frozenset({SCOPE_READ}))
    assert p.has_scope(SCOPE_READ)
    assert not p.has_scope(SCOPE_SEARCH)


def test_principal_anonimo_tem_acesso_total():
    p = Principal(key_id="anonymous", scopes=frozenset({SCOPE_READ}), anonymous=True)
    assert p.has_scope(SCOPE_SEARCH)


# --------------------------------------------------------------------------
# Mascaramento de dados sensíveis (SPEC §71)
# --------------------------------------------------------------------------

def test_mask_document_preserva_apenas_final():
    assert mask_document("123.456.789-00") == "***00"
    assert mask_document(None) is None
    assert mask_document("abc") == "***"


def test_masked_criteria_nao_expoe_valores_completos():
    resumo = masked_criteria(name="João da Silva", cpf="12345678900", process_number="0001")
    assert resumo["has_name"] == "true"
    assert resumo["cpf"] == "***00"
    assert "12345678900" not in str(resumo)
    assert resumo["has_process_number"] == "true"


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------

def test_rate_limiter_bloqueia_apos_limite():
    t = {"now": 0.0}
    limiter = SlidingWindowLimiter(2, 10, clock=lambda: t["now"])
    assert limiter.allow("c")[0] is True
    assert limiter.allow("c")[0] is True
    permitido, restantes, retry_after = limiter.allow("c")
    assert permitido is False
    assert restantes == 0
    assert retry_after > 0


def test_rate_limiter_libera_apos_janela():
    t = {"now": 0.0}
    limiter = SlidingWindowLimiter(1, 10, clock=lambda: t["now"])
    assert limiter.allow("c")[0] is True
    assert limiter.allow("c")[0] is False
    t["now"] = 11.0
    assert limiter.allow("c")[0] is True


def test_rate_limiter_isola_consumidores():
    limiter = SlidingWindowLimiter(1, 10)
    assert limiter.allow("a")[0] is True
    assert limiter.allow("b")[0] is True  # consumidor distinto não é afetado


# --------------------------------------------------------------------------
# Métricas (SPEC §72)
# --------------------------------------------------------------------------

def _result(status, sources, processes=0, signals=0):
    return SearchResult(
        search_id="x",
        status=status,
        sources=sources,
        processes=[Process(process_number=str(i), tribunal="TJPR", justice_type=JusticeType.STATE) for i in range(processes)],
        signals=[],
    )


def test_metrics_contabiliza_status_e_fontes():
    m = Metrics()
    sources = [
        SourceResult(provider="DATAJUD", tribunal="TJPR", justice_type=JusticeType.STATE, status=SourceStatus.SUCCESS, duration_ms=100, attempts=2),
        SourceResult(provider="DATAJUD", tribunal="TJSP", justice_type=JusticeType.STATE, status=SourceStatus.TIMEOUT, attempts=1),
        SourceResult(provider="DATAJUD", tribunal="TRF4", justice_type=JusticeType.FEDERAL, status=SourceStatus.UNSUPPORTED, attempts=1),
    ]
    m.record_search(_result(SearchStatus.PARTIAL, sources, processes=3))
    snap = m.snapshot()
    c = snap["counters"]
    assert c["searches_total"] == 1
    assert c["searches_partial"] == 1
    assert c["provider_timeouts"] == 1
    assert c["unsupported_queries"] == 1
    assert c["processes_found"] == 3
    assert c["retries_total"] == 1  # TJPR fez 2 tentativas => 1 retry
    assert snap["provider_latency"]["DATAJUD"]["count"] == 1


def test_metrics_reset():
    m = Metrics()
    m.inc("searches_total")
    m.reset()
    assert m.snapshot()["counters"]["searches_total"] == 0
