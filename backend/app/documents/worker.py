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
- Sem tentativa "gasta" em vão: o lease carrega um identificador de dono
  (``embedding_lease_owner``). Na etapa 2 o lock é re-adquirido de forma bloqueante com
  ``lock_timeout`` e o lease é REAVALIADO; se o lock não vier, a tentativa é devolvida (somente
  se o lease ainda for desta execução); se o lease já for de outra execução, nada é alterado.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
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
# Dimensionamento do lease (``WORKER_LEASE_SECONDS``): o lease NÃO é o mutex (quem exclui a
# execução simultânea é o lock de linha); ele só define em quanto tempo uma tentativa sem
# conclusão passa a ser tratada como interrompida. Regra prática:
#     lease >= lotes x (( 1 + LLM_MAX_RETRIES) x LLM_TIMEOUT_SECONDS + 10) + 60
# onde ``lotes = ceil(chunks_da_versão / 1000)`` (o cliente de embeddings envia até 1000
# textos por chamada). Com os padrões (timeout 90 s, 1 retry) cada lote custa até ~190 s no
# pior caso; 600 s cobre 2 lotes lentos (~2000 chunks) e 900 s cobre 4. Errar para MAIS só
# atrasa a recuperação de um crash; errar para MENOS apenas faz a versão aparecer como
# elegível enquanto um worker vivo a processa (o lock de linha impede a duplicidade).

# Espera máxima pelo lock de linha na etapa 2 (re-claim depois do commit da etapa 1).
LOCK_TIMEOUT_MS_DEFAULT = 5000

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
    meta.pop("embedding_lease_owner", None)


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


class LockUnavailable(Exception):
    """Lock de linha não obtido dentro do ``lock_timeout`` (SQLSTATE 55P03)."""


def _claim_row_blocking(db: Session, version_id: int, lock_timeout_ms: int) -> models.DocumentVersion | None:
    """Re-claim BLOQUEANTE (``FOR UPDATE``) com ``lock_timeout`` (só vale nesta transação).

    Usado na etapa 2, depois que a tentativa e o lease já foram gravados: quem pode estar
    segurando a linha nesse instante é um executor que apenas a inspeciona (milissegundos),
    então esperar é o correto; ``SKIP LOCKED`` faria a tentativa ser consumida sem processar.
    Levanta ``LockUnavailable`` no timeout (a transação é desfeita pelo chamador).
    """
    db.execute(text("SELECT set_config('lock_timeout', :ms, true)"), {"ms": str(max(1, int(lock_timeout_ms)))})
    try:
        return db.scalars(
            select(models.DocumentVersion)
            .where(models.DocumentVersion.id == version_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).first()
    except OperationalError as exc:
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "55P03":
            raise LockUnavailable(f"lock da versão {version_id} indisponível em {lock_timeout_ms} ms") from exc
        raise


def _give_back_attempt(db: Session, version_id: int, owner: str, lock_timeout_ms: int) -> dict[str, Any]:
    """A etapa 2 não conseguiu o lock: devolve a tentativa SE (e só se) o lease ainda for
    desta execução e o processamento não tiver começado. Nunca mexe em lease alheio."""
    base = {"version_id": version_id, "status": "EM_PROCESSAMENTO"}
    try:
        ver = _claim_row_blocking(db, version_id, lock_timeout_ms)
    except LockUnavailable:
        db.rollback()
        log.warning("worker: lock indisponível version_id=%s; tentativa permanece registrada (será tratada como interrompida se o lease vencer)", version_id)
        return {**base, "motivo": "lock indisponível; tentativa mantida até o lease vencer"}
    if ver is None:
        db.rollback()
        return {**base, "status": "NAO_ENCONTRADA"}
    meta = _meta(ver)
    if meta.get("embedding_lease_owner") != owner:
        db.rollback()                     # o lease pertence a outra execução: não toca em nada
        return {**base, "motivo": "lease pertence a outra execução"}
    meta["embedding_attempts"] = max(0, int(meta.get("embedding_attempts", 0) or 0) - 1)
    _clear_lease(meta)
    ver.status = states.AGUARDANDO_EMBEDDING
    ver.extraction_metadata = dict(meta)
    db.commit()
    log.info("worker: lock indisponível version_id=%s; tentativa devolvida", version_id)
    return {**base, "motivo": "lock indisponível; tentativa devolvida"}


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


def _record_failure(db: Session, version_id: int, exc: Exception, owner: str, lock_timeout_ms: int) -> dict[str, Any]:
    """Falha inesperada no processamento: motivo saneado, status ERRO, lease encerrado.

    Só altera a versão se o lease ainda for DESTA execução (``owner``); se o lock não puder
    ser obtido, nada é alterado e o lease vence normalmente (tentativa tratada como interrompida).
    """
    from ..ai.gateway import sanitize_error
    attempts = 0
    try:
        ver = _claim_row_blocking(db, version_id, lock_timeout_ms)
    except LockUnavailable:
        db.rollback()
        ver = None
    if ver is not None:
        meta = _meta(ver)
        attempts = int(meta.get("embedding_attempts", 0) or 0)
        if meta.get("embedding_lease_owner") == owner:
            meta["embedding_last_error"] = sanitize_error(str(exc))
            _clear_lease(meta)
            ver.extraction_metadata = dict(meta)
            ver.status = states.ERRO
            db.flush()
    log.warning("worker: falha ao processar version_id=%s attempt=%s", version_id, attempts)
    return {"version_id": version_id, "status": states.ERRO, "attempts": attempts}


def process_version(
    db: Session, version_id: int, *, max_attempts: int = MAX_ATTEMPTS_DEFAULT,
    lease_seconds: int = LEASE_SECONDS_DEFAULT, lock_timeout_ms: int = LOCK_TIMEOUT_MS_DEFAULT,
) -> dict[str, Any]:
    """Processa (embeddings pendentes de) uma versão de forma idempotente.

    Sem provider/chave: marca AGUARDANDO_EMBEDDING e retorna sem erro (o texto já está
    preservado). Com chave: gera vetores pendentes e marca INDEXADO ao concluir.

    Duas transações: (1) reivindica a versão, **grava a tentativa e o lease (com um
    identificador de dono) e faz commit**; (2) re-adquire o lock, reavalia o lease e só então
    processa. Assim, um crash na etapa 2 não perde a contagem, e uma tentativa nunca fica
    consumida por uma execução que não chegou a processar: se o lock não vier, a tentativa é
    devolvida (apenas se o lease ainda for desta execução).
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
    owner = uuid.uuid4().hex
    meta["embedding_attempts"] = int(meta.get("embedding_attempts", 0) or 0) + 1
    meta["embedding_lease_started_at"] = now
    meta["embedding_lease_until"] = now + max(1, int(lease_seconds))
    meta["embedding_lease_owner"] = owner
    ver.status = states.PROCESSANDO_EMBEDDING
    ver.extraction_metadata = dict(meta)
    db.commit()

    # Etapa 2: re-adquire o lock (BLOQUEANTE, com lock_timeout) e REAVALIA o estado. Quem pode
    # segurar a linha agora é só um executor que a inspeciona por instantes; ``SKIP LOCKED``
    # aqui consumiria a tentativa sem processar.
    try:
        ver = _claim_row_blocking(db, version_id, lock_timeout_ms)
    except LockUnavailable:
        db.rollback()
        return _give_back_attempt(db, version_id, owner, lock_timeout_ms)
    if ver is None:                         # versão removida entre as etapas
        db.rollback()
        return {"version_id": version_id, "status": "NAO_ENCONTRADA"}
    meta = _meta(ver)
    if meta.get("embedding_lease_owner") != owner:
        # O lease já não é desta execução (vencido e retomado por outra): não processa e não
        # toca em nada; a tentativa desta execução foi/será contabilizada como interrompida.
        db.rollback()
        return {"version_id": version_id, "status": "EM_PROCESSAMENTO", "motivo": "lease pertence a outra execução"}
    try:
        telemetry = embed_pending_chunks(db, version_id) or {}
    except Exception as exc:  # nunca deixa a exceção escapar do worker
        db.rollback()                       # descarta trabalho parcial; a tentativa já está commitada
        return _record_failure(db, version_id, exc, owner, lock_timeout_ms)

    _clear_lease(meta)
    if telemetry.get("embeddings_pendentes") == 0:
        # Nada havia a processar (outro caminho já indexou): não consome tentativa.
        meta["embedding_attempts"] = max(0, int(meta["embedding_attempts"]) - 1)
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
