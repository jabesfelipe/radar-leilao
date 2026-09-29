"""Persistência PostgreSQL da Judicial API (TASK FINAL — Entrega 1)."""
from .models import (
    JudicialProcessORM,
    JudicialProcessMovementORM,
    JudicialProcessPartyORM,
    JudicialProcessSubjectORM,
    JudicialSearchEventORM,
    JudicialSearchORM,
    JudicialSearchSourceORM,
    JudicialSignalORM,
)
from .postgres_store import PostgresSearchStore

__all__ = [
    "JudicialSearchORM",
    "JudicialSearchSourceORM",
    "JudicialProcessORM",
    "JudicialProcessPartyORM",
    "JudicialProcessSubjectORM",
    "JudicialProcessMovementORM",
    "JudicialSignalORM",
    "JudicialSearchEventORM",
    "PostgresSearchStore",
]
