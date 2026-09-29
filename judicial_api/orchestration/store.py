"""Persistência e histórico em memória (JUR-03).

Store simples e testável para pesquisas, resultados por fonte, processos e
eventos de auditoria (SPEC §56-69). A persistência definitiva em PostgreSQL fica
para uma fase posterior — aqui usamos um backing em memória por trás de uma
interface (``SearchStore``), preservando o contrato para trocar a implementação
sem afetar o orchestrator.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..enums import SearchEventType
from ..models import SearchRequest, SearchResult


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class SearchEvent:
    type: SearchEventType
    at: str = field(default_factory=_utc_now_iso)
    tribunal: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchRecord:
    """Registro persistido de uma pesquisa."""

    search_id: str
    correlation_id: str | None
    request_hash: str
    result: SearchResult
    request: "SearchRequest | None" = None
    events: list[SearchEvent] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)


class SearchStore(ABC):
    """Contrato de persistência de pesquisas."""

    @abstractmethod
    def save(self, record: SearchRecord) -> None: ...

    @abstractmethod
    def get(self, search_id: str) -> SearchRecord | None: ...

    @abstractmethod
    def find_by_request_hash(self, request_hash: str) -> SearchRecord | None: ...

    @abstractmethod
    def append_event(self, search_id: str, event: SearchEvent) -> None: ...


class InMemorySearchStore(SearchStore):
    """Implementação em memória (thread-safe o suficiente para o escopo atual)."""

    def __init__(self) -> None:
        self._by_id: dict[str, SearchRecord] = {}
        self._hash_to_id: dict[str, str] = {}

    def save(self, record: SearchRecord) -> None:
        record.updated_at = _utc_now_iso()
        self._by_id[record.search_id] = record
        # Mantém o mapa hash->id apontando para a pesquisa mais recente do hash.
        self._hash_to_id[record.request_hash] = record.search_id

    def get(self, search_id: str) -> SearchRecord | None:
        return self._by_id.get(search_id)

    def find_by_request_hash(self, request_hash: str) -> SearchRecord | None:
        search_id = self._hash_to_id.get(request_hash)
        return self._by_id.get(search_id) if search_id else None

    def append_event(self, search_id: str, event: SearchEvent) -> None:
        record = self._by_id.get(search_id)
        if record is not None:
            record.events.append(event)
            record.updated_at = _utc_now_iso()
