"""RAG direcionado para o Checklist Mestre.

Em vez de uma única busca genérica servir aos 27 itens, aqui derivamos uma
consulta por item (a partir de question/description/expected_evidence/category do
próprio Checklist Mestre) e reutilizamos o RAG existente (HybridRetriever) para
recuperar contexto relevante por item. Os chunks são deduplicados por chunk_id,
preservando rastreabilidade (quais perguntas recuperaram cada chunk), e o contexto
é limitado para não inflar tokens/custo.

NÃO cria um segundo mecanismo de RAG: reutiliza embeddings/pgvector/busca híbrida.
NÃO altera os 27 canonical_key nem as perguntas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..logging_config import get_logger
from .retriever import HybridRetriever, RetrieverFilters
from .service import RAGService

log = get_logger("rag.checklist")

# Quantos chunks recuperar por item (pequeno, para evitar explosão de contexto).
PER_ITEM_LIMIT = 4
# Teto de chunks distintos no contexto direcionado consolidado.
MAX_TOTAL_CHUNKS = 24


def build_item_query(item: dict[str, Any]) -> str:
    """Deriva uma consulta a partir dos campos do próprio item do Checklist.

    Usa question/description/expected_evidence/related_rules (quando presentes),
    sem listas manuais gigantes de palavras. A category entra como reforço leve.
    """
    parts: list[str] = []
    for key in ("question", "description"):
        value = item.get(key)
        if value and value not in parts:
            parts.append(str(value))
    for key in ("expected_evidence", "related_rules"):
        values = item.get(key) or []
        parts.extend(str(v) for v in values if v)
    category = item.get("category")
    if category:
        parts.append(str(category).lower())
    # Deduplica preservando ordem.
    seen: set[str] = set()
    query_parts = [p for p in parts if not (p in seen or seen.add(p))]
    return " ".join(query_parts).strip() or (item.get("canonical_key") or "")


@dataclass
class DirectedRetrieval:
    context: str
    chunk_ids: list[int]
    chunks: list[dict[str, Any]]
    per_item: dict[str, list[int]] = field(default_factory=dict)
    queries: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": len(self.chunk_ids),
            "chunk_ids": self.chunk_ids,
            "per_item": self.per_item,
            "queries": self.queries,
        }


def retrieve_for_checklist(db: Session, property_id: int, checklist_items: list[dict[str, Any]]) -> DirectedRetrieval:
    """Recupera contexto direcionado por item do Checklist, deduplicado e limitado.

    Perguntas diferentes podem recuperar chunks diferentes. Chunks repetidos entre
    perguntas são consolidados uma única vez, mantendo o registro de quais
    perguntas os recuperaram (rastreabilidade). Reutiliza o HybridRetriever/RAG.
    """
    retriever = HybridRetriever(db)
    rag = RAGService(db)

    aggregated: dict[int, dict[str, Any]] = {}
    per_item: dict[str, list[int]] = {}
    queries: dict[str, str] = {}
    # Rastreabilidade reversa: quais perguntas recuperaram cada chunk.
    chunk_questions: dict[int, list[str]] = {}

    for item in checklist_items:
        key = item.get("canonical_key")
        if not key:
            continue
        query = build_item_query(item)
        queries[key] = query
        embedding = None
        try:
            if settings.effective_llm_api_key:
                from ..ai.gateway import build_gateway
                embedding = build_gateway().embed([query])[0]
        except Exception:
            embedding = None  # cai no modo texto do retriever
        results = retriever.search(
            query=query,
            embedding=embedding,
            property_id=property_id,
            limit=PER_ITEM_LIMIT,
            filters=RetrieverFilters(property_id=property_id),
        )
        ids_for_item: list[int] = []
        for chunk in results:
            chunk_id = chunk["chunk_id"]
            ids_for_item.append(chunk_id)
            chunk_questions.setdefault(chunk_id, [])
            if key not in chunk_questions[chunk_id]:
                chunk_questions[chunk_id].append(key)
            # Mantém o chunk com o maior final_score observado.
            if chunk_id not in aggregated or chunk["final_score"] > aggregated[chunk_id]["final_score"]:
                aggregated[chunk_id] = chunk
        per_item[key] = ids_for_item

    # Ordena por relevância e aplica o teto global de chunks distintos.
    ordered = sorted(aggregated.values(), key=lambda c: c["final_score"], reverse=True)[:MAX_TOTAL_CHUNKS]
    ordered_ids = [chunk["chunk_id"] for chunk in ordered]

    # Formata o contexto reutilizando o formatador do RAG e anexando as perguntas
    # relacionadas (rastreabilidade item->chunk) sem alterar o conteúdo do chunk.
    blocks: list[str] = []
    for chunk in ordered:
        related = chunk_questions.get(chunk["chunk_id"], [])
        header = f"[checklist_keys={','.join(related)}]" if related else ""
        blocks.append(f"{header}\n{rag._format_chunk(chunk)}".strip())
    context = "\n\n".join(blocks)

    log.info("rag checklist direcionado: property_id=%s itens=%d chunks_distintos=%d (teto=%d por_item=%d)",
             property_id, len(checklist_items), len(ordered_ids), MAX_TOTAL_CHUNKS, PER_ITEM_LIMIT)

    return DirectedRetrieval(
        context=context,
        chunk_ids=ordered_ids,
        chunks=ordered,
        per_item=per_item,
        queries=queries,
    )
