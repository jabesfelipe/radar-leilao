from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from .retriever import HybridRetriever, RetrieverFilters, clamp_limit
from ..ai.gateway import build_gateway
from ..config import settings


@dataclass(frozen=True)
class RAGResult:
    context: str
    chunks: list[dict[str, Any]]
    chunk_ids: list[int]
    count: int
    context_found: bool
    vector_search: bool
    text_fallback: bool
    reason: str | None = None


class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self.retriever = HybridRetriever(db)

    def retrieve_context(self, query: str, property_id: int | None = None, limit: int | None = None, filters: RetrieverFilters | None = None) -> RAGResult:
        effective_filters = filters or RetrieverFilters(property_id=property_id)
        embedding = None
        text_fallback = False
        reason = None
        try:
            if not settings.effective_llm_api_key:
                text_fallback = True
                reason = "OPENAI_API_KEY não configurada"
            else:
                embedding = build_gateway().embed([query])[0]
        except RuntimeError as exc:
            text_fallback = True
            reason = str(exc)
        except Exception as exc:
            text_fallback = True
            reason = f"Busca vetorial indisponível: {exc}"
        chunks = self.retriever.search(query=query, embedding=embedding, property_id=property_id, limit=clamp_limit(limit), filters=effective_filters)
        context = "\n\n".join(self._format_chunk(chunk) for chunk in chunks)
        return RAGResult(context=context, chunks=chunks, chunk_ids=[chunk["chunk_id"] for chunk in chunks], count=len(chunks), context_found=bool(chunks), vector_search=embedding is not None, text_fallback=text_fallback, reason="evidência insuficiente" if not chunks else None)

    def context_text(self, query: str, property_id: int | None = None, limit: int | None = None, filters: RetrieverFilters | None = None) -> RAGResult:
        return self.retrieve_context(query=query, property_id=property_id, limit=limit, filters=filters)

    @staticmethod
    def _format_chunk(chunk: dict[str, Any]) -> str:
        return (f"[chunk_id={chunk['chunk_id']} property_id={chunk['property_id']} document_id={chunk['document_id']} "
                f"document_version_id={chunk['document_version_id']} document_version={chunk['document_version']} "
                f"document_type={chunk['document_type']} page={chunk.get('page') or '?'} section={chunk.get('section') or '?'} "
                f"vector_score={chunk['vector_score']:.4f} text_score={chunk['text_score']:.4f} final_score={chunk['final_score']:.4f}]\n"
                f"{chunk['content']}")
