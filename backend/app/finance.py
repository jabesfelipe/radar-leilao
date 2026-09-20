from decimal import Decimal

def calculate_financial(bid: Decimal, appraisal: Decimal, costs: list[dict], comparables: list[dict], area: Decimal):
    extras = sum((Decimal(str(item.get("amount", 0))) for item in costs), Decimal("0"))
    commission = bid * Decimal("0.05")
    total = bid + commission + extras
    market_prices = [Decimal(str(c["price"])) for c in comparables if c.get("kind", "VENDA") == "VENDA"]
    market_value = sum(market_prices, Decimal("0")) / len(market_prices) if market_prices else appraisal
    discount = ((market_value - total) / market_value * 100) if market_value else Decimal("0")
    sale_yield = (market_value / total - 1) * 100 if total else Decimal("0")
    return {"arrematacao": bid, "comissao": commission, "outros_custos": extras, "custo_total": total, "valor_mercado": market_value, "desconto_percentual": discount, "roi_estimado_percentual": sale_yield, "preco_m2": market_value / area if area else Decimal("0")}
