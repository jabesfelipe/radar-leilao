"""``PostgresSearchStore`` — persistência durável de pesquisas (TASK FINAL).

Implementa o contrato ``SearchStore`` (JUR-03) sobre o PostgreSQL compartilhado
com o Radar, substituindo o ``InMemorySearchStore`` como padrão de produção.

Garantias:
- **Durabilidade**: os resultados sobrevivem ao reinício da aplicação e são
  compartilhados por múltiplas instâncias (mesmo banco).
- **Transações**: cada operação abre uma sessão e faz commit/rollback atômico.
- **Idempotência no retry**: ``save`` faz UPSERT do agregado por ``search_id`` e
  substitui filhos (fontes/processos/sinais) pelo estado atual do ``SearchResult``,
  sem duplicar. As constraints únicas (search_id; search+tribunal;
  search+tribunal+numeroProcesso) protegem contra duplicação mesmo sob concorrência.
- **Auditoria**: eventos são anexados incrementalmente (nunca reescritos).

Traduz entre as entidades do domínio (pydantic ``SearchResult``/``SearchRequest``
e as dataclasses ``SearchRecord``/``SearchEvent``) e o ORM ``judicial_*``.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..db import get_sessionmaker
from ..enums import (
    JusticeType,
    SearchEventType,
    SearchStatus,
    SignalCategory,
    SignalEvidenceType,
    SignalSeverity,
    SourceStatus,
)
from ..models import (
    Completeness,
    Movement,
    Party,
    Process,
    ReanalyzeHint,
    SearchRequest,
    SearchResult,
    Signal,
    SourceError,
    SourceResult,
    Subject,
)
from ..orchestration.store import SearchEvent, SearchRecord, SearchStore, _utc_now_iso
from .models import (
    JudicialProcessMovementORM,
    JudicialProcessORM,
    JudicialProcessPartyORM,
    JudicialProcessSubjectORM,
    JudicialSearchEventORM,
    JudicialSearchORM,
    JudicialSearchSourceORM,
    JudicialSignalORM,
)


class PostgresSearchStore(SearchStore):
    def __init__(self, session_factory: sessionmaker | None = None) -> None:
        self._sessionmaker = session_factory or get_sessionmaker()

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._sessionmaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def save(self, record: SearchRecord) -> None:
        with self._session() as session:
            row = session.scalar(
                select(JudicialSearchORM).where(JudicialSearchORM.search_id == record.search_id)
            )
            if row is None:
                row = JudicialSearchORM(search_id=record.search_id)
                session.add(row)

            result = record.result
            row.correlation_id = record.correlation_id
            row.request_hash = record.request_hash
            row.status = result.status.value
            row.request_json = record.request.model_dump(mode="json") if record.request else None
            row.completeness_json = result.completeness.model_dump(mode="json")
            row.warnings_json = list(result.warnings)
            row.reanalyze_json = result.reanalyze.model_dump(mode="json")
            row.updated_at = _now()
            session.flush()  # garante row.id

            # Substitui filhos pelo estado atual (idempotente no retry).
            self._replace_sources(session, row, result.sources)
            self._replace_processes(session, row, result.processes)
            self._replace_signals(session, row, result.signals)
            # Eventos: anexa apenas os que ainda não foram persistidos.
            self._sync_events(session, row, record.events)

    def append_event(self, search_id: str, event: SearchEvent) -> None:
        with self._session() as session:
            row = session.scalar(
                select(JudicialSearchORM).where(JudicialSearchORM.search_id == search_id)
            )
            if row is None:
                return
            session.add(_event_to_orm(row.id, event))
            row.updated_at = _now()

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------
    def get(self, search_id: str) -> SearchRecord | None:
        with self._session() as session:
            row = session.scalar(
                select(JudicialSearchORM).where(JudicialSearchORM.search_id == search_id)
            )
            return self._to_record(row) if row else None

    def find_by_request_hash(self, request_hash: str) -> SearchRecord | None:
        with self._session() as session:
            row = session.scalars(
                select(JudicialSearchORM)
                .where(JudicialSearchORM.request_hash == request_hash)
                .order_by(JudicialSearchORM.id.desc())
            ).first()
            return self._to_record(row) if row else None

    # ------------------------------------------------------------------
    # Helpers de escrita
    # ------------------------------------------------------------------
    def _replace_sources(self, session: Session, row: JudicialSearchORM, sources: list[SourceResult]) -> None:
        for existing in list(row.sources):
            session.delete(existing)
        session.flush()
        for src in sources:
            session.add(
                JudicialSearchSourceORM(
                    search_pk=row.id,
                    provider=src.provider,
                    tribunal=src.tribunal,
                    justice_type=src.justice_type.value,
                    status=src.status.value,
                    http_status=src.http_status,
                    duration_ms=src.duration_ms,
                    pages=src.pages,
                    result_count=src.result_count,
                    attempts=src.attempts,
                    error_json=src.error.model_dump(mode="json") if src.error else None,
                )
            )

    def _replace_processes(self, session: Session, row: JudicialSearchORM, processes: list[Process]) -> None:
        for existing in list(row.processes):
            session.delete(existing)
        session.flush()
        for proc in processes:
            proc_orm = JudicialProcessORM(
                search_pk=row.id,
                process_number=proc.process_number,
                tribunal=proc.tribunal,
                justice_type=proc.justice_type.value,
                jurisdiction=proc.jurisdiction,
                court=proc.court,
                class_code=proc.class_code,
                class_name=proc.class_name,
                priority_json=list(proc.priority),
                electronic=proc.electronic,
                last_movement_at=proc.last_movement_at,
                source_identifier=proc.source_identifier,
            )
            proc_orm.parties = [
                JudicialProcessPartyORM(
                    name=p.name, document=p.document, document_type=p.document_type,
                    role=p.role, party_type=p.party_type, representation=p.representation,
                    source_identifier=p.source_identifier,
                )
                for p in proc.parties
            ]
            proc_orm.subjects = [
                JudicialProcessSubjectORM(code=s.code, name=s.name, source_identifier=s.source_identifier)
                for s in proc.subjects
            ]
            proc_orm.movements = [
                JudicialProcessMovementORM(
                    movement_date=m.movement_date, code=m.code, description=m.description,
                    complement=m.complement, source_identifier=m.source_identifier,
                )
                for m in proc.movements
            ]
            session.add(proc_orm)

    def _replace_signals(self, session: Session, row: JudicialSearchORM, signals: list[Signal]) -> None:
        for existing in list(row.signals):
            session.delete(existing)
        session.flush()
        for sig in signals:
            session.add(
                JudicialSignalORM(
                    search_pk=row.id,
                    signal_code=sig.signal_code,
                    category=sig.category.value,
                    severity=sig.severity.value,
                    confidence=sig.confidence,
                    evidence_text=sig.evidence_text,
                    evidence_type=sig.evidence_type.value,
                    process_number=sig.process_number,
                    tribunal=sig.tribunal,
                    source_identifier=sig.source_identifier,
                    rule_version=sig.rule_version,
                )
            )

    def _sync_events(self, session: Session, row: JudicialSearchORM, events: list[SearchEvent]) -> None:
        # Anexa apenas eventos novos (o índice de corte é a quantidade já gravada),
        # evitando duplicação quando save() é chamado várias vezes na mesma pesquisa.
        already = len(row.events)
        for event in events[already:]:
            session.add(_event_to_orm(row.id, event))

    # ------------------------------------------------------------------
    # Helpers de leitura (ORM -> domínio)
    # ------------------------------------------------------------------
    def _to_record(self, row: JudicialSearchORM) -> SearchRecord:
        result = SearchResult(
            search_id=row.search_id,
            status=SearchStatus(row.status),
            completeness=Completeness(**(row.completeness_json or {})),
            sources=[self._source_from_orm(s) for s in row.sources],
            processes=[self._process_from_orm(p) for p in row.processes],
            signals=[self._signal_from_orm(s) for s in row.signals],
            warnings=list(row.warnings_json or []),
            reanalyze=ReanalyzeHint(**(row.reanalyze_json or {})),
        )
        request = SearchRequest(**row.request_json) if row.request_json else None
        events = [
            SearchEvent(
                type=SearchEventType(e.event_type),
                at=e.at,
                tribunal=e.tribunal,
                detail=dict(e.detail_json or {}),
            )
            for e in sorted(row.events, key=lambda e: e.id)
        ]
        return SearchRecord(
            search_id=row.search_id,
            correlation_id=row.correlation_id,
            request_hash=row.request_hash,
            result=result,
            request=request,
            events=events,
        )

    @staticmethod
    def _source_from_orm(s: JudicialSearchSourceORM) -> SourceResult:
        return SourceResult(
            provider=s.provider,
            tribunal=s.tribunal,
            justice_type=JusticeType(s.justice_type),
            status=SourceStatus(s.status),
            http_status=s.http_status,
            duration_ms=s.duration_ms,
            pages=s.pages,
            result_count=s.result_count,
            attempts=s.attempts,
            error=SourceError(**s.error_json) if s.error_json else None,
        )

    @staticmethod
    def _process_from_orm(p: JudicialProcessORM) -> Process:
        return Process(
            process_number=p.process_number,
            tribunal=p.tribunal,
            justice_type=JusticeType(p.justice_type),
            jurisdiction=p.jurisdiction,
            court=p.court,
            class_code=p.class_code,
            class_name=p.class_name,
            subjects=[Subject(code=s.code, name=s.name, source_identifier=s.source_identifier) for s in p.subjects],
            parties=[
                Party(
                    name=pt.name, document=pt.document, document_type=pt.document_type,
                    role=pt.role, party_type=pt.party_type, representation=pt.representation,
                    source_identifier=pt.source_identifier,
                )
                for pt in p.parties
            ],
            movements=[
                Movement(
                    movement_date=m.movement_date, code=m.code, description=m.description,
                    complement=m.complement, source_identifier=m.source_identifier,
                )
                for m in p.movements
            ],
            priority=list(p.priority_json or []),
            electronic=p.electronic,
            last_movement_at=p.last_movement_at,
            source_identifier=p.source_identifier,
        )

    @staticmethod
    def _signal_from_orm(s: JudicialSignalORM) -> Signal:
        return Signal(
            signal_code=s.signal_code,
            category=SignalCategory(s.category),
            severity=SignalSeverity(s.severity),
            confidence=s.confidence,
            evidence_text=s.evidence_text,
            evidence_type=SignalEvidenceType(s.evidence_type),
            process_number=s.process_number,
            tribunal=s.tribunal,
            source_identifier=s.source_identifier,
            rule_version=s.rule_version,
        )


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _event_to_orm(search_pk: int, event: SearchEvent) -> JudicialSearchEventORM:
    return JudicialSearchEventORM(
        search_pk=search_pk,
        event_type=event.type.value,
        tribunal=event.tribunal,
        detail_json=dict(event.detail or {}),
        at=event.at,
    )
