"""Cliente de geocodificação (Google Maps Platform) — frente Geográfica da Due
Diligence.

Mesma filosofia do ``judicial_client``: cliente fino sobre ``httpx``, credencial e
timeout vindos de ``settings`` (nunca versionados, nunca no frontend). Regras:

- Sem API key configurada → ``GeocodingUnavailable("NAO_CONFIGURADO")``. O sistema
  NUNCA inventa coordenadas nem simula sucesso; a tela usa links externos e
  registro manual.
- Timeout/erro de transporte/5xx → ``GeocodingUnavailable`` (degradação graciosa).
- 4xx/resposta inesperada → ``GeocodingError``.

O cliente NÃO decide nada de negócio: só traduz endereço → (lat, lng, precisão,
endereço normalizado) ou sinaliza indisponibilidade. Não loga a API key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .config import settings


class GeocodingError(Exception):
    """Falha ao geocodificar (resposta inesperada / 4xx / configuração)."""


class GeocodingUnavailable(GeocodingError):
    """Geocodificação indisponível (sem chave, timeout, 5xx) — degradar graciosamente."""


@dataclass
class GeocodeResult:
    formatted_address: str | None
    latitude: float | None
    longitude: float | None
    location_type: str | None          # ROOFTOP | RANGE_INTERPOLATED | GEOMETRIC_CENTER | APPROXIMATE
    place_id: str | None
    partial_match: bool
    raw_status: str

    @property
    def found(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class GeocodingClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.google_maps_api_key
        self._base_url = (base_url or settings.google_geocoding_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.google_maps_timeout_seconds
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def _get(self, params: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return self._client.get(self._base_url, params=params, timeout=self._timeout)
        with httpx.Client() as client:
            return client.get(self._base_url, params=params, timeout=self._timeout)

    def geocode(self, address: str) -> GeocodeResult:
        """Geocodifica um endereço. Levanta GeocodingUnavailable quando não há chave
        ou a API está indisponível; GeocodingError em respostas inesperadas."""
        if not self._api_key:
            raise GeocodingUnavailable("NAO_CONFIGURADO")
        if not (address or "").strip():
            raise GeocodingError("Endereço vazio não pode ser geocodificado.")
        params = {"address": address, "key": self._api_key, "language": "pt-BR", "region": "br"}
        try:
            resp = self._get(params)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise GeocodingUnavailable(f"Geocodificação indisponível: {type(exc).__name__}") from exc
        if resp.status_code >= 500:
            raise GeocodingUnavailable(f"Geocodificação respondeu {resp.status_code}")
        if resp.status_code >= 400:
            raise GeocodingError(f"Geocodificação rejeitou a consulta ({resp.status_code}).")
        body = _safe_json(resp)
        status = str(body.get("status") or "UNKNOWN")
        if status == "ZERO_RESULTS":
            # Endereço não encontrado: resultado determinístico, não é erro nem invenção.
            return GeocodeResult(None, None, None, None, None, False, status)
        if status in ("OVER_QUERY_LIMIT", "REQUEST_DENIED", "INVALID_REQUEST", "UNKNOWN_ERROR"):
            # REQUEST_DENIED normalmente = chave inválida/sem faturamento → indisponível.
            raise GeocodingUnavailable(f"Geocodificação status {status}")
        results = body.get("results") or []
        if not results:
            return GeocodeResult(None, None, None, None, None, False, status)
        top = results[0]
        geometry = top.get("geometry") or {}
        location = geometry.get("location") or {}
        return GeocodeResult(
            formatted_address=top.get("formatted_address"),
            latitude=_as_float(location.get("lat")),
            longitude=_as_float(location.get("lng")),
            location_type=geometry.get("location_type"),
            place_id=top.get("place_id"),
            partial_match=bool(top.get("partial_match", False)),
            raw_status=status,
        )


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


# ---- Helpers de links externos (não dependem de chave; sempre disponíveis) ----
def maps_link(*, address: str | None = None, latitude: float | None = None, longitude: float | None = None) -> str | None:
    """Link externo para o Google Maps (abre no navegador). Não requer API key."""
    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
    if address and address.strip():
        from urllib.parse import quote
        return f"https://www.google.com/maps/search/?api=1&query={quote(address)}"
    return None


def street_view_link(*, address: str | None = None, latitude: float | None = None, longitude: float | None = None) -> str | None:
    """Link externo para o Street View. Não requer API key (abre a UI do Google)."""
    if latitude is not None and longitude is not None:
        return f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={latitude},{longitude}"
    if address and address.strip():
        from urllib.parse import quote
        return f"https://www.google.com/maps/search/?api=1&query={quote(address)}&layer=c"
    return None
