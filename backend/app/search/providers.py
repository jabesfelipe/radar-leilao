"""Provedores de pesquisa web por API oficial (v1.0.14).

Cada provedor traduz uma consulta em resultados normalizados (URL, título, trecho, data publicada). Nenhum faz scraping de
portal: só chama a API de pesquisa contratada, com a chave vinda do ambiente. Sem chave → ``configured`` falso e o serviço
registra NAO_CONFIGURADO (o Radar nunca simula resultado).

Avaliação (nov/2026) em ``docs/02-product/specs/PESQUISA-EXTERNA.md``: Tavily (principal: devolve o conteúdo relevante da
página, 1.000 créditos grátis/mês, US$ 0,008 por crédito) e Brave Search API (alternativo: índice próprio, US$ 5 por 1.000
consultas com US$ 5 de crédito mensal). Google Custom Search JSON API ficou de fora: fechada a novos clientes e encerrada
em 01/01/2027. APIs que raspam o Google (ex.: SerpAPI) ficaram de fora pelo risco de termos de uso.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

import httpx

from ..config import settings


class SearchError(Exception):
    """Falha da consulta (4xx, resposta inesperada)."""


class SearchUnavailable(SearchError):
    """Indisponibilidade transitória (timeout, transporte, 5xx, 429): pode tentar de novo ou usar o alternativo."""


@dataclass
class SearchHit:
    url: str
    title: str
    snippet: str
    published: str | None = None
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"url": self.url, "title": self.title, "snippet": self.snippet, "published": self.published, "score": self.score}


@dataclass
class SearchResponse:
    hits: list[SearchHit] = field(default_factory=list)
    cost_estimate_usd: Decimal | None = None


class SearchProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def search(self, query: str, *, max_results: int, include_domains: list[str] | None = None) -> SearchResponse: ...


def _raise_for(resp: httpx.Response, provider: str) -> None:
    if resp.status_code == 429 or resp.status_code >= 500:
        raise SearchUnavailable(f"{provider}: HTTP {resp.status_code}")
    if resp.status_code >= 400:
        raise SearchError(f"{provider}: HTTP {resp.status_code}")


class TavilyProvider:
    """https://docs.tavily.com — POST /search com Bearer token; ``search_depth=basic`` = 1 crédito."""
    name = "tavily"
    COST_PER_QUERY = Decimal("0.008")

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None, timeout: float | None = None,
                 client: httpx.Client | None = None) -> None:
        self._key = api_key if api_key is not None else settings.tavily_api_key
        self._url = base_url or settings.tavily_base_url
        self._timeout = timeout if timeout is not None else settings.search_timeout_seconds
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self._key)

    def search(self, query: str, *, max_results: int, include_domains: list[str] | None = None) -> SearchResponse:
        body: dict[str, Any] = {"query": query, "search_depth": "basic", "max_results": max_results, "include_answer": False}
        if include_domains:
            body["include_domains"] = include_domains
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        try:
            if self._client is not None:
                resp = self._client.post(self._url, json=body, headers=headers, timeout=self._timeout)
            else:
                with httpx.Client() as client:
                    resp = client.post(self._url, json=body, headers=headers, timeout=self._timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise SearchUnavailable(f"tavily: {type(exc).__name__}") from exc
        _raise_for(resp, self.name)
        try:
            data = resp.json()
            rows = data.get("results") or []
        except Exception as exc:  # noqa: BLE001
            raise SearchError("tavily: resposta inesperada") from exc
        hits = [SearchHit(url=str(r.get("url") or ""), title=str(r.get("title") or ""), snippet=str(r.get("content") or ""),
                          published=r.get("published_date"), score=r.get("score")) for r in rows if r.get("url")]
        return SearchResponse(hits=hits, cost_estimate_usd=self.COST_PER_QUERY)


class BraveProvider:
    """https://api-dashboard.search.brave.com — GET /res/v1/web/search com X-Subscription-Token."""
    name = "brave"
    COST_PER_QUERY = Decimal("0.005")

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None, timeout: float | None = None,
                 client: httpx.Client | None = None) -> None:
        self._key = api_key if api_key is not None else settings.brave_search_api_key
        self._url = base_url or settings.brave_search_base_url
        self._timeout = timeout if timeout is not None else settings.search_timeout_seconds
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self._key)

    def search(self, query: str, *, max_results: int, include_domains: list[str] | None = None) -> SearchResponse:
        q = query + ("".join(f" site:{d}" for d in include_domains[:1]) if include_domains else "")
        params = {"q": q, "count": min(max_results, 20), "country": "BR", "search_lang": "pt-br"}
        headers = {"X-Subscription-Token": str(self._key), "Accept": "application/json"}
        try:
            if self._client is not None:
                resp = self._client.get(self._url, params=params, headers=headers, timeout=self._timeout)
            else:
                with httpx.Client() as client:
                    resp = client.get(self._url, params=params, headers=headers, timeout=self._timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise SearchUnavailable(f"brave: {type(exc).__name__}") from exc
        _raise_for(resp, self.name)
        try:
            rows = ((resp.json().get("web") or {}).get("results")) or []
        except Exception as exc:  # noqa: BLE001
            raise SearchError("brave: resposta inesperada") from exc
        hits = []
        for r in rows:
            if not r.get("url"):
                continue
            extra = " ".join(str(x) for x in (r.get("extra_snippets") or []))
            hits.append(SearchHit(url=str(r["url"]), title=str(r.get("title") or ""), snippet=(str(r.get("description") or "") + " " + extra).strip(),
                                  published=r.get("page_age") or r.get("age")))
        return SearchResponse(hits=hits, cost_estimate_usd=self.COST_PER_QUERY)


PROVIDERS = {"tavily": TavilyProvider, "brave": BraveProvider}


def build(name: str | None) -> SearchProvider | None:
    cls = PROVIDERS.get(str(name or "").strip().lower())
    return cls() if cls else None
