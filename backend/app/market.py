from __future__ import annotations

from decimal import Decimal
import unicodedata
from typing import Any, Iterable

ZERO = Decimal("0")

# Amostra mínima recomendada pelo método (checklist: "7 a 10 imóveis similares").
MIN_SAMPLE = 7
# Acima deste coeficiente de variação a amostra é considerada dispersa/heterogênea.
HIGH_DISPERSION_CV = Decimal("0.30")


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


def _coefficient_of_variation(values: list[Decimal]) -> Decimal | None:
    """Coeficiente de variação (desvio padrão / média). Mede dispersão relativa
    da amostra. Requer >= 2 valores e média > 0."""
    if len(values) < 2:
        return None
    mean = sum(values, ZERO) / Decimal(len(values))
    if mean == ZERO:
        return None
    var = sum(((v - mean) ** 2 for v in values), ZERO) / Decimal(len(values))
    # raiz quadrada via Decimal
    std = var.sqrt()
    return std / mean


def _quality(values: list[Decimal], *, min_sample: int) -> dict[str, Any]:
    """Sinaliza a qualidade da amostra (SPEC/auditoria Task 2): amostra
    insuficiente e dispersão elevada. NÃO afirma verificação externa nem inventa
    dados — apenas descreve o que a amostra cadastrada permite."""
    n = len(values)
    cv = _coefficient_of_variation(values)
    avisos: list[str] = []
    if n == 0:
        avisos.append("Sem comparáveis cadastrados: não há base para estimativa de mercado.")
    elif n < min_sample:
        avisos.append(f"Amostra insuficiente ({n} < {min_sample} recomendados): estimativa apenas indicativa, não conclusiva.")
    if cv is not None and cv > HIGH_DISPERSION_CV:
        avisos.append("Dispersão elevada entre os comparáveis: possível heterogeneidade (área, localização, conservação ou preços discrepantes).")
    return {
        "quantidade": n,
        "amostra_suficiente": n >= min_sample,
        "coeficiente_variacao": cv,
        "dispersao_elevada": bool(cv is not None and cv > HIGH_DISPERSION_CV),
        "avaliacao_definitiva": False,  # média/mediana NUNCA é avaliação definitiva de mercado
        "avisos": avisos,
    }


def summarize_sale(comparables: list[dict], *, min_sample: int = MIN_SAMPLE) -> dict:
    rows = [(decimal(item.get("price")), decimal(item.get("area_m2"))) for item in comparables if normalize_kind(item.get("kind", "VENDA")) == "VENDA"]
    prices = [price for price, _ in rows if price is not None]
    price_per_m2 = [price / area for price, area in rows if price is not None and area is not None and area > ZERO]
    return {
        "quantidade": len(prices),
        "preco_medio": sum(prices, ZERO) / Decimal(len(prices)) if prices else None,
        "preco_mediano": median(prices),
        "preco_m2_medio": sum(price_per_m2, ZERO) / Decimal(len(price_per_m2)) if price_per_m2 else None,
        "preco_m2_mediano": median(price_per_m2),
        "quantidade_com_area": len(price_per_m2),
        "qualidade": _quality(prices, min_sample=min_sample),
    }


def summarize_rent(comparables: list[dict], *, min_sample: int = MIN_SAMPLE) -> dict:
    rows = [(decimal(item.get("rent")), decimal(item.get("area_m2"))) for item in comparables if normalize_kind(item.get("kind")) == "ALUGUEL"]
    rents = [rent for rent, _ in rows if rent is not None]
    rent_per_m2 = [rent / area for rent, area in rows if rent is not None and area is not None and area > ZERO]
    return {
        "quantidade": len(rents),
        "aluguel_medio": sum(rents, ZERO) / Decimal(len(rents)) if rents else None,
        "aluguel_mediano": median(rents),
        "aluguel_m2_medio": sum(rent_per_m2, ZERO) / Decimal(len(rent_per_m2)) if rent_per_m2 else None,
        "aluguel_m2_mediano": median(rent_per_m2),
        "quantidade_com_area": len(rent_per_m2),
        "qualidade": _quality(rents, min_sample=min_sample),
    }


def _sources(comparables: list[dict]) -> list[dict]:
    """Preserva a rastreabilidade da origem/URL de cada comparável quando disponível
    (sem inventar). Datas são incluídas quando o item as fornecer."""
    fontes: list[dict] = []
    for item in comparables:
        origem = item.get("source")
        url = item.get("url")
        if origem or url:
            fontes.append({
                "kind": normalize_kind(item.get("kind", "VENDA")),
                "source": origem,
                "url": url,
                "data": item.get("date") or item.get("data"),
            })
    return fontes


def calculate_market(comparables: list[dict] | None, *, min_sample: int = MIN_SAMPLE) -> dict:
    """Consolida exclusivamente comparáveis já cadastrados, sem scoring ou valuation
    automático. Sinaliza a qualidade da amostra (suficiência, dispersão) e preserva
    a origem/data quando disponível. A média/mediana NÃO é avaliação definitiva de
    mercado — isso é explicitado em ``qualidade`` (SPEC/auditoria Task 2)."""
    rows = comparables or []
    return {
        "venda": summarize_sale(rows, min_sample=min_sample),
        "aluguel": summarize_rent(rows, min_sample=min_sample),
        "fontes": _sources(rows),
        "observacao": "Estimativa baseada apenas em comparáveis cadastrados manualmente; não há verificação externa.",
    }
