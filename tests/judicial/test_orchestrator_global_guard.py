"""JUR-03 (revisão pontual) — guarda de prazo global no worker e evento
SOURCE_STARTED no início real.

Cobre:
1. fonte bloqueada + global expirado + próxima na fila: a segunda NÃO chama provider.search;
2. guarda no worker: se o global já expirou antes de iniciar, provider.search não é chamado;
3. fonte iniciada antes do deadline continua tratada pelo instante real de conclusão;
4. eventos: fonte não executada não recebe SOURCE_STARTED; a executada recebe.
"""
from __future__ import annotations

import threading
import time

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ExecutionMode, SearchEventType, SearchStatus, SourceStatus
from judicial_api.models import JusticeType, Process, SearchRequest
from judicial_api.orchestration.orchestrator import (
    OrchestratorConfig,
    SearchOrchestrator,
    _SourceTiming,
)
from judicial_api.orchestration.resilience import RetryPolicy
from judicial_api.orchestration.store import InMemorySearchStore
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry


def _proc(tribunal, numero):
    return Process(process_number=numero, tribunal=tribunal, justice_type=JusticeType.STATE)


class _Registry(ProviderRegistry):
    def __init__(self, provider):
        self._p = provider

    def get_provider(self, code):
        return self._p if code == self._p.code else None

    def provider_for_tribunal(self, tribunal_code):
        return self._p

    def list_providers(self):
        return [self._p]


class CountingProvider(JudicialProvider):
    """Registra quais tribunais chamaram search; a primeira fonte pode bloquear."""

    code = "DATAJUD"

    def __init__(self, block: str | None, gate: threading.Event):
        self._block = block
        self._gate = gate
        self.called: list[str] = []
        self._lock = threading.Lock()

    def search(self, request, tribunal):
        with self._lock:
            self.called.append(tribunal)
        if tribunal == self._block:
            self._gate.wait(timeout=5)
        return [_proc(tribunal, tribunal)]

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def test_segunda_fonte_na_fila_nao_chama_provider_apos_global(monkeypatch):
    gate = threading.Event()
    provider = CountingProvider(block="TJPR", gate=gate)
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=100, global_timeout_ms=250, retry=RetryPolicy(max_attempts=1)),
    )
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
        # TJPR chamou e bloqueou; o prazo global expirou; TJSP ficou na fila e NÃO
        # chegou a chamar provider.search.
        assert "TJSP" not in provider.called
        tjsp = next(s for s in res.sources if s.tribunal == "TJSP")
        assert tjsp.status == SourceStatus.TIMEOUT
    finally:
        gate.set()


def test_worker_guarda_prazo_global_antes_de_chamar_provider():
    # Exercita diretamente a guarda dentro do worker: com o prazo global já no
    # passado, o worker não chama provider.search e sinaliza skipped_global_timeout.
    provider = CountingProvider(block=None, gate=threading.Event())
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)),
    )
    entry = default_catalog().get("TJPR")
    timing = _SourceTiming()
    past_deadline = time.monotonic() - 1.0  # já expirado
    outcome = orch._run_one_source(SearchRequest(process_number="x"), entry, "sid", timing, past_deadline)
    assert provider.called == []                 # provider NÃO foi chamado
    assert timing.skipped_global_timeout is True
    assert timing.started_at is None             # não iniciou
    assert outcome.result.status == SourceStatus.TIMEOUT


def test_fonte_iniciada_antes_do_deadline_e_avaliada_pelo_fim_real():
    # Sem bloqueio: inicia dentro do prazo e conclui rápido -> SUCCESS.
    provider = CountingProvider(block=None, gate=threading.Event())
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=2000, global_timeout_ms=5000, retry=RetryPolicy(max_attempts=1)),
    )
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    assert "TJPR" in provider.called
    tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
    assert tjpr.status == SourceStatus.SUCCESS


def test_evento_source_started_apenas_para_fonte_executada():
    gate = threading.Event()
    provider = CountingProvider(block="TJPR", gate=gate)
    store = InMemorySearchStore()
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=store,
        config=OrchestratorConfig(source_timeout_ms=100, global_timeout_ms=250, retry=RetryPolicy(max_attempts=1)),
    )
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
        rec = store.get(res.search_id)
        started_tribunals = {e.tribunal for e in rec.events if e.type == SearchEventType.SOURCE_STARTED}
        # TJPR executou -> tem SOURCE_STARTED; TJSP não executou -> NÃO tem.
        assert "TJPR" in started_tribunals
        assert "TJSP" not in started_tribunals
    finally:
        gate.set()
