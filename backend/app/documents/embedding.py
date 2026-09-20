from sqlalchemy.orm import Session
from .. import models
from ..ai.gateway import build_gateway


def embed_pending_chunks(db: Session, version_id: int) -> int:
    chunks = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version_id, models.DocumentChunk.embedding.is_(None)).all()
    if not chunks:
        return 0
    embeddings = build_gateway().embed([chunk.content for chunk in chunks])
    for chunk, embedding in zip(chunks, embeddings): chunk.embedding = embedding
    db.flush()
    return len(chunks)
