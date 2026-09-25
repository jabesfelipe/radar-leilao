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


def _document_key(chunk: dict[str, Any]) -> Any:
    """Identidade do documento de origem do chunk para a cota de diversidade.

    Usa document_id (agrupa todas as versões do mesmo documento). Cai para
    document_version_id e, por fim, para o próprio chunk_id, se necessário.
    """
    return chunk.get("document_id") or chunk.get("document_version_id") or chunk.get("chunk_id")


def _select_with_document_diversity(chunks: list[dict[str, Any]], max_total: int) -> list[dict[str, Any]]:
    """Seleciona até max_total chunks garantindo diversidade por documento.

    Agrupa os candidatos por documento de origem, ordena cada grupo por
    final_score desc e percorre os grupos em round-robin (grupos ordenados pelo
    melhor score de cada um). Assim nenhum documento monopoliza todos os slots e
    documentos distintos (ex.: edital e matrícula) coexistem no resultado, sem
    aumentar o teto e preservando a ordem por relevância dentro de cada documento.
    """
    if max_total <= 0 or not chunks:
        return []
    grupos: dict[Any, list[dict[str, Any]]] = {}
    for chunk in chunks:
        grupos.setdefault(_document_key(chunk), []).append(chunk)
    for lista in grupos.values():
        lista.sort(key=lambda c: c["final_score"], reverse=True)
    # Ordena os grupos pelo melhor score de cada documento (documento mais
    # relevante primeiro), mantendo determinismo.
    ordem_grupos = sorted(grupos.values(), key=lambda g: g[0]["final_score"], reverse=True)
    selecionados: list[dict[str, Any]] = []
    indice = 0
    while len(selecionados) < max_total and any(indice < len(g) for g in ordem_grupos):
        for grupo in ordem_grupos:
            if indice < len(grupo):
                selecionados.append(grupo[indice])
                if len(selecionados) >= max_total:
                    break
        indice += 1
    # Mantém o resultado final ordenado por relevância (não altera rastreabilidade).
    selecionados.sort(key=lambda c: c["final_score"], reverse=True)
    return selecionados


@dataclass
class DirectedRetrieval:
    context: str
    chunk_ids: list[int]
    chunks: list[dict[str, Any]]
    per_item: dict[str, list[int]] = field(default_factory=dict)
    queries: dict[str, str] = field(default_factory=dict)
    # Telemetria de custo/recuperação (não contém conteúdo de documento nem segredos).
    telemetry: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": len(self.chunk_ids),
            "chunk_ids": self.chunk_ids,
            "per_item": self.per_item,
            "queries": self.queries,
            "telemetry": self.telemetry,
        }


def retrieve_for_checklist(db: Session, property_id: int, checklist_items: list[dict[str, Any]], analysis_id: int | None = None) -> DirectedRetrieval:
    """Recupera contexto direcionado por item do Checklist, deduplicado e limitado.

    Perguntas diferentes podem recuperar chunks diferentes. Chunks repetidos entre
    perguntas são consolidados uma única vez, mantendo o registro de quais
    perguntas os recuperaram (rastreabilidade). Reutiliza o HybridRetriever/RAG.

    Mede a quantidade de embeddings solicitados/executados/falhos e de chunks
    recuperados/distintos (telemetria de custo) — sem multiplicar chamadas de LLM
    de geração e sem registrar conteúdo do documento ou segredos.
    """
    retriever = HybridRetriever(db)
    rag = RAGService(db)

    aggregated: dict[int, dict[str, Any]] = {}
    per_item: dict[str, list[int]] = {}
    queries: dict[str, str] = {}
    # Rastreabilidade reversa: quais perguntas recuperaram cada chunk.
    chunk_questions: dict[int, list[str]] = {}

    # Telemetria de custo do RAG direcionado.
    items_with_query = 0
    embeddings_requested = 0
    embeddings_executed = 0
    embeddings_failed = 0
    chunks_recuperados_total = 0
    use_vector = bool(settings.effective_llm_api_key)

    for item in checklist_items:
        key = item.get("canonical_key")
        if not key:
            continue
        query = build_item_query(item)
        queries[key] = query
        items_with_query += 1
        embedding = None
        if use_vector:
            embeddings_requested += 1
            try:
                from ..ai.gateway import build_gateway
                embedding = build_gateway().embed([query])[0]
                embeddings_executed += 1
            except Exception:
                embeddings_failed += 1
                embedding = None  # cai no modo texto do retriever
        results = retriever.search(
            query=query,
            embedding=embedding,
            property_id=property_id,
            limit=PER_ITEM_LIMIT,
            filters=RetrieverFilters(property_id=property_id),
        )
        chunks_recuperados_total += len(results)
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

    # Seleção final com DIVERSIDADE POR DOCUMENTO (TASK 68).
    # Antes: sorted(...)[:MAX_TOTAL_CHUNKS] por score puro. Quando um documento tem
    # muito mais chunks vetorizados que outro (ex.: edital com 544 embeddings vs
    # matrícula com 8), o score puro faz o documento maior monopolizar todos os
    # slots e o outro é sistematicamente excluído. Para que documentos relevantes
    # (edital E matrícula) COEXISTAM no contexto, distribuímos os MAX_TOTAL_CHUNKS
    # por documento em round-robin (cada volta pega o melhor chunk ainda disponível
    # de cada documento, por ordem de score). Não altera PER_ITEM_LIMIT nem o teto,
    # não muda pesos/consulta/ranking do retriever e não recupera nada novo:
    # apenas reordena os candidatos já recuperados para garantir representatividade.
    ordered = _select_with_document_diversity(list(aggregated.values()), MAX_TOTAL_CHUNKS)
    ordered_ids = [chunk["chunk_id"] for chunk in ordered]

    # Formata o contexto reutilizando o formatador do RAG e anexando as perguntas
    # relacionadas (rastreabilidade item->chunk) sem alterar o conteúdo do chunk.
    blocks: list[str] = []
    for chunk in ordered:
        related = chunk_questions.get(chunk["chunk_id"], [])
        header = f"[checklist_keys={','.join(related)}]" if related else ""
        blocks.append(f"{header}\n{rag._format_chunk(chunk)}".strip())
    context = "\n\n".join(blocks)

    telemetry = {
        "itens": len(checklist_items),
        "itens_com_query": items_with_query,
        "embeddings_solicitados": embeddings_requested,
        "embeddings_executados": embeddings_executed,
        "embeddings_falhos": embeddings_failed,
        "chunks_recuperados_total": chunks_recuperados_total,
        "chunks_distintos": len(ordered_ids),
        "por_item": PER_ITEM_LIMIT,
        "teto": MAX_TOTAL_CHUNKS,
    }
    log.info(
        "rag checklist direcionado: property_id=%s analysis_id=%s itens=%d embeddings_solicitados=%d "
        "embeddings_executados=%d embeddings_falhos=%d chunks_recuperados_total=%d chunks_distintos=%d (teto=%d por_item=%d)",
        property_id, analysis_id, telemetry["itens"], embeddings_requested, embeddings_executed,
        embeddings_failed, chunks_recuperados_total, len(ordered_ids), MAX_TOTAL_CHUNKS, PER_ITEM_LIMIT,
    )

    return DirectedRetrieval(
        context=context,
        chunk_ids=ordered_ids,
        chunks=ordered,
        per_item=per_item,
        queries=queries,
        telemetry=telemetry,
    )
