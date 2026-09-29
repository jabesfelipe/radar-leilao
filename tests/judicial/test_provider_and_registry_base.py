"""JUR-01 — testes das interfaces base de Provider e Registry.

Garantem que as abstrações existem, são realmente abstratas (não instanciáveis
sem implementação) e que uma implementação mínima em memória satisfaz o contrato.
Nenhuma implementação concreta de DataJud é criada nesta fase.
"""
from __future__ import annotations

import pytest

from judicial_api.enums import JusticeType
from judicial_api.models import (
    Process,
    ProviderStatus,
    SearchRequest,
    TribunalCapabilities,
    TribunalInfo,
)
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry, TribunalRegistry


def test_provider_base_e_abstrato():
    with pytest.raises(TypeError):
        JudicialProvider()  # type: ignore[abstract]


def test_registries_base_sao_abstratos():
    with pytest.raises(TypeError):
        TribunalRegistry()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        ProviderRegistry()  # type: ignore[abstract]


class _FakeProvider(JudicialProvider):
    code = "FAKE"

    def search(self, request: SearchRequest, tribunal: str) -> list[Process]:
        return []

    def get_capabilities(self, tribunal: str) -> TribunalCapabilities:
        return TribunalCapabilities(tribunal=tribunal)

    def health_check(self) -> ProviderStatus:
        return ProviderStatus(provider=self.code, status="AVAILABLE")

    def normalize(self, raw, tribunal: str) -> list[Process]:
        return []


def test_implementacao_minima_de_provider_satisfaz_contrato():
    provider = _FakeProvider()
    assert provider.code == "FAKE"
    assert provider.search(SearchRequest(cpf="1"), "TJPR") == []
    assert provider.get_capabilities("TJPR").tribunal == "TJPR"
    assert provider.health_check().status == "AVAILABLE"
    assert provider.normalize({"x": 1}, "TJPR") == []


class _FakeTribunalRegistry(TribunalRegistry):
    def __init__(self) -> None:
        self._t = TribunalInfo(code="TJPR", name="Tribunal de Justiça do Paraná", justice_type=JusticeType.STATE, uf="PR")

    def list_tribunals(self):
        return [self._t]

    def get(self, code):
        return self._t if code == "TJPR" else None

    def resolve_alias(self, alias):
        return "TJPR" if "paran" in alias.lower() else None

    def for_justice_types(self, justice_types):
        return [self._t] if JusticeType.STATE in justice_types else []


def test_implementacao_minima_de_tribunal_registry():
    reg = _FakeTribunalRegistry()
    assert reg.list_tribunals()[0].code == "TJPR"
    assert reg.get("TJPR").uf == "PR"
    assert reg.get("XXXX") is None
    assert reg.resolve_alias("Tribunal do Paraná") == "TJPR"
    assert reg.for_justice_types([JusticeType.FEDERAL]) == []
