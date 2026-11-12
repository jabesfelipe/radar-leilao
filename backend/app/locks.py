"""Locks de aplicação baseados em advisory locks do PostgreSQL.

Usados para impedir execuções simultâneas duplicadas (e gasto duplicado com LLM) entre
processos/workers diferentes: por exemplo, duas requisições ``POST /analisar`` do mesmo
imóvel. O lock é de TRANSAÇÃO (``pg_try_advisory_xact_lock``): é liberado
automaticamente no ``commit``/``rollback`` da sessão da requisição — não há risco de
lock "esquecido" nem necessidade de limpeza. Não bloqueia: se já houver outra operação
em andamento, responde 409 imediatamente.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db


def try_advisory_xact_lock(db: Session, key: str) -> bool:
    """Tenta obter o lock ``key``. Retorna False se outra transação já o detém."""
    return bool(db.execute(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": key}).scalar())


def require_operation_lock(db: Session, key: str, message: str = "Operação já em andamento. Aguarde a conclusão e tente novamente.") -> None:
    """Obtém o lock ou responde 409 (Conflict)."""
    if not try_advisory_xact_lock(db, key):
        raise HTTPException(409, message)


def operation_lock(prefix: str, *path_params: str, message: str | None = None):
    """Fábrica de dependência de rota: obtém o lock ``prefix:<params da rota>`` na sessão
    da requisição (liberado no fim da transação) ou responde 409.

    Como dependência (``@app.post(..., dependencies=[Depends(operation_lock(...))])``) ela
    não altera a assinatura das funções de endpoint, preservando as chamadas diretas.
    """
    def _dependency(request: Request, db: Session = Depends(get_db)) -> None:
        key = ":".join([prefix, *(str(request.path_params.get(name, "")) for name in path_params)])
        require_operation_lock(db, key, message or "Já existe uma operação idêntica em andamento. Aguarde a conclusão e tente novamente.")
    return _dependency
