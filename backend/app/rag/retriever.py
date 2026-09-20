from sqlalchemy import text
from sqlalchemy.orm import Session


class HybridRetriever:
    """Retriever inicial que combina similaridade vetorial, texto e metadados."""

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, embedding: list[float] | None = None, property_id: int | None = None, limit: int = 8) -> list[dict]:
        filters = "AND d.property_id = :property_id" if property_id else ""
        params = {"query": query, "limit": limit, "property_id": property_id}
        if embedding:
            sql = text(f"""
                SELECT c.id, c.content, c.page, c.section, v.document_id,
                       (1 - (c.embedding <=> CAST(:embedding AS vector))) AS vector_score,
                       ts_rank_cd(to_tsvector('portuguese', c.content), plainto_tsquery('portuguese', :query)) AS text_score
                FROM document_chunks c
                JOIN document_versions v ON v.id = c.document_version_id
                JOIN documents d ON d.id = v.document_id
                WHERE c.embedding IS NOT NULL {filters}
                ORDER BY (COALESCE(vector_score, 0) * 0.7 + COALESCE(text_score, 0) * 0.3) DESC
                LIMIT :limit
            """)
            params["embedding"] = str(embedding)
        else:
            sql = text(f"""
                SELECT c.id, c.content, c.page, c.section, v.document_id,
                       0 AS vector_score,
                       ts_rank_cd(to_tsvector('portuguese', c.content), plainto_tsquery('portuguese', :query)) AS text_score
                FROM document_chunks c
                JOIN document_versions v ON v.id = c.document_version_id
                JOIN documents d ON d.id = v.document_id
                WHERE to_tsvector('portuguese', c.content) @@ plainto_tsquery('portuguese', :query) {filters}
                ORDER BY text_score DESC LIMIT :limit
            """)
        return [dict(row) for row in self.db.execute(sql, params).mappings().all()]
