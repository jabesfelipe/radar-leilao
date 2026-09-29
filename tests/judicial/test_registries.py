"""JUR-02 — testes dos registries concretos (baseados no catálogo)."""
from __future__ import annotations

from judicial_api.enums import JusticeType
from judicial_api.providers.datajud import DataJudProvider
from judicial_api.registry import CatalogTribunalRegistry, SimpleProviderRegistry


def test_tribunal_registry_lista_e_resolve():
    reg = CatalogTribunalRegistry()
    codes = {t.code for t in reg.list_tribunals()}
    assert {"TJPR", "TJSP"}.issubset(codes)
    assert "TJRJ" not in codes  # fora do escopo estadual

    assert reg.get("tjpr").code == "TJPR"
    assert reg.get("Tribunal de Justiça do Paraná").code == "TJPR"
    assert reg.get("XXXX") is None
    assert reg.resolve_alias("tjsp") == "TJSP"


def test_tribunal_registry_filtra_por_ramo():
    reg = CatalogTribunalRegistry()
    federais = {t.code for t in reg.for_justice_types([JusticeType.FEDERAL])}
    assert federais == {"TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"}


def test_provider_registry_resolve_provider_por_tribunal():
    trib = CatalogTribunalRegistry()
    provider = DataJudProvider()
    preg = SimpleProviderRegistry([provider], trib)

    assert preg.get_provider("DATAJUD") is provider
    assert preg.provider_for_tribunal("TJPR") is provider
    assert preg.provider_for_tribunal("tjsp") is provider  # via alias
    # tribunal fora do catálogo não resolve provider
    assert preg.provider_for_tribunal("TJRJ") is None
    assert preg.list_providers() == [provider]
