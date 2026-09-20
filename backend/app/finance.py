from __future__ import annotations

from decimal import Decimal
import unicodedata
from typing import Any

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def decimal(value: Any | None) -> Decimal:
    if value is None or value == "":
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def present(value: Any | None) -> bool:
    return value is not None and value != ""


def normalize_category(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "OUTROS")).encode("ascii", "ignore").decode().upper()
    return text.replace(" ", "_").replace("-", "_")


def calculate_max_acquisition_price(*args: Any, **kwargs: Any) -> None:
    """Preço máximo permanece pendente até existir fórmula canônica na SPEC."""
    return None


def calculate_financial(
    bid: Decimal = ZERO,
    appraisal: Decimal | None = None,
    costs: list[dict] | None = None,
    comparables: list[dict] | None = None,
    debts: list[dict] | None = None,
    occupancy: dict | None = None,
    area: Decimal = ZERO,
    expected_rent: Decimal | None = None,
    holding_months: int = 0,
    commission_percent: Decimal | None = None,
    commission_fixed: Decimal | None = None,
    market_value: Decimal | None = None,
) -> dict[str, Any]:
    """Calcula o impacto financeiro sem LLM e sem valores implícitos de negócio."""
    costs = costs or []
    comparables = comparables or []
    debts = debts or []
    occupancy = occupancy or {}
    acquisition = decimal(bid)
    appraisal_value = decimal(appraisal) if present(appraisal) else None

    commission_informed = False
    if present(commission_fixed):
        commission = decimal(commission_fixed)
        commission_informed = True
    elif present(commission_percent):
        commission = acquisition * decimal(commission_percent) / HUNDRED
        commission_informed = True
    else:
        commission = ZERO

    breakdown = {
        "aquisicao": acquisition,
        "comissao": commission,
        "itbi": ZERO,
        "registro": ZERO,
        "debitos": ZERO,
        "condominio": ZERO,
        "iptu": ZERO,
        "custos_juridicos": ZERO,
        "desocupacao": decimal(occupancy.get("estimated_cost")),
        "reforma": ZERO,
        "outros": ZERO,
    }
    informed = {key: False for key in breakdown}
    informed["aquisicao"] = present(bid)
    informed["comissao"] = commission_informed
    informed["desocupacao"] = present(occupancy.get("estimated_cost"))

    for cost in costs:
        amount = decimal(cost.get("amount"))
        category = normalize_category(cost.get("category"))
        target = {"ITBI": "itbi", "REGISTRO": "registro", "ESCRITURA": "registro", "CONDOMINIO": "condominio", "IPTU": "iptu", "DEBITOS": "debitos", "DEBITO": "debitos", "JURIDICO": "custos_juridicos", "CUSTOS_JURIDICOS": "custos_juridicos", "DESOCUPACAO": "desocupacao", "REFORMA": "reforma", "OUTROS": "outros"}.get(category, "outros")
        breakdown[target] += amount
        informed[target] = True

    for debt in debts:
        if normalize_category(debt.get("status", "PENDENTE")) != "QUITADO":
            breakdown["debitos"] += decimal(debt.get("amount"))
            informed["debitos"] = True

    sale_values = [decimal(item.get("price")) for item in comparables if normalize_category(item.get("kind", "VENDA")) == "VENDA" and present(item.get("price"))]
    rent_values = [decimal(item.get("rent")) for item in comparables if normalize_category(item.get("kind")) == "ALUGUEL" and present(item.get("rent"))]
    estimated_market = decimal(market_value) if present(market_value) else (sum(sale_values, ZERO) / Decimal(len(sale_values)) if sale_values else None)
    monthly_rent = decimal(expected_rent) if present(expected_rent) else (sum(rent_values, ZERO) / Decimal(len(rent_values)) if rent_values else None)
    if estimated_market is not None:
        informed["valor_mercado"] = True
    else:
        informed["valor_mercado"] = False
    if monthly_rent is not None:
        informed["aluguel_mensal"] = True
    else:
        informed["aluguel_mensal"] = False

    total = sum(breakdown.values(), ZERO)
    margin_absolute = estimated_market - total if estimated_market is not None else None
    margin_percent = margin_absolute / estimated_market if estimated_market not in (None, ZERO) else None
    discount_percent = HUNDRED * (Decimal("1") - acquisition / appraisal_value) if appraisal_value not in (None, ZERO) else None
    yield_monthly = monthly_rent / total if monthly_rent is not None and total != ZERO else None
    yield_annual = monthly_rent * Decimal("12") / total if monthly_rent is not None and total != ZERO else None
    pending = ["Fórmula canônica de preço máximo não está definida na SPEC; cálculo não foi inventado."]
    scenarios = [{"cenario": name, "custo_total": total, "valor_mercado": estimated_market, "margem_absoluta": margin_absolute} for name in ("BASE", "OTIMISTA", "PESSIMISTA")]

    result = {
        "valor_aquisicao": acquisition,
        "valor_avaliacao": appraisal_value,
        "valor_mercado": estimated_market,
        "aluguel_mensal": monthly_rent,
        "custos": breakdown,
        "custos_informados": informed,
        "custo_total": total,
        "desconto_percentual": discount_percent,
        "margem_absoluta": margin_absolute,
        "margem_percentual": margin_percent,
        "yield_mensal": yield_monthly,
        "yield_anual": yield_annual,
        "cenario": "BASE",
        "cenarios": scenarios,
        "preco_maximo": calculate_max_acquisition_price(),
        "pendencias": pending,
        "prazo_meses": holding_months,
        "preco_m2": estimated_market / decimal(area) if estimated_market is not None and decimal(area) != ZERO else None,
        "roi_estimado_percentual": margin_percent,
        # aliases mantidos para compatibilidade com consumidores existentes
        "arrematacao": acquisition,
        "comissao": commission,
        "outros_custos": breakdown["outros"],
        "dividas": breakdown["debitos"],
        "desocupacao": breakdown["desocupacao"],
    }
    return result
