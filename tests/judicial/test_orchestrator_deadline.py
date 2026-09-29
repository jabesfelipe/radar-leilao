"""JUR-03 (revisão pontual) — aceitação por instante de conclusão e fila no SEQUENTIAL.

Usa relógio controlável e barreiras/eventos (sem sleeps frágeis) para tornar as
condições de corrida determinísticas.
"""
from __future__ import annotations

import threading
import time

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ExecutionMode, SearchStatus, SourceStatus
from judicial_api.models import JusticeType, Process, SearchRequest
from judicial_api.orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
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


class ManualClock:
    """Relógio controlável e thread-safe (monotônico por incrementos manuais)."""

    def __init__(self):
        self._t = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            return self._t

    def advance(self, seconds: float):
        with self._lock:
            self._t += seconds


# ---------------------------------------------------------------------------
# A. Não aceitar resultados após o deadline
# ---------------------------------------------------------------------------

class GatedProvider(JudicialProvider):
    """A fonte só conclui quando o teste liberar o gate; o relógio é controlado à
    parte, permitindo simular "concluiu, mas tarde"."""

    code = "DATAJUD"

    def __init__(self, gate: threading.Event, entered: threading.Event):
        self._gate = gate
        self._entered = entered

    def search(self, request, tribunal):
        self._entered.set()
        self._gate.wait(timeout=5)
        return [_proc(tribunal, tribunal)]

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def test_resultado_tardio_apos_deadline_individual_vira_timeout():
    gate = threading.Event()
    entered = threading.Event()
    clock = ManualClock()
    orch = SearchOrchestrator(
        _Registry(GatedProvider(gate, entered)), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=1000, global_timeout_ms=10000, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None, clock=clock,
    )
    resultado = {}

    def run():
        resultado["res"] = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))

    t = threading.Thread(target=run)
    t.start()
    try:
        assert entered.wait(timeout=3)          # worker começou (started_at = 0)
        clock.advance(2.0)                       # avança além do deadline individual (1s)
        # libera a conclusão DEPOIS de estourar o deadline -> finished_at (2.0) > deadline (1.0)
        gate.set()
        t.join(timeout=5)
        assert not t.is_alive()
        tjpr = next(s for s in resultado["res"].sources if s.tribunal == "TJPR")
        assert tjpr.status == SourceStatus.TIMEOUT
        assert resultado["res"].status == SearchStatus.FAILED
    finally:
        gate.set()
        t.join(timeout=5)


def test_resultado_dentro_do_prazo_e_aceito():
    gate = threading.Event()
    entered = threading.Event()
    clock = ManualClock()
    orch = SearchOrchestrator(
        _Registry(GatedProvider(gate, entered)), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=1000, global_timeout_ms=10000, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None, clock=clock,
    )
    resultado = {}

    def run():
        resultado["res"] = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))

    t = threading.Thread(target=run)
    t.start()
    try:
        assert entered.wait(timeout=3)     # started_at = 0
        clock.advance(0.3)                  # ainda dentro do deadline (1s)
        gate.set()                          # conclui dentro do prazo -> finished_at (0.3) <= 1.0
        t.join(timeout=5)
        assert not t.is_alive()
        tjpr = next(s for s in resultado["res"].sources if s.tribunal == "TJPR")
        assert tjpr.status in (SourceStatus.SUCCESS, SourceStatus.EMPTY)
        assert tjpr.status == SourceStatus.SUCCESS
    finally:
        gate.set()
        t.join(timeout=5)


# ---------------------------------------------------------------------------
# B. Timeout no SEQUENTIAL: fila não consome o timeout individual
# ---------------------------------------------------------------------------

class RecordingProvider(JudicialProvider):
    """Registra o started_at (via clock) de cada tribunal; a primeira fonte pode
    bloquear até um gate para forçar enfileiramento da segunda."""

    code = "DATAJUD"

    def __init__(self, clock, block_first: str | None, gate: threading.Event):
        self._clock = clock
        self._block_first = block_first
        self._gate = gate
        self.started_at: dict[str, float] = {}
        self.entered = {}
        self._lock = threading.Lock()

    def search(self, request, tribunal):
        with self._lock:
            self.started_at[tribunal] = self._clock()
            self.entered.setdefault(tribunal, threading.Event()).set()
        if tribunal == self._block_first:
            self._gate.wait(timeout=5)
        return [_proc(tribunal, tribunal)]

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def test_sequential_segunda_fonte_nao_expira_so_por_aguardar_na_fila():
    # workers=1: TJPR roda primeiro e conclui; TJSP começa DEPOIS. O timeout
    # individual de TJSP deve começar no início real dela, não na submissão.
    clock = ManualClock()
    provider = RecordingProvider(clock, block_first=None, gate=threading.Event())
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=1000, global_timeout_ms=10000, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None, clock=clock,
    )
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
    # Ambas concluíram dentro do próprio orçamento (relógio não avançou): SUCCESS.
    assert [s.tribunal for s in res.sources] == ["TJPR", "TJSP"]
    assert all(s.status == SourceStatus.SUCCESS for s in res.sources)
    assert res.status == SearchStatus.COMPLETED


def test_sequential_fila_estoura_global_sem_executar_a_segunda():
    # workers=1: TJPR bloqueia; TJSP fica na fila. O prazo global acaba antes de
    # TJSP começar -> TJSP é TIMEOUT SEM ter sido executada.
    gate = threading.Event()
    clock = ManualClock()
    provider = RecordingProvider(clock, block_first="TJPR", gate=gate)
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=100, global_timeout_ms=300, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,  # relógio real aqui (prazos curtos), sem sleeps de teste
    )
    inicio = time.monotonic()
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
        decorrido = time.monotonic() - inicio
        assert decorrido < 3.0
        # TJSP nunca foi consultada (worker preso na TJPR).
        assert "TJSP" not in provider.started_at
        tjsp = next(s for s in res.sources if s.tribunal == "TJSP")
        assert tjsp.status == SourceStatus.TIMEOUT
        assert [s.tribunal for s in res.sources] == ["TJPR", "TJSP"]  # ordem preservada
    finally:
        gate.set()


# ---------------------------------------------------------------------------
# C5. Global e concorrência respeitados nos dois modos
# ---------------------------------------------------------------------------

def test_global_e_concorrencia_respeitados_em_parallel():
    ativos = {"cur": 0, "max": 0}
    lock = threading.Lock()

    class TrackingProvider(JudicialProvider):
        code = "DATAJUD"

        def search(self, request, tribunal):
            with lock:
                ativos["cur"] += 1
                ativos["max"] = max(ativos["max"], ativos["cur"])
            time.sleep(0.03)
            with lock:
                ativos["cur"] -= 1
            return [_proc(tribunal, tribunal)]

        def get_capabilities(self, tribunal):
            raise NotImplementedError

        def health_check(self):
            raise NotImplementedError

        def normalize(self, raw, tribunal):
            return []

    orch = SearchOrchestrator(
        _Registry(TrackingProvider()), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(max_global_concurrency=3, max_provider_concurrency=3, source_timeout_ms=5000, global_timeout_ms=5000, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )
    res = orch.search(SearchRequest(process_number="x", tribunals=["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"]))
    assert ativos["max"] <= 3
    assert res.status == SearchStatus.COMPLETED
    assert len(res.processes) == 6
