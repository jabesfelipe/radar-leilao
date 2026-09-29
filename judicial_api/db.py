"""Camada de banco da Judicial API (TASK FINAL — Entrega 1).

O módulo permanece autocontido (não importa nada do Radar), mas reutiliza o MESMO
PostgreSQL: a URL vem de ``DATABASE_URL``/``JUDICIAL_DATABASE_URL`` (a mesma do
Radar). As tabelas usam o prefixo ``judicial_`` no schema ``public``, evitando
qualquer colisão com o schema do Radar — não é uma segunda infraestrutura.

O engine é criado sob demanda (lazy) e cacheado, para que importar o pacote não
exija um banco disponível (a suíte in-memory e os testes de unidade continuam
funcionando sem PostgreSQL).
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class JudicialBase(DeclarativeBase):
    """Base declarativa isolada das tabelas ``judicial_*``."""


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def reset_engine() -> None:
    """Descarta engine/sessionmaker cacheados (usado em testes que trocam a URL)."""
    try:
        get_engine().dispose()
    except Exception:  # noqa: BLE001 - dispose best-effort
        pass
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
