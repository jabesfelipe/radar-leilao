"""Backfill de embeddings ausentes — capacidade controlada (Fase 2 — RAG).

A auditoria mostrou ~1.097 de 1.649 chunks sem embedding (ingeridos sem chave). Este
módulo oferece a CAPACIDADE de reprocessar esses vetores, mas de forma segura:

- **dry_run=True por padrão**: por padrão apenas RELATA (nunca gera vetor real).
- **enabled=False por padrão**: a execução real exige ``enabled=True`` + chave de
  provider presente. Sem isso, retorna apenas o diagnóstico.
- **Sem chamadas externas implícitas**: a geração real só ocorre com dry_run=False E
  enabled=True E provider disponível — decisão explícita do operador.
- **Idempotente**: só considera chunks com ``embedding IS NULL`` e valida a dimensão
  antes de persistir (descarta incompatíveis), reusando ``embed_pending_chunks``.
- **NÃO faz backfill do histórico automaticamente** nesta missão; é ferramenta sob demanda.

Uso típico (diagnóstico, sempre seguro):
    coverage_report(db)                      # métricas de cobertura
    backfill_missing_embeddings(db)          # dry-run: lista o que faria

Uso real (decisão explícita do operador, fora desta missão):
    backfill_missing_embeddings(db, dry_run=False, enabled=True, limit=100)
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..logging_config import get_logger
from .embedding import embed_pending_chunks

log = get_logger("documentos")


def coverage_report(db: Session) -> dict[str, int | float | bool | str]:
    """Métricas de cobertura de embeddings (somente leitura). Sem segredos."""
    total = db.scalar(select(func.count()).select_from(models.DocumentChunk)) or 0
    com_vetor = db.scalar(
        select(func.count()).select_from(models.DocumentChunk).where(models.DocumentChunk.embedding.is_not(None))
    ) or 0
    sem_vetor = total - com_vetor
    versions_pendentes = db.scalar(
        select(func.count(func.distinct(models.DocumentChunk.document_version_id)))
        .where(models.DocumentChunk.embedding.is_(None))
    ) or 0
    return {
        "chunks_total": int(total),
        "chunks_com_embedding": int(com_vetor),
        "chunks_sem_embedding": int(sem_vetor),
        "cobertura_pct": round(100.0 * com_vetor / total, 1) if total else 0.0,
        "versions_com_pendencia": int(versions_pendentes),
        "modelo": settings.embedding_model,
        "dimensao": settings.embedding_dimensions,
        "provider_disponivel": bool(settings.effective_llm_api_key),
    }


def _versions_with_missing(db: Session, limit: int | None) -> list[int]:
    stmt = (
        select(models.DocumentChunk.document_version_id)
        .where(models.DocumentChunk.embedding.is_(None))
        .group_by(models.DocumentChunk.document_version_id)
        .order_by(models.DocumentChunk.document_version_id)
    )
    rows = [r for r in db.scalars(stmt).all()]
    if limit is not None:
        rows = rows[:limit]
    return rows


def backfill_missing_embeddings(
    db: Session,
    *,
    dry_run: bool = True,
    enabled: bool = False,
    limit: int | None = None,
) -> dict:
    """Identifica (e opcionalmente gera) embeddings de chunks pendentes.

    Por padrão é um **dry-run desabilitado**: apenas relata o que faria. A geração
    real só ocorre com ``dry_run=False`` E ``enabled=True`` E provider disponível.
    """
    report = coverage_report(db)
    versions = _versions_with_missing(db, limit)
    plano = {
        "dry_run": dry_run,
        "enabled": enabled,
        "versions_alvo": versions,
        "cobertura": report,
        "executado": False,
        "embeddings_persistidos": 0,
        "motivo": "",
    }

    if dry_run or not enabled:
        plano["motivo"] = "dry-run (padrao): nenhuma geracao executada. Para executar: dry_run=False, enabled=True."
        return plano
    if not settings.effective_llm_api_key:
        plano["motivo"] = "provider indisponivel: sem chave configurada; nenhuma geracao executada."
        return plano

    # Execução real (explícita): reusa embed_pending_chunks por versão (idempotente).
    persisted = 0
    for version_id in versions:
        tele = embed_pending_chunks(db, version_id) or {}
        persisted += int(tele.get("embeddings_persistidos", 0) or 0)
    db.flush()
    plano["executado"] = True
    plano["embeddings_persistidos"] = persisted
    plano["motivo"] = "execucao real concluida"
    log.info("backfill de embeddings executado: versions=%d persistidos=%d", len(versions), persisted)
    return plano
