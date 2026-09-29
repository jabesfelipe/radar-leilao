"""JUR-03 (revisão pontual) — corrida entre a checagem de prazo global e a
chamada real ao provider.

A autorização é reverificada imediatamente antes de CADA chamada ao provider
(sob lock curto, liberado antes da rede). Estes testes forçam deterministicamente
o instante em que o prazo global expira ENTRE a entrada do worker e a chamada,
comprovando que provider.search não é chamado e que SOURCE_STARTED não é emitido.
"""
from __future__ import annotations

import threading

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ErrorCode, SearchEventType, SourceStatus
from judicial_api.errors import JudicialError
from judicial_api.models import JusticeType, Process, SearchRequest
from judicial_api.orchestration.orchestrator import (
    OrchestratorConfig,
    SearchOrchestrator,
    _SourceTiming,
)
from judicial_api.orchestration.resilience import BackoffPolicy, RetryPolicy
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


class ScriptedClock:
    """Relógio determinístico que devolve valores de uma sequência a cada chamada
    (repetindo o último). Permite posicionar o 'agora' em pontos específicos do
    fluxo do worker: entrada, autorização, conclusão, etc."""

    def __init__(self, valores):
        self._valores = list(valores)
        self._i = 0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            v = self._valores[min(self._i, len(self._valores) - 1)]
            self._i += 1
            return v


class RecordingProvider(JudicialProvider):
    code = "DATAJUD"

    def __init__(self, behavior=None):
        self.called: list[str] = []
        self._behavior = behavior or {}

    def search(self, request, tribunal):
        self.called.append(tribunal)
        kind = self._behavior.get(tribunal)
        if kind == "transient_once":
            # falha transitória na 1ª chamada para exercitar retry
            if self.called.count(tribunal) == 1:
                raise JudicialError(ErrorCode.PROVIDER_TIMEOUT, "t", http_status=504, tribunal=tribunal)
        return [_proc(tribunal, tribunal)]

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def _make(provider, clock, retry_attempts=1):
    return SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=retry_attempts, backoff=BackoffPolicy(base_ms=0, jitter_ms=0))),
        sleep=lambda _: None, clock=clock,
    )


def test_prazo_expira_entre_entrada_do_worker_e_a_chamada():
    # A autorização (imediatamente antes da chamada) vê o relógio já em 2.0, além
    # do deadline 1.0 => IMPEDE. Simula o prazo ter expirado enquanto a fonte
    # aguardava, exatamente no ponto anterior à chamada real ao provider.
    provider = RecordingProvider()
    clock = ScriptedClock([2.0, 2.0])
    orch = _make(provider, clock)
    store = orch._store
    entry = default_catalog().get("TJPR")
    timing = _SourceTiming()

    outcome = orch._run_one_source(SearchRequest(process_number="x"), entry, "sid", timing, global_deadline=1.0)

    # provider NÃO foi chamado (impedido na autorização, imediatamente antes da chamada).
    assert provider.called == []
    assert timing.skipped_global_timeout is True
    assert timing.started_at is None


def test_source_started_nao_emitido_quando_impedido_pela_corrida():
    from judicial_api.orchestration.store import SearchRecord
    from judicial_api.models import SearchResult
    from judicial_api.enums import SearchStatus

    provider = RecordingProvider()
    clock = ScriptedClock([5.0, 5.0])  # autorização=5.0 >= deadline 1.0 => impede
    orch = _make(provider, clock)
    store = orch._store
    # Semeia um registro para que os eventos possam ser anexados.
    store.save(SearchRecord(search_id="sid", correlation_id=None, request_hash="h",
                            result=SearchResult(search_id="sid", status=SearchStatus.PENDING)))

    entry = default_catalog().get("TJPR")
    timing = _SourceTiming()
    orch._run_one_source(SearchRequest(process_number="x"), entry, "sid", timing, global_deadline=1.0)

    rec = store.get("sid")
    started = {e.tribunal for e in rec.events if e.type == SearchEventType.SOURCE_STARTED}
    assert "TJPR" not in started          # impedida => sem SOURCE_STARTED
    assert provider.called == []
    assert timing.skipped_global_timeout is True


def test_chamada_autorizada_antes_do_deadline_executa_normalmente():
    # Sequência: autorização=0.5 (< deadline 1.0) => autoriza; now_auth=0.5; finished=0.9.
    provider = RecordingProvider()
    clock = ScriptedClock([0.5, 0.5, 0.9])
    orch = _make(provider, clock)
    entry = default_catalog().get("TJPR")
    timing = _SourceTiming()
    outcome = orch._run_one_source(SearchRequest(process_number="x"), entry, "sid", timing, global_deadline=1.0)
    assert provider.called == ["TJPR"]
    assert timing.started_at == 0.5
    assert outcome.result.status == SourceStatus.SUCCESS


def test_retry_reverifica_prazo_e_impede_segunda_chamada_apos_deadline():
    # 1ª chamada autorizada (t<deadline) e falha transitória; antes do retry o
    # relógio passa do deadline => a 2ª chamada é IMPEDIDA (não chama provider de novo).
    provider = RecordingProvider(behavior={"TJPR": "transient_once"})
    # sequência: autoriza 1ª (check=0.2, now_auth=0.2) -> provider chamado e falha;
    # on_retry/backoff (sleep no-op); autoriza 2ª (check=3.0 >= deadline 1.0) => impede.
    clock = ScriptedClock([0.2, 0.2, 3.0])
    orch = _make(provider, clock, retry_attempts=3)
    entry = default_catalog().get("TJPR")
    timing = _SourceTiming()
    outcome = orch._run_one_source(SearchRequest(process_number="x"), entry, "sid", timing, global_deadline=1.0)
    # provider foi chamado só UMA vez (a 1ª); o retry foi impedido pela reverificação.
    assert provider.called == ["TJPR"]
    assert timing.skipped_global_timeout is True
    assert outcome.result.status == SourceStatus.TIMEOUT
