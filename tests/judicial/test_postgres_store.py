"""TASK FINAL — testes de persistência PostgreSQL do PostgresSearchStore.

Exigem PostgreSQL (RAG_TEST_DATABASE_URL); pulam quando indisponível. Cobrem:
- save/get round-trip fiel do SearchResult (fontes, processos+filhos, sinais);
- idempotência: save repetido não duplica fontes/processos/sinais;
- retry: reprocessar uma fonte falha atualiza-a no lugar, sem duplicar;
- eventos anexados incrementalmente (append_event) e via save;
- sobrevivência a "restart": um novo store lê o que outro gravou;
- find_by_request_hash.
"""
from __future__ import annotations

import uuid

import pytest

from judicial_api.enums import (
    JusticeType,
    SearchEventType,
    SearchStatus,
    SignalCategory,
    SignalEvidenceType,
    SignalSeverity,
    SourceStatus,
)
from judicial_api.models import (
    Movement,
    Party,
    Process,
    SearchRequest,
    SearchResult,
    Signal,
    SourceError,
    SourceResult,
    Subject,
)
from judicial_api.orchestration.store import SearchEvent, SearchRecord


def _new_id(pg_store) -> str:
    sid = f"test-{uuid.uuid4()}"
    pg_store._created_ids.append(sid)
    return sid


def _process(number="0001", tribunal="TJPR"):
    return Process(
        process_number=number,
        tribunal=tribunal,
        justice_type=JusticeType.STATE,
        court="1ª Vara",
        class_name="Execução",
        subjects=[Subject(code="123", name="Penhora")],
        parties=[Party(name="JOÃO DA SILVA", document="12345678900", document_type="CPF", role="DEFENDANT")],
        movements=[Movement(movement_date="2026-01-10", description="Penhora efetivada")],
    )


def _signal():
    return Signal(
        signal_code="PENHORA",
        category=SignalCategory.PATRIMONIAL,
        severity=SignalSeverity.HIGH,
        confidence=0.85,
        evidence_text="Evidência de penhora",
        evidence_type=SignalEvidenceType.MOVEMENT,
        process_number="0001",
        tribunal="TJPR",
    )


def _source(status=SourceStatus.SUCCESS, attempts=1, result_count=1):
    return SourceResult(
        provider="DATAJUD", tribunal="TJPR", justice_type=JusticeType.STATE,
        status=status, http_status=200, duration_ms=100, pages=1,
        result_count=result_count, attempts=attempts,
    )


def _record(search_id, *, status=SearchStatus.COMPLETED, sources=None, processes=None, signals=None, events=None):
    result = SearchResult(
        search_id=search_id,
        status=status,
        sources=sources if sources is not None else [_source()],
        processes=processes if processes is not None else [_process()],
        signals=signals if signals is not None else [_signal()],
    )
    return SearchRecord(
        search_id=search_id,
        correlation_id="corr-1",
        request_hash=f"hash-{search_id}",
        result=result,
        request=SearchRequest(process_number="0001", tribunals=["TJPR"]),
        events=events or [],
    )


def test_save_and_get_roundtrip(pg_store):
    sid = _new_id(pg_store)
    pg_store.save(_record(sid))

    got = pg_store.get(sid)
    assert got is not None
    assert got.search_id == sid
    assert got.result.status == SearchStatus.COMPLETED
    assert len(got.result.sources) == 1
    assert len(got.result.processes) == 1
    proc = got.result.processes[0]
    assert proc.process_number == "0001"
    assert proc.parties[0].name == "JOÃO DA SILVA"
    assert proc.subjects[0].name == "Penhora"
    assert proc.movements[0].description == "Penhora efetivada"
    assert {s.signal_code for s in got.result.signals} == {"PENHORA"}


def test_get_inexistente_retorna_none(pg_store):
    assert pg_store.get(f"nao-existe-{uuid.uuid4()}") is None


def test_save_idempotente_nao_duplica(pg_store):
    sid = _new_id(pg_store)
    record = _record(sid)
    pg_store.save(record)
    pg_store.save(record)  # segundo save do MESMO estado
    pg_store.save(record)  # terceiro

    got = pg_store.get(sid)
    assert len(got.result.sources) == 1
    assert len(got.result.processes) == 1
    assert len(got.result.signals) == 1
    # filhos do processo não duplicam
    assert len(got.result.processes[0].parties) == 1
    assert len(got.result.processes[0].movements) == 1


def test_retry_atualiza_fonte_no_lugar(pg_store):
    sid = _new_id(pg_store)
    # 1ª gravação: fonte em TIMEOUT, sem processos.
    rec = _record(sid, status=SearchStatus.PARTIAL,
                  sources=[_source(status=SourceStatus.TIMEOUT, attempts=1, result_count=0)],
                  processes=[], signals=[])
    pg_store.save(rec)

    # Retry: a MESMA fonte agora teve SUCCESS com um processo (mais tentativas).
    rec.result.status = SearchStatus.COMPLETED
    rec.result.sources = [_source(status=SourceStatus.SUCCESS, attempts=2, result_count=1)]
    rec.result.processes = [_process()]
    rec.result.signals = [_signal()]
    pg_store.save(rec)

    got = pg_store.get(sid)
    assert len(got.result.sources) == 1  # não duplicou a fonte
    assert got.result.sources[0].status == SourceStatus.SUCCESS
    assert got.result.sources[0].attempts == 2
    assert got.result.status == SearchStatus.COMPLETED
    assert len(got.result.processes) == 1


def test_eventos_anexados_incrementalmente(pg_store):
    sid = _new_id(pg_store)
    rec = _record(sid, events=[SearchEvent(type=SearchEventType.SEARCH_CREATED)])
    pg_store.save(rec)
    # append_event adiciona sem reescrever os já persistidos.
    pg_store.append_event(sid, SearchEvent(type=SearchEventType.SEARCH_COMPLETED, tribunal="TJPR"))

    got = pg_store.get(sid)
    tipos = [e.type for e in got.events]
    assert SearchEventType.SEARCH_CREATED in tipos
    assert SearchEventType.SEARCH_COMPLETED in tipos


def test_save_repetido_nao_duplica_eventos(pg_store):
    sid = _new_id(pg_store)
    rec = _record(sid, events=[SearchEvent(type=SearchEventType.SEARCH_CREATED)])
    pg_store.save(rec)
    pg_store.save(rec)  # mesmo record, mesmos eventos

    got = pg_store.get(sid)
    assert [e.type for e in got.events].count(SearchEventType.SEARCH_CREATED) == 1


def test_sobrevive_a_restart_novo_store_le_o_gravado(pg_store, judicial_engine):
    from sqlalchemy.orm import sessionmaker

    from judicial_api.persistence.postgres_store import PostgresSearchStore

    sid = _new_id(pg_store)
    pg_store.save(_record(sid))

    # Simula reinício: uma instância NOVA de store (novo sessionmaker) lê o dado.
    factory = sessionmaker(bind=judicial_engine, autoflush=False, autocommit=False, future=True)
    novo_store = PostgresSearchStore(session_factory=factory)
    got = novo_store.get(sid)
    assert got is not None
    assert got.result.processes[0].process_number == "0001"


def test_find_by_request_hash(pg_store):
    sid = _new_id(pg_store)
    rec = _record(sid)
    pg_store.save(rec)
    found = pg_store.find_by_request_hash(rec.request_hash)
    assert found is not None
    assert found.search_id == sid
