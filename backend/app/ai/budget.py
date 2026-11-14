"""Orçamento mensal de LLM (controle de custo na aplicação).

Soma ``llm_runs.total_cost`` do mês corrente (UTC). Quando ``LLM_BUDGET_USD_MONTH`` está
definido e o gasto registrado atinge o teto, o gateway deixa de ser criado: os agentes
devolvem ``ORCAMENTO_EXCEDIDO`` em vez de chamar a OpenAI.

O que entra no orçamento (``llm_runs``):
- chamadas de CHAT, com os tokens reais devolvidos pela OpenAI (inclusive respostas inválidas, já cobradas);
- EMBEDDINGS, com tokens ESTIMADOS (caracteres/4) e preço de referência (``ai/usage.py``).
Sem preço ativo em ``llm_pricing`` para o modelo de chat, o orçamento falha FECHADO (``sem_preco``).

Limites desta proteção (ver PLANO-ATIVACAO-OPENAI.md):
- a estimativa de embeddings é aproximada; retries internos do SDK (``LLM_MAX_RETRIES``) podem cobrar
  uma chamada duas vezes e não são vistos pela aplicação;
- o teto é verificado ANTES de cada chamada; análises simultâneas podem ultrapassá-lo em até
  (nº de análises simultâneas × ``LLM_BUDGET_USD_PER_ANALYSIS``);
- NÃO substitui o limite de gasto no painel da OpenAI, que continua obrigatório.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    # created_at é gravado sem timezone (UTC); compara com datetime ingênuo.
    return datetime(now.year, now.month, 1)


def month_status(db: Session | None = None) -> dict[str, Any]:
    """Gasto do mês x teto. Sem teto configurado: ``limite=None`` e ``excedido=False``."""
    limit = settings.llm_budget_usd_month
    if limit is None:
        return {"limite_usd": None, "gasto_usd": None, "excedido": False, "sem_preco": False}
    own = db is None
    if own:
        from ..database import SessionLocal
        db = SessionLocal()
    try:
        spent = db.scalar(
            select(func.coalesce(func.sum(models.LLMRun.total_cost), 0)).where(models.LLMRun.created_at >= _month_start())
        ) or Decimal("0")
        # Sem preço ativo do modelo de chat em llm_pricing, ``total_cost`` fica None e o gasto contabilizado
        # seria sempre 0: o orçamento não teria como disparar. Sinalizado para falhar FECHADO.
        from .costs import resolve_pricing
        sem_preco = resolve_pricing(db, settings.llm_provider, settings.llm_model) is None
    finally:
        if own:
            db.close()
    spent_f = float(spent)
    return {"limite_usd": float(limit), "gasto_usd": round(spent_f, 6), "excedido": spent_f >= float(limit), "sem_preco": sem_preco}


def pricing_missing(db: Session | None = None) -> bool:
    """O modelo de chat configurado NÃO tem preço ativo em ``llm_pricing``.

    Com qualquer teto configurado (mensal OU por análise) isso precisa falhar FECHADO: sem preço o custo de cada
    chamada é desconhecido (None) e nenhum teto dispararia — gasto ilimitado por ausência de preço."""
    from .costs import resolve_pricing
    own = db is None
    if own:
        from ..database import SessionLocal
        db = SessionLocal()
    try:
        return resolve_pricing(db, settings.llm_provider, settings.llm_model) is None
    finally:
        if own:
            db.close()


def unavailable_reason(db: Session | None = None) -> tuple[str, str]:
    """Por que o LLM não está disponível: (status do LLMCall, mensagem pública)."""
    if not settings.effective_llm_api_key:
        return "SEM_CHAVE", "LLM não configurada; análise deste domínio aguarda OPENAI_API_KEY"
    if settings.llm_require_budget and (settings.llm_budget_usd_month is None or settings.llm_budget_usd_per_analysis is None):
        from .gateway import MISSING_BUDGET_MESSAGE
        return "ORCAMENTO_EXCEDIDO", MISSING_BUDGET_MESSAGE
    try:
        status = month_status(db)
        if status["excedido"]:
            return "ORCAMENTO_EXCEDIDO", "Orçamento mensal de IA atingido; nenhuma chamada foi feita ao provider"
        if status.get("sem_preco") or (settings.llm_budget_usd_per_analysis is not None and pricing_missing(db)):
            return "ORCAMENTO_EXCEDIDO", "Modelo sem preço em llm_pricing: o orçamento não pode ser aplicado; nenhuma chamada foi feita"
    except Exception:
        pass
    return "SEM_CHAVE", "Provider de LLM indisponível; análise deste domínio não foi executada"
