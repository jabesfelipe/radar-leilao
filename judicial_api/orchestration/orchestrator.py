"""Search Orchestrator multi-fonte (JUR-03).

Transforma a consulta individual (JUR-02) numa pesquisa robusta:
- seleciona as fontes aplicáveis (selection.select_sources);
- executa em paralelo com concorrência limitada (ThreadPoolExecutor);
- aplica retry (só transitórios) e timeout por fonte e timeout global;
- isola falhas: uma fonte com erro/timeout não derruba as demais;
- normaliza e deduplica os processos (chave provider+tribunal+numeroProcesso);
- calcula o status agregado COMPLETED/EMPTY/PARTIAL/FAILED (EMPTY != PARTIAL);
- registra resultado por fonte, eventos e persiste (idempotência via request_hash);
- permite reanálise reprocessando SOMENTE as fontes que falharam.

Determinístico para testes: relógio (``clock``), ``sleep`` e ``jitter`` são
injetáveis; providers são injetados. Nenhuma chamada real de rede aqui.
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Callable

from ..catalog.loader import CatalogEntry, JudicialCatalog, default_catalog
from ..enums import ErrorCode, SearchEventType, SearchStatus, SourceStatus
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
from ..providers.base import JudicialProvider
from ..registry.base import ProviderRegistry
from .resilience import RetryPolicy, run_with_retry
from .selection import compute_request_hash, select_sources
from .store import InMemorySearchStore, SearchEvent, SearchRecord, SearchStore

# Status por fonte que NÃO exigem reprocessamento (a fonte respondeu com sucesso).
_SUCCESS_STATUSES = {SourceStatus.SUCCESS, SourceStatus.EMPTY}
# Status por fonte que são falhas transitórias/indisponibilidade (reprocessáveis).
_RETRYABLE_SOURCE_STATUSES = {SourceStatus.TIMEOUT, SourceStatus.UNAVAILABLE, SourceStatus.ERROR}


@dataclass(frozen=True)
class OrchestratorConfig:
    max_global_concurrency: int = 20
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
class _SourceOutcome:
    result: SourceResult
    processes: list[Process]
    retried: bool = False


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

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def search(self, request: SearchRequest, *, correlation_id: str | None = None) -> SearchResult:
        request_hash = compute_request_hash(request)
        search_id = str(uuid.uuid4())
        sources = select_sources(request, self._catalog)

        result = SearchResult(search_id=search_id, status=SearchStatus.PENDING)
        record = SearchRecord(
            search_id=search_id, correlation_id=correlation_id, request_hash=request_hash,
            result=result, request=request,
        )
        self._store.save(record)
        self._event(search_id, SearchEventType.SEARCH_CREATED, detail={"request_hash": request_hash, "sources": len(sources)})
        for entry in sources:
            self._event(search_id, SearchEventType.SOURCE_SELECTED, tribunal=entry.code)

        outcomes = self._run_sources(request, sources, search_id)
        self._assemble(result, outcomes)
        self._store.save(record)
        self._event(search_id, SearchEventType.SEARCH_COMPLETED, detail={"status": result.status.value})
        return result

    def get(self, search_id: str) -> SearchResult | None:
        record = self._store.get(search_id)
        return record.result if record else None

    def retry_failed(self, search_id: str) -> SearchResult | None:
        """Reprocessa SOMENTE as fontes que falharam (SPEC §20-21).

        Fontes já concluídas (SUCCESS/EMPTY) e não suportadas (UNSUPPORTED) não
        são reconsultadas. Mantém idempotência: o mesmo search_id é atualizado.
        """
        record = self._store.get(search_id)
        if record is None:
            return None
        self._event(search_id, SearchEventType.REANALYSIS_REQUESTED)

        result = record.result
        failed_codes = [s.tribunal for s in result.sources if s.status in _RETRYABLE_SOURCE_STATUSES]
        entries = [e for e in (self._catalog.get(code) for code in failed_codes) if e is not None]
        if not entries:
            return result

        # A request original foi preservada no registro para permitir a reconsulta
        # exata das fontes que falharam.
        request = record.request
        if request is None:
            return result

        outcomes = self._run_sources(request, entries, search_id)
        # Mescla: substitui os SourceResult reprocessados e adiciona novos processos.
        by_tribunal = {o.result.tribunal: o for o in outcomes}
        merged_sources: list[SourceResult] = []
        for source in result.sources:
            if source.tribunal in by_tribunal:
                merged_sources.append(by_tribunal[source.tribunal].result)
            else:
                merged_sources.append(source)
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
    # Execução paralela + resiliência
    # ------------------------------------------------------------------
    def _run_sources(self, request: SearchRequest, sources: list[CatalogEntry], search_id: str) -> list[_SourceOutcome]:
        if not sources:
            return []
        workers = max(1, min(self._config.max_global_concurrency, len(sources)))
        deadline = self._clock() + self._config.global_timeout_ms / 1000.0
        outcomes: list[_SourceOutcome] = []

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map: dict[Future, CatalogEntry] = {}
            for entry in sources:
                self._event(search_id, SearchEventType.SOURCE_STARTED, tribunal=entry.code)
                future_map[pool.submit(self._run_one_source, request, entry, search_id)] = entry

            for future, entry in future_map.items():
                remaining = deadline - self._clock()
                per_source = self._config.source_timeout_ms / 1000.0
                budget = per_source if remaining <= 0 else min(per_source, remaining)
                try:
                    outcomes.append(future.result(timeout=max(0.0, budget)))
                except FutureTimeout:
                    outcomes.append(self._timeout_outcome(entry))
                    self._event(search_id, SearchEventType.SOURCE_FAILED, tribunal=entry.code, detail={"status": SourceStatus.TIMEOUT.value})
        return outcomes

    def _run_one_source(self, request: SearchRequest, entry: CatalogEntry, search_id: str) -> _SourceOutcome:
        provider = self._providers.provider_for_tribunal(entry.code)
        started = self._clock()
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
            duration = int((self._clock() - started) * 1000)
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

        duration = int((self._clock() - started) * 1000)
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
            # Nenhuma fonte respondeu com confiabilidade.
            result.status = SearchStatus.FAILED
        elif failed > 0 or unsupported > 0:
            # Ao menos uma respondeu, mas houve falhas/timeout/não suportado.
            result.status = SearchStatus.PARTIAL
        elif result.processes:
            result.status = SearchStatus.COMPLETED
        else:
            # Todas as fontes responderam corretamente e nada foi encontrado.
            result.status = SearchStatus.EMPTY

        affected = [s.tribunal for s in sources if s.status in _RETRYABLE_SOURCE_STATUSES]
        result.reanalyze = ReanalyzeHint(
            recommended=bool(affected),
            reason="TRIBUNAL_UNAVAILABLE" if affected else None,
            sources_affected=affected,
        )

    def _event(self, search_id: str, event_type: SearchEventType, *, tribunal: str | None = None, detail: dict | None = None) -> None:
        self._store.append_event(search_id, SearchEvent(type=event_type, tribunal=tribunal, detail=detail or {}))
