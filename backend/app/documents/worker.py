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
- Concorrência: ``FOR UPDATE SKIP LOCKED`` na versão enquanto ela é processada.
- Tentativa contabilizada ANTES do trabalho arriscado: cada tentativa é gravada (commit)
  junto com um "lease" (``embedding_lease_until``) antes de chamar o provider. Se o
  processo morrer no meio (kill, OOM, queda do host), o rollback da transação de
  processamento não desfaz a contagem: ao expirar o lease a versão é marcada como
  INTERROMPIDA (motivo registrado), recebe backoff e, ao atingir ``WORKER_MAX_ATTEMPTS``,
  sai da fila com status ERRO — nunca é marcada como concluída e nenhum chunk é apagado.
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
# Tempo máximo esperado para o processamento de UMA versão. Passado esse prazo sem que o
# worker conclua, a tentativa é considerada interrompida (crash). Deve exceder o pior caso
# de uma versão (lotes de embeddings x timeout do provider) para não haver falso positivo;
# mesmo assim, enquanto o worker vivo mantém o lock de linha, ele nunca é "recuperado".
LEASE_SECONDS_DEFAULT = 600

# Falhas que não indicam problema do documento: credencial, limite de taxa, timeout,
# rede e indisponibilidade do provider. Não consomem as tentativas definitivas.
TRANSIENT_ERROR_CATEGORIES = frozenset({"AUTENTICACAO", "RATE_LIMIT", "TIMEOUT", "CONEXAO", "PROVEDOR"})
BASE_BACKOFF_SECONDS = 60
MAX_BACKOFF_SECONDS = 900

INTERRUPTED_MESSAGE = "[INTERROMPIDO] a tentativa anterior não terminou (worker encerrado, reiniciado ou sem resposta durante o processamento)"


def _now() -> float:
    return time.time()


def _meta(version: models.DocumentVersion) -> dict[str, Any]:
    return dict(version.extraction_metadata or {})


def _backoff(failures: int) -> float:
    return min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** max(0, failures - 1)))


def _lease_state(meta: dict[str, Any], now: float) -> str:
    """``NONE`` (sem tentativa em curso), ``ACTIVE`` (lease válido) ou ``EXPIRED`` (a
    tentativa registrada não concluiu e o prazo acabou => interrompida)."""
    until = float(meta.get("embedding_lease_until", 0) or 0)
    if not until:
        return "NONE"
    return "ACTIVE" if until > now else "EXPIRED"


def _clear_lease(meta: dict[str, Any]) -> None:
    meta.pop("embedding_lease_until", None)
    meta.pop("embedding_lease_started_at", None)


def _register_interruption(meta: dict[str, Any], now: float) -> int:
    """Registra que a tentativa anterior foi interrompida: motivo, contador e backoff."""
    interruptions = int(meta.get("embedding_interruptions", 0) or 0) + 1
    meta["embedding_interruptions"] = interruptions
    meta["embedding_last_error"] = INTERRUPTED_MESSAGE
    meta["embedding_last_error_at"] = now
    meta["embedding_retry_after"] = now + _backoff(interruptions)
    _clear_lease(meta)
    return interruptions


def _claim_row(db: Session, version_id: int) -> models.DocumentVersion | None:
    """``FOR UPDATE SKIP LOCKED``: linha travada por outro worker/sessão => ``None``."""
    return db.scalars(
        select(models.DocumentVersion)
        .where(models.DocumentVersion.id == version_id)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    ).first()


def _pending_ids(db: Session) -> list[int]:
    stmt = (
        select(models.DocumentChunk.document_version_id)
        .where(models.DocumentChunk.embedding.is_(None))
        .group_by(models.DocumentChunk.document_version_id)
        .order_by(models.DocumentChunk.document_version_id)
    )
    return [r for r in db.scalars(stmt).all()]


def pending_versions(db: Session, *, limit: int | None = None, max_attempts: int = MAX_ATTEMPTS_DEFAULT) -> list[int]:
    """Versões que têm chunks sem embedding E ainda não excederam as tentativas.

    Fonte da fila: existência de ``DocumentChunk.embedding IS NULL`` ligada à versão.
    Não depende de provider — apenas identifica o trabalho pendente.
    """
    out: list[int] = []
    now = _now()
    for vid in _pending_ids(db):
        ver = db.get(models.DocumentVersion, vid)
        if ver is None:
            continue
        meta = _meta(ver)
        attempts = int(meta.get("embedding_attempts", 0) or 0)
        if attempts >= max_attempts:
            continue
        # Backoff após falha transitória ou interrupção: não insiste a cada ciclo.
        if float(meta.get("embedding_retry_after", 0) or 0) > now:
            continue
        # Tentativa em curso (lease válido): outro worker pode estar processando.
        if _lease_state(meta, now) == "ACTIVE":
            continue
        out.append(vid)
    if limit is not None:
        out = out[:limit]
    return out


def recover_interrupted(db: Session, *, max_attempts: int = MAX_ATTEMPTS_DEFAULT) -> list[int]:
    """Trata tentativas interrompidas (processo morto no meio do processamento).

    Uma versão com lease EXPIRADO e cuja linha não está travada por um worker vivo teve a
    tentativa interrompida. A tentativa JÁ foi contada (commit antes do processamento);
    aqui registramos o motivo, aplicamos backoff e, ao esgotar ``max_attempts``, retiramos a
    versão da fila com status ERRO. Chunks e vetores já gerados permanecem intactos e a
    versão nunca é marcada como concluída."""
    now = _now()
    recovered: list[int] = []
    for vid in _pending_ids(db):
        ver = _claim_row(db, vid)
        if ver is None:                       # em processamento por um worker vivo: não mexe
            continue
        meta = _meta(ver)
        if _lease_state(meta, now) != "EXPIRED":
            db.commit()                       # libera o lock de linha
            continue
        interruptions = _register_interruption(meta, now)
        attempts = int(meta.get("embedding_attempts", 0) or 0)
        if attempts >= max_attempts:
            meta["embedding_last_error"] = f"{INTERRUPTED_MESSAGE}; limite de {max_attempts} tentativas atingido, revisão manual necessária"
            ver.status = states.ERRO
        else:
            ver.status = states.AGUARDANDO_EMBEDDING   # volta à fila (com backoff); não fica "processando" para sempre
        ver.extraction_metadata = dict(meta)
        db.commit()
        recovered.append(vid)
        log.warning("worker: tentativa interrompida version_id=%s interrupcoes=%s tentativas=%s/%s", vid, interruptions, attempts, max_attempts)
    return recovered


def _record_failure(db: Session, version_id: int, exc: Exception) -> dict[str, Any]:
    """Falha inesperada no processamento: motivo saneado, status ERRO, lease encerrado."""
    from ..ai.gateway import sanitize_error
    ver = _claim_row(db, version_id)
    attempts = 0
    if ver is not None:
        meta = _meta(ver)
        meta["embedding_last_error"] = sanitize_error(str(exc))
        _clear_lease(meta)
        attempts = int(meta.get("embedding_attempts", 0) or 0)
        ver.extraction_metadata = dict(meta)
        ver.status = states.ERRO
        db.flush()
    log.warning("worker: falha ao processar version_id=%s attempt=%s", version_id, attempts)
    return {"version_id": version_id, "status": states.ERRO, "attempts": attempts}


def process_version(db: Session, version_id: int, *, max_attempts: int = MAX_ATTEMPTS_DEFAULT, lease_seconds: int = LEASE_SECONDS_DEFAULT) -> dict[str, Any]:
    """Processa (embeddings pendentes de) uma versão de forma idempotente.

    Sem provider/chave: marca AGUARDANDO_EMBEDDING e retorna sem erro (o texto já está
    preservado). Com chave: gera vetores pendentes e marca INDEXADO ao concluir.

    Duas transações: (1) reivindica a versão, **grava a tentativa e o lease e faz commit**;
    (2) processa com o lock de linha. Assim, um crash na etapa 2 não perde a contagem.
    """
    # Claim de linha: ``FOR UPDATE SKIP LOCKED`` impede que o worker e o endpoint de
    # reprocessamento (ou dois workers) processem a MESMA versão ao mesmo tempo (o que
    # geraria embeddings duplicados e custo duplicado). Quem encontra a linha travada a ignora.
    ver = _claim_row(db, version_id)
    if ver is None:
        exists = db.scalar(select(models.DocumentVersion.id).where(models.DocumentVersion.id == version_id))
        return {"version_id": version_id, "status": "NAO_ENCONTRADA" if exists is None else "EM_PROCESSAMENTO"}

    if not settings.effective_llm_api_key:
        ver.status = states.AGUARDANDO_EMBEDDING
        db.flush()
        return {"version_id": version_id, "status": ver.status, "motivo": "sem provider: embedding pendente preservado"}

    now = _now()
    meta = _meta(ver)
    state = _lease_state(meta, now)
    if state == "ACTIVE":
        return {"version_id": version_id, "status": "EM_PROCESSAMENTO", "motivo": "tentativa em curso (lease válido)"}
    if state == "EXPIRED":
        _register_interruption(meta, now)   # a tentativa anterior morreu no meio; registra o motivo

    # Etapa 1: contabiliza a tentativa e registra o lease de forma DURÁVEL antes de qualquer
    # chamada externa. Sempre atribuir uma CÓPIA: a coluna JSON não rastreia mutação in-place.
    meta["embedding_attempts"] = int(meta.get("embedding_attempts", 0) or 0) + 1
    meta["embedding_lease_started_at"] = now
    meta["embedding_lease_until"] = now + max(1, int(lease_seconds))
    ver.status = states.PROCESSANDO_EMBEDDING
    ver.extraction_metadata = dict(meta)
    db.commit()

    # Etapa 2: processamento com o lock de linha da nova transação.
    ver = _claim_row(db, version_id)
    if ver is None:
        return {"version_id": version_id, "status": "EM_PROCESSAMENTO"}
    meta = _meta(ver)
    try:
        telemetry = embed_pending_chunks(db, version_id) or {}
    except Exception as exc:  # nunca deixa a exceção escapar do worker
        db.rollback()                       # descarta trabalho parcial; a tentativa já está commitada
        return _record_failure(db, version_id, exc)

    _clear_lease(meta)
    erro = telemetry.get("erro")
    if erro:
        categoria = str(telemetry.get("erro_categoria") or "DESCONHECIDO")
        meta["embedding_last_error"] = f"[{categoria}] {erro}"[:500]
        meta["embedding_last_error_at"] = _now()
        if categoria in TRANSIENT_ERROR_CATEGORIES:
            # Falha transitória/de credencial: não consome as tentativas definitivas
            # (corrigir a chave ou esperar o rate limit deve retomar o processamento);
            # aplica backoff exponencial para não insistir a cada ciclo.
            meta["embedding_attempts"] = max(0, int(meta["embedding_attempts"]) - 1)
            failures = int(meta.get("embedding_transient_failures", 0) or 0) + 1
            meta["embedding_transient_failures"] = failures
            meta["embedding_retry_after"] = _now() + _backoff(failures)
        log.warning("worker: embedding falhou version_id=%s categoria=%s tentativas=%s", version_id, categoria, meta["embedding_attempts"])
    else:
        for key in ("embedding_last_error", "embedding_last_error_at", "embedding_transient_failures", "embedding_retry_after", "embedding_interruptions"):
            meta.pop(key, None)

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


def run_once(db: Session, *, limit: int | None = None, max_attempts: int = MAX_ATTEMPTS_DEFAULT, lease_seconds: int = LEASE_SECONDS_DEFAULT) -> dict[str, Any]:
    """Uma varredura: recupera tentativas interrompidas e processa as versões pendentes (até ``limit``)."""
    recuperadas = recover_interrupted(db, max_attempts=max_attempts)
    vids = pending_versions(db, limit=limit, max_attempts=max_attempts)
    resultados = []
    for vid in vids:
        resultados.append(process_version(db, vid, max_attempts=max_attempts, lease_seconds=lease_seconds))
        # Commit por versão: um erro/queda no meio do lote não descarta vetores já pagos
        # e libera o lock de linha da versão assim que ela termina.
        db.commit()
    db.commit()
    return {"processadas": len(resultados), "versions": vids, "resultados": resultados, "interrompidas": recuperadas}
