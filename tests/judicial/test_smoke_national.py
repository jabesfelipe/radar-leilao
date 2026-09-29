"""JUR-05 — smoke test nacional (SPEC §85).

Verifica, com um provider falso (sem rede), que uma pesquisa ampla exercita
representantes de todos os ramos da Justiça e agrega o resultado por status de
fonte. Não valida dados reais — valida que a orquestração multi-ramo funciona
ponta a ponta e produz o resumo TOTAL/SUCCESS/EMPTY/TIMEOUT/ERROR/UNSUPPORTED.
"""
from __future__ import annotations

from collections import Counter

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ErrorCode, JusticeType, SourceStatus
from judicial_api.errors import JudicialError
from judicial_api.models import Movement, Process, SearchRequest
from judicial_api.orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
from judicial_api.orchestration.resilience import RetryPolicy
from judicial_api.orchestration.store import InMemorySearchStore
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry

# Um representante por ramo (SPEC §85).
REPRESENTATIVES = {
    "SUPERIOR": "STJ",
    "FEDERAL": "TRF4",
    "STATE": "TJPR",
    "LABOR": "TRT9",
    "ELECTORAL": "TSE",
    "MILITARY": "TJMSP",
}


class _SmokeProvider(JudicialProvider):
    """Comportamento distinto por tribunal, cobrindo todos os desfechos."""

    code = "DATAJUD"

    def search(self, request, tribunal):
        if tribunal == "TJPR":
            return [Process(process_number="1", tribunal="TJPR", justice_type=JusticeType.STATE,
                            movements=[Movement(description="penhora")])]
        if tribunal == "TRF4":
            return []  # EMPTY
        if tribunal == "STJ":
            raise JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504, tribunal=tribunal)
        if tribunal == "TRT9":
            raise JudicialError(ErrorCode.PROVIDER_SERVER_ERROR, "erro", http_status=502, tribunal=tribunal, retryable=False)
        if tribunal == "TSE":
            raise JudicialError(ErrorCode.UNSUPPORTED_SEARCH_CRITERIA, "n/s", http_status=422, tribunal=tribunal)
        return [Process(process_number="9", tribunal=tribunal, justice_type=JusticeType.MILITARY)]

    def get_capabilities(self, tribunal):  # pragma: no cover
        raise NotImplementedError

    def health_check(self):  # pragma: no cover
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


class _Registry(ProviderRegistry):
    def __init__(self, p):
        self._p = p

    def get_provider(self, code):
        return self._p if code == self._p.code else None

    def provider_for_tribunal(self, tribunal_code):
        return self._p

    def list_providers(self):
        return [self._p]


def test_smoke_nacional_por_ramo():
    orch = SearchOrchestrator(
        _Registry(_SmokeProvider()),
        catalog=default_catalog(),
        store=InMemorySearchStore(),
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )
    request = SearchRequest(process_number="1", tribunals=list(REPRESENTATIVES.values()))
    result = orch.search(request)

    consultados = {s.tribunal for s in result.sources}
    assert set(REPRESENTATIVES.values()).issubset(consultados)

    resumo = Counter(s.status for s in result.sources)
    # Cada desfecho previsto aparece ao menos uma vez.
    assert resumo[SourceStatus.SUCCESS] >= 1
    assert resumo[SourceStatus.EMPTY] >= 1
    assert resumo[SourceStatus.TIMEOUT] >= 1
    assert resumo[SourceStatus.ERROR] >= 1
    assert resumo[SourceStatus.UNSUPPORTED] >= 1
    # TOTAL bate com o número de fontes selecionadas.
    assert len(result.sources) == len(REPRESENTATIVES)
