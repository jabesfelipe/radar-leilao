"""Modelos ORM das tabelas ``judicial_*`` (TASK FINAL — Entrega 1, SPEC §56-68).

Mapeiam o resultado de uma pesquisa (agregado, fontes, processos + partes/
assuntos/movimentos, sinais e eventos de auditoria) para o PostgreSQL
compartilhado com o Radar. Tabelas prefixadas ``judicial_`` no schema ``public``.

Regras de integridade relevantes ao retry/idempotência:
- ``judicial_searches.search_id`` é único (UUID textual estável do contrato REST);
- ``judicial_search_sources`` é único por (search_id, tribunal) — o retry faz
  UPSERT da fonte, nunca duplica;
- ``judicial_processes`` é único por (search_id, tribunal, process_number) —
  reflete a chave lógica de deduplicação (SPEC §33) dentro de uma pesquisa.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import JudicialBase


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JudicialSearchORM(JudicialBase):
    __tablename__ = "judicial_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    # Critérios da pesquisa (para reanálise/auditoria) e o agregado do resultado.
    request_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    completeness_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    reanalyze_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)

    sources: Mapped[list["JudicialSearchSourceORM"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )
    processes: Mapped[list["JudicialProcessORM"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )
    signals: Mapped[list["JudicialSignalORM"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )
    events: Mapped[list["JudicialSearchEventORM"]] = relationship(
        back_populates="search", cascade="all, delete-orphan"
    )


class JudicialSearchSourceORM(JudicialBase):
    __tablename__ = "judicial_search_sources"
    __table_args__ = (
        UniqueConstraint("search_pk", "tribunal", name="uq_judicial_source_search_tribunal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    search_pk: Mapped[int] = mapped_column(ForeignKey("judicial_searches.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    tribunal: Mapped[str] = mapped_column(String(40))
    justice_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    http_status: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    search: Mapped[JudicialSearchORM] = relationship(back_populates="sources")


class JudicialProcessORM(JudicialBase):
    __tablename__ = "judicial_processes"
    __table_args__ = (
        UniqueConstraint(
            "search_pk", "tribunal", "process_number",
            name="uq_judicial_process_search_tribunal_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    search_pk: Mapped[int] = mapped_column(ForeignKey("judicial_searches.id", ondelete="CASCADE"), index=True)
    process_number: Mapped[str] = mapped_column(String(60))
    tribunal: Mapped[str] = mapped_column(String(40))
    justice_type: Mapped[str] = mapped_column(String(20))
    jurisdiction: Mapped[str | None] = mapped_column(String(120))
    court: Mapped[str | None] = mapped_column(String(240))
    class_code: Mapped[str | None] = mapped_column(String(40))
    class_name: Mapped[str | None] = mapped_column(String(240))
    priority_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    electronic: Mapped[bool | None] = mapped_column()
    last_movement_at: Mapped[str | None] = mapped_column(String(40))
    source_identifier: Mapped[str | None] = mapped_column(String(120))

    search: Mapped[JudicialSearchORM] = relationship(back_populates="processes")
    parties: Mapped[list["JudicialProcessPartyORM"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["JudicialProcessSubjectORM"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )
    movements: Mapped[list["JudicialProcessMovementORM"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )


class JudicialProcessPartyORM(JudicialBase):
    __tablename__ = "judicial_process_parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_pk: Mapped[int] = mapped_column(ForeignKey("judicial_processes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(Text)
    document: Mapped[str | None] = mapped_column(String(40))
    document_type: Mapped[str | None] = mapped_column(String(10))
    role: Mapped[str | None] = mapped_column(String(60))
    party_type: Mapped[str | None] = mapped_column(String(20))
    representation: Mapped[str | None] = mapped_column(Text)
    source_identifier: Mapped[str | None] = mapped_column(String(120))

    process: Mapped[JudicialProcessORM] = relationship(back_populates="parties")


class JudicialProcessSubjectORM(JudicialBase):
    __tablename__ = "judicial_process_subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_pk: Mapped[int] = mapped_column(ForeignKey("judicial_processes.id", ondelete="CASCADE"), index=True)
    code: Mapped[str | None] = mapped_column(String(40))
    name: Mapped[str | None] = mapped_column(Text)
    source_identifier: Mapped[str | None] = mapped_column(String(120))

    process: Mapped[JudicialProcessORM] = relationship(back_populates="subjects")


class JudicialProcessMovementORM(JudicialBase):
    __tablename__ = "judicial_process_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_pk: Mapped[int] = mapped_column(ForeignKey("judicial_processes.id", ondelete="CASCADE"), index=True)
    movement_date: Mapped[str | None] = mapped_column(String(40))
    code: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    complement: Mapped[str | None] = mapped_column(Text)
    source_identifier: Mapped[str | None] = mapped_column(String(120))

    process: Mapped[JudicialProcessORM] = relationship(back_populates="movements")


class JudicialSignalORM(JudicialBase):
    __tablename__ = "judicial_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    search_pk: Mapped[int] = mapped_column(ForeignKey("judicial_searches.id", ondelete="CASCADE"), index=True)
    signal_code: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    evidence_text: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(20))
    process_number: Mapped[str | None] = mapped_column(String(60))
    tribunal: Mapped[str | None] = mapped_column(String(40))
    source_identifier: Mapped[str | None] = mapped_column(String(120))
    rule_version: Mapped[int] = mapped_column(Integer, default=1)

    search: Mapped[JudicialSearchORM] = relationship(back_populates="signals")


class JudicialSearchEventORM(JudicialBase):
    __tablename__ = "judicial_search_events"
    __table_args__ = (
        Index("ix_judicial_event_search_pk", "search_pk"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    search_pk: Mapped[int] = mapped_column(ForeignKey("judicial_searches.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    tribunal: Mapped[str | None] = mapped_column(String(40))
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    at: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    search: Mapped[JudicialSearchORM] = relationship(back_populates="events")
