"""JUR-03 (code review) — testes de regressão dos ajustes solicitados:

1. timeout efetivo (provider bloqueado não trava a orquestração);
2. retry seletivo respeitando retryable=False;
3. idempotência operacional (coalescência de concorrentes);
4. execution_mode (SEQUENTIAL suportado; inválido rejeitado);
5. rate limiting/concorrência (limite efetivo de workers).
"""
from __future__ import annotations

import threading
import time

import pytest

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ErrorCode, ExecutionMode, SearchStatus, SourceStatus
from judicial_api.errors import JudicialError
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


# ---------------------------------------------------------------------------
# 1. Timeout efetivo — provider que bloqueia não impede o retorno da orquestração
# ---------------------------------------------------------------------------

class BlockingProvider(JudicialProvider):
    code = "DATAJUD"

    def __init__(self, release: threading.Event):
        self._release = release
        self.entered = threading.Event()

    def search(self, request, tribunal):
        self.entered.set()
        # Bloqueia até ser liberado (simula fonte que não responde). Em produção o
        # timeout do transporte HTTP encerraria a chamada; aqui provamos que a
        # ORQUESTRAÇÃO retorna dentro do orçamento sem esperar a thread.
        self._release.wait(timeout=5)
        return []

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def test_timeout_por_fonte_efetivo_com_provider_bloqueado():
    release = threading.Event()
    provider = BlockingProvider(release)
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(source_timeout_ms=150, global_timeout_ms=1000, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )
    inicio = time.monotonic()
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    decorrido = time.monotonic() - inicio
    try:
        # Retorna rápido (perto do timeout de 150ms), não perto dos 5s de bloqueio.
        assert decorrido < 2.0
        tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
        assert tjpr.status == SourceStatus.TIMEOUT
        assert res.status == SearchStatus.FAILED  # única fonte falhou por timeout
    finally:
        release.set()  # libera a thread abandonada


def test_prazo_global_marca_restantes_como_timeout_em_sequential():
    # Em SEQUENTIAL, com global_timeout_ms=0, o prazo global já está estourado ao
    # iniciar a coleta: todas as fontes são marcadas TIMEOUT e o resultado é FAILED.
    # (A execução usa pool com deadlines individuais desde a submissão; uma chamada
    # pode chegar a iniciar antes do corte, mas isso não altera o contrato de status.)
    class Counter(JudicialProvider):
        code = "DATAJUD"

        def __init__(self):
            self.calls = 0

        def search(self, request, tribunal):
            self.calls += 1
            return [_proc(tribunal, "1")]

        def get_capabilities(self, tribunal):
            raise NotImplementedError

        def health_check(self):
            raise NotImplementedError

        def normalize(self, raw, tribunal):
            return []

    provider = Counter()
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(global_timeout_ms=0, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
    # Contrato: todas TIMEOUT e status FAILED (independe de uma chamada ter iniciado).
    assert all(s.status == SourceStatus.TIMEOUT for s in res.sources)
    assert res.status == SearchStatus.FAILED
    # No máximo uma fonte pode ter começado antes do corte (concorrência 1).
    assert provider.calls <= 1


# ---------------------------------------------------------------------------
# 2. Retry seletivo respeitando retryable=False
# ---------------------------------------------------------------------------

class ScriptedProvider(JudicialProvider):
    code = "DATAJUD"

    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = {}

    def search(self, request, tribunal):
        self.calls[tribunal] = self.calls.get(tribunal, 0) + 1
        kind, payload = self.behavior[tribunal]
        if kind == "raise":
            raise payload
        return list(payload)

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


def _orch(behavior, config=None):
    provider = ScriptedProvider(behavior)
    orch = SearchOrchestrator(
        _Registry(provider), catalog=default_catalog(), store=InMemorySearchStore(),
        config=config or OrchestratorConfig(retry=RetryPolicy(max_attempts=3)),
        sleep=lambda _: None,
    )
    return orch, provider


def test_timeout_marcado_como_nao_recuperavel_nao_reexecuta():
    # PROVIDER_TIMEOUT normalmente é transitório, mas aqui é marcado retryable=False.
    erro = JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout definitivo", http_status=504, retryable=False, tribunal="TJPR")
    orch, provider = _orch({"TJPR": ("raise", erro)}, config=OrchestratorConfig(retry=RetryPolicy(max_attempts=5)))
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    # não reexecutou apesar de max_attempts=5
    assert provider.calls["TJPR"] == 1
    tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
    assert tjpr.error.retryable is False
    # e não é elegível para reanálise
    assert "TJPR" not in res.reanalyze.sources_affected


def test_erros_definitivos_nao_sao_reprocessados_na_reanalise():
    for code in (ErrorCode.AUTHENTICATION_ERROR, ErrorCode.AUTHORIZATION_ERROR, ErrorCode.BAD_REQUEST, ErrorCode.CONFIGURATION_ERROR):
        erro = JudicialError(code, "definitivo", http_status=400, tribunal="TJPR")
        orch, provider = _orch({"TJPR": ("raise", erro)}, config=OrchestratorConfig(retry=RetryPolicy(max_attempts=4)))
        res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
        assert provider.calls["TJPR"] == 1, code
        assert "TJPR" not in res.reanalyze.sources_affected


def test_erro_transitorio_e_reprocessavel_na_reanalise():
    erro = JudicialError(ErrorCode.PROVIDER_UNAVAILABLE, "indisponível", http_status=502, tribunal="TJPR")
    orch, _ = _orch({"TJPR": ("raise", erro)}, config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)))
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    assert "TJPR" in res.reanalyze.sources_affected


# ---------------------------------------------------------------------------
# 3. Idempotência operacional (coalescência de concorrentes)
# ---------------------------------------------------------------------------

def test_coalesce_pesquisas_concorrentes_identicas():
    barrier = threading.Barrier(2, timeout=5)
    execucoes = {"n": 0}
    lock = threading.Lock()

    class SlowProvider(JudicialProvider):
        code = "DATAJUD"

        def search(self, request, tribunal):
            with lock:
                execucoes["n"] += 1
            # Sincroniza para garantir que as duas chamadas estejam concorrentes.
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            time.sleep(0.05)
            return [_proc(tribunal, "1")]

        def get_capabilities(self, tribunal):
            raise NotImplementedError

        def health_check(self):
            raise NotImplementedError

        def normalize(self, raw, tribunal):
            return []

    orch = SearchOrchestrator(
        _Registry(SlowProvider()), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)), sleep=lambda _: None,
    )
    req = SearchRequest(process_number="0000000-00.0000.0.00.0000", tribunals=["TJPR"])
    resultados = {}

    def run(key):
        resultados[key] = orch.search(req)

    t1 = threading.Thread(target=run, args=("a",))
    t2 = threading.Thread(target=run, args=("b",))
    t1.start(); t2.start()
    t1.join(); t2.join()

    # A segunda chamada concorrente foi coalescida: o provider executou uma única vez
    # e ambos os chamadores receberam o MESMO search_id.
    assert execucoes["n"] == 1
    assert resultados["a"].search_id == resultados["b"].search_id


def test_pesquisas_sequenciais_identicas_reexecutam():
    # Semântica documentada: mesma consulta em momentos diferentes NÃO é deduplicada.
    class OkProvider(JudicialProvider):
        code = "DATAJUD"

        def search(self, request, tribunal):
            return [_proc(tribunal, "1")]

        def get_capabilities(self, tribunal):
            raise NotImplementedError

        def health_check(self):
            raise NotImplementedError

        def normalize(self, raw, tribunal):
            return []

    orch = SearchOrchestrator(
        _Registry(OkProvider()), catalog=default_catalog(), store=InMemorySearchStore(),
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)), sleep=lambda _: None,
    )
    req = SearchRequest(process_number="1", tribunals=["TJPR"])
    r1 = orch.search(req)
    r2 = orch.search(req)
    assert r1.search_id != r2.search_id  # reexecuta (dados podem ter mudado)


# ---------------------------------------------------------------------------
# 4. execution_mode
# ---------------------------------------------------------------------------

def test_execution_mode_sequential_funciona():
    orch, provider = _orch({
        "TJPR": ("ok", [_proc("TJPR", "1")]),
        "TJSP": ("ok", [_proc("TJSP", "2")]),
    }, config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)))
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"], execution_mode=ExecutionMode.SEQUENTIAL))
    assert res.status == SearchStatus.COMPLETED
    assert len(res.processes) == 2


def test_execution_mode_invalido_e_rejeitado():
    orch, _ = _orch({"TJPR": ("ok", [_proc("TJPR", "1")])})
    req = SearchRequest(process_number="x", tribunals=["TJPR"])
    # força um valor não suportado sem quebrar o enum do modelo
    object.__setattr__(req, "execution_mode", "TURBO")
    with pytest.raises(JudicialError) as exc:
        orch.search(req)
    assert exc.value.code == ErrorCode.BAD_REQUEST
    assert exc.value.retryable is False


# ---------------------------------------------------------------------------
# 5. Rate limiting / concorrência efetiva
# ---------------------------------------------------------------------------

def test_concorrencia_efetiva_respeita_limite():
    ativos = {"cur": 0, "max": 0}
    lock = threading.Lock()

    class TrackingProvider(JudicialProvider):
        code = "DATAJUD"

        def search(self, request, tribunal):
            with lock:
                ativos["cur"] += 1
                ativos["max"] = max(ativos["max"], ativos["cur"])
            time.sleep(0.05)
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
        config=OrchestratorConfig(max_global_concurrency=2, max_provider_concurrency=2, global_timeout_ms=5000, source_timeout_ms=5000, retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )
    # 6 TRFs -> mas no máximo 2 simultâneos
    res = orch.search(SearchRequest(process_number="x", tribunals=["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"]))
    assert ativos["max"] <= 2
    assert len(res.processes) == 6
