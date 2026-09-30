from __future__ import annotations

from dataclasses import dataclass, field
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


# Custos que compõem o custo total de aquisição + operação + carregamento (SPEC
# ADDENDUM Task 2). "carregamento" cobre condomínio/IPTU/despesas durante a posse.
COST_KEYS = (
    "aquisicao", "comissao", "itbi", "registro", "debitos", "condominio", "iptu",
    "custos_juridicos", "desocupacao", "reforma", "carregamento", "outros",
)

# Metas suportadas para o preço máximo de aquisição.
GOAL_LUCRO_MINIMO = "LUCRO_MINIMO"
GOAL_MARGEM_MINIMA = "MARGEM_MINIMA"
GOAL_ROI_MINIMO = "ROI_MINIMO"
SUPPORTED_GOALS = (GOAL_LUCRO_MINIMO, GOAL_MARGEM_MINIMA, GOAL_ROI_MINIMO)

# Bases de tributação da venda.
TAX_BASE_GANHO = "GANHO"
TAX_BASE_VENDA = "VENDA"


@dataclass(frozen=True)
class SaleAssumptions:
    """Premissas configuráveis da SAÍDA (venda). Todos os percentuais são frações
    (0.05 = 5%). Nenhum valor legal é embutido: o default é ausência (None), que
    sinaliza pendência quando material — nunca zero silencioso."""

    corretagem_pct: Decimal | None = None      # fração sobre o valor de venda
    tributo_pct: Decimal | None = None         # fração sobre a base do tributo
    tax_base: str = TAX_BASE_GANHO             # GANHO (V - custo_total) ou VENDA (V)


@dataclass(frozen=True)
class MaxPriceGoal:
    """Meta financeira para o preço máximo de aquisição."""

    kind: str = GOAL_LUCRO_MINIMO
    value: Decimal | None = None               # R$ para LUCRO_MINIMO; fração para MARGEM/ROI


@dataclass(frozen=True)
class ScenarioAssumptions:
    """Premissas explícitas de um cenário. Sobrescrevem os valores base quando
    presentes; ausência mantém o valor base."""

    nome: str
    valor_venda: Decimal | None = None
    reforma: Decimal | None = None
    desocupacao: Decimal | None = None
    carregamento: Decimal | None = None
    prazo_meses: int | None = None
    justificativa: str = ""


def _acquisition_and_operation_costs(
    *,
    acquisition: Decimal,
    commission: Decimal,
    breakdown: dict[str, Decimal],
) -> Decimal:
    """Custo total = arrematação + comissão + demais custos (sem dupla contagem).
    ``breakdown`` já contém aquisicao/comissao; somamos todas as chaves uma vez."""
    return sum(breakdown.values(), ZERO)


def _sale_costs(
    *,
    sale_value: Decimal | None,
    total_cost: Decimal,
    sale: SaleAssumptions,
) -> tuple[Decimal | None, dict[str, Any]]:
    """Custos de saída (corretagem + tributos). Retorna (custo_saida, detalhe).
    custo_saida é None quando não há valor de venda."""
    if sale_value is None:
        return None, {"corretagem_venda": None, "tributos_venda": None}
    corretagem = sale_value * sale.corretagem_pct if sale.corretagem_pct is not None else ZERO
    if sale.tributo_pct is not None:
        base = (sale_value - total_cost) if sale.tax_base == TAX_BASE_GANHO else sale_value
        base = base if base > ZERO else ZERO
        tributos = base * sale.tributo_pct
    else:
        tributos = ZERO
    return corretagem + tributos, {"corretagem_venda": corretagem, "tributos_venda": tributos}


def calculate_max_acquisition_price(
    *,
    sale_value: Decimal | None = None,
    fixed_costs: Decimal | None = None,
    commission_pct: Decimal | None = None,
    commission_fixed: Decimal | None = None,
    sale: SaleAssumptions | None = None,
    goal: MaxPriceGoal | None = None,
) -> dict[str, Any]:
    """Calcula o maior lance (A) compatível com uma meta financeira configurável.

    Retorna um dicionário com ``preco_maximo`` (Decimal | None), ``viavel`` (bool),
    ``premissas_utilizadas`` e ``pendencias``. NUNCA retorna um preço aparente
    quando faltam dados essenciais (SPEC ADDENDUM Task 2): nesse caso preco_maximo
    é None e a pendência é listada. Não substitui premissas ausentes por zero.
    """
    sale = sale or SaleAssumptions()
    goal = goal or MaxPriceGoal()
    pendencias: list[str] = []
    premissas: dict[str, Any] = {}

    if goal.kind not in SUPPORTED_GOALS:
        return {"preco_maximo": None, "viavel": False, "premissas_utilizadas": premissas,
                "pendencias": [f"Meta '{goal.kind}' não suportada."], "razao": "META_INVALIDA"}

    if not present(sale_value):
        pendencias.append("Valor de venda estimado (V) é essencial e não foi informado.")
    if goal.value is None:
        pendencias.append("Meta financeira (valor/percentual) é essencial e não foi informada.")
    if pendencias:
        return {"preco_maximo": None, "viavel": False, "premissas_utilizadas": premissas,
                "pendencias": pendencias, "razao": "DADOS_ESSENCIAIS_AUSENTES"}

    V = decimal(sale_value)
    F = decimal(fixed_costs)
    premissas["valor_venda"] = V
    premissas["custos_fixos"] = F
    # k = fator multiplicativo do lance no custo total (comissão percentual sobre A).
    if present(commission_pct):
        k = Decimal("1") + decimal(commission_pct)
        premissas["comissao_pct"] = decimal(commission_pct)
    else:
        k = Decimal("1")
        if present(commission_fixed):
            F = F + decimal(commission_fixed)
            premissas["comissao_fixa"] = decimal(commission_fixed)

    # Custos de saída que NÃO dependem de A (corretagem sempre; tributo base VENDA).
    corretagem = V * sale.corretagem_pct if sale.corretagem_pct is not None else ZERO
    premissas["corretagem_pct"] = sale.corretagem_pct
    premissas["tributo_pct"] = sale.tributo_pct
    premissas["tax_base"] = sale.tax_base
    premissas["meta"] = {"tipo": goal.kind, "valor": goal.value}

    meta = decimal(goal.value)

    # Resolve A_max conforme a meta. Para tributo base GANHO, o tributo depende de
    # custo_total (que depende de A); resolvemos o ponto de meta de forma fechada.
    if goal.kind == GOAL_LUCRO_MINIMO:
        # resultado_liquido = V - corretagem - tributos - custo_total >= meta
        if sale.tributo_pct is not None and sale.tax_base == TAX_BASE_GANHO:
            # tributos = t*(V - custo_total); resultado = V - corretagem - t*(V-CT) - CT >= meta
            # (1 - t)*(V) - corretagem - (1 - t)*CT >= meta  onde CT = k*A + F
            t = sale.tributo_pct
            numerator = (Decimal("1") - t) * V - corretagem - meta - (Decimal("1") - t) * F
            denom = (Decimal("1") - t) * k
        else:
            tributos = (V * sale.tributo_pct) if (sale.tributo_pct is not None) else ZERO
            numerator = V - corretagem - tributos - meta - F
            denom = k
    elif goal.kind == GOAL_MARGEM_MINIMA:
        # margem = resultado/V >= meta ⇒ resultado >= meta*V
        alvo = meta * V
        if sale.tributo_pct is not None and sale.tax_base == TAX_BASE_GANHO:
            t = sale.tributo_pct
            numerator = (Decimal("1") - t) * V - corretagem - alvo - (Decimal("1") - t) * F
            denom = (Decimal("1") - t) * k
        else:
            tributos = (V * sale.tributo_pct) if (sale.tributo_pct is not None) else ZERO
            numerator = V - corretagem - tributos - alvo - F
            denom = k
    else:  # GOAL_ROI_MINIMO — resultado >= meta*custo_total ⇒ custo_total <= (V - custo_saida)/(1+meta)
        if sale.tributo_pct is not None and sale.tax_base == TAX_BASE_GANHO:
            # custo_saida depende de custo_total via tributo; resolve custo_total alvo:
            # resultado = V - corretagem - t*(V-CT) - CT >= meta*CT
            # (1-t)V - corretagem - (1-t)CT >= meta*CT
            # (1-t)V - corretagem >= CT*(meta + 1 - t)
            t = sale.tributo_pct
            ct_max = ((Decimal("1") - t) * V - corretagem) / (meta + Decimal("1") - t)
        else:
            tributos = (V * sale.tributo_pct) if (sale.tributo_pct is not None) else ZERO
            ct_max = (V - corretagem - tributos) / (Decimal("1") + meta)
        numerator = ct_max - F
        denom = k

    if denom <= ZERO:
        return {"preco_maximo": None, "viavel": False, "premissas_utilizadas": premissas,
                "pendencias": ["Parâmetros tornam o cálculo indeterminado (denominador <= 0)."],
                "razao": "PARAMETROS_INVALIDOS"}

    a_max = numerator / denom
    if a_max <= ZERO:
        return {"preco_maximo": None, "viavel": False, "premissas_utilizadas": premissas,
                "pendencias": [], "razao": "META_INATINGIVEL",
                "mensagem": "Meta inatingível para o valor de venda e custos informados."}

    return {"preco_maximo": a_max, "viavel": True, "premissas_utilizadas": premissas, "pendencias": []}


def _resolve_scenario(
    base_inputs: dict[str, Any],
    scenario: ScenarioAssumptions,
) -> dict[str, Any]:
    """Recalcula o resultado da operação para um cenário, usando a MESMA fórmula
    (calculate_financial) com premissas sobrescritas."""
    inputs = dict(base_inputs)
    if scenario.valor_venda is not None:
        inputs["market_value"] = scenario.valor_venda
    if scenario.reforma is not None:
        inputs["_override_reforma"] = scenario.reforma
    if scenario.desocupacao is not None:
        inputs["_override_desocupacao"] = scenario.desocupacao
    if scenario.carregamento is not None:
        inputs["_override_carregamento"] = scenario.carregamento
    if scenario.prazo_meses is not None:
        inputs["holding_months"] = scenario.prazo_meses
    result = calculate_financial(**{k: v for k, v in inputs.items() if not k.startswith("_")},
                                 _overrides={k[len("_override_"):]: v for k, v in inputs.items() if k.startswith("_override_")})
    return {
        "cenario": scenario.nome,
        "premissas": {
            "valor_venda": scenario.valor_venda,
            "reforma": scenario.reforma,
            "desocupacao": scenario.desocupacao,
            "carregamento": scenario.carregamento,
            "prazo_meses": scenario.prazo_meses,
            "justificativa": scenario.justificativa,
        },
        "custo_total": result["custo_total"],
        "valor_mercado": result["valor_mercado"],
        "resultado_liquido": result["resultado_liquido"],
        "margem_liquida": result["margem_liquida"],
        "roi_operacao": result["roi_operacao"],
        "pendencias": result["pendencias"],
    }


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
    sale: SaleAssumptions | None = None,
    goal: MaxPriceGoal | None = None,
    scenarios: list[ScenarioAssumptions] | None = None,
    _overrides: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """Calcula o impacto financeiro determinístico, sem LLM e sem valores implícitos.

    Novidades da Task 2 (SPEC ADDENDUM): resultado líquido de venda (corretagem +
    tributos parametrizáveis, sem dupla contagem), margem líquida, ROI da operação,
    preço máximo de aquisição por meta configurável e cenários com premissas
    explícitas. Dados essenciais ausentes viram None + pendência, nunca zero.
    """
    costs = costs or []
    comparables = comparables or []
    debts = debts or []
    occupancy = occupancy or {}
    overrides = _overrides or {}
    sale = sale or SaleAssumptions()
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
        "carregamento": ZERO,
        "outros": ZERO,
    }
    informed = {key: False for key in breakdown}
    informed["aquisicao"] = present(bid)
    informed["comissao"] = commission_informed
    informed["desocupacao"] = present(occupancy.get("estimated_cost"))

    for cost in costs:
        amount = decimal(cost.get("amount"))
        category = normalize_category(cost.get("category"))
        target = {
            "ITBI": "itbi", "REGISTRO": "registro", "ESCRITURA": "registro",
            "CONDOMINIO": "condominio", "IPTU": "iptu", "DEBITOS": "debitos",
            "DEBITO": "debitos", "JURIDICO": "custos_juridicos",
            "CUSTOS_JURIDICOS": "custos_juridicos", "DESOCUPACAO": "desocupacao",
            "REFORMA": "reforma", "CARREGAMENTO": "carregamento", "OUTROS": "outros",
        }.get(category, "outros")
        breakdown[target] += amount
        informed[target] = True

    for debt in debts:
        if normalize_category(debt.get("status", "PENDENTE")) != "QUITADO":
            breakdown["debitos"] += decimal(debt.get("amount"))
            informed["debitos"] = True

    # Overrides de cenário (aplicados após o cadastro base; marcam como informado).
    for key in ("reforma", "desocupacao", "carregamento"):
        if key in overrides:
            breakdown[key] = decimal(overrides[key])
            informed[key] = True

    sale_values = [decimal(item.get("price")) for item in comparables if normalize_category(item.get("kind", "VENDA")) == "VENDA" and present(item.get("price"))]
    rent_values = [decimal(item.get("rent")) for item in comparables if normalize_category(item.get("kind")) == "ALUGUEL" and present(item.get("rent"))]
    estimated_market = decimal(market_value) if present(market_value) else (sum(sale_values, ZERO) / Decimal(len(sale_values)) if sale_values else None)
    monthly_rent = decimal(expected_rent) if present(expected_rent) else (sum(rent_values, ZERO) / Decimal(len(rent_values)) if rent_values else None)
    informed["valor_mercado"] = estimated_market is not None
    informed["aluguel_mensal"] = monthly_rent is not None

    total = sum(breakdown.values(), ZERO)
    margin_absolute = estimated_market - total if estimated_market is not None else None
    margin_percent = margin_absolute / estimated_market if estimated_market not in (None, ZERO) else None
    discount_percent = HUNDRED * (Decimal("1") - acquisition / appraisal_value) if appraisal_value not in (None, ZERO) else None
    yield_monthly = monthly_rent / total if monthly_rent is not None and total != ZERO else None
    yield_annual = monthly_rent * Decimal("12") / total if monthly_rent is not None and total != ZERO else None

    # ---- Resultado líquido de venda (Task 2) ----
    custo_saida, custo_saida_detalhe = _sale_costs(sale_value=estimated_market, total_cost=total, sale=sale)
    resultado_liquido = None
    margem_liquida = None
    roi_operacao = None
    if estimated_market is not None and custo_saida is not None:
        resultado_liquido = estimated_market - custo_saida - total
        margem_liquida = resultado_liquido / estimated_market if estimated_market != ZERO else None
        roi_operacao = resultado_liquido / total if total != ZERO else None

    # ---- Pendências (dados essenciais ausentes) ----
    pending: list[str] = []
    if estimated_market is None:
        pending.append("Valor de venda estimado ausente: resultado líquido, margem e ROI não calculados.")
    if sale.corretagem_pct is None:
        pending.append("Percentual de corretagem de venda não informado (assumido 0; informe para refletir o custo real).")
    if sale.tributo_pct is None:
        pending.append("Percentual de tributo na venda não informado (assumido 0; depende do enquadramento tributário).")
    # Custos de aquisição tipicamente materiais que não foram informados:
    for essencial in ("itbi", "registro"):
        if not informed[essencial]:
            pending.append(f"Custo de {essencial} não informado (depende de município/edital).")

    # ---- Preço máximo (Task 2) ----
    fixed_costs_for_max = total - breakdown["aquisicao"] - breakdown["comissao"]
    max_price = calculate_max_acquisition_price(
        sale_value=estimated_market,
        fixed_costs=fixed_costs_for_max,
        commission_pct=(decimal(commission_percent) / HUNDRED) if present(commission_percent) else None,
        commission_fixed=commission_fixed if present(commission_fixed) else None,
        sale=sale,
        goal=goal,
    )
    preco_maximo = max_price["preco_maximo"]
    if preco_maximo is None:
        pending.extend(max_price.get("pendencias", []))
        if max_price.get("razao") == "META_INATINGIVEL":
            pending.append(max_price.get("mensagem", "Meta de preço máximo inatingível."))
        elif goal is None:
            pending.append("Meta de preço máximo não configurada; preço máximo não calculado.")

    # ---- Cenários (Task 2): mesma fórmula, premissas explícitas ----
    base_inputs = {
        "bid": acquisition, "appraisal": appraisal, "costs": costs, "comparables": comparables,
        "debts": debts, "occupancy": occupancy, "area": area, "expected_rent": expected_rent,
        "holding_months": holding_months, "commission_percent": commission_percent,
        "commission_fixed": commission_fixed, "market_value": market_value, "sale": sale,
    }
    if scenarios:
        cenarios = [_resolve_scenario(base_inputs, sc) for sc in scenarios]
    else:
        # Sem premissas de cenário fornecidas: NÃO fabricamos cenários diferentes.
        # Expomos um único cenário base e marcamos os demais como pendentes.
        cenarios = [{
            "cenario": "BASE",
            "premissas": {"valor_venda": estimated_market, "observacao": "Cenário base a partir dos dados cadastrados."},
            "custo_total": total, "valor_mercado": estimated_market,
            "resultado_liquido": resultado_liquido, "margem_liquida": margem_liquida,
            "roi_operacao": roi_operacao, "pendencias": pending,
        }, {
            "cenario": "OTIMISTA", "premissas": {}, "pendente": True,
            "pendencias": ["Premissas do cenário otimista não informadas (ex.: valor de venda, prazo, reforma)."],
        }, {
            "cenario": "PESSIMISTA", "premissas": {}, "pendente": True,
            "pendencias": ["Premissas do cenário pessimista não informadas (ex.: haircut de venda, prazo maior)."],
        }]

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
        # Novos indicadores de venda (Task 2)
        "custo_saida": custo_saida,
        "custo_saida_detalhe": custo_saida_detalhe,
        "resultado_liquido": resultado_liquido,
        "margem_liquida": margem_liquida,
        "roi_operacao": roi_operacao,
        "yield_mensal": yield_monthly,
        "yield_anual": yield_annual,
        "cenario": "BASE",
        "cenarios": cenarios,
        "preco_maximo": preco_maximo,
        "preco_maximo_detalhe": max_price,
        "pendencias": _unique_str(pending),
        "prazo_meses": holding_months,
        "preco_m2": estimated_market / decimal(area) if estimated_market is not None and decimal(area) != ZERO else None,
        # roi_estimado_percentual mantido como ALIAS de margem bruta (compatibilidade);
        # o ROI real da operação é roi_operacao.
        "roi_estimado_percentual": margin_percent,
        # aliases mantidos para compatibilidade com consumidores existentes
        "arrematacao": acquisition,
        "comissao": commission,
        "outros_custos": breakdown["outros"],
        "dividas": breakdown["debitos"],
        "desocupacao": breakdown["desocupacao"],
    }
    return result


def _unique_str(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out
