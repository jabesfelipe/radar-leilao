"""Revisão final da PR #7: duplicidade de débitos, consulta indisponível × estimativa, parâmetros municipais, estimativa
condominial (bordas e fórmula) e privacidade/autorização das rotas novas. Dados fictícios; sem rede."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.app import debts_service, models, parameters as params
from backend.app.estimates_service import estimate_from_registry
from backend.app.registry_chain import read_registry
from backend.app.registry_timeline import build_timeline
from backend.app.viability import debt_exposure, market_intelligence, municipality_id_for, verdict_finance
from tests.test_checklist_evidencias import CONDICOES_FICTICIAS, _doc, _leilao, _prop
from tests.test_security_gate import _login, _property, env  # noqa: F401 (fixture com o portão real)

D = Decimal


def _linha(db, prop, chave):
    db.flush(); db.expire(prop)
    return next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == chave)


def _base(db, condicoes=False):
    prop = _prop(db)
    _leilao(db, prop)
    if condicoes:
        _doc(db, prop, CONDICOES_FICTICIAS, "condicoes.txt", "CONDICOES_VENDA")
    db.flush()
    return prop


# =============================================================== 1. duplicidade de débitos

def test_mesmo_debito_no_legado_e_na_central_conta_uma_vez(db):
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=D("1200"), status="PENDENTE"))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="COTA_CONDOMINIAL", status="INFORMADO", original_amount=D("1200")))
    linha = _linha(db, prop, "condominio_atraso")
    assert linha["divida_total"] == D("1200.00")
    assert len(linha["duplicidades"]) == 1 and linha["duplicidades"][0]["descartado"].startswith("Debt #")
    assert [c["origem"] for c in linha["componentes"]] == ["PropertyDebt"] and "contado(s) uma vez só" in linha["observacao"]


def test_legado_confirmado_prevalece_sobre_central_informada(db):
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="IPTU", amount=D("800"), status="CONFIRMADO", reference_date=date(2024, 3, 1)))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="INFORMADO", original_amount=D("800"), fiscal_year=2024))
    linha = _linha(db, prop, "tributos_atraso")
    assert linha["divida_total"] == D("800.00") and linha["fonte_divida"] == "CONFIRMADO"
    assert linha["duplicidades"][0]["descartado"].startswith("PropertyDebt #")


def test_debitos_distintos_somam_e_exercicio_diferente_nao_e_duplicidade(db):
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="IPTU", amount=D("800"), status="PENDENTE", reference_date=date(2023, 3, 1)))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="INFORMADO", original_amount=D("800"), fiscal_year=2024))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="INFORMADO", original_amount=D("150"), fiscal_year=2024))
    linha = _linha(db, prop, "tributos_atraso")
    assert linha["divida_total"] == D("1750.00") and linha["duplicidades"] == [] and len(linha["componentes"]) == 3


def test_consulta_repetida_na_central_nao_duplica(db):
    prop = _base(db)
    for _ in range(2):
        db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="INFORMADO", original_amount=D("300"), competence="2025",
                                   fiscal_year=2025))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="INFORMADO", original_amount=D("90"), external_id="X-1"))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="INFORMADO", original_amount=D("95"), external_id="X-1"))
    linha = _linha(db, prop, "tributos_atraso")
    assert linha["divida_total"] == D("390.00") and len(linha["duplicidades"]) == 2


def test_legado_repetido_so_e_duplicidade_com_a_mesma_data(db):
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=D("400"), status="PENDENTE", reference_date=date(2025, 1, 10)))
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=D("400"), status="PENDENTE", reference_date=date(2025, 1, 10)))
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=D("400"), status="PENDENTE"))       # sem data: cota distinta possível
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=D("400"), status="PENDENTE"))
    linha = _linha(db, prop, "condominio_atraso")
    assert linha["divida_total"] == D("1200.00") and len(linha["duplicidades"]) == 1


def test_custo_cadastrado_do_mesmo_tipo_nao_soma_com_a_divida(db):
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=D("1000"), status="PENDENTE"))
    db.add(models.Cost(property_id=prop.id, category="Condomínio", description="condomínio em atraso (mesma dívida)", amount=D("1000")))
    linha = _linha(db, prop, "condominio_atraso")
    intel_total = linha["divida_total"]
    assert intel_total == D("1000.00") and linha["custo_ignorado"] == D("1000.00") and "não somado" in linha["observacao"]


def test_taxa_condominial_nao_entra_como_tributo_e_estimado_legado_nao_e_divida(db):
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="TAXA CONDOMINIAL", amount=D("700"), status="PENDENTE"))
    db.add(models.Debt(property_id=prop.id, category="IPTU", amount=D("500"), status="ESTIMADO"))
    db.flush(); db.expire(prop)
    exp = debt_exposure(db, prop, {})
    assert exp["condominio_atraso"]["valor"] == D("700.00")
    assert exp["tributos_atraso"]["valor"] is None and exp["tributos_atraso"]["fonte"] == "ESTIMATIVA"   # estimativa, não dívida


def test_consolidacao_da_central_tambem_sem_dupla_contagem(db):
    debts_service.seed_all(db)
    prop = _base(db)
    db.add(models.Debt(property_id=prop.id, category="IPTU", amount=D("500"), status="CONFIRMADO"))
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", status="CONFIRMADO", updated_amount=D("500")))
    db.flush()
    c = debts_service.consolidate(db, prop.id)
    assert c["totais"]["confirmados"] == D("500") and len(c["duplicidades"]) == 1


# =============================================================== 2. consulta indisponível × estimativa

def test_indisponivel_com_estimativa_fica_como_estimativa_e_mantem_a_ressalva(db):
    prop = _base(db, condicoes=True)
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="COTA_CONDOMINIAL", status="INDISPONIVEL"))
    db.add(models.CondominiumEstimate(property_id=prop.id, monthly_source="INFORMADO", scenario_otimista=D("1000"), scenario_provavel=D("3000"),
                                      scenario_conservador=D("6000"), confidence="BAIXA", assumptions={}))
    linha = _linha(db, prop, "condominio_atraso")
    assert linha["status"] == "ESTIMADO" and linha["natureza_valor"] == "ESTIMATIVA" and linha["fonte_divida"] == "ESTIMATIVA"
    assert linha["exposicao"]["divida_confirmada"] is None and linha["divida_total"] is None
    assert linha["consulta_indisponivel"] is True
    assert any("ESTIMATIVA, não dívida confirmada" in r for r in linha["ressalvas"]) and "Consulta indisponível" in linha["observacao"]
    assert linha["observacao"].startswith("ESTIMATIVA, não dívida confirmada")
    fin = verdict_finance(db, prop)
    assert any("não é dívida confirmada" in p and "Consulta indisponível" in p for p in fin["pendencias"])
    item = next(c for c in fin["composicao_custos"] if c["chave"] == "condominio_atraso")
    assert item["natureza"] == "ESTIMADO"                                                    # nunca CONFIRMADO


def test_indisponivel_sem_estimativa_nunca_vira_zero(db):
    prop = _base(db)
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="COTA_CONDOMINIAL", status="EM_VALIDACAO"))
    linha = _linha(db, prop, "condominio_atraso")
    assert linha["valor_base"] is None and linha["status"] == "PENDENTE" and linha["consulta_indisponivel"] is True


# =============================================================== 3. parâmetros municipais

def _itbi(db, prop):
    return _linha(db, prop, "itbi")


def _param(db, municipality_id, value):
    if municipality_id is None:   # o GLOBAL já vem do seed (sem valor): só recebe o valor
        glob = db.query(models.Parameter).filter(models.Parameter.key == "viabilidade.itbi_aliquota", models.Parameter.scope == "GLOBAL").one()
        params.update_parameter(db, glob, {"value": value}, actor="teste", justification="fonte fictícia")
    else:
        params.create_parameter(db, {"key": "viabilidade.itbi_aliquota", "name": "ITBI", "category": "financeiro", "data_type": "DECIMAL",
                                     "scope": "MUNICIPIO", "municipality_id": municipality_id, "value": value},
                                actor="teste", justification="fonte fictícia")
    db.flush()


def _muni(db, name, state):
    return db.query(models.Municipality).filter(models.Municipality.name == name, models.Municipality.state == state).one()


def _prop_em(db, city, state):
    prop = _base(db)
    prop.city, prop.state = city, state
    db.flush()
    return prop


def test_itbi_municipal_prevalece_e_nao_vaza_para_outro_municipio(db):
    debts_service.seed_all(db)
    _param(db, None, "0.02")
    _param(db, _muni(db, "Curitiba", "PR").id, "0.027")
    cwb, frg = _prop_em(db, "Curitiba", "PR"), _prop_em(db, "Fazenda Rio Grande", "PR")
    a, b = _itbi(db, cwb), _itbi(db, frg)
    assert a["valor"] == (D("132970.97") * D("0.027")).quantize(D("0.01")) and "do município" in a["origem"]
    assert b["valor"] == (D("132970.97") * D("0.02")).quantize(D("0.01")) and "do município" not in b["origem"]


def test_registro_municipal_sem_valor_usa_o_global_sem_rotular_como_municipal(db):
    debts_service.seed_all(db)
    _param(db, None, "0.02")
    _param(db, _muni(db, "Assis", "SP").id, None)
    linha = _itbi(db, _prop_em(db, "Assis", "SP"))
    assert linha["status"] == "ESTIMADO" and "do município" not in linha["origem"]


def test_sem_aliquota_ou_municipio_desconhecido_itbi_fica_pendente(db):
    debts_service.seed_all(db)
    _param(db, _muni(db, "Curitiba", "PR").id, "0.027")
    assert _itbi(db, _prop_em(db, "Fazenda Rio Grande", "PR"))["status"] == "PENDENTE"         # só Curitiba tem alíquota
    assert _itbi(db, _prop_em(db, "Cidade Inexistente", "PR"))["status"] == "PENDENTE"
    assert _itbi(db, _prop_em(db, "Curitiba", "SC"))["status"] == "PENDENTE"                   # mesmo nome, outra UF


def test_imovel_sem_uf_so_casa_municipio_de_nome_unico(db):
    debts_service.seed_all(db)
    db.add(models.Municipality(name="Assis", state="MG", coverage_active=False))                # homônimo fictício
    db.flush()
    sem_uf = _prop_em(db, "Assis", "")
    assert municipality_id_for(db, sem_uf) is None
    assert municipality_id_for(db, _prop_em(db, "Curitiba", "")) == _muni(db, "Curitiba", "PR").id


# =============================================================== 4. estimativa condominial: bordas e fórmula

def _est(db, prop, acq, cons, fee="500", today=date(2025, 1, 1)):
    return estimate_from_registry(db, prop, monthly_reference=D(fee), acquisition_date=acq, consolidation_date=cons, today=today)


def test_sem_datas_e_datas_invertidas_nao_calculam(db):
    prop = _base(db)
    assert "data de aquisição" in _est(db, prop, None, None)["motivo"]
    out = _est(db, prop, date(2022, 5, 1), date(2021, 5, 1))
    assert out["possivel"] is False and "datas incoerentes" in out["motivo"]
    assert "ao menos um mês" in _est(db, prop, date(2022, 5, 1), date(2022, 5, 20))["motivo"]


def test_arredondamento_meio_para_cima(db):
    out = _est(db, _base(db), date(2020, 1, 1), date(2020, 11, 1), today=date(2020, 11, 1))   # período de 10 meses
    d = out["cenarios_detalhe"]
    assert [d[k]["meses_em_atraso"] for k in ("baixo", "provavel", "alto")] == [2, 4, 7]       # 1,5→2; 3,5→4; 7
    assert "meio para cima" in out["memoria_calculo"]["formula"]


def test_periodo_acima_do_teto_e_consolidacao_antiga_seguem_a_formula_exibida(db):
    acq, cons, today = date(2010, 1, 1), date(2018, 1, 1), date(2025, 1, 1)
    out = _est(db, _base(db), acq, cons, today=today)
    m = out["memoria_calculo"]
    assert m["periodo_meses"] == 96 and m["periodo_considerado_meses"] == 60 and m["meses_desde_consolidacao"] == 84
    fee, juros, multa, corr = D("500"), D("0.01"), D("0.02"), D("0.004")
    for nome, fator in (("baixo", D("0.15")), ("provavel", D("0.35")), ("alto", D("0.70"))):
        n = int((D(60) * fator).to_integral_value(rounding="ROUND_HALF_UP"))
        soma = D(n) * D(84) + D(n) * D(n + 1) / 2                                             # Σ (offset + k), k = 1..n
        principal = (fee * n).quantize(D("0.01"))
        esperado = principal + (principal * multa).quantize(D("0.01")) + (fee * juros * soma).quantize(D("0.01")) \
            + (fee * corr * soma).quantize(D("0.01"))
        c = out["cenarios_detalhe"][nome]
        assert (c["meses_em_atraso"], c["total"]) == (n, esperado), nome
        assert c["natureza"] == "ESTIMATIVA_OPERACIONAL" and c["status"] == "ESTIMADO"         # encargos nunca são dívida confirmada
    assert out["status"] == "ESTIMADO" and out["natureza"] == "ESTIMATIVA_OPERACIONAL"


# =============================================================== 5. privacidade e autorização

def test_trechos_da_linha_do_tempo_sem_cpf_e_nome_sem_qualificacao():
    texto = ["Matrícula nº 1\nPROPRIETÁRIA: CONSTRUTORA EXEMPLO LTDA.\n",
             "R-1 - Matrícula nº 1 - COMPRA E VENDA. A CONSTRUTORA EXEMPLO LTDA, já qualificada, vendeu a FULANO FICTÍCIO, brasileiro, "
             "solteiro, CPF nº 529.982.247-25, RG 12.345.678-9, pelo preço de R$ 10,00.\n"]
    chunks = [{"chunk_id": i + 1, "content": t, "page": None, "section": None} for i, t in enumerate(texto)]
    tl = build_timeline(read_registry(chunks, 1), {"document_id": 1, "document_version_id": 1, "nome": "m.txt"}, date(2026, 1, 1))
    venda = next(e for e in tl["eventos"] if e["ato"] == "R-1")
    assert "529.982.247-25" not in venda["trecho"] and "[CPF]" in venda["trecho"] and "12.345.678-9" not in venda["trecho"]
    comprador = next(p for p in venda["partes"] if p["papel"] == "COMPRADOR")
    assert comprador["nome"] == "FULANO FICTÍCIO"


ROTAS_NOVAS_GET = ["/api/imoveis/{pid}/matricula/linha-do-tempo", "/api/imoveis/{pid}/ocupacao/possiveis-ocupantes",
                   "/api/imoveis/{pid}/debitos/orientacao-iptu"]


@pytest.mark.security_gate
def test_rotas_novas_exigem_autenticacao(env):
    pid = _property(env).id
    for rota in ROTAS_NOVAS_GET:
        assert env.client.get(rota.format(pid=pid)).status_code == 401, rota
    assert env.client.post(f"/api/imoveis/{pid}/debitos/estimar-condominio/matricula", json={}).status_code == 401


@pytest.mark.security_gate
def test_papel_somente_leitura_le_mas_nao_registra_estimativa(env):
    pid = _property(env).id
    headers = _login(env, "CONSULTA")
    for rota in ROTAS_NOVAS_GET:
        assert env.client.get(rota.format(pid=pid), headers=headers).status_code == 200, rota
    resp = env.client.post(f"/api/imoveis/{pid}/debitos/estimar-condominio/matricula", json={"persist": True}, headers=headers)
    assert resp.status_code == 403
