"""Métricas em memória da Judicial API (JUR-05, SPEC §72).

Coletor leve e thread-safe, sem dependências externas (sem Prometheus). Expõe as
métricas mínimas exigidas pela SPEC §72 e um snapshot serializável para o endpoint
``/metrics``. O objetivo é observabilidade básica embutida; a exportação para um
backend real (Prometheus/OTel) pode ser adicionada depois sem quebrar o contrato.

Categorias:
- contadores monotônicos (searches_total, retries_total, ...);
- observações de latência por provider (contagem + soma, p/ média).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .enums import SearchStatus, SourceStatus


@dataclass
class _LatencyAccumulator:
    count: int = 0
    total_ms: float = 0.0

    def observe(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += max(0.0, duration_ms)

    @property
    def avg_ms(self) -> float:
        return (self.total_ms / self.count) if self.count else 0.0


class Metrics:
    """Registro de métricas em memória (thread-safe)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {
            "searches_total": 0,
            "searches_completed": 0,
            "searches_empty": 0,
            "searches_partial": 0,
            "searches_failed": 0,
            "provider_errors": 0,
            "provider_timeouts": 0,
            "processes_found": 0,
            "signals_found": 0,
            "retries_total": 0,
            "unsupported_queries": 0,
        }
        # Latência por provider (nome -> acumulador).
        self._provider_latency: dict[str, _LatencyAccumulator] = {}

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------
    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            if name in self._counters:
                self._counters[name] += amount

    def observe_provider_latency(self, provider: str, duration_ms: float) -> None:
        with self._lock:
            acc = self._provider_latency.setdefault(provider, _LatencyAccumulator())
            acc.observe(duration_ms)

    def record_search(self, result) -> None:
        """Contabiliza um SearchResult concluído (agregado + fontes + sinais)."""
        with self._lock:
            self._counters["searches_total"] += 1
            status = getattr(result, "status", None)
            if status == SearchStatus.COMPLETED:
                self._counters["searches_completed"] += 1
            elif status == SearchStatus.EMPTY:
                self._counters["searches_empty"] += 1
            elif status == SearchStatus.PARTIAL:
                self._counters["searches_partial"] += 1
            elif status == SearchStatus.FAILED:
                self._counters["searches_failed"] += 1

            self._counters["processes_found"] += len(getattr(result, "processes", []) or [])
            self._counters["signals_found"] += len(getattr(result, "signals", []) or [])

            for source in getattr(result, "sources", []) or []:
                if source.status == SourceStatus.TIMEOUT:
                    self._counters["provider_timeouts"] += 1
                elif source.status == SourceStatus.ERROR:
                    self._counters["provider_errors"] += 1
                elif source.status == SourceStatus.UNSUPPORTED:
                    self._counters["unsupported_queries"] += 1
                if source.attempts and source.attempts > 1:
                    self._counters["retries_total"] += source.attempts - 1
                if source.duration_ms is not None:
                    acc = self._provider_latency.setdefault(source.provider, _LatencyAccumulator())
                    acc.observe(source.duration_ms)

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            counters = dict(self._counters)
            latency = {
                provider: {"count": acc.count, "avg_ms": round(acc.avg_ms, 2)}
                for provider, acc in self._provider_latency.items()
            }
        return {"counters": counters, "provider_latency": latency}

    def reset(self) -> None:
        with self._lock:
            for k in self._counters:
                self._counters[k] = 0
            self._provider_latency.clear()


# Instância padrão do processo. Injetável nos testes via reset()/nova instância.
_METRICS = Metrics()


def get_metrics() -> Metrics:
    return _METRICS
