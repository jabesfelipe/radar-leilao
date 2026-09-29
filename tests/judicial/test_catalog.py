"""JUR-02 — testes do catálogo de fontes (escopo controlado + dados corretos)."""
from __future__ import annotations

from judicial_api.catalog import build_search_url, load_catalog
from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import JusticeType


def test_escopo_estadual_somente_tjpr_tjsp():
    catalog = default_catalog()
    estaduais = {e.code for e in catalog.for_justice_types([JusticeType.STATE])}
    assert estaduais == {"TJPR", "TJSP"}


def test_demais_tjs_estaduais_ausentes():
    catalog = default_catalog()
    codes = set(catalog.codes())
    for ausente in ["TJRJ", "TJMG", "TJRS", "TJSC", "TJBA", "TJDFT", "TJCE"]:
        assert ausente not in codes


def test_cobertura_federal_trf1_a_trf6():
    catalog = default_catalog()
    federais = {e.code for e in catalog.for_justice_types([JusticeType.FEDERAL])}
    assert federais == {"TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"}


def test_cobertura_trabalhista_trt1_a_trt24():
    catalog = default_catalog()
    trts = {e.code for e in catalog.for_justice_types([JusticeType.LABOR])}
    assert trts == {f"TRT{i}" for i in range(1, 25)}


def test_superiores_stj_tst_tse_stm():
    catalog = default_catalog()
    superiores = {e.code for e in catalog.for_justice_types([JusticeType.SUPERIOR])}
    assert superiores == {"STJ", "TST", "TSE", "STM"}


def test_eleitoral_tem_27_tres_mais_tse():
    catalog = default_catalog()
    eleitorais = {e.code for e in catalog.for_justice_types([JusticeType.ELECTORAL])}
    # 27 TREs + o TSE (que é SUPERIOR e ELECTORAL simultaneamente).
    assert len(eleitorais) == 28
    assert "TRE-PR" in eleitorais and "TRE-SP" in eleitorais
    assert "TSE" in eleitorais


def test_tse_pertence_a_superior_e_eleitoral_sem_duplicar():
    catalog = default_catalog()
    # Uma única entrada TSE no catálogo (não duplicada).
    assert catalog.codes().count("TSE") == 1
    tse = catalog.get("TSE")
    assert set(tse.justice_types) == {JusticeType.SUPERIOR, JusticeType.ELECTORAL}
    # aparece nos dois filtros
    superiores = {e.code for e in catalog.for_justice_types([JusticeType.SUPERIOR])}
    eleitorais = {e.code for e in catalog.for_justice_types([JusticeType.ELECTORAL])}
    assert "TSE" in superiores and "TSE" in eleitorais


def test_militar_somente_fontes_disponiveis():
    catalog = default_catalog()
    militares = {e.code for e in catalog.for_justice_types([JusticeType.MILITARY])}
    assert militares == {"TJMMG", "TJMRS", "TJMSP"}


def test_search_url_encapsula_alias_do_datajud():
    catalog = default_catalog()
    tjpr = catalog.get("TJPR")
    assert tjpr is not None
    assert tjpr.search_url == "https://api-publica.datajud.cnj.jus.br/api_publica_tjpr/_search"
    # TRE usa alias com hífen na doc oficial.
    tre_pr = catalog.get("TRE-PR")
    assert tre_pr.search_url.endswith("/api_publica_tre-pr/_search")


def test_build_search_url_helper():
    assert build_search_url("https://x/", "tjsp") == "https://x/api_publica_tjsp/_search"


def test_capabilities_padrao_refletem_criterios_comprovados():
    catalog = default_catalog()
    cap = catalog.get("TJPR").capabilities
    # comprovadas na doc oficial (glossário) -> têm query correspondente
    assert cap.process_number is True
    assert cap.class_ is True
    assert cap.subject is True
    assert cap.court is True
    assert cap.grau is True
    # não comprovadas => nunca assumidas
    assert cap.name is False
    assert cap.cpf is False
    assert cap.cnpj is False


def test_resolve_alias_por_texto_e_codigo():
    catalog = default_catalog()
    assert catalog.resolve_alias("tjpr") == "TJPR"
    assert catalog.resolve_alias("Tribunal de Justiça do Paraná") == "TJPR"
    assert catalog.resolve_alias("TJPR") == "TJPR"
    assert catalog.resolve_alias("inexistente") is None


def test_base_url_override_no_loader():
    catalog = load_catalog(base_url_override="https://mock.local")
    assert catalog.get("TJSP").search_url == "https://mock.local/api_publica_tjsp/_search"
