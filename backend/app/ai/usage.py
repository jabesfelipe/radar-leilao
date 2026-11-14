"""Contabilização de EMBEDDINGS em ``llm_runs`` (antes invisíveis ao orçamento).

A API de embeddings do LangChain não devolve a contagem de tokens; por isso o registro usa uma
ESTIMATIVA (``caracteres / 4``, ordem de grandeza para texto em português) e o preço de referência
``EMBEDDING_PRICE_PER_1M_USD``. O registro é gravado numa sessão PRÓPRIA e confirmado na hora:
o gasto já aconteceu, mesmo que a requisição que o originou sofra rollback.

Política de custo para chamadas que FALHAM (conservadora): erros que podem ter sido cobrados
(timeout, provedor, desconhecido) contam o custo estimado; erros em que a OpenAI recusa antes de
processar (autenticação, limite de taxa, requisição inválida, conexão, orçamento) não contam.
Mesmo assim, o valor real deve ser conferido no painel da OpenAI.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from .. import models
from ..config import settings
from ..logging_config import get_logger

log = get_logger("llm.uso")

# Categorias de erro em que a chamada PODE ter sido cobrada pelo provider.
POSSIBLY_BILLED_ERRORS = frozenset({"TIMEOUT", "PROVEDOR", "DESCONHECIDO"})


def estimate_tokens(texts: list[str]) -> int:
    return sum(len(t or "") for t in texts) // 4 + len(texts)


def embedding_cost(tokens: int) -> Decimal:
    return Decimal(tokens) / Decimal(1_000_000) * Decimal(str(settings.embedding_price_per_1m_usd))


def record_embedding_usage(*, model: str, texts: list[str], status: str, error_category: str | None = None, error_message: str | None = None) -> None:
    """Grava uma linha em ``llm_runs`` (agent='embedding'). Nunca levanta exceção."""
    try:
        from ..database import SessionLocal
        tokens = estimate_tokens(texts)
        counts = status == "CONCLUIDO" or (error_category in POSSIBLY_BILLED_ERRORS)
        cost = embedding_cost(tokens) if counts else None
        with SessionLocal() as session:
            session.add(models.LLMRun(
                agent="embedding", provider="openai", model=model,
                input_tokens=tokens, output_tokens=0, total_tokens=tokens,
                input_cost=cost, output_cost=Decimal(0) if cost is not None else None, total_cost=cost,
                input_price_per_1m=Decimal(str(settings.embedding_price_per_1m_usd)),
                status=status, error_type=error_category, error_message=(error_message or "tokens estimados (caracteres/4)")[:500],
                retrieved_chunk_ids=[],
            ))
            session.commit()
    except Exception as exc:  # contabilização nunca derruba o fluxo, mas a falha precisa aparecer no log
        log.error("falha ao registrar uso de embeddings em llm_runs: %s", type(exc).__name__)


def usage_summary(rows: list[Any]) -> dict[str, Any]:
    return {"chamadas": len(rows)}
