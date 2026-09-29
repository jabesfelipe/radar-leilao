"""JUR-03 (revisão de timeout) — testes determinísticos de prazos.

Cobrem, medindo tempo de retorno e estados por fonte:
1. fonte bloqueada em SEQUENTIAL retorna dentro do limite;
2. várias fontes bloqueadas em PARALLEL respeitam o timeout individual contado
   desde o início de cada execução (não somam);
3. uma fonte lenta não concede novo timeout completo às já bloqueadas;
4. o prazo global limita a duração total;
5. fontes restantes após o prazo global são marcadas TIMEOUT.
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


class ConfigurableProvider(JudicialProvider):
    """Provider cujo tempo de resposta por tribunal é configurável.

    delays[tribunal] = segundos de bloqueio (se >= 5 usamos um Event p/ liberar
    ao final do teste e não vazar thread). Sem entrada => responde imediatamente.
    """

    code = "DATAJUD"

    def __init__(self, delays, release: threading.Event):
        self.delays = delays
        self._release = release
        self.started_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def search(self, request, tribunal):
        with self._lock:
            self.started_at[tribunal] = time.monotonic()
        delay = self.delays.get(tribunal, 0.0)
        if delay >= 5:
            self._release.wait(timeout=delay)
        elif delay > 0:
            time.sleep(delay)
        return [_proc(tribunal, tribunal)]

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def _orch(delays, release, config):
    provider = ConfigurableProvider(delays, release)
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=config, sleep=lambda _: None,
    )
    return orch, provider


def test_sequential_fonte_bloqueada_retorna_dentro_do_limite():
    release = threading.Event()
    # TJPR bloqueia; TJSP responderia rápido, mas em SEQUENTIAL fica após o global.
    cfg = OrchestratorConfig(source_timeout_ms=200, global_timeout_ms=600, retry=RetryPolicy(max_attempts=1))
    orch, _ = _orch({"TJPR": 10}, release, cfg)
    inicio = time.monotonic()
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
        decorrido = time.monotonic() - inicio
        # Retorna dentro do prazo global (com folga), não nos 10s de bloqueio.
        assert decorrido < 3.0
        tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
        assert tjpr.status == SourceStatus.TIMEOUT
        # TJSP não pôde ser consultada (worker preso na TJPR) -> TIMEOUT pelo global.
        tjsp = next(s for s in res.sources if s.tribunal == "TJSP")
        assert tjsp.status == SourceStatus.TIMEOUT
    finally:
        release.set()


def test_parallel_varias_bloqueadas_respeitam_timeout_individual():
    release = threading.Event()
    cfg = OrchestratorConfig(
        source_timeout_ms=300, global_timeout_ms=5000,
        max_global_concurrency=10, max_provider_concurrency=10, retry=RetryPolicy(max_attempts=1),
    )
    # 3 fontes bloqueadas simultaneamente; todas iniciam ~juntas.
    orch, _ = _orch({"TJPR": 10, "TJSP": 10, "TRF4": 10}, release, cfg)
    inicio = time.monotonic()
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP", "TRF4"]))
        decorrido = time.monotonic() - inicio
        # Como rodam em paralelo e cada uma tem 300ms, o total fica bem abaixo da
        # soma (0.9s) e MUITO abaixo dos 10s de bloqueio. Damos folga de agendamento.
        assert decorrido < 2.0
        assert all(s.status == SourceStatus.TIMEOUT for s in res.sources)
        assert res.status == SearchStatus.FAILED
    finally:
        release.set()


def test_parallel_fonte_lenta_nao_posterga_timeout_das_bloqueadas():
    release = threading.Event()
    # rápida (0.05s) + duas bloqueadas. O timeout das bloqueadas é contado desde o
    # início delas, não é reiniciado por causa da fonte que concluiu antes.
    cfg = OrchestratorConfig(
        source_timeout_ms=300, global_timeout_ms=5000,
        max_global_concurrency=10, max_provider_concurrency=10, retry=RetryPolicy(max_attempts=1),
    )
    orch, provider = _orch({"TJSP": 10, "TRF4": 10}, release, cfg)  # TJPR rápida (sem delay)
    inicio = time.monotonic()
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP", "TRF4"]))
        decorrido = time.monotonic() - inicio
        # A conclusão rápida da TJPR não deve conceder novo orçamento às bloqueadas.
        assert decorrido < 2.0
        tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
        assert tjpr.status in (SourceStatus.SUCCESS, SourceStatus.EMPTY)
        for code in ("TJSP", "TRF4"):
            s = next(s for s in res.sources if s.tribunal == code)
            assert s.status == SourceStatus.TIMEOUT
    finally:
        release.set()


def test_prazo_global_limita_duracao_total_em_parallel():
    release = threading.Event()
    # Muitas fontes bloqueadas, concorrência baixa: o prazo global encerra tudo.
    cfg = OrchestratorConfig(
        source_timeout_ms=5000, global_timeout_ms=400,
        max_global_concurrency=2, max_provider_concurrency=2, retry=RetryPolicy(max_attempts=1),
    )
    orch, _ = _orch({t: 10 for t in ("TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6")}, release, cfg)
    inicio = time.monotonic()
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"]))
        decorrido = time.monotonic() - inicio
        # Retorna perto do prazo global (0.4s), não do source_timeout (5s).
        assert decorrido < 2.5
        assert len(res.sources) == 6
        assert all(s.status == SourceStatus.TIMEOUT for s in res.sources)
    finally:
        release.set()


def test_fontes_restantes_apos_global_marcadas_timeout_preservando_as_concluidas():
    release = threading.Event()
    # concorrência 1: TJPR responde rápido e é registrada; TJSP bloqueia e estoura
    # o prazo global; TRF4 nem chega a iniciar -> TIMEOUT (global).
    cfg = OrchestratorConfig(
        source_timeout_ms=5000, global_timeout_ms=400,
        max_global_concurrency=1, max_provider_concurrency=1, retry=RetryPolicy(max_attempts=1),
    )
    orch, _ = _orch({"TJSP": 10}, release, cfg)  # TJPR e TRF4 rápidas; TJSP bloqueia
    inicio = time.monotonic()
    try:
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP", "TRF4"]))
        decorrido = time.monotonic() - inicio
        assert decorrido < 2.5
        tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
        assert tjpr.status in (SourceStatus.SUCCESS, SourceStatus.EMPTY)  # concluída preservada
        for code in ("TJSP", "TRF4"):
            s = next(s for s in res.sources if s.tribunal == code)
            assert s.status == SourceStatus.TIMEOUT
        # ordem das fontes preservada no resultado
        assert [s.tribunal for s in res.sources] == ["TJPR", "TJSP", "TRF4"]
    finally:
        release.set()
