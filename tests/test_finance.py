from decimal import Decimal

from backend.app.finance import (
    GOAL_LUCRO_MINIMO,
    GOAL_MARGEM_MINIMA,
    GOAL_ROI_MINIMO,
    MaxPriceGoal,
    SaleAssumptions,
    ScenarioAssumptions,
    calculate_financial,
    calculate_max_acquisition_price,
)


# ---------------------------------------------------------------------------
# Custos / comissão / margem bruta (comportamento preservado)
# ---------------------------------------------------------------------------

def test_custo_total_explicito_do_cenario_da_task():
    result = calculate_financial(bid=Decimal("200000"), costs=[{"category": "REFORMA", "amount": Decimal("20000")}, {"category": "DEBITOS", "amount": Decimal("5000")}], commission_fixed=Decimal("10000"))
    assert result["custo_total"] == Decimal("235000")
    assert result["custos"]["aquisicao"] == Decimal("200000")
    assert result["custos"]["comissao"] == Decimal("10000")
    assert result["custos"]["reforma"] == Decimal("20000")
    assert result["custos"]["debitos"] == Decimal("5000")
    assert result["custos_informados"]["reforma"] is True
    assert result["custos_informados"]["itbi"] is False


def test_comissao_percentual_e_fixa():
    percentual = calculate_financial(bid=Decimal("200000"), commission_percent=Decimal("5"))
    fixa = calculate_financial(bid=Decimal("200000"), commission_fixed=Decimal("10000"))
    sem_comissao = calculate_financial(bid=Decimal("200000"))
    assert percentual["comissao"] == Decimal("10000.00")
    assert fixa["comissao"] == Decimal("10000")
    assert sem_comissao["comissao"] == Decimal("0")
    assert sem_comissao["custos_informados"]["comissao"] is False


def test_desconto_margem_bruta_e_divisao_por_zero():
    result = calculate_financial(bid=Decimal("200000"), appraisal=Decimal("250000"), commission_fixed=Decimal("0"), market_value=Decimal("320000"))
    assert result["desconto_percentual"] == Decimal("20.0")
    assert result["margem_absoluta"] == Decimal("120000")
    assert result["margem_percentual"] == Decimal("0.375")
    zero = calculate_financial()
    assert zero["desconto_percentual"] is None
    assert zero["margem_percentual"] is None


def test_yield_mensal_e_anual_sobre_custo_total():
    result = calculate_financial(bid=Decimal("200000"), costs=[{"category": "REFORMA", "amount": Decimal("20000")}], expected_rent=Decimal("2200"))
    assert result["custo_total"] == Decimal("220000")
    assert result["yield_mensal"] == Decimal("0.01")
    assert result["yield_anual"] == Decimal("0.12")


def test_valores_monetarios_preservam_decimal():
    result = calculate_financial(bid=Decimal("123.45"), costs=[{"category": "ITBI", "amount": Decimal("0.55")}])
    assert isinstance(result["custo_total"], Decimal)
    assert result["custo_total"] == Decimal("124.00")


# ---------------------------------------------------------------------------
# Resultado líquido de venda (Task 2) — exemplo 1 da SPEC
# ---------------------------------------------------------------------------

def test_resultado_liquido_com_corretagem_e_tributo_base_ganho():
    result = calculate_financial(
        bid=Decimal("200000"),
        commission_fixed=Decimal("10000"),
        costs=[{"category": "ITBI", "amount": Decimal("6000")}, {"category": "REGISTRO", "amount": Decimal("4000")}, {"category": "REFORMA", "amount": Decimal("20000")}],
        market_value=Decimal("320000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0.15")),
    )
    assert result["custo_total"] == Decimal("240000")
    assert result["custo_saida_detalhe"]["corretagem_venda"] == Decimal("16000.00")
    assert result["custo_saida_detalhe"]["tributos_venda"] == Decimal("12000.00")
    assert result["custo_saida"] == Decimal("28000.00")
    assert result["resultado_liquido"] == Decimal("52000.00")
    assert result["margem_liquida"] == (Decimal("52000.00") / Decimal("320000"))
    assert result["roi_operacao"] == (Decimal("52000.00") / Decimal("240000"))


def test_resultado_liquido_nao_e_margem_bruta():
    # margem bruta ignora custos de saída; resultado líquido os considera.
    result = calculate_financial(
        bid=Decimal("200000"), commission_fixed=Decimal("0"), market_value=Decimal("300000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.06"), tributo_pct=Decimal("0")),
    )
    assert result["margem_absoluta"] == Decimal("100000")          # bruta
    assert result["custo_saida"] == Decimal("18000.00")            # 6% de 300000
    assert result["resultado_liquido"] == Decimal("82000.00")      # 300000 - 18000 - 200000


def test_valor_de_venda_ausente_nao_calcula_resultado_liquido():
    result = calculate_financial(bid=Decimal("200000"))
    assert result["valor_mercado"] is None
    assert result["resultado_liquido"] is None
    assert result["margem_liquida"] is None
    assert any("Valor de venda estimado ausente" in p for p in result["pendencias"])


def test_custos_ausentes_nao_viram_zero_silencioso_nas_pendencias():
    result = calculate_financial(bid=Decimal("100000"), market_value=Decimal("150000"))
    # ITBI/registro não informados aparecem como pendência (dependem de município/edital).
    assert any("itbi" in p.lower() for p in result["pendencias"])
    assert any("registro" in p.lower() for p in result["pendencias"])
    assert result["custos_informados"]["itbi"] is False


# ---------------------------------------------------------------------------
# Preço máximo de aquisição (Task 2)
# ---------------------------------------------------------------------------

def test_preco_maximo_lucro_minimo_comissao_percentual():
    # Exemplo 2 da SPEC: V=320000, corretagem 5%, tributo 0, F=30000, comissão 5%, meta 40000.
    out = calculate_max_acquisition_price(
        sale_value=Decimal("320000"),
        fixed_costs=Decimal("30000"),
        commission_pct=Decimal("0.05"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert out["viavel"] is True
    # (320000 - 16000 - 30000 - 40000) / 1.05 = 234000/1.05
    assert out["preco_maximo"] == (Decimal("234000") / Decimal("1.05"))


def test_preco_maximo_verificacao_do_resultado():
    # Confere que ao arrematar pelo preço máximo, o lucro é exatamente a meta.
    A = (Decimal("234000") / Decimal("1.05"))
    result = calculate_financial(
        bid=A, commission_percent=Decimal("5"),
        costs=[{"category": "ITBI", "amount": Decimal("10000")}, {"category": "REGISTRO", "amount": Decimal("20000")}],
        market_value=Decimal("320000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
    )
    # resultado_liquido ~ 40000 (tolerância de centavos por divisão)
    assert abs(result["resultado_liquido"] - Decimal("40000")) < Decimal("0.01")


def test_preco_maximo_margem_minima_com_comissao_fixa():
    # V=400000, comissão fixa 12000, F=8000 (=20000 total fixo), corretagem 0, tributo 0, margem 20%.
    out = calculate_max_acquisition_price(
        sale_value=Decimal("400000"),
        fixed_costs=Decimal("8000"),
        commission_fixed=Decimal("12000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_MARGEM_MINIMA, value=Decimal("0.20")),
    )
    assert out["viavel"] is True
    # A_max = (400000*0.8 - 0 - 20000)/1 = 320000 - 20000 = 300000
    assert out["preco_maximo"] == Decimal("300000")


def test_preco_maximo_roi_minimo():
    # V=300000, sem custos fixos/comissão, corretagem 0, tributo 0, ROI 25%.
    out = calculate_max_acquisition_price(
        sale_value=Decimal("300000"),
        fixed_costs=Decimal("0"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_ROI_MINIMO, value=Decimal("0.25")),
    )
    assert out["viavel"] is True
    # custo_total <= 300000/1.25 = 240000; A_max = 240000
    assert out["preco_maximo"] == Decimal("240000")


# ---------------------------------------------------------------------------
# Preço máximo SEGURO (Task 4): definitivo vs. provisório por custos desconhecidos
# ---------------------------------------------------------------------------

def test_preco_maximo_definitivo_quando_sem_custos_desconhecidos():
    out = calculate_max_acquisition_price(
        sale_value=Decimal("320000"), fixed_costs=Decimal("30000"), commission_pct=Decimal("0.05"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
        unknown_costs=[],
    )
    assert out["viavel"] is True
    assert out["definitivo"] is True
    assert out["provisorio"] is False


def test_preco_maximo_provisorio_quando_ha_custos_desconhecidos():
    out = calculate_max_acquisition_price(
        sale_value=Decimal("320000"), fixed_costs=Decimal("30000"), commission_pct=Decimal("0.05"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
        unknown_costs=["itbi", "registro"],
    )
    # O valor ainda é calculado (estimativa), mas NÃO é definitivo.
    assert out["preco_maximo"] is not None
    assert out["definitivo"] is False
    assert out["provisorio"] is True
    assert any("ESTIMATIVA PROVISÓRIA" in p for p in out["pendencias"])
    assert out["custos_desconhecidos"] == ["itbi", "registro"]


def test_calculate_financial_itbi_desconhecido_torna_preco_maximo_provisorio():
    # ITBI/registro não informados => preço máximo provisório (não definitivo).
    result = calculate_financial(
        bid=Decimal("200000"), commission_percent=Decimal("5"), market_value=Decimal("320000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert result["preco_maximo"] is not None
    assert result["preco_maximo_provisorio"] is True
    assert result["preco_maximo_definitivo"] is False
    assert "itbi" in result["preco_maximo_detalhe"]["custos_desconhecidos"]


def test_calculate_financial_comissao_desconhecida_torna_provisorio():
    # Sem comissão informada (nem % nem fixa) => comissão de arrematação desconhecida.
    result = calculate_financial(
        bid=Decimal("200000"), market_value=Decimal("320000"),
        costs=[{"category": "ITBI", "amount": Decimal("6000")}, {"category": "REGISTRO", "amount": Decimal("4000")}],
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0.15")),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert result["preco_maximo_provisorio"] is True
    assert "comissao_arrematacao" in result["preco_maximo_detalhe"]["custos_desconhecidos"]


def test_calculate_financial_corretagem_desconhecida_torna_provisorio():
    result = calculate_financial(
        bid=Decimal("200000"), commission_fixed=Decimal("10000"), market_value=Decimal("320000"),
        costs=[{"category": "ITBI", "amount": Decimal("6000")}, {"category": "REGISTRO", "amount": Decimal("4000")}],
        sale=SaleAssumptions(tributo_pct=Decimal("0.15")),  # corretagem ausente
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert result["preco_maximo_provisorio"] is True
    assert "corretagem_venda" in result["preco_maximo_detalhe"]["custos_desconhecidos"]


def test_calculate_financial_tributo_desconhecido_torna_provisorio():
    result = calculate_financial(
        bid=Decimal("200000"), commission_fixed=Decimal("10000"), market_value=Decimal("320000"),
        costs=[{"category": "ITBI", "amount": Decimal("6000")}, {"category": "REGISTRO", "amount": Decimal("4000")}],
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05")),  # tributo ausente
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert result["preco_maximo_provisorio"] is True
    assert "tributo_venda" in result["preco_maximo_detalhe"]["custos_desconhecidos"]


def test_calculate_financial_premissas_completas_preco_maximo_definitivo():
    # Todos os custos materiais informados => preço máximo DEFINITIVO com valor esperado.
    result = calculate_financial(
        bid=Decimal("200000"), commission_percent=Decimal("5"), market_value=Decimal("320000"),
        costs=[{"category": "ITBI", "amount": Decimal("10000")}, {"category": "REGISTRO", "amount": Decimal("20000")}],
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert result["preco_maximo_definitivo"] is True
    assert result["preco_maximo_provisorio"] is False
    # F = 30000, corretagem 16000, meta 40000, k=1.05 => (320000-16000-30000-40000)/1.05
    assert result["preco_maximo"] == (Decimal("234000") / Decimal("1.05"))


def test_preco_maximo_provisorio_por_margem_e_roi():
    for goal in (MaxPriceGoal(kind=GOAL_MARGEM_MINIMA, value=Decimal("0.2")), MaxPriceGoal(kind=GOAL_ROI_MINIMO, value=Decimal("0.25"))):
        out = calculate_max_acquisition_price(
            sale_value=Decimal("400000"), fixed_costs=Decimal("0"),
            sale=SaleAssumptions(corretagem_pct=Decimal("0"), tributo_pct=Decimal("0"), tax_base="VENDA"),
            goal=goal, unknown_costs=["itbi"],
        )
        assert out["preco_maximo"] is not None
        assert out["provisorio"] is True


def test_preco_maximo_inviavel_retorna_none():
    out = calculate_max_acquisition_price(
        sale_value=Decimal("100000"),
        fixed_costs=Decimal("90000"),
        commission_pct=Decimal("0.05"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("50000")),
    )
    assert out["preco_maximo"] is None
    assert out["viavel"] is False
    assert out["razao"] == "META_INATINGIVEL"


def test_preco_maximo_sem_valor_de_venda_e_pendente():
    out = calculate_max_acquisition_price(goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("10000")))
    assert out["preco_maximo"] is None
    assert out["viavel"] is False
    assert any("Valor de venda" in p for p in out["pendencias"])


def test_preco_maximo_sem_meta_e_pendente():
    out = calculate_max_acquisition_price(sale_value=Decimal("300000"))
    assert out["preco_maximo"] is None
    assert any("Meta financeira" in p for p in out["pendencias"])


def test_preco_maximo_meta_invalida():
    out = calculate_max_acquisition_price(sale_value=Decimal("300000"), goal=MaxPriceGoal(kind="OUTRA", value=Decimal("1")))
    assert out["preco_maximo"] is None
    assert out["razao"] == "META_INVALIDA"


def test_calculate_financial_sem_meta_nao_calcula_preco_maximo():
    # Sem goal configurado, o preço máximo permanece None e vira pendência (não é inventado).
    result = calculate_financial(bid=Decimal("100000"), market_value=Decimal("150000"))
    assert result["preco_maximo"] is None
    assert any("Meta de preço máximo não configurada" in p for p in result["pendencias"])


def test_calculate_financial_com_meta_calcula_preco_maximo():
    result = calculate_financial(
        bid=Decimal("200000"), commission_percent=Decimal("5"),
        costs=[{"category": "ITBI", "amount": Decimal("10000")}, {"category": "REGISTRO", "amount": Decimal("20000")}],
        market_value=Decimal("320000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        goal=MaxPriceGoal(kind=GOAL_LUCRO_MINIMO, value=Decimal("40000")),
    )
    assert result["preco_maximo"] == (Decimal("234000") / Decimal("1.05"))
    assert result["preco_maximo_detalhe"]["viavel"] is True


# ---------------------------------------------------------------------------
# Cenários (Task 2)
# ---------------------------------------------------------------------------

def test_cenarios_sem_premissas_marcam_otimista_e_pessimista_como_pendentes():
    result = calculate_financial(bid=Decimal("100"), market_value=Decimal("200"))
    por_nome = {c["cenario"]: c for c in result["cenarios"]}
    assert set(por_nome) == {"BASE", "OTIMISTA", "PESSIMISTA"}
    assert por_nome["OTIMISTA"].get("pendente") is True
    assert por_nome["PESSIMISTA"].get("pendente") is True
    assert por_nome["BASE"].get("pendente") is not True


def test_resultado_provisorio_quando_custos_materiais_desconhecidos():
    # Sem ITBI/registro/corretagem/tributo informados, o resultado é provisório.
    result = calculate_financial(bid=Decimal("200000"), market_value=Decimal("300000"))
    assert result["resultado_liquido"] is not None
    assert result["resultado_provisorio"] is True
    assert result["resultado_completo"] is False
    assert result["custos_status"]["itbi"] == "DESCONHECIDO"
    assert result["saida_status"]["corretagem_venda"] == "DESCONHECIDO"


def test_resultado_completo_quando_custos_materiais_informados():
    result = calculate_financial(
        bid=Decimal("200000"),
        costs=[{"category": "ITBI", "amount": Decimal("6000")}, {"category": "REGISTRO", "amount": Decimal("4000")}],
        market_value=Decimal("300000"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0.15")),
    )
    assert result["resultado_provisorio"] is False
    assert result["resultado_completo"] is True
    assert result["custos_status"]["itbi"] == "INFORMADO"
    assert result["saida_status"]["tributos_venda"] == "INFORMADO"


def test_carregamento_mensal_multiplica_pelo_prazo_sem_duplicar():
    # 500/mês por 10 meses = 5000 de carregamento recorrente.
    result = calculate_financial(bid=Decimal("100000"), monthly_carrying=Decimal("500"), holding_months=10)
    assert result["carregamento_recorrente"] == Decimal("5000")
    assert result["custos"]["carregamento"] == Decimal("5000")
    # custo único de carregamento informado NÃO é duplicado pelo mensal.
    result2 = calculate_financial(
        bid=Decimal("100000"), monthly_carrying=Decimal("500"), holding_months=10,
        costs=[{"category": "CARREGAMENTO", "amount": Decimal("1000")}],
    )
    assert result2["custos"]["carregamento"] == Decimal("6000")  # 1000 único + 5000 recorrente


def test_prazo_zero_nao_gera_carregamento_recorrente():
    result = calculate_financial(bid=Decimal("100000"), monthly_carrying=Decimal("500"), holding_months=0)
    assert result["carregamento_recorrente"] == Decimal("0")


def test_cenarios_com_premissas_usam_mesma_formula_e_diferenciam_resultado():
    base = ScenarioAssumptions(nome="BASE", valor_venda=Decimal("300000"))
    otimista = ScenarioAssumptions(nome="OTIMISTA", valor_venda=Decimal("340000"), justificativa="venda acima da média")
    pessimista = ScenarioAssumptions(nome="PESSIMISTA", valor_venda=Decimal("260000"), reforma=Decimal("30000"), justificativa="haircut + reforma maior")
    result = calculate_financial(
        bid=Decimal("200000"), commission_fixed=Decimal("0"),
        sale=SaleAssumptions(corretagem_pct=Decimal("0"), tributo_pct=Decimal("0"), tax_base="VENDA"),
        scenarios=[base, otimista, pessimista],
    )
    por_nome = {c["cenario"]: c for c in result["cenarios"]}
    # Mesma fórmula: resultado_liquido = V - 0 - custo_total.
    assert por_nome["BASE"]["resultado_liquido"] == Decimal("100000")     # 300000 - 200000
    assert por_nome["OTIMISTA"]["resultado_liquido"] == Decimal("140000")  # 340000 - 200000
    # pessimista tem reforma 30000 no custo total: 260000 - 230000 = 30000
    assert por_nome["PESSIMISTA"]["resultado_liquido"] == Decimal("30000")
    # premissas visíveis
    assert por_nome["PESSIMISTA"]["premissas"]["justificativa"] == "haircut + reforma maior"
