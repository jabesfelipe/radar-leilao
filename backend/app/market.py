from __future__ import annotations

from decimal import Decimal
import unicodedata
from typing import Any, Iterable

ZERO = Decimal("0")


def decimal(value: Any | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def normalize_kind(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().upper()


def median(values: Iterable[Decimal]) -> Decimal | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def summarize_sale(comparables: list[dict]) -> dict:
    rows = [(decimal(item.get("price")), decimal(item.get("area_m2"))) for item in comparables if normalize_kind(item.get("kind", "VENDA")) == "VENDA"]
    prices = [price for price, _ in rows if price is not None]
    price_per_m2 = [price / area for price, area in rows if price is not None and area is not None and area > ZERO]
    return {"quantidade": len(prices), "preco_medio": sum(prices, ZERO) / Decimal(len(prices)) if prices else None, "preco_mediano": median(prices), "preco_m2_medio": sum(price_per_m2, ZERO) / Decimal(len(price_per_m2)) if price_per_m2 else None, "preco_m2_mediano": median(price_per_m2), "quantidade_com_area": len(price_per_m2)}


def summarize_rent(comparables: list[dict]) -> dict:
    rows = [(decimal(item.get("rent")), decimal(item.get("area_m2"))) for item in comparables if normalize_kind(item.get("kind")) == "ALUGUEL"]
    rents = [rent for rent, _ in rows if rent is not None]
    rent_per_m2 = [rent / area for rent, area in rows if rent is not None and area is not None and area > ZERO]
    return {"quantidade": len(rents), "aluguel_medio": sum(rents, ZERO) / Decimal(len(rents)) if rents else None, "aluguel_mediano": median(rents), "aluguel_m2_medio": sum(rent_per_m2, ZERO) / Decimal(len(rent_per_m2)) if rent_per_m2 else None, "aluguel_m2_mediano": median(rent_per_m2), "quantidade_com_area": len(rent_per_m2)}


def calculate_market(comparables: list[dict] | None) -> dict:
    """Consolida exclusivamente comparáveis já cadastrados, sem scoring ou valuation."""
    rows = comparables or []
    return {"venda": summarize_sale(rows), "aluguel": summarize_rent(rows)}
