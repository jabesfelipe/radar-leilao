"""Extração determinística de dados de anúncio a partir do resultado de pesquisa (título + trecho devolvidos pela API).

Não abre a página do portal (sem scraping). Lê só o que a API de pesquisa devolveu: preço, área, quartos, vagas,
condomínio, IPTU, taxa extra e o tipo (venda ou aluguel). Página de listagem (vários preços) não vira comparável. Valor que
não estiver no texto fica ausente (nunca é deduzido). Todo valor extraído é preço ANUNCIADO, não transação.
"""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_MONEY = re.compile(r"R\$\s*([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{2})?|[0-9]+(?:,[0-9]{2})?)(\s*mil\b)?", re.IGNORECASE)
_AREA = re.compile(r"(\d{2,4}(?:[.,]\d{1,2})?)\s*(?:m²|m2|metros\s+quadrados)", re.IGNORECASE)
_BEDS = re.compile(r"(\d{1,2})\s*(?:quartos?|dormit[óo]rios?|dorms?\.?)\b", re.IGNORECASE)
_PARK = re.compile(r"(\d{1,2})\s*vagas?\b", re.IGNORECASE)
_CONDO = re.compile(r"(?:condom[íi]nio|cond\.)\s*(?:de|:)?\s*R\$\s*([0-9.]+(?:,[0-9]{2})?)", re.IGNORECASE)
_IPTU = re.compile(r"IPTU\s*(?:de|:)?\s*R\$\s*([0-9.]+(?:,[0-9]{2})?)", re.IGNORECASE)
_EXTRA = re.compile(r"taxa\s+extra|chamada\s+de\s+capital|fundo\s+de\s+obras|rateio\s+extra", re.IGNORECASE)
_RENT = re.compile(r"alug|loca[çc][ãa]o|/\s*m[êe]s|por\s+m[êe]s|mensal", re.IGNORECASE)
_SALE = re.compile(r"\bvenda\b|[àa]\s+venda|comprar|vende-se", re.IGNORECASE)
_SPACED_THOUSANDS = re.compile(r"(\d)\.\s+(\d{3})(?!\d)")
# Vírgula decimal com espaço: só quando o número da esquerda não é já a parte decimal de outro ("1.800,00, 45" não vira "00,45").
_SPACED_DECIMAL = re.compile(r"(?<![,\d])(\d{1,4}(?:\.\d{3})*),\s+(\d{2})(?!\d)")
_LIST_PAGE = re.compile(r"\b\d{2,}\s+(?:im[óo]veis|apartamentos|casas|an[úu]ncios|resultados)\b", re.IGNORECASE)


def _dec(raw: str, thousand: bool = False) -> Decimal | None:
    try:
        value = Decimal(raw.replace(".", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return value * 1000 if thousand else value


def fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().upper()


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."), parts.path.rstrip("/"), "", ""))


def domain(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def extract_listing(hit: dict[str, Any], expected_kind: str) -> dict[str, Any]:
    """Campos do anúncio lidos no título/trecho. ``utilizavel`` só quando é um anúncio único com preço do tipo esperado."""
    text = f"{hit.get('title') or ''} \n {hit.get('snippet') or ''}"
    # Trechos de pesquisa costumam vir com espaço depois de ponto/vírgula de número ("R$ 1. 800, 00", "45, 50 m²"): junta antes de ler.
    text = _SPACED_THOUSANDS.sub(r"\1.\2", text)
    text = _SPACED_DECIMAL.sub(r"\1,\2", text)
    condo = _CONDO.search(text)
    iptu = _IPTU.search(text)
    spans_excluded = [m.span(1) for m in (condo, iptu) if m]
    prices = []
    for m in _MONEY.finditer(text):
        if any(a <= m.start(1) < b for a, b in spans_excluded):
            continue
        value = _dec(m.group(1), bool(m.group(2)))
        if value is not None and value > 0:
            prices.append(value)
    rent_words = bool(_RENT.search(text))
    sale_words = bool(_SALE.search(text))
    if expected_kind == "ALUGUEL":
        candidates = [p for p in prices if Decimal("200") <= p <= Decimal("30000")]
    else:
        candidates = [p for p in prices if p >= Decimal("30000")]
    area = _AREA.search(text)
    beds = _BEDS.search(text)
    park = _PARK.search(text)
    distinct = sorted(set(candidates))
    list_page = bool(_LIST_PAGE.search(text)) or len(distinct) > 2
    kind_ok = (rent_words and expected_kind == "ALUGUEL") or (expected_kind == "VENDA" and (sale_words or not rent_words))
    price = distinct[0] if len(distinct) == 1 else None
    area_v = _dec(area.group(1)) if area else None
    reasons = []
    if list_page:
        reasons.append("Página de listagem com vários imóveis: não é um anúncio único.")
    if price is None and not list_page:
        reasons.append("Preço não encontrado no trecho devolvido pela pesquisa." if not distinct else "Mais de um preço no trecho.")
    if not kind_ok:
        reasons.append(f"O texto não indica {'aluguel' if expected_kind == 'ALUGUEL' else 'venda'}.")
    if area_v is None:
        reasons.append("Área não informada no trecho: não entra no cálculo por m².")
    usable = bool(price is not None and not list_page and kind_ok)
    filled = sum(x is not None for x in (price, area_v, beds, park))
    confidence = "MEDIA" if (usable and area_v is not None and filled >= 3) else ("BAIXA" if usable else "INSUFICIENTE")
    return {
        "url": hit.get("url"), "url_normalizada": normalize_url(str(hit.get("url") or "")), "fonte": domain(str(hit.get("url") or "")),
        "titulo": (hit.get("title") or "")[:240], "publicado": hit.get("published"),
        "tipo": expected_kind, "valor": price, "area_m2": area_v, "quartos": int(beds.group(1)) if beds else None,
        "vagas": int(park.group(1)) if park else None,
        "condominio": _dec(condo.group(1)) if condo else None, "iptu": _dec(iptu.group(1)) if iptu else None,
        "taxa_extra_mencionada": bool(_EXTRA.search(text)),
        "pagina_lista": list_page, "utilizavel": usable, "confianca": confidence, "motivos": reasons,
    }


def dedupe(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Marca duplicatas: mesma URL normalizada, ou mesmo tipo + preço + área (o mesmo imóvel anunciado em portais diferentes)."""
    seen_url: dict[str, int] = {}
    seen_key: dict[tuple, int] = {}
    for i, row in enumerate(listings):
        row.setdefault("duplicata_de", None)
        url = row.get("url_normalizada")
        if url and url in seen_url:
            row["duplicata_de"] = seen_url[url]
            row["utilizavel"] = False
            row["motivos"] = row.get("motivos", []) + ["Mesmo anúncio já encontrado (mesma URL)."]
            continue
        if url:
            seen_url[url] = i
        if row.get("valor") is not None and row.get("area_m2") is not None:
            key = (row["tipo"], row["valor"], row["area_m2"].quantize(Decimal("1")))
            if key in seen_key:
                row["duplicata_de"] = seen_key[key]
                row["utilizavel"] = False
                row["motivos"] = row.get("motivos", []) + ["Provável repetição do mesmo imóvel em outro portal (mesmo preço e área)."]
                continue
            seen_key[key] = i
    return listings
