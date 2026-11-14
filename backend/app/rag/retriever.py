from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..documents import states as doc_states

_TOKEN = re.compile(r"[^\W_]{2,}", re.UNICODE)


def build_or_tsquery(query: str | None) -> str | None:
    """Converte o texto da consulta em uma ``tsquery`` com OR entre os termos.

    ``plainto_tsquery`` exige TODOS os termos (AND): com a consulta padrão ("análise
    documental do imóvel") um documento sem a palavra "análise" nunca era encontrado.
    Os termos são reduzidos a caracteres alfanuméricos (sem operadores), então a expressão é
    segura para ``to_tsquery``. Retorna ``None`` se não houver termo utilizável.
    """
    seen: list[str] = []
    for token in _TOKEN.findall((query or "").lower()):
        if token not in seen:
            seen.append(token)
    return " | ".join(seen[:24]) if seen else None


@dataclass(frozen=True)
class RetrieverFilters:
    property_id: int | None = None
    document_id: int | None = None
    document_type: str | None = None
    document_version: int | None = None
    category: str | None = None
    opportunity_id: int | None = None  # isolamento por oportunidade (via metadata do chunk)


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

    def search(self, query: str, embedding: list[float] | None = None, property_id: int | None = None, limit: int | None = None, filters: RetrieverFilters | None = None, broad: bool = False, allow_global: bool = False) -> list[dict[str, Any]]:
        """Busca híbrida. ``broad=True`` é para consultas GENÉRICAS de contexto (consulta padrão da análise,
        consultas fixas dos agentes): a busca textual passa a usar OR entre os termos e, sem vetor e sem
        nenhuma correspondência, devolve os primeiros trechos dos documentos prontos (``match_type=posicional``).
        Consultas explícitas (usuário, itens do checklist) continuam estritas (AND), sem inventar contexto."""
        filters = filters or RetrieverFilters(property_id=property_id)
        if property_id is not None and filters.property_id is None:
            filters = replace(filters, property_id=property_id)
        if filters.property_id is None and not allow_global:
            # Isolamento FECHADO por padrão: uma busca sem imóvel atravessaria todos os imóveis (e todos os
            # documentos reais). Quem realmente precisa de busca global deve pedir ``allow_global=True``.
            raise ValueError("Busca RAG exige property_id (isolamento por imóvel)")
        effective_limit = clamp_limit(limit)
        has_embedding = bool(embedding)
        or_query = build_or_tsquery(query) if broad else None
        tsquery = "to_tsquery(CAST(:text_config AS regconfig), :or_query)" if or_query else "plainto_tsquery(CAST(:text_config AS regconfig), :query)"
        # ATENÇÃO: parênteses obrigatórios. Sem eles, ``A OR B AND filtro_de_imovel`` vira ``A OR (B AND filtro)`` e,
        # com embedding (``:has_embedding`` verdadeiro), TODOS os filtros (imóvel, versão, estado) eram ignorados.
        where = [f"(:has_embedding OR to_tsvector(CAST(:text_config AS regconfig), c.content) @@ {tsquery})"]
        params: dict[str, Any] = {"query": query, "or_query": or_query, "limit": effective_limit, "has_embedding": has_embedding, "text_config": settings.rag_text_config, "vector_weight": settings.rag_vector_weight, "text_weight": settings.rag_text_weight, "embedding": str(embedding or [0.0] * settings.embedding_dimensions)}
        # Versões sem texto utilizável (OCR necessário/falhou, sem texto, erro) nunca entram no RAG.
        where.append("NOT (v.status = ANY(CAST(:blocked_states AS text[])))")
        params["blocked_states"] = sorted(doc_states.NOT_READY_STATES)
        if filters.property_id is not None:
            where.append("d.property_id = :property_id"); params["property_id"] = filters.property_id
        if filters.document_id is not None:
            where.append("d.id = :document_id"); params["document_id"] = filters.document_id
        if filters.document_type is not None:
            where.append("d.document_type = :document_type"); params["document_type"] = filters.document_type
        if filters.document_version is not None:
            where.append("v.version = :document_version"); params["document_version"] = filters.document_version
        else:
            # Histórico de versões: por padrão só a versão MAIS RECENTE PRONTA de cada documento. Versões antigas
            # (substituídas) deixam de competir com a nova e de gerar fatos contraditórios; uma versão mais nova
            # ainda sem texto utilizável não esconde a anterior que está pronta.
            where.append(
                "v.version = (SELECT MAX(v2.version) FROM document_versions v2 WHERE v2.document_id = v.document_id"
                " AND NOT (v2.status = ANY(CAST(:blocked_states AS text[]))))"
            )
        if filters.category is not None:
            # Domínio de análise: chunk novo grava ``category`` + ``domains`` (documents/categories.py).
            # Chunks LEGADOS (ingeridos antes da correção, sem nenhuma das duas chaves) continuam
            # elegíveis: antes eram invisíveis a qualquer busca por domínio.
            where.append(
                "(c.metadata_json ->> 'category' = :category"
                " OR jsonb_exists(CAST(c.metadata_json AS jsonb) -> 'domains', :category)"
                " OR (c.metadata_json ->> 'category' IS NULL AND (CAST(c.metadata_json AS jsonb) -> 'domains') IS NULL))"
            )
            params["category"] = filters.category
        if filters.opportunity_id is not None:
            # Isolamento por oportunidade: só chunks cujo metadata carrega o mesmo
            # opportunity_id. Chunks sem o campo (legado/sem contexto de oportunidade)
            # NÃO vazam para um escopo restrito — comportamento seguro por padrão.
            where.append("c.metadata_json ->> 'opportunity_id' = :opportunity_id")
            params["opportunity_id"] = str(filters.opportunity_id)

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
                        {tsquery}
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
        rows = [dict(row) for row in self.db.execute(sql, params).mappings().all()]
        for row in rows:
            row["match_type"] = "vetor" if has_embedding else "texto"
        if broad and not rows and not has_embedding and filters.property_id is not None:
            rows = self._positional_fallback(" AND ".join(where[1:]), params, effective_limit)
        return rows

    def _positional_fallback(self, where_sql: str, params: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        """Sem embedding e sem nenhuma correspondência textual: devolve os primeiros trechos
        dos documentos PRONTOS do imóvel (mesmos filtros de imóvel/domínio/estado), marcados
        ``match_type='posicional'`` e com score 0. É contexto de contingência explícito — o
        chamador (RAGService) sinaliza isso no resultado; nunca é apresentado como busca
        relevante. Só ocorre sem vetor (com vetor a busca já devolve os mais próximos)."""
        sql = text(f"""
            SELECT c.id AS chunk_id, c.content, d.id AS document_id, c.document_version_id,
                   v.version AS document_version, d.name AS document_name, d.document_type,
                   d.source AS document_source, d.property_id, c.page, c.section, c.chunk_index,
                   c.metadata_json, CAST(0 AS float) AS vector_score, CAST(0 AS float) AS text_score,
                   CAST(0 AS float) AS normalized_text_score, CAST(0 AS float) AS final_score
            FROM document_chunks c
            JOIN document_versions v ON v.id = c.document_version_id
            JOIN documents d ON d.id = v.document_id
            WHERE {where_sql}
            ORDER BY d.id ASC, v.version DESC, c.chunk_index ASC
            LIMIT :limit
        """)
        rows = [dict(row) for row in self.db.execute(sql, params).mappings().all()]
        for row in rows:
            row["match_type"] = "posicional"
        return rows
