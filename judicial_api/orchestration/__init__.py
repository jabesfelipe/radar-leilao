"""Orquestração da Judicial API (JUR-03).

Reúne a resiliência (retry/backoff/timeout), a seleção de fontes, a persistência
em memória e o Search Orchestrator multi-fonte.
"""

from .resilience import BackoffPolicy, RetryPolicy, compute_backoff, run_with_retry
from .selection import compute_request_hash, select_sources
from .store import InMemorySearchStore, SearchRecord, SearchStore
from .orchestrator import SearchOrchestrator

__all__ = [
    "BackoffPolicy",
    "RetryPolicy",
    "compute_backoff",
    "run_with_retry",
    "compute_request_hash",
    "select_sources",
    "InMemorySearchStore",
    "SearchRecord",
    "SearchStore",
    "SearchOrchestrator",
]
