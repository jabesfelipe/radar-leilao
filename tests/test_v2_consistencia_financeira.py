"""Consistência financeira (v2): o cálculo do veredito (``build_finance``) e a inteligência de mercado (``market_intelligence``)
usam a MESMA composição de custos, o MESMO IR e o MESMO preço máximo.

Regras cobertas: ITBI pela alíquota entra no custo; sem alíquota/base fica pendente; corretagem e tributo não informados nunca
são zero silencioso (padrão declarado, sinalizado e provisório); confirmado x estimado x premissa x reserva x pendente x não
aplicável; resultado, ROI, break-even e preço máximo pela mesma composição; recálculo ao mudar premissas; nenhuma pendência
some do veredito; a meta nunca é automática. Sem banco: dublês do imóvel 7 (comparáveis reais, matrícula não usada).
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.services import build_finance
from backend.app.verdict_engine import VerdictEngine
from backend.app.viability import market_intelligence
from tests.mercado_imovel7_dados import COMPARAVEIS_ALUGUEL, COMPARAVEIS_VENDA, IMOVEL7, PREMISSAS_IMOVEL7
from tests.test_v108_inteligencia_mercado import fake_property

ATTRS = {k: IMOVEL7[k] for k in ("city", "neighborhood", "property_type", "bedrooms", "parking_spots", "area_m2", "private_area_m2")}
VENDA = Decimal("212062.30")
CENT = Decimal("0.01")

# Premissas COMPLETAS do usuário: nenhum item da composição fica pendente ou com reserva do sistema.
COMPLETAS = {**PREMISSAS_IMOVEL7, "valor_venda_estimado": str(VENDA), "corretagem_pct": "0.06", "tributo_pct": "0.15", "tax_base": "GANHO",
             "prazo_meses": 12, "carregamento_mensal": "350", "goal_kind": "ROI_MINIMO", "goal_value": "0.20",
             "certidoes": "600", "regularizacao": "1500", "regularizacao_origem": "orçamento de despachante (teste)",
             "iptu_anual": "480", "iptu_anual_origem": "carnê (teste)"}
CUSTOS = ({"category": "Registro", "amount": Decimal("2800")}, {"category": "Reforma", "amount": Decimal("6000")})
DIVIDAS = ({"category": "CONDOMINIO", "amount": Decimal("30000"), "status": "PENDENTE"},   # acima do teto Caixa (22.000)
           {"category": "IPTU", "amount": Decimal("1800"), "status": "PENDENTE"})
DESOCUPADO = SimpleNamespace(id=1, status="DESOCUPADO", estimated_cost=None)


def _prop(assumptions=None, *, acquisition="132970.97", costs=CUSTOS, debts=DIVIDAS, occupancy=DESOCUPADO, comparables=None):
    comps = COMPARAVEIS_VENDA + COMPARAVEIS_ALUGUEL if comparables is None else comparables
    comps = [{"rent": None, "price": None, **c} for c in comps]   # o motor legado lê price e rent de todo comparável
    return fake_property(comps, acquisition=acquisition,
                         assumptions=COMPLETAS if assumptions is None else assumptions, costs=costs, debts=debts, occupancy=occupancy, **ATTRS)


def _item(fin, key):
    return next(i for i in fin["composicao_custos"] if i["chave"] == key)


# ------------------------------------------------------------------ ITBI

def test_itbi_pela_aliquota_entra_no_custo_total():
    fin = build_finance(_prop())
    itbi = _item(fin, "itbi")
    assert itbi["valor"] == Decimal("3545.64") and itbi["incluido"] and itbi["natureza"] == "ESTIMADO"   # 2,5% × R$ 141.825,75 (base mínima)
    assert "Av-5" in itbi["origem"] and fin["custos"]["itbi"] == Decimal("3545.64") and fin["custos_status"]["itbi"] == "ESTIMADO"
    assert fin["custo_total"] == sum(i["valor"] for i in fin["composicao_custos"] if i["incluido"])
    assert not any("itbi" in p.lower() for p in fin["pendencias"])


@pytest.mark.parametrize("assumptions,acquisition", [
    ({k: v for k, v in COMPLETAS.items() if not k.startswith("itbi_")}, "132970.97"),   # sem alíquota
    (COMPLETAS, None),                                                                    # alíquota sem base (sem preço de aquisição)
])
def test_itbi_sem_aliquota_ou_base_valida_fica_pendente(assumptions, acquisition):
    prop = _prop(assumptions)
    if acquisition is None:
        prop.auctions[0].acquisition_value = prop.auctions[0].bid_value = None
    fin = build_finance(prop)
    itbi = _item(fin, "itbi")
    assert itbi["valor"] is None and not itbi["incluido"] and itbi["natureza"] == "PENDENTE"
    assert fin["custos_status"]["itbi"] == "DESCONHECIDO" and fin["custos"]["itbi"] == 0      # fora da soma, nunca estimado
    assert any(p.startswith("Custo de ITBI não informado: fora da soma, não é zero") for p in fin["pendencias"])
    if fin["resultado_liquido"] is not None:
        assert fin["resultado_provisorio"] is True and fin["resultado_completo"] is False


# ------------------------------------------------------------------ corretagem e tributo nunca zero silencioso

@pytest.mark.parametrize("campo,codigo,texto", [("corretagem_pct", "corretagem_venda", "padrão de 6%"),
                                                ("tributo_pct", "tributo_venda", "IR de 15% sobre o ganho")])
def test_corretagem_ou_tributo_nao_informado_usa_padrao_sinalizado_e_provisorio(campo, codigo, texto):
    fin = build_finance(_prop({k: v for k, v in COMPLETAS.items() if k != campo}))
    detalhe = fin["custo_saida_detalhe"]["corretagem_venda" if campo == "corretagem_pct" else "tributos_venda"]
    assert detalhe > 0                                                                       # não é zero
    assert fin["saida_status"]["corretagem_venda" if campo == "corretagem_pct" else "tributos_venda"] == "ESTIMADO"
    assert any(texto in p and "PROVISÓRIOS" in p for p in fin["pendencias"])
    assert codigo in fin["preco_maximo_detalhe"]["custos_desconhecidos"]
    assert fin["resultado_provisorio"] is True and fin["preco_maximo_provisorio"] is True and fin["preco_maximo_definitivo"] is False
    assert fin["premissas_origem"][campo].startswith("padrão do sistema")


def test_premissas_do_usuario_sao_confirmadas_e_o_calculo_fica_completo():
    fin = build_finance(_prop())
    assert fin["saida_status"] == {"corretagem_venda": "INFORMADO", "tributos_venda": "INFORMADO"}
    assert fin["resultado_completo"] is True and fin["preco_maximo_definitivo"] is True and fin["custos_pendentes"] == []
    naturezas = {i["chave"]: i["natureza"] for i in fin["composicao_custos"]}
    assert naturezas["aquisicao"] == "CONFIRMADO" and naturezas["registro"] == "CONFIRMADO" and naturezas["certidoes"] == "PREMISSA_USUARIO"
    assert naturezas["regularizacao"] == "PREMISSA_USUARIO" and naturezas["manutencao_posse"] == "PREMISSA_USUARIO"
    assert naturezas["desocupacao"] == "NAO_APLICAVEL" and naturezas["itbi"] == "ESTIMADO"


# ------------------------------------------------------------------ os dois motores: mesmos resultados

def test_os_dois_motores_dao_os_mesmos_resultados_para_as_mesmas_premissas():
    prop = _prop()
    fin, intel = build_finance(prop), market_intelligence(None, prop)
    base = next(s for s in intel["cenarios"] if s["cenario"] == "BASE")
    assert base["valor_venda"] == VENDA == fin["valor_mercado"] and base["completo"] is True
    assert fin["custo_total"] == base["investimento_total"]
    assert fin["resultado_liquido"] == base["resultado_liquido"] and fin["roi_operacao"] == base["roi"]
    assert fin["break_even"] == base["venda_equilibrio"]
    assert fin["custo_saida_detalhe"] == {"corretagem_venda": base["corretagem_venda"], "tributos_venda": base["tributo_venda"]}
    assert fin["preco_maximo"] == intel["preco_maximo"]["por_cenario"]["BASE"]["preco_maximo"]   # meta ROI 20% do usuário nos dois
    # regra Caixa preservada no veredito: do condomínio de R$ 30.000, o comprador paga até o teto de R$ 22.000
    assert _item(fin, "condominio_atraso")["valor"] == Decimal("22000.00") and fin["custos"]["debitos"] == Decimal("23800.00")


def test_preco_maximo_considera_todos_os_custos_e_entrega_a_meta():
    fin = build_finance(_prop())
    teto = fin["preco_maximo"]
    no_teto = build_finance(_prop(acquisition=str(teto)))
    um_real_acima = build_finance(_prop(acquisition=str(teto + 1)))
    roi = lambda f: f["resultado_liquido"] / f["custo_total"]                               # sem o arredondamento de exibição
    assert roi(no_teto) >= Decimal("0.20") > roi(um_real_acima)
    # o ITBI acompanha o preço (base mínima de R$ 141.825,75 quando o preço é menor)
    assert _item(no_teto, "itbi")["valor"] == (max(teto, Decimal("141825.75")) * Decimal("0.025")).quantize(CENT)


def test_break_even_zera_o_resultado():
    fin = build_finance(_prop())
    no_equilibrio = build_finance(_prop({**COMPLETAS, "valor_venda_estimado": str(fin["break_even"])}))
    assert abs(no_equilibrio["resultado_liquido"]) <= Decimal("0.05")


# ------------------------------------------------------------------ recálculo e pendências

def test_alterar_premissa_recalcula_com_a_mesma_composicao():
    antes = build_finance(_prop())
    depois = build_finance(_prop({**COMPLETAS, "corretagem_pct": "0.05"}))
    assert depois["custo_total"] == antes["custo_total"]                                     # composição inalterada
    # 1 p.p. de corretagem a menos: corretagem cai 1% da venda e o IR sobe 15% disso (corretagem reduz a base do ganho)
    delta = (VENDA * Decimal("0.01")).quantize(CENT)
    esperado = delta - (delta * Decimal("0.15")).quantize(CENT)
    assert abs((depois["resultado_liquido"] - antes["resultado_liquido"]) - esperado) <= CENT  # corretagem e IR arredondados ao centavo
    assert depois["preco_maximo"] > antes["preco_maximo"]


def test_custos_pendentes_e_reservas_aparecem_e_nao_somem_do_veredito():
    # imóvel 7 como está: só premissas da v1.0.8 (ITBI e condições Caixa), sem dívidas, reforma ou ocupação levantadas
    fin = build_finance(_prop(PREMISSAS_IMOVEL7, costs=(), debts=(), occupancy=None))
    pendentes = [i for i in fin["composicao_custos"] if i["natureza"] == "PENDENTE"]
    reservas = [i for i in fin["composicao_custos"] if i["natureza"] == "RESERVA"]
    assert {i["chave"] for i in pendentes} >= {"condominio_atraso", "tributos_atraso", "desocupacao", "regularizacao", "iptu_posse"}
    assert {i["chave"] for i in reservas} >= {"registro", "certidoes", "reforma"}
    for item in pendentes:
        assert not item["incluido"] and any(item["descricao"].lower()[1:] in p.lower() for p in fin["pendencias"]), item["chave"]
    for item in reservas:
        assert item["incluido"] and any(p.startswith(item["descricao"]) for p in fin["pendencias"]), item["chave"]
    decisao = VerdictEngine().evaluate(1, 1, checklist_results=[], evidence_ids=[1], financial=fin)
    assert set(fin["pendencias"]) <= set(decisao.pending_items)                              # nenhuma pendência some
    assert decisao.overall == "INCONCLUSIVO" and decisao.financial["decisao"]["avaliacao_financeira"]["status"] != "VIAVEL"


def test_meta_nunca_e_automatica():
    sem_meta = {k: v for k, v in COMPLETAS.items() if k not in ("goal_kind", "goal_value")}
    fin = build_finance(_prop(sem_meta))
    assert fin["preco_maximo"] is None and fin["preco_maximo_detalhe"]["razao"] == "DADOS_ESSENCIAIS_AUSENTES"
    assert any("Meta financeira" in p for p in fin["pendencias"])
    # a inteligência de mercado segue mostrando seu critério declarado (ROI padrão), separado do veredito
    assert "padrão do sistema" in market_intelligence(None, _prop(sem_meta))["preco_maximo"]["criterio"]


# ------------------------------------------------------------------ meta financeira única

@pytest.mark.parametrize("kind,value,descricao", [("ROI_MINIMO", "0.20", "ROI mínimo de 20%"), ("MARGEM_MINIMA", "0.15", "Margem mínima de 15%"),
                                                  ("LUCRO_MINIMO", "30000", "Lucro mínimo de R$ 30.000,00")])
def test_inteligencia_de_mercado_respeita_a_meta_do_usuario_e_bate_com_o_veredito(kind, value, descricao):
    prop = _prop({**COMPLETAS, "goal_kind": kind, "goal_value": value})
    fin, intel = build_finance(prop), market_intelligence(None, prop)
    meta = intel["preco_maximo"]["meta"]
    assert (meta["tipo"], meta["valor"], meta["do_usuario"]) == (kind, Decimal(value), True)
    assert intel["preco_maximo"]["criterio"].startswith(descricao) and "padrão" not in intel["preco_maximo"]["criterio"]
    base = intel["preco_maximo"]["por_cenario"]["BASE"]
    assert base["preco_maximo"] == fin["preco_maximo"] and base["meta_tipo"] == kind          # mesmo preço máximo nos dois
    assert fin["preco_maximo_detalhe"]["premissas_utilizadas"]["meta"] == {"tipo": kind, "valor": Decimal(value)}
    # o indicador da meta no teto atende a meta; o ROI no teto é o ROI de fato (não o indicador)
    assert base["indicador_no_teto"] >= Decimal(value) and base["roi_no_teto"] == fin["preco_maximo_detalhe"]["roi_no_teto"]


def test_sem_meta_do_usuario_a_referencia_padrao_e_identificada_e_o_veredito_nao_calcula():
    prop = _prop({k: v for k, v in COMPLETAS.items() if k not in ("goal_kind", "goal_value")})
    meta = market_intelligence(None, prop)["preco_maximo"]["meta"]
    assert meta["do_usuario"] is False and "meta do investidor não configurada" in meta["origem"]
    assert build_finance(prop)["preco_maximo"] is None


# ------------------------------------------------------------------ cenários do usuário

def test_cenario_do_usuario_usa_a_mesma_composicao_e_preserva_os_parametros():
    cenario = {"nome": "PESSIMISTA", "valor_venda": "190000", "reforma": "12000", "prazo_meses": 18, "justificativa": "venda lenta (teste)"}
    fin = build_finance(_prop({**COMPLETAS, "cenarios": [cenario]}))
    [sc] = fin["cenarios"]
    assert sc["cenario"] == "PESSIMISTA" and sc["motor"].startswith("composição única")
    assert sc["premissas"] == {"valor_venda": Decimal("190000"), "reforma": Decimal("12000"), "desocupacao": None, "carregamento": None,
                               "prazo_meses": 18, "justificativa": "venda lenta (teste)"}
    # equivalente: o cálculo principal com as mesmas premissas (venda 190.000, prazo 18 meses, reforma de R$ 12.000)
    custos = ({"category": "Registro", "amount": Decimal("2800")}, {"category": "Reforma", "amount": Decimal("12000")})
    ref = build_finance(_prop({**COMPLETAS, "valor_venda_estimado": "190000", "prazo_meses": 18}, costs=custos))
    for campo in ("custo_total", "resultado_liquido", "roi_operacao", "break_even", "preco_maximo"):
        assert sc[campo] == ref[campo], campo
    assert fin["resultado_liquido"] != sc["resultado_liquido"]                             # o BASE não é alterado pelo cenário


@pytest.mark.parametrize("kind,value", [("LUCRO_MINIMO", "30000"), ("MARGEM_MINIMA", "0.15")])
def test_metas_de_lucro_e_margem_no_teto(kind, value):
    fin = build_finance(_prop({**COMPLETAS, "goal_kind": kind, "goal_value": value}))
    no_teto = build_finance(_prop({**COMPLETAS, "goal_kind": kind, "goal_value": value}, acquisition=str(fin["preco_maximo"])))
    indicador = no_teto["resultado_liquido"] if kind == "LUCRO_MINIMO" else no_teto["margem_liquida"]
    assert indicador >= Decimal(value) and fin["preco_maximo_definitivo"] is True
