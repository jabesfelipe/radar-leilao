"""Serviço de pesquisa externa (v1.0.14): provedor principal + alternativo, cache, retry, timeout, limite e registro.

Fluxo de uma consulta:

1. Pesquisa desativada (``SEARCH_ENABLED=false``) ou nenhum provedor com chave → registra NAO_CONFIGURADO e devolve vazio.
2. Cache: a mesma consulta (tipo + texto + domínios) feita com sucesso dentro de ``SEARCH_CACHE_HOURS`` é reaproveitada,
   sem nova chamada (custo zero).
3. Provedor principal com retry só para falha transitória (timeout, 5xx, 429); se falhar, o alternativo.
4. Cada chamada vira uma linha em ``external_searches`` (status, provedor, duração, tentativas, custo estimado, erro,
   resultados com URL/título/trecho/data). A API key nunca é registrada.
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from . import providers as pv

logger = logging.getLogger(__name__)

NAO_CONFIGURADO_TEXTO = ("Pesquisa automática não configurada: defina TAVILY_API_KEY (principal) ou BRAVE_SEARCH_API_KEY (alternativo) "
                         "no ambiente do backend. Sem chave, o Radar não pesquisa e não simula resultados.")


def provider_chain(primary: str | None = None, fallback: str | None = None) -> list[pv.SearchProvider]:
    names = [primary if primary is not None else settings.search_provider_primary,
             fallback if fallback is not None else settings.search_provider_fallback]
    out: list[pv.SearchProvider] = []
    for name in names:
        p = pv.build(name)
        if p is not None and p.configured and all(x.name != p.name for x in out):
            out.append(p)
    return out


def status() -> dict[str, Any]:
    """Situação dos provedores para a tela (sem expor chave)."""
    rows = []
    for role, name in (("principal", settings.search_provider_primary), ("alternativo", settings.search_provider_fallback)):
        p = pv.build(name)
        rows.append({"papel": role, "provedor": name or None, "configurado": bool(p and p.configured),
                     "variavel": {"tavily": "TAVILY_API_KEY", "brave": "BRAVE_SEARCH_API_KEY"}.get(str(name or "").lower())})
    active = settings.search_enabled and any(r["configurado"] for r in rows)
    return {"ativo": active, "habilitado": settings.search_enabled, "provedores": rows,
            "status": "CONFIGURADO" if active else "NAO_CONFIGURADO", "texto": None if active else NAO_CONFIGURADO_TEXTO,
            "cache_horas": settings.search_cache_hours, "limite_por_execucao": settings.search_max_queries_per_run}


def cache_key(kind: str, query: str, include_domains: list[str] | None, property_id: int | None = None) -> str:
    """Chave do cache por imóvel: dois imóveis com a mesma consulta não compartilham registro (histórico e rastreabilidade
    ficam no imóvel que pesquisou)."""
    raw = f"{property_id or 0}|{kind}|{' '.join(query.lower().split())}|{','.join(sorted(include_domains or []))}"
    return hashlib.sha256(raw.encode()).hexdigest()


def search(db: Session, *, kind: str, query: str, property_id: int | None = None, include_domains: list[str] | None = None,
           chain: list[pv.SearchProvider] | None = None, now: datetime | None = None, use_cache: bool = True) -> models.ExternalSearch:
    now = now or datetime.utcnow()
    key = cache_key(kind, query, include_domains, property_id)
    if use_cache:
        cached = db.scalar(select(models.ExternalSearch).where(
            models.ExternalSearch.cache_key == key, models.ExternalSearch.status.in_(("SUCESSO", "SEM_RESULTADO")),
            models.ExternalSearch.expires_at > now).order_by(models.ExternalSearch.id.desc()))
        if cached is not None:
            return cached
    chain = chain if chain is not None else (provider_chain() if settings.search_enabled else [])
    row = models.ExternalSearch(property_id=property_id, kind=kind, query=query, cache_key=key, results=[], attempts=0)
    if not chain:
        row.provider, row.status, row.error = "nenhum", "NAO_CONFIGURADO", NAO_CONFIGURADO_TEXTO
        db.add(row); db.flush()
        return row
    errors: list[str] = []
    started = time.monotonic()
    for provider in chain:
        tries = max(1, 1 + int(settings.search_max_retries))
        for attempt in range(tries):
            row.attempts = (row.attempts or 0) + 1
            try:
                resp = provider.search(query, max_results=settings.search_max_results, include_domains=include_domains)
            except pv.SearchUnavailable as exc:
                errors.append(str(exc))
                logger.warning("pesquisa externa indisponível provider=%s kind=%s tentativa=%s erro=%s", provider.name, kind, attempt + 1, exc)
                if attempt + 1 < tries and settings.search_retry_backoff_seconds > 0:
                    time.sleep(settings.search_retry_backoff_seconds * (attempt + 1))   # 429/5xx: espera antes de tentar de novo
                continue
            except pv.SearchError as exc:
                errors.append(str(exc))
                logger.warning("pesquisa externa falhou provider=%s kind=%s erro=%s", provider.name, kind, exc)
                break
            row.provider = provider.name
            row.results = [h.to_dict() for h in resp.hits]
            row.results_count = len(resp.hits)
            row.status = "SUCESSO" if resp.hits else "SEM_RESULTADO"
            row.cost_estimate_usd = resp.cost_estimate_usd
            row.duration_ms = int((time.monotonic() - started) * 1000)
            row.error = "; ".join(errors) or None
            row.expires_at = now + timedelta(hours=settings.search_cache_hours)
            logger.info("pesquisa externa provider=%s kind=%s status=%s resultados=%s ms=%s", provider.name, kind, row.status,
                        row.results_count, row.duration_ms)
            db.add(row); db.flush()
            return row
    row.provider = chain[-1].name
    row.status = "ERRO"
    row.error = "; ".join(errors)[:2000]
    row.duration_ms = int((time.monotonic() - started) * 1000)
    db.add(row); db.flush()
    return row
