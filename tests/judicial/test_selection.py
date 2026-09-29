"""JUR-03 — testes de seleção de fontes e idempotência (request_hash)."""
from __future__ import annotations

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import JusticeType
from judicial_api.models import SearchRequest
from judicial_api.orchestration.selection import compute_request_hash, select_sources


CAT = default_catalog()


def test_selecao_por_tribunals_resolve_alias():
    req = SearchRequest(process_number="1", tribunals=["tjpr", "TJSP", "Tribunal de Justiça do Paraná"])
    codes = [e.code for e in select_sources(req, CAT)]
    # dedup: TJPR aparece uma vez apesar de citado 2x (código + alias textual)
    assert sorted(codes) == ["TJPR", "TJSP"]


def test_selecao_por_justice_types():
    req = SearchRequest(process_number="1", justice_types=[JusticeType.FEDERAL])
    codes = {e.code for e in select_sources(req, CAT)}
    assert codes == {"TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"}


def test_selecao_ampla_pega_todas_habilitadas():
    req = SearchRequest(process_number="1")
    codes = {e.code for e in select_sources(req, CAT)}
    assert {"TJPR", "TJSP", "TRF4", "TRT9", "STJ", "TSE"}.issubset(codes)
    # escopo estadual controlado permanece
    assert "TJRJ" not in codes


def test_selecao_por_uf_mantem_nacionais():
    req = SearchRequest(process_number="1", uf="PR")
    codes = {e.code for e in select_sources(req, CAT)}
    # fontes com UF casam por PR
    assert "TJPR" in codes and "TRE-PR" in codes
    # fonte estadual de outra UF é filtrada
    assert "TJSP" not in codes
    # fontes nacionais (sem UF) permanecem elegíveis
    assert "TRF4" in codes and "STJ" in codes


def test_tribunal_fora_do_catalogo_e_ignorado():
    req = SearchRequest(process_number="1", tribunals=["TJRJ", "TJPR"])
    codes = [e.code for e in select_sources(req, CAT)]
    assert codes == ["TJPR"]


def test_request_hash_estavel_e_sensivel():
    a = SearchRequest(process_number="0000000-00.0000.0.00.0000", uf="pr")
    b = SearchRequest(process_number="00000000000000000000", uf="PR")
    # normalização torna os dois equivalentes
    assert compute_request_hash(a) == compute_request_hash(b)
    c = SearchRequest(process_number="99999999999999999999", uf="PR")
    assert compute_request_hash(a) != compute_request_hash(c)
