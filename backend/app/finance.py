from decimal import Decimal

ZERO = Decimal("0")

def calculate_financial(bid: Decimal, appraisal: Decimal, costs: list[dict], comparables: list[dict], debts: list[dict] | None = None, occupancy: dict | None = None, area: Decimal = ZERO, expected_rent: Decimal = ZERO, holding_months: int = 0):
    debts = debts or []
    occupancy = occupancy or {}
    extras = sum((Decimal(str(item.get("amount", 0))) for item in costs), ZERO)
    debt_total = sum((Decimal(str(item.get("amount", 0))) for item in debts if item.get("status", "PENDENTE") != "QUITADO"), ZERO)
    occupancy_cost = Decimal(str(occupancy.get("estimated_cost", 0)))
    commission = bid * Decimal("0.05")
    total = bid + commission + extras + debt_total + occupancy_cost
    sale_prices = [Decimal(str(c["price"])) for c in comparables if c.get("kind", "VENDA") == "VENDA" and Decimal(str(c.get("area_m2", 0))) > 0]
    rent_values = [Decimal(str(c.get("rent", 0))) for c in comparables if c.get("kind") == "ALUGUEL" and c.get("rent")]
    market_value = (sum(sale_prices, ZERO) / len(sale_prices)) if sale_prices else appraisal
    monthly_rent = expected_rent or ((sum(rent_values, ZERO) / len(rent_values)) if rent_values else ZERO)
    discount = ((market_value - total) / market_value * 100) if market_value else ZERO
    roi = ((market_value - total) / total * 100) if total else ZERO
    annual_yield = (monthly_rent * 12 / total * 100) if total else ZERO
    margin = market_value - total
    max_price = market_value * Decimal("0.8") - commission - extras - debt_total - occupancy_cost
    scenarios = {"conservador": total * Decimal("1.10"), "base": total, "otimista": total * Decimal("0.95")}
    return {"arrematacao": bid, "comissao": commission, "outros_custos": extras, "dividas": debt_total, "desocupacao": occupancy_cost, "custo_total": total, "valor_mercado": market_value, "desconto_percentual": discount, "margem": margin, "roi_estimado_percentual": roi, "yield_anual_percentual": annual_yield, "aluguel_mensal": monthly_rent, "preco_maximo": max_price, "prazo_meses": holding_months, "preco_m2": market_value / area if area else ZERO, "cenarios": scenarios}
