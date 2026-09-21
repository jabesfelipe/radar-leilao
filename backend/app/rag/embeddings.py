from __future__ import annotations

from sqlalchemy.orm import Session

from .service import RAGService
from .. import models
from ..ai.gateway import LLMGateway, build_gateway
from ..config import settings


def generate_embedding(text: str, gateway: LLMGateway | None = None) -> list[float]:
    """Gera e valida um único embedding através do gateway existente."""
    if not str(text or "").strip():
        raise ValueError("Texto para embedding é obrigatório")
    vectors = (gateway or build_gateway()).embed([text])
    if len(vectors) != 1:
        raise ValueError("Provider deve retornar exatamente um embedding")
    embedding = vectors[0]
    if len(embedding) != settings.embedding_dimensions:
        raise ValueError(f"Embedding possui dimensão {len(embedding)}; esperada {settings.embedding_dimensions}")
    return embedding


def embed_pending_chunks(db: Session, version_id: int) -> int:
    chunks = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version_id, models.DocumentChunk.embedding.is_(None)).all()
    if not chunks:
        return 0
    embeddings = [generate_embedding(chunk.content) for chunk in chunks]
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding
    db.flush()
    return len(chunks)
