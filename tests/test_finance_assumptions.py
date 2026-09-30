"""TASK 3 — integração das premissas financeiras (persistência + build_finance +
endpoints + veredito). Usa PostgreSQL real (fixture ``db``; rollback ao final).
Sem LLM e sem análise real.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException

from backend.app import models, services


def _property_com_leilao(db, *, bid=Decimal("200000")):
    prop = models.Property(title="Imóvel Fin", address="Rua Fin", city="São Paulo", state="SP", area_m2=70, bedrooms=2)
    db.add(prop)
    db.flush()
    auction = models.Auction(property_id=prop.id, bid_value=bid, appraisal_value=Decimal("300000"))
    db.add(auction)
    db.flush()
    return prop, auction


# --------------------------------------------------------------------------
# build_finance repassa as premissas persistidas ao motor
# --------------------------------------------------------------------------

def test_build_finance_sem_premissas_preco_maximo_pendente(db):
    prop, _ = _property_com_leilao(db)
    result = services.build_finance(prop)
    assert result["preco_maximo"] is None
    assert any("Meta de preço máximo não configurada" in p for p in result["pendencias"])


def test_build_finance_com_premissas_calcula_preco_maximo(db):
    prop, auction = _property_com_leilao(db)
    auction.financial_assumptions = {
        "goal_kind": "LUCRO_MINIMO", "goal_value": "40000",
        "corretagem_pct": "0.05", "tributo_pct": "0", "tax_base": "VENDA",
        "valor_venda_estimado": "320000",
    }
    db.flush()
    result = services.build_finance(prop)
    assert result["preco_maximo"] is not None
    assert result["preco_maximo_detalhe"]["viavel"] is True


def test_build_finance_carregamento_mensal_x_prazo(db):
    prop, auction = _property_com_leilao(db)
    auction.financial_assumptions = {"carregamento_mensal": "500", "prazo_meses": 8}
    db.flush()
    result = services.build_finance(prop)
    assert result["carregamento_recorrente"] == Decimal("4000")


# --------------------------------------------------------------------------
# Endpoint: informar, recuperar, persistir e reexecutar
# --------------------------------------------------------------------------

def test_endpoint_set_e_get_premissas_persistem(db):
    from backend.app.main import get_finance_assumptions, set_finance_assumptions
    from backend.app import schemas

    prop, _ = _property_com_leilao(db)
    payload = schemas.FinanceAssumptions(
        goal_kind="MARGEM_MINIMA", goal_value=Decimal("0.2"),
        corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0.15"), tax_base="GANHO",
        valor_venda_estimado=Decimal("320000"), prazo_meses=12, carregamento_mensal=Decimal("400"),
    )
    out = set_finance_assumptions(prop.id, payload, db)
    assert out["premissas"]["goal_kind"] == "MARGEM_MINIMA"
    assert out["financeiro"]["preco_maximo"] is not None

    # Recupera as premissas (persistência).
    got = get_finance_assumptions(prop.id, db)
    assert got["premissas"]["valor_venda_estimado"] == "320000"
    assert got["premissas"]["carregamento_mensal"] == "400"


def test_endpoint_premissas_valida_percentual_fora_do_limite():
    from backend.app import schemas
    with pytest.raises(Exception):
        schemas.FinanceAssumptions(corretagem_pct=Decimal("1.5"))  # > 1 (150%)


def test_endpoint_premissas_valida_meta_incompleta():
    from backend.app import schemas
    with pytest.raises(Exception):
        schemas.FinanceAssumptions(goal_kind="LUCRO_MINIMO")  # sem goal_value


def test_analyze_financial_snapshota_premissas_e_preserva_historico(db):
    from backend.app.main import analyze_financial, set_finance_assumptions
    from backend.app import schemas

    prop, _ = _property_com_leilao(db)
    set_finance_assumptions(prop.id, schemas.FinanceAssumptions(
        goal_kind="LUCRO_MINIMO", goal_value=Decimal("40000"),
        corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA",
        valor_venda_estimado=Decimal("320000"),
    ), db)

    v1 = analyze_financial(prop.id, db)
    assert v1["analysis_version"] == 1
    assert v1["premissas"]["goal_kind"] == "LUCRO_MINIMO"

    # Altera a premissa e reexecuta: nova versão, histórico preservado.
    set_finance_assumptions(prop.id, schemas.FinanceAssumptions(
        goal_kind="LUCRO_MINIMO", goal_value=Decimal("60000"),
        corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA",
        valor_venda_estimado=Decimal("320000"),
    ), db)
    v2 = analyze_financial(prop.id, db)
    assert v2["analysis_version"] == 2

    historico = db.scalars(
        __import__("sqlalchemy").select(models.FinancialAnalysis).where(models.FinancialAnalysis.property_id == prop.id).order_by(models.FinancialAnalysis.analysis_version)
    ).all()
    assert len(historico) == 2
    # O snapshot da v1 preserva a meta antiga (40000); a v2 tem a nova (60000).
    assert historico[0].inputs["premissas"]["goal_value"] == "40000"
    assert historico[1].inputs["premissas"]["goal_value"] == "60000"


def test_imovel_inexistente_premissas_404(db):
    from backend.app.main import get_finance_assumptions
    with pytest.raises(HTTPException) as exc:
        get_finance_assumptions(999999, db)
    assert exc.value.status_code == 404
