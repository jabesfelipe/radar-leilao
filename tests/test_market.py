from decimal import Decimal
import pytest
from fastapi import HTTPException

from backend.app.market import calculate_market


def comparable(kind, price=None, rent=None, area=None):
    return {"kind": kind, "price": price, "rent": rent, "area_m2": area}


def test_sem_comparaveis():
    result = calculate_market([])
    assert result == {"venda": {"quantidade": 0, "preco_medio": None, "preco_mediano": None, "preco_m2_medio": None, "preco_m2_mediano": None, "quantidade_com_area": 0}, "aluguel": {"quantidade": 0, "aluguel_medio": None, "aluguel_mediano": None, "aluguel_m2_medio": None, "aluguel_m2_mediano": None, "quantidade_com_area": 0}}


def test_somente_venda_com_media_mediana_e_m2():
    result = calculate_market([comparable("VENDA", Decimal("100"), area=Decimal("10")), comparable("VENDA", Decimal("200"), area=Decimal("20")), comparable("VENDA", Decimal("300"), area=Decimal("30"))])
    venda = result["venda"]
    assert venda["quantidade"] == 3
    assert venda["preco_medio"] == Decimal("200")
    assert venda["preco_mediano"] == Decimal("200")
    assert venda["preco_m2_medio"] == Decimal("10")
    assert venda["preco_m2_mediano"] == Decimal("10")


def test_somente_aluguel_com_mediana_par():
    result = calculate_market([comparable("ALUGUEL", rent=Decimal("1000"), area=Decimal("50")), comparable("ALUGUEL", rent=Decimal("1500"), area=Decimal("50")), comparable("ALUGUEL", rent=Decimal("2000"), area=Decimal("100")), comparable("ALUGUEL", rent=Decimal("2500"), area=Decimal("100"))])
    aluguel = result["aluguel"]
    assert aluguel["quantidade"] == 4
    assert aluguel["aluguel_medio"] == Decimal("1750")
    assert aluguel["aluguel_mediano"] == Decimal("1750")
    assert aluguel["aluguel_m2_medio"] == Decimal("23.75")
    assert aluguel["aluguel_m2_mediano"] == Decimal("22.5")
    assert result["venda"]["quantidade"] == 0


def test_venda_e_aluguel_juntos():
    result = calculate_market([comparable("VENDA", Decimal("200000"), area=Decimal("100")), comparable("ALUGUEL", rent=Decimal("2000"), area=Decimal("100"))])
    assert result["venda"]["quantidade"] == 1
    assert result["aluguel"]["quantidade"] == 1


def test_registros_sem_area_nao_entram_no_m2():
    result = calculate_market([comparable("VENDA", Decimal("100000")), comparable("VENDA", Decimal("200000"), area=Decimal("100")), comparable("ALUGUEL", rent=Decimal("1500"), area=Decimal("0"))])
    assert result["venda"]["quantidade"] == 2
    assert result["venda"]["quantidade_com_area"] == 1
    assert result["venda"]["preco_m2_medio"] == Decimal("2000")
    assert result["aluguel"]["quantidade"] == 1
    assert result["aluguel"]["aluguel_m2_medio"] is None


def test_decimal_e_divisao_por_zero():
    result = calculate_market([comparable("VENDA", Decimal("123.45"), area=Decimal("0"))])
    assert isinstance(result["venda"]["preco_medio"], Decimal)
    assert result["venda"]["preco_m2_mediano"] is None


def test_endpoint_valida_imovel_inexistente():
    from backend.app.main import get_market
    class Db:
        def get(self, model, property_id): return None
    with pytest.raises(HTTPException) as error:
        get_market(999, Db())
    assert error.value.status_code == 404


def test_endpoint_consumes_comparables_do_imovel():
    from backend.app.main import get_market
    class Db:
        def get(self, model, property_id): return type("Property", (), {"id": property_id, "comparables": [type("Comparable", (), {"kind": "VENDA", "price": Decimal("100"), "rent": None, "area_m2": Decimal("10")})()]})()
    result = get_market(1, Db())
    assert result["property_id"] == 1
    assert result["mercado"]["venda"]["preco_medio"] == Decimal("100")
