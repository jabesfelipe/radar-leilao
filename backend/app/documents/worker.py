"""Processamento assíncrono de documentos — worker DB-backed (Fase 6).

Decisão de arquitetura (menor complexidade): NÃO introduzimos Redis/Celery/RQ. O
estado de processamento já é PERSISTIDO em ``DocumentVersion.status`` (ver
``states.py``), então a própria tabela funciona como fila durável. Um worker simples
faz polling das versões pendentes e processa de forma IDEMPOTENTE, reusando
``embed_pending_chunks`` (que só toca chunks com ``embedding IS NULL``).

Garantias:
- Idempotência: reprocessar uma versão já indexada é no-op (não duplica chunks nem
  vetores). Retry é seguro.
- Recuperação após reinício: como o estado está no banco, reiniciar o worker retoma
  de onde parou (não há estado em memória).
- Controle de tentativas: ``extraction_metadata['embedding_attempts']`` (contador) e
  ``embedding_last_error`` (mensagem saneada) — sem schema novo (campo JSON já existe).
- Sem chamadas externas implícitas: sem provider/chave, marca AGUARDANDO_EMBEDDING e
  segue (nunca chama OpenAI por conta própria).
- Concorrência: o processamento por versão usa a transação da sessão; o claim é por
  atualização de status (PROCESSANDO_EMBEDDING) antes de gerar — reduz corrida entre
  workers. Para o MVP (1 worker), é suficiente.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..logging_config import get_logger
from . import states
from .embedding import embed_pending_chunks

log = get_logger("worker")

MAX_ATTEMPTS_DEFAULT = 5


def _meta(version: models.DocumentVersion) -> dict[str, Any]:
    return dict(version.extraction_metadata or {})


def pending_versions(db: Session, *, limit: int | None = None, max_attempts: int = MAX_ATTEMPTS_DEFAULT) -> list[int]:
    """Versões que têm chunks sem embedding E ainda não excederam as tentativas.

    Fonte da fila: existência de ``DocumentChunk.embedding IS NULL`` ligada à versão.
    Não depende de provider — apenas identifica o trabalho pendente.
    """
    stmt = (
        select(models.DocumentChunk.document_version_id)
        .where(models.DocumentChunk.embedding.is_(None))
        .group_by(models.DocumentChunk.document_version_id)
        .order_by(models.DocumentChunk.document_version_id)
    )
    ids = [r for r in db.scalars(stmt).all()]
    out: list[int] = []
    for vid in ids:
        ver = db.get(models.DocumentVersion, vid)
        if ver is None:
            continue
        attempts = int(_meta(ver).get("embedding_attempts", 0) or 0)
        if attempts >= max_attempts:
            continue
        out.append(vid)
    if limit is not None:
        out = out[:limit]
    return out


def process_version(db: Session, version_id: int, *, max_attempts: int = MAX_ATTEMPTS_DEFAULT) -> dict[str, Any]:
    """Processa (embeddings pendentes de) uma versão de forma idempotente.

    Sem provider/chave: marca AGUARDANDO_EMBEDDING e retorna sem erro (o texto já está
    preservado). Com chave: gera vetores pendentes e marca INDEXADO ao concluir.
    """
    ver = db.get(models.DocumentVersion, version_id)
    if ver is None:
        return {"version_id": version_id, "status": "NAO_ENCONTRADA"}

    if not settings.effective_llm_api_key:
        ver.status = states.AGUARDANDO_EMBEDDING
        db.flush()
        return {"version_id": version_id, "status": ver.status, "motivo": "sem provider: embedding pendente preservado"}

    meta = _meta(ver)
    meta["embedding_attempts"] = int(meta.get("embedding_attempts", 0) or 0) + 1
    ver.status = states.PROCESSANDO_EMBEDDING
    ver.extraction_metadata = meta
    db.flush()

    try:
        telemetry = embed_pending_chunks(db, version_id) or {}
    except Exception as exc:  # nunca deixa a exceção escapar do worker
        from ..ai.gateway import sanitize_error
        meta["embedding_last_error"] = sanitize_error(str(exc))
        ver.extraction_metadata = meta
        ver.status = states.ERRO
        db.flush()
        log.warning("worker: falha ao processar version_id=%s attempt=%s", version_id, meta["embedding_attempts"])
        return {"version_id": version_id, "status": states.ERRO, "attempts": meta["embedding_attempts"]}

    # Recalcula pendência: se ainda houver chunk sem vetor, segue AGUARDANDO; senão INDEXADO.
    restantes = db.scalar(
        select(models.DocumentChunk.id).where(
            models.DocumentChunk.document_version_id == version_id,
            models.DocumentChunk.embedding.is_(None),
        ).limit(1)
    )
    ver.status = states.INDEXADO if restantes is None else states.AGUARDANDO_EMBEDDING
    meta.pop("embedding_last_error", None)
    ver.extraction_metadata = meta
    db.flush()
    return {
        "version_id": version_id,
        "status": ver.status,
        "attempts": meta["embedding_attempts"],
        "persistidos": int(telemetry.get("embeddings_persistidos", 0) or 0),
    }


def run_once(db: Session, *, limit: int | None = None, max_attempts: int = MAX_ATTEMPTS_DEFAULT) -> dict[str, Any]:
    """Uma varredura: processa todas as versões pendentes (até ``limit``)."""
    vids = pending_versions(db, limit=limit, max_attempts=max_attempts)
    resultados = [process_version(db, vid, max_attempts=max_attempts) for vid in vids]
    db.commit()
    return {"processadas": len(resultados), "versions": vids, "resultados": resultados}
