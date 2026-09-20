from sqlalchemy.orm import Session
from .retriever import HybridRetriever
from ..ai.gateway import build_gateway


class RAGService:
    def __init__(self, db: Session):
        self.db = db

    def retrieve_context(self, query: str, property_id: int | None = None, limit: int = 8) -> list[dict]:
        embedding = None
        try:
            embedding = build_gateway().embed([query])[0]
        except RuntimeError:
            pass
        return HybridRetriever(self.db).search(query, embedding, property_id, limit)

    def context_text(self, query: str, property_id: int | None = None, limit: int = 8) -> tuple[str, list[int]]:
        chunks = self.retrieve_context(query, property_id, limit)
        context = "\n\n".join(f"[Documento {c['document_id']} · página {c.get('page') or '?'}]\n{c['content']}" for c in chunks)
        return context, [c["id"] for c in chunks]
