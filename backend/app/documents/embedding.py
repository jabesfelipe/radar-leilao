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
from ..ai.gateway import build_gateway, classify_provider_error, sanitize_error
from ..config import settings
from ..logging_config import get_logger
from ..privacy_context import aliaser_for_property

log = get_logger("documentos")


def embed_pending_chunks(db: Session, version_id: int) -> dict[str, int | bool]:
    """Gera e persiste embeddings dos chunks pendentes de uma document_version.

    Retorna telemetria (sem segredos): quantos chunks estavam pendentes, quantos
    embeddings foram solicitados/executados/persistidos e se houve falha. Nunca
    levanta exceção: qualquer erro é capturado para não quebrar a ingestão.
    """
    telemetry: dict[str, int | bool | str] = {
        "embeddings_pendentes": 0,
        "embeddings_solicitados": 0,
        "embeddings_executados": 0,
        "embeddings_persistidos": 0,
        "embeddings_falhos": 0,
        "provider_disponivel": bool(settings.effective_llm_api_key),
        "dimensao": 0,
        "tokens_estimados": 0,
        "custo_estimado_usd": 0.0,
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
    # Estimativa de custo (sem chamada extra): ~4 caracteres por token x preço de referência.
    # Só para log/telemetria; o custo real deve ser conferido no painel da OpenAI.
    estimated_tokens = sum(len(chunk.content or "") for chunk in chunks) // 4
    telemetry["tokens_estimados"] = estimated_tokens
    telemetry["custo_estimado_usd"] = round(estimated_tokens * settings.embedding_price_per_1m_usd / 1_000_000, 6)
    try:
        texts = [chunk.content for chunk in chunks]
        try:
            # Pseudonimização de pessoas físicas conhecidas do imóvel (titular, partes, ocupantes + nomes após
            # rótulos jurídicos) ANTES do envio ao provider. O texto armazenado no banco não é alterado.
            document = chunks[0].document_version.document
            aliaser = aliaser_for_property(db, document.property_id)
            for text in texts:
                aliaser.learn_from_text(text)
            texts = [aliaser.apply(text) for text in texts]
        except Exception:
            texts = [chunk.content for chunk in chunks]   # o gateway ainda mascara identificadores
        vectors = build_gateway().embed(texts)
    except Exception as exc:  # falha do provider não pode quebrar a ingestão
        telemetry["embeddings_falhos"] = len(chunks)
        # Registra a causa (sanitizada) na telemetria para o chamador persistir em
        # ``extraction_metadata`` — antes o erro só aparecia no log.
        telemetry["erro_categoria"] = classify_provider_error(exc)
        telemetry["erro"] = sanitize_error(str(exc))[:400]
        log.warning(
            "embedding de chunks falhou: version_id=%s chunks=%d categoria=%s erro=%s",
            version_id, len(chunks), telemetry["erro_categoria"], sanitize_error(str(exc)),
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
        "embeddings de chunks: version_id=%s pendentes=%d solicitados=%d executados=%d persistidos=%d falhos=%d dimensao=%d modelo=%s tokens_est=%d custo_est_usd=%s",
        version_id,
        telemetry["embeddings_pendentes"],
        telemetry["embeddings_solicitados"],
        telemetry["embeddings_executados"],
        telemetry["embeddings_persistidos"],
        telemetry["embeddings_falhos"],
        telemetry["dimensao"],
        settings.embedding_model,
        telemetry["tokens_estimados"],
        telemetry["custo_estimado_usd"],
    )
    return telemetry
