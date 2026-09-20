from decimal import Decimal

from backend.app.finance import calculate_financial, calculate_max_acquisition_price


def test_custo_total_explicito_do_cenario_da_task():
    result = calculate_financial(bid=Decimal("200000"), costs=[{"category": "REFORMA", "amount": Decimal("20000")}, {"category": "DEBITOS", "amount": Decimal("5000")}], commission_fixed=Decimal("10000"))
    assert result["custo_total"] == Decimal("235000")
    assert result["custos"] == {"aquisicao": Decimal("200000"), "comissao": Decimal("10000"), "itbi": Decimal("0"), "registro": Decimal("0"), "debitos": Decimal("5000"), "condominio": Decimal("0"), "iptu": Decimal("0"), "custos_juridicos": Decimal("0"), "desocupacao": Decimal("0"), "reforma": Decimal("20000"), "outros": Decimal("0")}
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


def test_desconto_margem_e_divisao_por_zero():
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


def test_comparaveis_sao_consumidos_sem_calcular_comparaveis():
    result = calculate_financial(bid=Decimal("100000"), comparables=[{"kind": "VENDA", "price": Decimal("200000")}, {"kind": "ALUGUEL", "rent": Decimal("1500")}])
    assert result["valor_mercado"] == Decimal("200000")
    assert result["aluguel_mensal"] == Decimal("1500")


def test_cenarios_sao_estruturas_neutras_e_preco_maximo_pendente():
    result = calculate_financial(bid=Decimal("100"))
    assert {item["cenario"] for item in result["cenarios"]} == {"BASE", "OTIMISTA", "PESSIMISTA"}
    assert all(item["custo_total"] == Decimal("100") for item in result["cenarios"])
    assert result["preco_maximo"] is None
    assert calculate_max_acquisition_price() is None


def test_valores_monetarios_preservam_decimal():
    result = calculate_financial(bid=Decimal("123.45"), costs=[{"category": "ITBI", "amount": Decimal("0.55")}])
    assert isinstance(result["custo_total"], Decimal)
    assert result["custo_total"] == Decimal("124.00")
