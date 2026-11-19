"""v1.0.12 — Fase E: estimativa condominial pelo período da matrícula (dados fictícios)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app import models, parameters as params
from backend.app.estimates_service import AVISO_ESTIMATIVA, estimate_from_registry, persist_condominium_estimate
from backend.app.parameter_seeds import seed_parameters
from backend.app.viability import market_intelligence
from tests.test_checklist_evidencias import CONDICOES_FICTICIAS, _doc, _leilao, _prop
from tests.test_v107_imovel7_regressao import MATRICULA_FICTICIA
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)

DIA = date(2003, 4, 3)   # mesmo dia da consolidação fictícia: sem meses após a consolidação


def _imovel(db, condicoes=True):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    if condicoes:
        _doc(db, prop, CONDICOES_FICTICIAS, "condicoes.txt", "CONDICOES_VENDA")
    db.flush(); db.expire(prop)
    return prop


def test_periodo_da_matricula_cenarios_e_encargos(db):
    out = estimate_from_registry(db, _imovel(db), monthly_reference=Decimal("500"), today=DIA)
    assert out["possivel"] and out["aviso"] == AVISO_ESTIMATIVA and out["status"] == "ESTIMADO"
    m = out["memoria_calculo"]
    assert (m["data_aquisicao"], m["origem_data_aquisicao"]) == ("2001-02-01", "matrícula (R-2)")
    assert (m["data_consolidacao"], m["origem_data_consolidacao"]) == ("2003-04-03", "matrícula (Av-5)")
    assert m["periodo_meses"] == 26 and m["periodo_considerado_meses"] == 26 and m["teto_periodo_meses"] == 60
    assert "NÃO prova inadimplência" in m["nota"]
    d = out["cenarios_detalhe"]
    assert [d[k]["meses_em_atraso"] for k in ("baixo", "provavel", "alto")] == [4, 9, 18]
    assert (d["provavel"]["principal"], d["provavel"]["multa"], d["provavel"]["juros"], d["provavel"]["correcao"], d["provavel"]["total"]) == (
        Decimal("4500.00"), Decimal("90.00"), Decimal("225.00"), Decimal("90.00"), Decimal("4905.00"))
    assert d["alto"]["total"] == Decimal("10377.00") and d["baixo"]["total"] == Decimal("2110.00")
    assert out["cenarios"] == {"conservador": Decimal("10377.00"), "provavel": Decimal("4905.00"), "otimista": Decimal("2110.00")}
    assert out["confianca"] == "MEDIA"                                             # valor informado + datas da matrícula


def test_regra_da_venda_aplicada_depois_da_estimativa(db):
    out = estimate_from_registry(db, _imovel(db), monthly_reference=Decimal("2000"), today=DIA)
    alto = out["cenarios_detalhe"]["alto"]
    assert alto["divida_potencial"] == Decimal("41508.00")
    assert (alto["responsabilidade_comprador"], alto["responsabilidade_caixa"], alto["valor_no_financeiro"]) == (
        Decimal("22000.00"), Decimal("19508.00"), Decimal("22000.00"))
    assert out["cenarios_detalhe"]["baixo"]["valor_no_financeiro"] is None and out["regra_venda"]["fonte"] == "DOCUMENTO"


def test_teto_do_periodo_configuravel(db):
    seed_parameters(db)
    param = db.query(models.Parameter).filter(models.Parameter.key == "condominio.periodo_maximo_meses", models.Parameter.scope == "GLOBAL").one()
    params.update_parameter(db, param, {"value": "12"}, actor="admin", justification="teste")
    db.flush()
    out = estimate_from_registry(db, _imovel(db), monthly_reference=Decimal("500"), today=DIA)
    assert out["memoria_calculo"]["periodo_considerado_meses"] == 12 and out["cenarios_detalhe"]["provavel"]["meses_em_atraso"] == 4


def test_valor_mensal_do_admin_quando_nao_informado(db):
    seed_parameters(db)
    param = db.query(models.Parameter).filter(models.Parameter.key == "condominio.valor_mensal_referencia", models.Parameter.scope == "GLOBAL").one()
    params.update_parameter(db, param, {"value": "300"}, actor="admin", justification="teste")
    db.flush()
    out = estimate_from_registry(db, _imovel(db), today=DIA)
    assert out["memoria_calculo"]["origem_valor_mensal"] == "ADMIN" and out["memoria_calculo"]["valor_mensal_referencia"] == Decimal("300")
    assert out["confianca"] == "BAIXA"


def test_sem_dados_nao_inventa(db):
    prop = _prop(db)
    out = estimate_from_registry(db, prop, today=DIA)
    assert out["possivel"] is False and "valor mensal" in out["motivo"] and "data de aquisição" in out["motivo"] and out["cenarios"] is None


def test_estimativa_registrada_alimenta_a_composicao(db):
    prop = _imovel(db)
    computed = estimate_from_registry(db, prop, monthly_reference=Decimal("2000"), today=DIA)
    persist_condominium_estimate(db, prop, computed=computed, monthly_reference=Decimal("2000"), property_age_years=None, condominium_age_years=None,
                                 financing_age_years=None, justification="teste")
    db.flush(); db.expire(prop)
    linha = next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == "condominio_atraso")
    assert linha["status"] == "ESTIMADO" and linha["fonte_divida"] == "ESTIMATIVA"
    assert linha["valor_base"] == Decimal("19620.00")                               # provável (abaixo do teto)
    assert linha["valor_conservador"] == Decimal("22000.00")                        # alto (41.508) limitado ao teto


def test_api_calcula_e_registra(api):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    client.post(f"/api/imoveis/{pid}/documentos", files={"file": ("matricula.txt", "\n".join(MATRICULA_FICTICIA).encode(), "text/plain")},
                data={"document_type": "MATRICULA"})
    previa = client.post(f"/api/imoveis/{pid}/debitos/estimar-condominio/matricula", json={"monthly_reference": "500"}).json()
    assert previa["estimativa"]["possivel"] and previa["estimativa_id"] is None
    salvo = client.post(f"/api/imoveis/{pid}/debitos/estimar-condominio/matricula", json={"monthly_reference": "500", "persist": True}).json()
    assert salvo["estimativa_id"] is not None
    lista = client.get(f"/api/imoveis/{pid}/debitos/estimativas-condominio").json()["estimativas"]
    assert lista[0]["id"] == salvo["estimativa_id"] and lista[0]["assumptions"]["memoria_calculo"]["metodo"] == "PERIODO_MATRICULA"
