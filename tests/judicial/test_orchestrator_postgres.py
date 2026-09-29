"""TASK FINAL — orchestrator sobre PostgresSearchStore (persistência real).

Exercita o fluxo do SearchOrchestrator persistindo no PostgreSQL, incluindo
reanálise (retry_failed) sem duplicação. Pula sem PostgreSQL.
"""
from __future__ import annotations

import uuid

import pytest

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ErrorCode, SearchStatus, SourceStatus
from judicial_api.errors import JudicialError
from judicial_api.models import JusticeType, Movement, Process, SearchRequest
from judicial_api.orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
from judicial_api.orchestration.resilience import RetryPolicy
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry


class _Provider(JudicialProvider):
    code = "DATAJUD"

    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = {}

    def search(self, request, tribunal):
        self.calls[tribunal] = self.calls.get(tribunal, 0) + 1
        kind, payload = self.behavior.get(tribunal, ("empty", []))
        if kind == "ok":
            return list(payload)
        if kind == "raise_then_ok":
            n, procs = payload
            if self.calls[tribunal] <= n:
                raise JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504, tribunal=tribunal)
            return list(procs)
        return []

    def get_capabilities(self, tribunal):  # pragma: no cover
        raise NotImplementedError

    def health_check(self):  # pragma: no cover
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


class _Registry(ProviderRegistry):
    def __init__(self, p):
        self._p = p

    def get_provider(self, code):
        return self._p if code == self._p.code else None

    def provider_for_tribunal(self, tribunal_code):
        return self._p

    def list_providers(self):
        return [self._p]


def _orch(behavior, store):
    return SearchOrchestrator(
        _Registry(_Provider(behavior)),
        catalog=default_catalog(),
        store=store,
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )


def test_pesquisa_persistida_no_postgres(pg_store):
    proc = Process(process_number=f"P{uuid.uuid4().hex[:8]}", tribunal="TJPR", justice_type=JusticeType.STATE,
                   movements=[Movement(description="penhora efetivada")])
    orch = _orch({"TJPR": ("ok", [proc])}, pg_store)
    res = orch.search(SearchRequest(process_number=proc.process_number, tribunals=["TJPR"]))
    pg_store._created_ids.append(res.search_id)

    # Recupera do banco (novo get) — resultado durável.
    got = pg_store.get(res.search_id)
    assert got is not None
    assert got.result.status in (SearchStatus.COMPLETED, SearchStatus.EMPTY, SearchStatus.PARTIAL)
    assert any(p.process_number == proc.process_number for p in got.result.processes)
    # sinais persistidos
    assert any(s.signal_code == "PENHORA" for s in got.result.signals)


def test_retry_failed_no_postgres_sem_duplicar(pg_store):
    numero = f"P{uuid.uuid4().hex[:8]}"
    proc = Process(process_number=numero, tribunal="TJPR", justice_type=JusticeType.STATE)
    # TJPR falha na 1ª tentativa (timeout) e só tem sucesso no retry manual.
    orch = _orch({"TJPR": ("raise_then_ok", (1, [proc]))}, pg_store)
    res = orch.search(SearchRequest(process_number=numero, tribunals=["TJPR"]))
    pg_store._created_ids.append(res.search_id)
    assert res.status in (SearchStatus.PARTIAL, SearchStatus.FAILED)

    # Reanálise reprocessa só a fonte falha; agora responde com o processo.
    res2 = orch.retry_failed(res.search_id)
    assert res2 is not None

    got = pg_store.get(res.search_id)
    # A fonte TJPR não é duplicada após o retry (constraint + replace).
    tjpr = [s for s in got.result.sources if s.tribunal == "TJPR"]
    assert len(tjpr) == 1
    assert tjpr[0].status == SourceStatus.SUCCESS
    assert any(p.process_number == numero for p in got.result.processes)
