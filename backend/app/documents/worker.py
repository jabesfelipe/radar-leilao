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

import time
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

# Falhas que não indicam problema do documento: credencial, limite de taxa, timeout,
# rede e indisponibilidade do provider. Não consomem as tentativas definitivas.
TRANSIENT_ERROR_CATEGORIES = frozenset({"AUTENTICACAO", "RATE_LIMIT", "TIMEOUT", "CONEXAO", "PROVEDOR"})
BASE_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 900


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
    now = time.time()
    for vid in ids:
        ver = db.get(models.DocumentVersion, vid)
        if ver is None:
            continue
        meta = _meta(ver)
        attempts = int(meta.get("embedding_attempts", 0) or 0)
        if attempts >= max_attempts:
            continue
        # Backoff após falha transitória (rate limit, timeout, rede, credencial): não
        # insiste a cada ciclo do worker.
        if float(meta.get("embedding_retry_after", 0) or 0) > now:
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
    # Claim de linha: ``FOR UPDATE SKIP LOCKED`` impede que o worker e o endpoint de
    # reprocessamento (ou dois workers) processem a MESMA versão ao mesmo tempo (o que
    # geraria embeddings duplicados e custo duplicado). O lock vale até o commit/rollback
    # da sessão; quem encontra a linha travada simplesmente a ignora.
    ver = db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.id == version_id)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    ).first()
    if ver is None:
        exists = db.scalar(select(models.DocumentVersion.id).where(models.DocumentVersion.id == version_id))
        return {"version_id": version_id, "status": "NAO_ENCONTRADA" if exists is None else "EM_PROCESSAMENTO"}

    if not settings.effective_llm_api_key:
        ver.status = states.AGUARDANDO_EMBEDDING
        db.flush()
        return {"version_id": version_id, "status": ver.status, "motivo": "sem provider: embedding pendente preservado"}

    meta = _meta(ver)
    meta["embedding_attempts"] = int(meta.get("embedding_attempts", 0) or 0) + 1
    ver.status = states.PROCESSANDO_EMBEDDING
    # Sempre atribuir uma CÓPIA: a coluna JSON não é mutável rastreada; reatribuir o mesmo
    # dict alterado in place não seria detectado como mudança e a alteração se perderia.
    ver.extraction_metadata = dict(meta)
    db.flush()

    try:
        telemetry = embed_pending_chunks(db, version_id) or {}
    except Exception as exc:  # nunca deixa a exceção escapar do worker
        from ..ai.gateway import sanitize_error
        meta["embedding_last_error"] = sanitize_error(str(exc))
        ver.extraction_metadata = dict(meta)
        ver.status = states.ERRO
        db.flush()
        log.warning("worker: falha ao processar version_id=%s attempt=%s", version_id, meta["embedding_attempts"])
        return {"version_id": version_id, "status": states.ERRO, "attempts": meta["embedding_attempts"]}

    erro = telemetry.get("erro")
    if erro:
        categoria = str(telemetry.get("erro_categoria") or "DESCONHECIDO")
        meta["embedding_last_error"] = f"[{categoria}] {erro}"[:500]
        meta["embedding_last_error_at"] = time.time()
        if categoria in TRANSIENT_ERROR_CATEGORIES:
            # Falha transitória/de credencial: não consome as tentativas definitivas
            # (corrigir a chave ou esperar o rate limit deve retomar o processamento);
            # aplica backoff exponencial para não insistir a cada ciclo.
            meta["embedding_attempts"] = max(0, int(meta["embedding_attempts"]) - 1)
            failures = int(meta.get("embedding_transient_failures", 0) or 0) + 1
            meta["embedding_transient_failures"] = failures
            meta["embedding_retry_after"] = time.time() + min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** (failures - 1)))
        log.warning("worker: embedding falhou version_id=%s categoria=%s tentativas=%s", version_id, categoria, meta["embedding_attempts"])
    else:
        meta.pop("embedding_last_error", None)
        meta.pop("embedding_last_error_at", None)
        meta.pop("embedding_transient_failures", None)
        meta.pop("embedding_retry_after", None)

    # Recalcula pendência: se ainda houver chunk sem vetor, segue AGUARDANDO; senão INDEXADO.
    restantes = db.scalar(
        select(models.DocumentChunk.id).where(
            models.DocumentChunk.document_version_id == version_id,
            models.DocumentChunk.embedding.is_(None),
        ).limit(1)
    )
    ver.status = states.INDEXADO if restantes is None else states.AGUARDANDO_EMBEDDING
    ver.extraction_metadata = dict(meta)
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
    resultados = []
    for vid in vids:
        resultados.append(process_version(db, vid, max_attempts=max_attempts))
        # Commit por versão: um erro/queda no meio do lote não descarta vetores já pagos
        # e libera o lock de linha da versão assim que ela termina.
        db.commit()
    db.commit()
    return {"processadas": len(resultados), "versions": vids, "resultados": resultados}
