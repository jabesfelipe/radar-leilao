"""Search Orchestrator multi-fonte (JUR-03).

Transforma a consulta individual (JUR-02) numa pesquisa robusta:
- seleciona as fontes aplicáveis (selection.select_sources);
- executa em paralelo (com concorrência limitada) ou sequencial (execution_mode);
- aplica retry (só transitórios) e faz valer o timeout por fonte e o prazo global;
- isola falhas: uma fonte com erro/timeout não derruba as demais;
- normaliza e deduplica os processos (chave provider+tribunal+numeroProcesso);
- calcula o status agregado COMPLETED/EMPTY/PARTIAL/FAILED (EMPTY != PARTIAL);
- registra resultado por fonte, eventos e persiste;
- coalescê pesquisas concorrentes idênticas (idempotência operacional);
- permite reanálise reprocessando SOMENTE as fontes com falha recuperável.

Determinístico para testes: relógio (``clock``), ``sleep`` e ``jitter`` são
injetáveis; providers são injetados. Nenhuma chamada real de rede aqui.

Semântica de idempotência (documentada): duas pesquisas com os MESMOS critérios
(request_hash igual) que chegam CONCORRENTEMENTE são coalescidas — a segunda não
dispara execução nova, aguarda e recebe o mesmo resultado. Pesquisas idênticas
feitas em MOMENTOS DIFERENTES NÃO são deduplicadas automaticamente: os dados das
fontes podem ter mudado, então uma nova pesquisa reexecuta e gera novo search_id.
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Callable

from ..catalog.loader import CatalogEntry, JudicialCatalog, default_catalog
from ..enums import ErrorCode, ExecutionMode, SearchEventType, SearchStatus, SourceStatus
from ..errors import JudicialError
from ..models import (
    Completeness,
    Process,
    ReanalyzeHint,
    SearchRequest,
    SearchResult,
    SourceError,
    SourceResult,
)
from ..registry.base import ProviderRegistry
from .resilience import RetryPolicy, run_with_retry
from .selection import compute_request_hash, select_sources
from .store import InMemorySearchStore, SearchEvent, SearchRecord, SearchStore

# Status por fonte que NÃO exigem reprocessamento (a fonte respondeu com sucesso).
_SUCCESS_STATUSES = {SourceStatus.SUCCESS, SourceStatus.EMPTY}
# Status por fonte que são falhas recuperáveis (reprocessáveis na reanálise).
_RETRYABLE_SOURCE_STATUSES = {SourceStatus.TIMEOUT, SourceStatus.UNAVAILABLE, SourceStatus.ERROR}


@dataclass(frozen=True)
class OrchestratorConfig:
    # Concorrência / rate limiting (SPEC §13). São controles de TAXA/paralelismo,
    # distintos do retry de HTTP 429 (que é resiliência a erro transitório).
    max_global_concurrency: int = 20
    max_provider_concurrency: int = 20
    max_tribunal_concurrency: int = 1
    source_timeout_ms: int = 8000
    global_timeout_ms: int = 60000
    retry: RetryPolicy = RetryPolicy()


def _error_to_source_status(code: ErrorCode) -> SourceStatus:
    if code == ErrorCode.PROVIDER_TIMEOUT:
        return SourceStatus.TIMEOUT
    if code in (ErrorCode.PROVIDER_UNAVAILABLE, ErrorCode.RATE_LIMITED):
        return SourceStatus.UNAVAILABLE
    if code == ErrorCode.UNSUPPORTED_SEARCH_CRITERIA:
        return SourceStatus.UNSUPPORTED
    return SourceStatus.ERROR


@dataclass
class _SourceTiming:
    """Instantes reais de execução de uma fonte, compartilhados entre o worker e
    o coletor. Permite decidir SUCCESS/TIMEOUT pelo instante de conclusão, não
    apenas por ``future.done()``.

    - ``started_at``: quando a fonte REALMENTE começou a executar (None enquanto
      enfileirada). O timeout individual é contado a partir daqui.
    - ``finished_at``: quando a execução terminou (None se ainda não terminou).
    """

    started_at: float | None = None
    finished_at: float | None = None
    # True quando o worker abortou ANTES de chamar o provider por o prazo global já
    # ter expirado (a fonte não chegou a executar / não emitiu SOURCE_STARTED).
    skipped_global_timeout: bool = False


@dataclass
class _SourceOutcome:
    result: SourceResult
    processes: list[Process]
    retried: bool = False


@dataclass
class _InFlight:
    """Controle de coalescência: pesquisa em andamento para um request_hash."""

    done: threading.Event = field(default_factory=threading.Event)
    result: SearchResult | None = None


class SearchOrchestrator:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        catalog: JudicialCatalog | None = None,
        store: SearchStore | None = None,
        config: OrchestratorConfig | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = lambda: 0.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._providers = provider_registry
        self._catalog = catalog or default_catalog()
        self._store = store or InMemorySearchStore()
        self._config = config or OrchestratorConfig()
        self._sleep = sleep
        self._jitter = jitter
        self._clock = clock
        # Registro de pesquisas em andamento por request_hash (idempotência op.).
        self._inflight: dict[str, _InFlight] = {}
        self._inflight_lock = threading.Lock()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def search(self, request: SearchRequest, *, correlation_id: str | None = None) -> SearchResult:
        # execution_mode: aceitamos apenas os modos implementados; valores não
        # suportados são rejeitados explicitamente (não são ignorados em silêncio).
        if request.execution_mode not in (ExecutionMode.PARALLEL, ExecutionMode.SEQUENTIAL):
            raise JudicialError(
                ErrorCode.BAD_REQUEST,
                f"execution_mode não suportado: {request.execution_mode}.",
                http_status=400,
                retryable=False,
            )

        request_hash = compute_request_hash(request)

        # Idempotência operacional: coalesce pesquisas idênticas CONCORRENTES.
        leader, inflight = self._acquire_inflight(request_hash)
        if not leader:
            # Outro chamador idêntico já está executando: aguarda e reusa.
            inflight.done.wait()
            if inflight.result is not None:
                return inflight.result
            # Se por algum motivo não houve resultado, cai para execução própria.

        try:
            result = self._execute(request, request_hash, correlation_id)
            inflight.result = result
            return result
        finally:
            self._release_inflight(request_hash, inflight)

    def get(self, search_id: str) -> SearchResult | None:
        record = self._store.get(search_id)
        return record.result if record else None

    def retry_failed(self, search_id: str) -> SearchResult | None:
        """Reprocessa SOMENTE as fontes com falha recuperável (SPEC §20-21).

        Fontes concluídas (SUCCESS/EMPTY) e não recuperáveis (UNSUPPORTED e erros
        definitivos como AUTH/CONFIG/BAD_REQUEST) não são reconsultadas.
        """
        record = self._store.get(search_id)
        if record is None:
            return None
        self._event(search_id, SearchEventType.REANALYSIS_REQUESTED)

        result = record.result
        failed_codes = [s.tribunal for s in result.sources if self._is_source_reprocessable(s)]
        entries = [e for e in (self._catalog.get(code) for code in failed_codes) if e is not None]
        if not entries:
            return result
        request = record.request
        if request is None:
            return result

        outcomes = self._run_sources(request, entries, search_id)
        by_tribunal = {o.result.tribunal: o for o in outcomes}
        merged_sources: list[SourceResult] = []
        for source in result.sources:
            merged_sources.append(by_tribunal[source.tribunal].result if source.tribunal in by_tribunal else source)
        merged_processes = list(result.processes)
        for outcome in outcomes:
            merged_processes.extend(outcome.processes)

        result.sources = merged_sources
        result.processes = self._dedupe(merged_processes)
        self._recompute_aggregate(result)
        self._store.save(record)
        self._event(search_id, SearchEventType.SEARCH_COMPLETED, detail={"status": result.status.value, "reanalysis": True})
        return result

    # ------------------------------------------------------------------
    # Idempotência operacional (coalescência de concorrentes)
    # ------------------------------------------------------------------
    def _acquire_inflight(self, request_hash: str) -> tuple[bool, _InFlight]:
        with self._inflight_lock:
            existing = self._inflight.get(request_hash)
            if existing is not None:
                return False, existing
            created = _InFlight()
            self._inflight[request_hash] = created
            return True, created

    def _release_inflight(self, request_hash: str, inflight: _InFlight) -> None:
        with self._inflight_lock:
            # Só o líder remove o próprio registro.
            if self._inflight.get(request_hash) is inflight:
                del self._inflight[request_hash]
        inflight.done.set()

    # ------------------------------------------------------------------
    # Execução de uma pesquisa
    # ------------------------------------------------------------------
    def _execute(self, request: SearchRequest, request_hash: str, correlation_id: str | None) -> SearchResult:
        search_id = str(uuid.uuid4())
        sources = select_sources(request, self._catalog)

        result = SearchResult(search_id=search_id, status=SearchStatus.PENDING)
        record = SearchRecord(
            search_id=search_id, correlation_id=correlation_id, request_hash=request_hash,
            result=result, request=request,
        )
        self._store.save(record)
        self._event(search_id, SearchEventType.SEARCH_CREATED, detail={"request_hash": request_hash, "sources": len(sources), "mode": request.execution_mode.value})
        for entry in sources:
            self._event(search_id, SearchEventType.SOURCE_SELECTED, tribunal=entry.code)

        outcomes = self._run_sources(request, sources, search_id, mode=request.execution_mode)
        self._assemble(result, outcomes)
        self._store.save(record)
        self._event(search_id, SearchEventType.SEARCH_COMPLETED, detail={"status": result.status.value})
        return result

    # ------------------------------------------------------------------
    # Execução das fontes: paralela ou sequencial, com timeout efetivo
    # ------------------------------------------------------------------
    def _run_sources(
        self,
        request: SearchRequest,
        sources: list[CatalogEntry],
        search_id: str,
        *,
        mode: ExecutionMode = ExecutionMode.PARALLEL,
    ) -> list[_SourceOutcome]:
        if not sources:
            return []
        # PARALLEL e SEQUENTIAL usam a MESMA estratégia segura (thread pool): a
        # diferença é apenas a concorrência (SEQUENTIAL => 1 worker). Isso garante
        # que uma fonte bloqueada nunca execute de forma síncrona travando o retorno.
        workers = 1 if mode == ExecutionMode.SEQUENTIAL else self._effective_workers(len(sources))
        return self._run_pool(request, sources, search_id, workers)

    def _effective_workers(self, n_sources: int) -> int:
        # Concorrência efetiva respeita global e provider (tribunal=1 é inerente:
        # há no máximo uma tarefa por tribunal). Nunca menos que 1.
        limit = min(self._config.max_global_concurrency, self._config.max_provider_concurrency)
        return max(1, min(limit, n_sources))

    def _run_pool(self, request, sources, search_id, workers) -> list[_SourceOutcome]:
        """Executa as fontes em um pool com timeout individual E prazo global.

        Pontos-chave da correção de prazos:
        - o timeout individual de cada fonte é contado a partir do INÍCIO REAL da
          execução (timing.started_at + source_timeout). Enquanto a fonte está
          ENFILEIRADA (ainda não começou), ela consome apenas o prazo global, não o
          timeout individual — importante no modo SEQUENTIAL (workers=1);
        - a aceitação de um resultado usa o INSTANTE DE CONCLUSÃO (timing.finished_at),
          não apenas future.done(): um resultado que só ficou pronto DEPOIS do
          deadline individual ou do prazo global é rejeitado e marcado TIMEOUT;
        - uma fonte lenta NÃO posterga o timeout das demais nem lhes concede novo
          orçamento; resultados concluídos dentro dos prazos são preservados;
        - ao final, o pool é desligado sem esperar threads bloqueadas
          (shutdown(wait=False, cancel_futures=True)); Python não permite matar a
          thread, então a chamada travada só termina pelo timeout do transporte HTTP.
        """
        per_source = self._config.source_timeout_ms / 1000.0
        global_deadline = self._clock() + self._config.global_timeout_ms / 1000.0

        pool = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="judicial-src")
        # Preserva a ordem das fontes no resultado (índice -> outcome).
        outcomes: list[_SourceOutcome | None] = [None] * len(sources)
        # Cada fonte pendente carrega sua timing (início/fim reais), o índice e a entry.
        pending: dict[Future, tuple[int, CatalogEntry, _SourceTiming]] = {}
        try:
            for idx, entry in enumerate(sources):
                # NÃO emitimos SOURCE_STARTED aqui (submissão != início real). O
                # evento é emitido dentro do worker, quando a fonte efetivamente
                # começa a executar. Passamos o prazo global para o worker abortar
                # antes de chamar o provider caso ele já tenha expirado.
                timing = _SourceTiming()
                future = pool.submit(self._run_one_source, request, entry, search_id, timing, global_deadline)
                pending[future] = (idx, entry, timing)

            def _individual_deadline(timing: _SourceTiming) -> float | None:
                # Só existe quando a fonte REALMENTE começou (saiu da fila). Enquanto
                # enfileirada, não há deadline individual — só o prazo global corre.
                return None if timing.started_at is None else timing.started_at + per_source

            def _mark_timeout(idx, entry, fut, reason=None):
                fut.cancel()
                outcomes[idx] = self._timeout_outcome(entry)
                detail = {"status": SourceStatus.TIMEOUT.value}
                if reason:
                    detail["reason"] = reason
                self._event(search_id, SearchEventType.SOURCE_FAILED, tribunal=entry.code, detail=detail)

            while pending:
                now = self._clock()
                global_expired = now >= global_deadline

                # 1) Colhe fontes concluídas, decidindo pelo INSTANTE DE CONCLUSÃO
                #    (não só por future.done()): um resultado tardio (após o deadline
                #    individual ou o global) é rejeitado e marcado TIMEOUT.
                harvested = False
                for fut in list(pending.keys()):
                    if not fut.done():
                        continue
                    idx, entry, timing = pending.pop(fut)
                    harvested = True
                    if timing.skipped_global_timeout:
                        # O worker abortou antes de chamar o provider (prazo global
                        # já expirado). Não houve SOURCE_STARTED; registra GLOBAL_TIMEOUT.
                        outcomes[idx] = fut.result()
                        self._event(search_id, SearchEventType.SOURCE_FAILED, tribunal=entry.code, detail={"status": SourceStatus.TIMEOUT.value, "reason": "GLOBAL_TIMEOUT"})
                        continue
                    ind = _individual_deadline(timing)
                    finished_at = timing.finished_at
                    late_individual = ind is not None and finished_at is not None and finished_at > ind
                    late_global = finished_at is not None and finished_at > global_deadline
                    if late_individual or late_global:
                        # Concluiu, mas fora do orçamento: não aceita como sucesso.
                        outcomes[idx] = self._timeout_outcome(entry)
                        self._event(search_id, SearchEventType.SOURCE_FAILED, tribunal=entry.code, detail={"status": SourceStatus.TIMEOUT.value, "reason": "GLOBAL_TIMEOUT" if late_global else "SOURCE_TIMEOUT"})
                    else:
                        outcomes[idx] = fut.result()
                if harvested:
                    continue

                # 2) Prazo global estourou: fontes ainda pendentes (rodando ou na
                #    fila) viram TIMEOUT. Threads que já rodam são abandonadas.
                if global_expired:
                    for fut, (idx, entry, _t) in list(pending.items()):
                        _mark_timeout(idx, entry, fut, reason="GLOBAL_TIMEOUT")
                    pending.clear()
                    break

                # 3) Fontes que já iniciaram e estouraram o deadline individual.
                expiradas = [
                    fut for fut, (_i, _e, timing) in pending.items()
                    if (d := _individual_deadline(timing)) is not None and now >= d and not fut.done()
                ]
                for fut in expiradas:
                    idx, entry, _t = pending.pop(fut)
                    _mark_timeout(idx, entry, fut, reason="SOURCE_TIMEOUT")
                if expiradas:
                    continue

                # 4) Calcula o próximo instante relevante: menor entre os deadlines
                #    individuais das fontes JÁ INICIADAS e o prazo global. Fontes
                #    enfileiradas (sem início) só respondem ao prazo global.
                proximos = [d for (_i, _e, timing) in pending.values() if (d := _individual_deadline(timing)) is not None]
                wait_until = min([global_deadline, *proximos]) if proximos else global_deadline
                timeout = max(0.0, wait_until - now)
                if timeout <= 0:
                    # Já há algo a colher/expirar: reavalia imediatamente.
                    continue
                try:
                    # Acorda quando QUALQUER Future concluir, ou quando a janela expirar.
                    next(as_completed(list(pending.keys()), timeout=timeout))
                except FutureTimeout:
                    pass
                # Volta ao topo para reavaliar conclusões/deadlines com o relógio atual.
        finally:
            # Não espera threads travadas; descarta as que ainda não iniciaram.
            pool.shutdown(wait=False, cancel_futures=True)

        # Garante que nenhum slot ficou vazio (defensivo).
        for idx, entry in enumerate(sources):
            if outcomes[idx] is None:
                outcomes[idx] = self._timeout_outcome(entry)
        return [o for o in outcomes if o is not None]

    def _run_one_source(self, request: SearchRequest, entry: CatalogEntry, search_id: str, timing: _SourceTiming | None = None, global_deadline: float | None = None) -> _SourceOutcome:
        provider = self._providers.provider_for_tribunal(entry.code)
        # Verificação de prazo global DENTRO do worker, imediatamente antes de
        # iniciar a consulta: se o worker só foi escalonado após o prazo global
        # (fonte que esperou na fila), NÃO chama o provider. Trata a corrida entre a
        # liberação da thread e o encerramento do prazo global.
        if global_deadline is not None and self._clock() >= global_deadline:
            if timing is not None:
                timing.skipped_global_timeout = True
            return self._timeout_outcome(entry)

        started = self._clock()
        if timing is not None:
            # Marca o INÍCIO REAL da execução (a fonte saiu da fila e começou).
            timing.started_at = started
        # SOURCE_STARTED só quando a fonte EFETIVAMENTE começa a executar.
        self._event(search_id, SearchEventType.SOURCE_STARTED, tribunal=entry.code)
        attempts_box = {"n": 0, "retried": False}

        def _call() -> list[Process]:
            attempts_box["n"] += 1
            if provider is None:
                raise JudicialError(ErrorCode.CONFIGURATION_ERROR, "Sem provider para a fonte.", http_status=500, tribunal=entry.code)
            return provider.search(request, entry.code)

        def _on_retry(attempt: int, exc: BaseException) -> None:
            attempts_box["retried"] = True
            self._event(search_id, SearchEventType.SOURCE_RETRY, tribunal=entry.code, detail={"attempt": attempt})

        try:
            processes = run_with_retry(
                _call, self._config.retry, sleep=self._sleep, jitter=self._jitter, on_retry=_on_retry,
            )
        except JudicialError as exc:
            finished = self._clock()
            if timing is not None:
                timing.finished_at = finished
            duration = int((finished - started) * 1000)
            status = _error_to_source_status(exc.code)
            self._event(search_id, SearchEventType.SOURCE_FAILED, tribunal=entry.code, detail={"status": status.value, "code": exc.code.value})
            return _SourceOutcome(
                result=SourceResult(
                    provider=exc.provider or (provider.code if provider else "DATAJUD"),
                    tribunal=entry.code,
                    justice_type=entry.justice_type,
                    status=status,
                    duration_ms=duration,
                    attempts=attempts_box["n"],
                    error=SourceError(code=exc.code.value, retryable=exc.retryable, message=exc.message),
                ),
                processes=[],
                retried=attempts_box["retried"],
            )

        finished = self._clock()
        if timing is not None:
            timing.finished_at = finished
        duration = int((finished - started) * 1000)
        status = SourceStatus.SUCCESS if processes else SourceStatus.EMPTY
        self._event(search_id, SearchEventType.SOURCE_SUCCESS, tribunal=entry.code, detail={"count": len(processes)})
        return _SourceOutcome(
            result=SourceResult(
                provider=provider.code if provider else "DATAJUD",
                tribunal=entry.code,
                justice_type=entry.justice_type,
                status=status,
                http_status=200,
                duration_ms=duration,
                result_count=len(processes),
                attempts=attempts_box["n"],
            ),
            processes=processes,
            retried=attempts_box["retried"],
        )

    def _timeout_outcome(self, entry: CatalogEntry) -> _SourceOutcome:
        return _SourceOutcome(
            result=SourceResult(
                provider="DATAJUD",
                tribunal=entry.code,
                justice_type=entry.justice_type,
                status=SourceStatus.TIMEOUT,
                duration_ms=self._config.source_timeout_ms,
                error=SourceError(code=ErrorCode.PROVIDER_TIMEOUT.value, retryable=True, message="Timeout ao consultar a fonte."),
            ),
            processes=[],
        )

    # ------------------------------------------------------------------
    # Montagem do resultado / status agregado / dedup
    # ------------------------------------------------------------------
    @staticmethod
    def _is_source_reprocessable(source: SourceResult) -> bool:
        # Recuperável por status E respeitando o flag do erro (não reprocessa o que
        # foi marcado explicitamente como não recuperável).
        if source.status not in _RETRYABLE_SOURCE_STATUSES:
            return False
        if source.error is not None and source.error.retryable is False:
            return False
        return True

    def _assemble(self, result: SearchResult, outcomes: list[_SourceOutcome]) -> None:
        result.sources = [o.result for o in outcomes]
        processes: list[Process] = []
        for o in outcomes:
            processes.extend(o.processes)
        result.processes = self._dedupe(processes)
        self._recompute_aggregate(result)

    @staticmethod
    def _dedupe(processes: list[Process]) -> list[Process]:
        # Chave lógica: provider(fixo DataJud) + tribunal + numeroProcesso (SPEC §33).
        seen: set[tuple[str, str]] = set()
        unique: list[Process] = []
        for p in processes:
            key = (p.tribunal, p.process_number)
            if key in seen:
                continue
            seen.add(key)
            unique.append(p)
        return unique

    def _recompute_aggregate(self, result: SearchResult) -> None:
        sources = result.sources
        total = len(sources)
        successful = sum(1 for s in sources if s.status in _SUCCESS_STATUSES)
        unsupported = sum(1 for s in sources if s.status == SourceStatus.UNSUPPORTED)
        failed = sum(1 for s in sources if s.status in _RETRYABLE_SOURCE_STATUSES)

        result.completeness = Completeness(
            requested_sources=total,
            successful_sources=successful,
            failed_sources=failed,
            unsupported_sources=unsupported,
        )

        if total == 0:
            result.status = SearchStatus.EMPTY
        elif failed == total:
            result.status = SearchStatus.FAILED
        elif failed > 0 or unsupported > 0:
            result.status = SearchStatus.PARTIAL
        elif result.processes:
            result.status = SearchStatus.COMPLETED
        else:
            result.status = SearchStatus.EMPTY

        affected = [s.tribunal for s in sources if self._is_source_reprocessable(s)]
        result.reanalyze = ReanalyzeHint(
            recommended=bool(affected),
            reason="TRIBUNAL_UNAVAILABLE" if affected else None,
            sources_affected=affected,
        )

    def _event(self, search_id: str, event_type: SearchEventType, *, tribunal: str | None = None, detail: dict | None = None) -> None:
        self._store.append_event(search_id, SearchEvent(type=event_type, tribunal=tribunal, detail=detail or {}))
