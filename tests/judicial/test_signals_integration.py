"""JUR-04 — integração: sinais gerados pelo orquestrador e persistidos no store."""
from __future__ import annotations

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import JusticeType, SearchEventType
from judicial_api.models import Movement, Party, Process, SearchRequest
from judicial_api.orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
from judicial_api.orchestration.resilience import RetryPolicy
from judicial_api.orchestration.store import InMemorySearchStore
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry


class _Registry(ProviderRegistry):
    def __init__(self, provider):
        self._p = provider

    def get_provider(self, code):
        return self._p if code == self._p.code else None

    def provider_for_tribunal(self, tribunal_code):
        return self._p

    def list_providers(self):
        return [self._p]


class ProcessProvider(JudicialProvider):
    code = "DATAJUD"

    def __init__(self, processes_by_tribunal):
        self._map = processes_by_tribunal

    def search(self, request, tribunal):
        return list(self._map.get(tribunal, []))

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def _orch(processes_by_tribunal, store=None):
    store = store or InMemorySearchStore()
    return SearchOrchestrator(
        _Registry(ProcessProvider(processes_by_tribunal)),
        catalog=default_catalog(), store=store,
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    ), store


def test_search_gera_sinais_no_resultado():
    proc = Process(
        process_number="1", tribunal="TJPR", justice_type=JusticeType.STATE,
        movements=[Movement(description="Penhora efetivada sobre imóvel")],
    )
    orch, _ = _orch({"TJPR": [proc]})
    res = orch.search(SearchRequest(process_number="1", tribunals=["TJPR"]))
    codes = {s.signal_code for s in res.signals}
    assert "PENHORA" in codes
    assert "PROPERTY_PENHORA_EVIDENCE" in codes


def test_evento_signal_analysis_completed_registrado():
    proc = Process(process_number="1", tribunal="TJPR", justice_type=JusticeType.STATE,
                   movements=[Movement(description="execução fiscal")])
    store = InMemorySearchStore()
    orch, store = _orch({"TJPR": [proc]}, store=store)
    res = orch.search(SearchRequest(process_number="1", tribunals=["TJPR"]))
    rec = store.get(res.search_id)
    tipos = [e.type for e in rec.events]
    assert SearchEventType.SIGNAL_ANALYSIS_COMPLETED in tipos
    # o resultado persistido carrega os sinais
    assert rec.result.signals == res.signals
    assert len(res.signals) >= 1


def test_homonimo_no_fluxo_publico_por_nome_sem_documento():
    proc = Process(process_number="1", tribunal="TJPR", justice_type=JusticeType.STATE,
                   parties=[Party(name="JOÃO DA SILVA")],
                   movements=[Movement(description="cobrança")])
    orch, _ = _orch({"TJPR": [proc]})
    res = orch.search(SearchRequest(name="João da Silva", tribunals=["TJPR"]))
    codes = {s.signal_code for s in res.signals}
    assert "HOMONYM_POSSIBLE" in codes


def test_sem_processos_sem_sinais():
    orch, _ = _orch({"TJPR": []})
    res = orch.search(SearchRequest(process_number="1", tribunals=["TJPR"]))
    assert res.signals == []
