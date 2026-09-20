from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings


@dataclass(frozen=True)
class RetrieverFilters:
    property_id: int | None = None
    document_id: int | None = None
    document_type: str | None = None
    document_version: int | None = None
    category: str | None = None


def clamp_limit(limit: int | None) -> int:
    requested = settings.rag_default_limit if limit is None else int(limit)
    return max(1, min(requested, settings.rag_max_limit))


def normalize_vector_score(score: float | None) -> float:
    return max(0.0, min(float(score or 0.0), 1.0))


def calculate_final_score(vector_score: float | None, text_score: float | None, max_text_score: float | None, vector_weight: float | None = None, text_weight: float | None = None) -> float:
    vector_weight = settings.rag_vector_weight if vector_weight is None else vector_weight
    text_weight = settings.rag_text_weight if text_weight is None else text_weight
    total_weight = vector_weight + text_weight
    if total_weight <= 0:
        raise ValueError("Os pesos do ranking RAG devem somar um valor maior que zero")
    normalized_vector = normalize_vector_score(vector_score)
    normalized_text = 0.0 if not max_text_score or max_text_score <= 0 else max(0.0, min(float(text_score or 0.0) / float(max_text_score), 1.0))
    return (normalized_vector * vector_weight + normalized_text * text_weight) / total_weight


class HybridRetriever:
    """Recuperador híbrido PostgreSQL isolado por imóvel e preparado para filtros."""

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, embedding: list[float] | None = None, property_id: int | None = None, limit: int | None = None, filters: RetrieverFilters | None = None) -> list[dict[str, Any]]:
        filters = filters or RetrieverFilters(property_id=property_id)
        if property_id is not None and filters.property_id is None:
            filters = replace(filters, property_id=property_id)
        effective_limit = clamp_limit(limit)
        has_embedding = bool(embedding)
        where = [":has_embedding OR to_tsvector(CAST(:text_config AS regconfig), c.content) @@ plainto_tsquery(CAST(:text_config AS regconfig), :query)"]
        params: dict[str, Any] = {"query": query, "limit": effective_limit, "has_embedding": has_embedding, "text_config": settings.rag_text_config, "vector_weight": settings.rag_vector_weight, "text_weight": settings.rag_text_weight, "embedding": str(embedding or [0.0] * settings.embedding_dimensions)}
        if filters.property_id is not None:
            where.append("d.property_id = :property_id"); params["property_id"] = filters.property_id
        if filters.document_id is not None:
            where.append("d.id = :document_id"); params["document_id"] = filters.document_id
        if filters.document_type is not None:
            where.append("d.document_type = :document_type"); params["document_type"] = filters.document_type
        if filters.document_version is not None:
            where.append("v.version = :document_version"); params["document_version"] = filters.document_version
        if filters.category is not None:
            where.append("c.metadata_json ->> 'category' = :category"); params["category"] = filters.category

        where_sql = " AND ".join(where)
        sql = text(f"""
            WITH candidates AS (
                SELECT
                    c.id AS chunk_id,
                    c.content,
                    c.page,
                    c.section,
                    c.chunk_index,
                    c.metadata_json,
                    c.document_version_id,
                    d.id AS document_id,
                    v.version AS document_version,
                    d.property_id,
                    d.name AS document_name,
                    d.document_type,
                    d.source AS document_source,
                    CASE
                        WHEN :has_embedding AND c.embedding IS NOT NULL
                        THEN GREATEST(0.0, LEAST(1.0, 1.0 - (c.embedding <=> CAST(:embedding AS vector))))
                        ELSE 0.0
                    END AS vector_score,
                    ts_rank_cd(
                        to_tsvector(CAST(:text_config AS regconfig), c.content),
                        plainto_tsquery(CAST(:text_config AS regconfig), :query)
                    ) AS text_score
                FROM document_chunks c
                JOIN document_versions v ON v.id = c.document_version_id
                JOIN documents d ON d.id = v.document_id
                WHERE {where_sql}
            ),
            scored AS (
                SELECT
                    candidates.*,
                    CASE
                        WHEN MAX(text_score) OVER () > 0
                        THEN LEAST(1.0, text_score / MAX(text_score) OVER ())
                        ELSE 0.0
                    END AS normalized_text_score
                FROM candidates
            )
            SELECT
                chunk_id,
                content,
                document_id,
                document_version_id,
                document_version,
                document_name,
                document_type,
                document_source,
                property_id,
                page,
                section,
                chunk_index,
                metadata_json,
                vector_score,
                text_score,
                normalized_text_score,
                (
                    (vector_score * :vector_weight) +
                    (normalized_text_score * :text_weight)
                ) / NULLIF(:vector_weight + :text_weight, 0) AS final_score
            FROM scored
            WHERE :has_embedding OR text_score > 0
            ORDER BY final_score DESC, chunk_id ASC
            LIMIT :limit
        """)
        return [dict(row) for row in self.db.execute(sql, params).mappings().all()]
