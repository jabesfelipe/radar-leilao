"""Geração e persistência de embeddings de DocumentChunk durante a ingestão.

Correção mínima do pipeline (TASK 66): novos chunks recebem embedding no campo
vetorial já existente (`document_chunks.embedding`, `Vector(embedding_dimensions)`),
reutilizando o gateway/provider de embeddings existente. Não cria RAG/agente novo,
não cria migration (a coluna já existe) e não faz backfill automático do histórico.

Regras:
- Sem `OPENAI_API_KEY`/provider: não gera embedding (ingestão segue por texto).
- Idempotente: só embeda chunks com `embedding IS NULL` (não regenera vetores).
- Tolerante a falha: erro do provider não quebra a ingestão — é registrado com
  segurança (sem expor chave nem conteúdo integral) e a ingestão prossegue.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models
from ..ai.gateway import build_gateway, sanitize_error
from ..config import settings
from ..logging_config import get_logger

log = get_logger("documentos")


def embed_pending_chunks(db: Session, version_id: int) -> dict[str, int | bool]:
    """Gera e persiste embeddings dos chunks pendentes de uma document_version.

    Retorna telemetria (sem segredos): quantos chunks estavam pendentes, quantos
    embeddings foram solicitados/executados/persistidos e se houve falha. Nunca
    levanta exceção: qualquer erro é capturado para não quebrar a ingestão.
    """
    telemetry: dict[str, int | bool] = {
        "embeddings_pendentes": 0,
        "embeddings_solicitados": 0,
        "embeddings_executados": 0,
        "embeddings_persistidos": 0,
        "embeddings_falhos": 0,
        "provider_disponivel": bool(settings.effective_llm_api_key),
        "dimensao": 0,
    }

    if not settings.effective_llm_api_key:
        # Sem chave/provider: ingestão continua por texto; nada a fazer aqui.
        return telemetry

    # Idempotência: apenas chunks ainda sem vetor.
    chunks = (
        db.query(models.DocumentChunk)
        .filter(
            models.DocumentChunk.document_version_id == version_id,
            models.DocumentChunk.embedding.is_(None),
        )
        .all()
    )
    telemetry["embeddings_pendentes"] = len(chunks)
    if not chunks:
        return telemetry

    telemetry["embeddings_solicitados"] = len(chunks)
    try:
        vectors = build_gateway().embed([chunk.content for chunk in chunks])
    except Exception as exc:  # falha do provider não pode quebrar a ingestão
        telemetry["embeddings_falhos"] = len(chunks)
        log.warning(
            "embedding de chunks falhou: version_id=%s chunks=%d erro=%s",
            version_id, len(chunks), sanitize_error(str(exc)),
        )
        return telemetry

    telemetry["embeddings_executados"] = len(vectors)
    persisted = 0
    for chunk, embedding in zip(chunks, vectors):
        if embedding is None:
            telemetry["embeddings_falhos"] = int(telemetry["embeddings_falhos"]) + 1
            continue
        if len(embedding) != settings.embedding_dimensions:
            # Dimensão incompatível com o modelo/coluna: descarta com segurança.
            telemetry["embeddings_falhos"] = int(telemetry["embeddings_falhos"]) + 1
            log.warning(
                "embedding com dimensao inesperada: version_id=%s obtido=%d esperado=%d",
                version_id, len(embedding), settings.embedding_dimensions,
            )
            continue
        chunk.embedding = embedding
        telemetry["dimensao"] = len(embedding)
        persisted += 1

    telemetry["embeddings_persistidos"] = persisted
    if persisted:
        db.flush()
    log.info(
        "embeddings de chunks: version_id=%s pendentes=%d solicitados=%d executados=%d persistidos=%d falhos=%d dimensao=%d modelo=%s",
        version_id,
        telemetry["embeddings_pendentes"],
        telemetry["embeddings_solicitados"],
        telemetry["embeddings_executados"],
        telemetry["embeddings_persistidos"],
        telemetry["embeddings_falhos"],
        telemetry["dimensao"],
        settings.embedding_model,
    )
    return telemetry
