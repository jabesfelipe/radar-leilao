"""v1.0.12 — Fase B: premissas financeiras no Admin (catálogo de parâmetros) e valor de venda preliminar (avaliação × fator).

Dados fictícios. Cobre: seed idempotente com os mesmos padrões do motor; precedência imóvel > catálogo > padrão; valor por município
(ITBI); premissa sem padrão continua pendente; valor preliminar só sem valor informado e sem comparáveis.
"""
from __future__ import annotations

from decimal import Decimal

from backend.app import debts_service, models, parameters as params
from backend.app.parameter_seeds import all_parameter_seeds, seed_parameters
from backend.app.viability import DEFAULTS, market_intelligence, resolve_premises, verdict_finance
from tests.mercado_imovel7_dados import COMPARAVEIS_VENDA
from tests.test_checklist_evidencias import _comparavel, _leilao, _prop
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)


def _linha(intel, chave):
    return next(l for l in intel["custos"] if l["chave"] == chave)


def _global(db, key):
    return db.query(models.Parameter).filter(models.Parameter.key == key, models.Parameter.scope == "GLOBAL").one()


def test_seed_espelha_os_padroes_do_motor_e_e_idempotente(db):
    criados = seed_parameters(db)
    assert criados == len(all_parameter_seeds())
    for key, (valor, _) in DEFAULTS.items():
        assert Decimal(str(params.resolve(db, key))) == Decimal(str(valor)), key       # o seed não muda nenhum cálculo
    assert params.resolve(db, "viabilidade.fator_venda_avaliacao") == Decimal("0.85")
    assert params.resolve(db, "condominio.fator_cenario_provavel") == Decimal("0.35")
    assert params.resolve(db, "viabilidade.itbi_aliquota") is None                     # sem padrão do sistema: não inventa
    assert seed_parameters(db) == 0


def test_seed_nao_sobrescreve_edicao_do_operador(db):
    seed_parameters(db)
    param = _global(db, "venda.corretagem_pct")
    params.update_parameter(db, param, {"value": "0.05"}, actor="admin", justification="teste")
    db.flush()
    seed_parameters(db)
    assert params.resolve(db, "venda.corretagem_pct") == Decimal("0.05")


def test_catalogo_entra_com_origem_e_nunca_sobrescreve_o_valor_do_imovel(db):
    seed_parameters(db)
    params.update_parameter(db, _global(db, "venda.corretagem_pct"), {"value": "0.05"}, actor="admin", justification="teste")
    db.flush()
    premissas = resolve_premises(db, {})
    assert premissas["venda.corretagem_pct"]["valor"] == Decimal("0.05")
    assert premissas["venda.corretagem_pct"]["origem"] == "catálogo de parâmetros (venda.corretagem_pct)"
    proprio = resolve_premises(db, {"corretagem_pct": "0.04"})
    assert proprio["venda.corretagem_pct"] == {**proprio["venda.corretagem_pct"], "valor": Decimal("0.04"), "origem": "premissa do imóvel"}


def test_itbi_por_municipio_vale_so_no_municipio(db):
    debts_service.seed_all(db)
    fazenda = db.query(models.Municipality).filter(models.Municipality.name == "Fazenda Rio Grande").one()
    params.create_parameter(db, {"key": "viabilidade.itbi_aliquota", "name": "ITBI (alíquota)", "category": "financeiro", "data_type": "DECIMAL",
                                 "scope": "MUNICIPIO", "municipality_id": fazenda.id, "value": "0.02"}, actor="admin", justification="fonte fictícia")
    db.flush()
    local = _prop(db)
    local.city, local.state = "Fazenda Rio Grande", "PR"
    _leilao(db, local)
    outro = _prop(db)
    _leilao(db, outro)
    db.flush(); db.expire_all()
    itbi = _linha(market_intelligence(db, local), "itbi")
    assert itbi["status"] == "ESTIMADO" and itbi["valor"] == Decimal("2659.42")          # 2% de R$ 132.970,97
    assert itbi["origem"] == "catálogo de parâmetros do município (viabilidade.itbi_aliquota)"
    assert _linha(market_intelligence(db, outro), "itbi")["status"] == "PENDENTE"


def test_premissa_sem_padrao_continua_pendente_ate_ser_preenchida(db):
    seed_parameters(db)
    prop = _prop(db)
    _leilao(db, prop)
    db.expire(prop)
    assert _linha(market_intelligence(db, prop), "regularizacao")["valor_base"] is None
    params.update_parameter(db, _global(db, "viabilidade.regularizacao_padrao"), {"value": "3000"}, actor="admin", justification="teste")
    db.flush(); db.expire(prop)
    linha = _linha(market_intelligence(db, prop), "regularizacao")
    assert linha["status"] == "PENDENTE" and linha["valor_base"] == linha["valor_conservador"] == Decimal("3000.00")
    assert "viabilidade.regularizacao_padrao" in linha["tratamento_base"]


# ------------------------------------------------------------------ valor de venda preliminar (decisão 2.2)

def test_sem_comparaveis_e_sem_valor_informado_valor_de_venda_fica_desconhecido(db):
    # v1.0.14: avaliação × percentual não é dado de mercado; sem amostra, o valor de venda é DESCONHECIDO (nunca 85% da avaliação).
    prop = _prop(db)
    _leilao(db, prop)
    db.expire(prop)
    intel = market_intelligence(db, prop)
    assert intel["valores"]["venda_preliminar"] is None
    base = next(s for s in intel["cenarios"] if s["cenario"] == "BASE")
    assert base["valor_venda"] is None and base.get("resultado_liquido") is None
    assert intel["venda"]["qualidade_amostra"]["nivel"] == "INSUFICIENTE"
    assert intel["conclusao"]["resultado"] != "FAVORAVEL"
    fin = verdict_finance(db, prop)
    assert fin["valor_mercado"] is None and fin["valor_venda_preliminar"] is None
    assert any("Valor de venda estimado ausente" in p for p in fin["pendencias"])


def test_fator_configurado_no_admin_nao_vira_valor_de_venda_e_valor_do_usuario_prevalece(db):
    seed_parameters(db)
    params.update_parameter(db, _global(db, "viabilidade.fator_venda_avaliacao"), {"value": "0.80"}, actor="admin", justification="teste")
    prop = _prop(db)
    _leilao(db, prop)
    db.flush(); db.expire(prop)
    assert market_intelligence(db, prop)["valores"]["venda_preliminar"] is None
    outro = _prop(db)
    _leilao(db, outro, {"valor_venda_estimado": "200000"})
    db.flush(); db.expire(outro)
    intel = market_intelligence(db, outro)
    assert intel["valores"]["venda_preliminar"] is None
    assert next(s for s in intel["cenarios"] if s["cenario"] == "BASE")["valor_venda"] == Decimal("200000.00")


def test_com_comparaveis_suficientes_o_fator_nao_e_usado(db):
    prop = _prop(db)
    prop.property_type, prop.city, prop.neighborhood, prop.area_m2 = "Apartamento", "Fazenda Rio Grande", "Estados", Decimal("48.74")
    _leilao(db, prop)
    for dados in COMPARAVEIS_VENDA:
        _comparavel(db, prop, dados)
    db.flush(); db.expire(prop)
    intel = market_intelligence(db, prop)
    assert intel["valores"]["valor_mercado_estimado"] is not None and intel["valores"]["venda_preliminar"] is None


def test_api_lista_premissas_financeiras_semeadas(api):
    client, _ = api
    body = client.get("/api/admin/parametros", params={"category": "financeiro"}).json()
    chaves = {p["key"] for p in body["itens"]}
    assert {"venda.corretagem_pct", "viabilidade.fator_venda_avaliacao", "viabilidade.itbi_aliquota", "viabilidade.reserva_desocupacao"} <= chaves
    itbi = next(p for p in body["itens"] if p["key"] == "viabilidade.itbi_aliquota")
    assert itbi["value"] is None and itbi["scope"] == "GLOBAL"
    assert client.get("/api/admin/parametros", params={"category": "estimativa"}).json()["total"] >= 8
