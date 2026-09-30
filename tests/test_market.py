from decimal import Decimal
import pytest
from fastapi import HTTPException

from backend.app.market import calculate_market


def comparable(kind, price=None, rent=None, area=None):
    return {"kind": kind, "price": price, "rent": rent, "area_m2": area}


def test_sem_comparaveis():
    result = calculate_market([])
    assert result["venda"]["quantidade"] == 0
    assert result["venda"]["preco_medio"] is None
    assert result["aluguel"]["quantidade"] == 0
    assert result["aluguel"]["aluguel_medio"] is None
    # Qualidade sinaliza ausência de base — média/mediana nunca é avaliação definitiva.
    assert result["venda"]["qualidade"]["amostra_suficiente"] is False
    assert result["venda"]["qualidade"]["avaliacao_definitiva"] is False
    assert any("Sem comparáveis" in a for a in result["venda"]["qualidade"]["avisos"])
    assert result["fontes"] == []


def test_amostra_insuficiente_e_sinalizada():
    # 3 comparáveis (< 7 recomendados) → indicativo, não conclusivo.
    result = calculate_market([comparable("VENDA", Decimal("100000"), area=Decimal("50")) for _ in range(3)])
    q = result["venda"]["qualidade"]
    assert q["quantidade"] == 3
    assert q["amostra_suficiente"] is False
    assert any("Amostra insuficiente" in a for a in q["avisos"])


def test_amostra_suficiente_homogenea():
    # 7 comparáveis iguais → suficiente e sem dispersão.
    result = calculate_market([comparable("VENDA", Decimal("200000"), area=Decimal("100")) for _ in range(7)])
    q = result["venda"]["qualidade"]
    assert q["amostra_suficiente"] is True
    assert q["dispersao_elevada"] is False


def test_dispersao_elevada_e_sinalizada():
    precos = [Decimal("100000"), Decimal("120000"), Decimal("130000"), Decimal("500000"), Decimal("140000"), Decimal("110000"), Decimal("125000")]
    result = calculate_market([comparable("VENDA", p, area=Decimal("100")) for p in precos])
    q = result["venda"]["qualidade"]
    assert q["amostra_suficiente"] is True
    assert q["dispersao_elevada"] is True
    assert any("Dispersão elevada" in a for a in q["avisos"])


def test_fontes_preservam_origem_e_url():
    result = calculate_market([
        {"kind": "VENDA", "price": Decimal("100000"), "area_m2": Decimal("50"), "source": "Portal X", "url": "http://x", "date": "2026-09-01"},
        {"kind": "VENDA", "price": Decimal("110000"), "area_m2": Decimal("50")},
    ])
    assert len(result["fontes"]) == 1
    assert result["fontes"][0]["source"] == "Portal X"
    assert result["fontes"][0]["data"] == "2026-09-01"


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
