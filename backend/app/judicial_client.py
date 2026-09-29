"""Cliente HTTP da Judicial API (TASK FINAL — Entrega 3).

O Radar NÃO duplica o DataJudProvider, o orchestrator nem o motor de sinais: ele
consome a Judicial API por HTTP, através deste cliente fino. URL-base, credencial
e timeout vêm de configuração/secret (``settings.judicial_api_*``).

Contrato consumido (Judicial API, SPEC §51-55):
- ``POST /api/v1/judicial/search`` — dispara uma pesquisa e devolve o resultado
  agregado (processos normalizados + sinais + fontes + status).

Robustez (SPEC/Entrega 3, item 7): indisponibilidade e timeout NÃO devem
interromper indevidamente as demais análises. Este cliente traduz falhas de rede
em ``JudicialApiUnavailable`` (com o status agregado) para que o chamador decida
degradar graciosamente, sem derrubar a análise documental/financeira.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import settings


class JudicialApiError(Exception):
    """Falha ao consumir a Judicial API (rede, timeout, HTTP inesperado)."""


class JudicialApiUnavailable(JudicialApiError):
    """Judicial API indisponível/timeout — o chamador deve degradar graciosamente."""


@dataclass
class JudicialSearchOutcome:
    """Resultado normalizado de uma consulta à Judicial API."""

    search_id: str | None
    status: str
    processes: list[dict[str, Any]] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reanalyze: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class JudicialApiClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = (base_url or settings.judicial_api_base_url).rstrip("/")
        self._api_key = api_key if api_key is not None else settings.judicial_api_key
        self._timeout = timeout if timeout is not None else settings.judicial_api_timeout_seconds
        self._client = client

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        # A API key do CONSUMIDOR (não confundir com a credencial do DataJud) só é
        # enviada quando configurada; em ambiente local a Judicial API aceita sem auth.
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _post(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        url = f"{self._base_url}{path}"
        if self._client is not None:
            return self._client.post(url, json=payload, headers=self._headers(), timeout=self._timeout)
        with httpx.Client() as client:
            return client.post(url, json=payload, headers=self._headers(), timeout=self._timeout)

    def search(self, criteria: dict[str, Any]) -> JudicialSearchOutcome:
        """Dispara uma pesquisa processual. Levanta ``JudicialApiUnavailable`` em
        indisponibilidade/timeout e ``JudicialApiError`` em respostas inesperadas."""
        # Remove chaves nulas para não enviar critérios vazios.
        payload = {k: v for k, v in criteria.items() if v not in (None, "", [], {})}
        try:
            resp = self._post("/api/v1/judicial/search", payload)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise JudicialApiUnavailable(f"Judicial API indisponível: {type(exc).__name__}") from exc

        if resp.status_code >= 500 or resp.status_code in (502, 503, 504):
            raise JudicialApiUnavailable(f"Judicial API respondeu {resp.status_code}")
        if resp.status_code >= 400:
            # 4xx (ex.: 400 critério ausente, 401/403 auth) é erro do chamador/config.
            detail = _safe_json(resp)
            raise JudicialApiError(f"Judicial API rejeitou a consulta ({resp.status_code}): {detail.get('code')}")

        body = _safe_json(resp)
        return JudicialSearchOutcome(
            search_id=body.get("search_id"),
            status=body.get("status", "FAILED"),
            processes=body.get("processes", []) or [],
            signals=body.get("signals", []) or [],
            sources=body.get("sources", []) or [],
            warnings=body.get("warnings", []) or [],
            reanalyze=body.get("reanalyze", {}) or {},
            raw=body,
        )


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - resposta malformada tratada como vazia
        return {}
