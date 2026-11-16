"""v1.0.8: inteligência de mercado e viabilidade financeira.

Cobertura pedida: comparáveis rastreáveis, ausência e insuficiência de comparáveis, discrepantes, custos ausentes,
cenários, preço máximo, separação entre preço anunciado e transacionado e bloqueio de conclusão favorável sem dados
críticos. Inclui a validação do imóvel 7 (RESIDENCIAL AMERICA 5) com os comparáveis reais coletados.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app import market as mk
from backend.app.viability import DESFAVORAVEL, FAVORAVEL, INCONCLUSIVO, INFORMADO, PENDENTE, consolidate, market_intelligence
from tests.mercado_imovel7_dados import COMPARAVEIS_ALUGUEL, COMPARAVEIS_VENDA, IMOVEL7, PREMISSAS_IMOVEL7

SUBJECT = {"city": "Fazenda Rio Grande", "neighborhood": "Estados", "property_type": "Apartamento", "bedrooms": 2, "parking_spots": 1, "area": Decimal("45.5")}


def comp(i, price, area="45", *, kind="VENDA", price_type="ANUNCIADO", bairro="Estados", city="Fazenda Rio Grande", rent=None, **extra):
    data = {"id": i, "kind": kind, "price": Decimal(price) if kind == "VENDA" else Decimal("0"), "rent": Decimal(rent) if rent else None, "area_m2": Decimal(area),
            "source": f"Portal {i}", "url": f"https://exemplo.invalid/anuncio/{i}", "price_type": price_type, "collected_at": "2026-11-16",
            "neighborhood": bairro, "city": city, "property_type": "Apartamento", "bedrooms": 2, "parking_spots": 1}
    data.update(extra)
    return data


# ------------------------------------------------------------------ estimativa

def test_comparaveis_rastreaveis_trazem_fonte_url_data_e_tipo_de_preco():
    est = mk.estimate(SUBJECT, [comp(i, 200000 + i * 1000) for i in range(1, 6)])
    for row in est["comparaveis"]:
        assert row["fonte"] and row["url"].startswith("https://") and row["consultado_em"] == "2026-11-16"
        assert row["tipo_preco"] == "ANUNCIADO" and row["similaridade"] is not None and "criterios" in row
    assert est["quantidade_usada"] == 5 and est["valor_estimado"] is not None


def test_sem_comparaveis_nao_ha_estimativa_nem_faixa():
    est = mk.estimate(SUBJECT, [])
    assert est["confianca"] == mk.CONF_SEM_DADOS and est["valor_estimado"] is None and est["faixa"] is None
    assert any("Nenhum comparável" in a for a in est["avisos"])


def test_comparaveis_insuficientes_dao_so_faixa_indicativa():
    est = mk.estimate(SUBJECT, [comp(1, 200000), comp(2, 220000)])
    assert est["quantidade_usada"] == 2 and est["indicativa"] is True and est["valor_estimado"] is None
    assert est["faixa"] is not None and est["confianca"] == mk.CONF_BAIXA


def test_mesmo_valor_mesma_area_mesmo_bairro_e_duplicata_mas_valores_proximos_nao():
    rows = {r["id"]: r for r in mk.estimate(SUBJECT, [comp(1, 200000), comp(2, 200000), comp(3, 201000), comp(4, 200000, bairro="Nações")])["comparaveis"]}
    assert rows[2]["motivo"].startswith("Provável duplicata") and rows[3]["usado"] and rows[4]["usado"]


def test_valor_discrepante_e_excluido_com_motivo():
    comps = [comp(i, v) for i, v in enumerate([200000, 205000, 210000, 198000, 202000, 900000], start=1)]
    est = mk.estimate(SUBJECT, comps)
    [outlier] = [r for r in est["comparaveis"] if r["id"] == 6]
    assert outlier["usado"] is False and outlier["motivo"].startswith("Valor discrepante")
    assert est["quantidade_usada"] == 5 and est["limites_discrepancia"] is not None


def test_duplicata_proprio_imovel_e_outro_municipio_ficam_fora():
    comps = [comp(1, 200000), comp(2, 200000, area="45.5"), comp(3, 132970, excluded=True, exclusion_reason="É o próprio imóvel"),
             comp(4, 210000, city="Curitiba"), comp(5, 215000)]
    rows = {r["id"]: r for r in mk.estimate(SUBJECT, comps)["comparaveis"]}
    assert rows[2]["motivo"].startswith("Provável duplicata")
    assert rows[3]["motivo"].startswith("Excluído no cadastro")
    assert rows[4]["motivo"] == "Fora do município do imóvel"
    assert rows[1]["usado"] and rows[5]["usado"]


def test_anunciado_tem_desconto_de_negociacao_e_transacionado_nao():
    anunciado = mk.estimate(SUBJECT, [comp(i, 196000 + i * 4000) for i in range(1, 5)], negotiation_discount=Decimal("0.10"))
    fechado = mk.estimate(SUBJECT, [comp(i, 196000 + i * 4000, price_type="TRANSACIONADO") for i in range(1, 5)], negotiation_discount=Decimal("0.10"))
    a = anunciado["estatisticas_m2"]
    assert a["m2_ajustado_mediana"] == (a["m2_anunciado_mediana"] * Decimal("0.9")).quantize(Decimal("0.01"))
    assert fechado["estatisticas_m2"]["m2_ajustado_mediana"] == fechado["estatisticas_m2"]["m2_anunciado_mediana"]
    assert anunciado["quantidade_anunciada"] == 4 and any("ANÚNCIO" in w for w in anunciado["avisos"])
    assert fechado["quantidade_anunciada"] == 0


def test_so_anuncios_limitam_confianca_a_media():
    homogeneos = [comp(i, 200000 + i * 500) for i in range(1, 9)]
    assert mk.estimate(SUBJECT, homogeneos)["confianca"] == mk.CONF_MEDIA
    com_negocio = homogeneos[:-1] + [comp(9, 203250, price_type="TRANSACIONADO")]   # valor distinto: não é duplicata
    assert mk.estimate(SUBJECT, com_negocio)["confianca"] == mk.CONF_ALTA


def test_aluguel_e_estimado_separado_da_venda():
    comps = [comp(i, 0, kind="ALUGUEL", rent=1200 + i * 20) for i in range(1, 5)] + [comp(9, 200000)]
    est = mk.estimate(SUBJECT, comps, "ALUGUEL")
    assert est["tipo"] == "ALUGUEL" and est["quantidade_usada"] == 4 and Decimal("900") < est["valor_estimado"] < Decimal("1300")


def test_liquidez_sem_dados_e_indeterminada_e_nunca_presume_prazo():
    liq = mk.liquidity(mk.estimate(SUBJECT, []), mk.estimate(SUBJECT, [], "ALUGUEL"), SUBJECT)
    assert liq["classificacao"] == mk.LIQ_INDETERMINADA and liq["prazo_estimado_meses"] is None
    cheia = mk.liquidity(mk.estimate(SUBJECT, [comp(i, 200000 + i * 500) for i in range(1, 9)]), mk.estimate(SUBJECT, [], "ALUGUEL"), SUBJECT)
    assert cheia["classificacao"] in (mk.LIQ_ALTA, mk.LIQ_MEDIA) and cheia["justificativa"] and cheia["prazo_estimado_meses"] is None


# ------------------------------------------------------------------ viabilidade (objetos em memória, sem banco)

def fake_property(comparables, *, acquisition="132970.97", appraisal="220000", assumptions=None, costs=(), debts=(), risks=(), occupancy=None, **attrs):
    auction = SimpleNamespace(id=1, acquisition_value=Decimal(acquisition), bid_value=Decimal(acquisition), appraisal_value=Decimal(appraisal),
                              commission_percent=Decimal("0"), commission_fixed=None, financial_assumptions=assumptions or {})
    base = dict(id=99, city="Fazenda Rio Grande", neighborhood="Estados", property_type="Apartamento", bedrooms=2, parking_spots=1,
                area_m2=Decimal("48.74"), private_area_m2=Decimal("45.50"), auctions=[auction],
                comparables=[SimpleNamespace(**{"id": i + 1, **c}) for i, c in enumerate(comparables)],
                costs=[SimpleNamespace(**c) for c in costs], debts=[SimpleNamespace(**d) for d in debts], risks=[SimpleNamespace(**r) for r in risks],
                occupancy_analyses=[occupancy] if occupancy else [], checklist_executions=[],
                documents=[SimpleNamespace(document_type="MATRICULA")])
    base.update(attrs)
    return SimpleNamespace(**base)


def market_comps(n=8, price=210000):
    return [{k: v for k, v in comp(i, price + i * 1000).items() if k != "id"} for i in range(1, n + 1)]


def test_custos_ausentes_ficam_pendentes_e_bloqueiam_conclusao_favoravel():
    out = market_intelligence(None, fake_property(market_comps()))
    custos = {c["chave"]: c for c in out["custos"]}
    assert custos["itbi"]["status"] == PENDENTE and custos["itbi"]["critico"] is True and custos["itbi"]["valor"] is None
    assert custos["aquisicao"]["status"] == INFORMADO
    assert out["conclusao"]["resultado"] == INCONCLUSIVO
    assert any("ITBI" in b for b in out["conclusao"]["bloqueios"])


def test_regras_caixa_limitam_condominio_e_tributos_do_comprador():
    regras = {"condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.10", "tributos_limite_pct_avaliacao": "0.10"}}
    sem_divida = {c["chave"]: c for c in market_intelligence(None, fake_property(market_comps(), assumptions=regras))["custos"]}
    assert sem_divida["condominio_atraso"]["status"] == PENDENTE and sem_divida["condominio_atraso"]["valor_conservador"] == Decimal("22000.00")
    assert sem_divida["condominio_atraso"]["critico"] is False   # há teto contratual
    dividas = [{"category": "Condomínio", "amount": Decimal("30000"), "status": "PENDENTE"}, {"category": "IPTU", "amount": Decimal("30000"), "status": "PENDENTE"}]
    com_divida = {c["chave"]: c for c in market_intelligence(None, fake_property(market_comps(), assumptions=regras, debts=dividas))["custos"]}
    assert com_divida["condominio_atraso"]["valor"] == Decimal("22000.00")   # comprador paga até 10% da avaliação
    assert com_divida["tributos_atraso"]["valor"] == Decimal("0.00")         # acima de 10%: Caixa paga integralmente
    pequena = [{"category": "IPTU", "amount": Decimal("5000"), "status": "PENDENTE"}]
    assert {c["chave"]: c for c in market_intelligence(None, fake_property(market_comps(), assumptions=regras, debts=pequena))["custos"]}["tributos_atraso"]["valor"] == Decimal("5000.00")
    sem_regra = {c["chave"]: c for c in market_intelligence(None, fake_property(market_comps()))["custos"]}
    assert sem_regra["condominio_atraso"]["critico"] is True and sem_regra["condominio_atraso"]["valor_conservador"] is None


def test_cenarios_conservador_base_otimista_sao_coerentes():
    out = market_intelligence(None, fake_property(market_comps(), assumptions={"itbi_aliquota": "0.025"}))
    cons, base, otim = out["cenarios"]
    assert [s["cenario"] for s in out["cenarios"]] == ["CONSERVADOR", "BASE", "OTIMISTA"]
    assert cons["valor_venda"] <= base["valor_venda"] <= otim["valor_venda"]
    assert cons["investimento_total"] >= base["investimento_total"]
    assert cons["prazo_meses"] > base["prazo_meses"] > otim["prazo_meses"]
    assert base["resultado_liquido"] is not None and base["roi"] is not None and base["margem_seguranca"] is not None


def test_preco_maximo_entrega_o_roi_minimo_configurado():
    completos = {"itbi_aliquota": "0.025", "registro_estimado": "2500", "certidoes": "500", "reforma": "0", "regularizacao": "0", "carregamento_mensal": "350",
                 "iptu_anual": "600", "goal_kind": "ROI_MINIMO", "goal_value": "0.20",
                 "condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.10", "tributos_limite_pct_avaliacao": "0.10"}}
    debts = [{"category": "Condomínio", "amount": Decimal("1000"), "status": "PENDENTE"}, {"category": "IPTU", "amount": Decimal("800"), "status": "PENDENTE"}]
    occ = SimpleNamespace(id=1, status="DESOCUPADO", estimated_cost=None)
    out = market_intelligence(None, fake_property(market_comps(), assumptions=completos, debts=debts, occupancy=occ))
    teto = out["preco_maximo"]["por_cenario"]["BASE"]
    assert teto["preco_maximo"] is not None and teto["definitivo"] is True
    # Comprando exatamente pelo teto, o ROI do cenário base é a meta (20%).
    no_teto = market_intelligence(None, fake_property(market_comps(), acquisition=str(teto["preco_maximo"]), assumptions=completos, debts=debts, occupancy=occ))
    assert abs(no_teto["cenarios"][1]["roi"] - Decimal("0.20")) < Decimal("0.001")


def _completo():
    return {"itbi_aliquota": "0.025", "registro_estimado": "2500", "certidoes": "500", "reforma": "3000", "regularizacao": "0", "carregamento_mensal": "350",
            "iptu_anual": "600", "condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.10", "tributos_limite_pct_avaliacao": "0.10"}}


def test_composicao_de_cada_cenario_fecha_ao_centavo_e_sem_item_repetido():
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_completo()))
    for s in out["cenarios"]:
        c = s["composicao"]
        chaves = [i["chave"] for i in c["itens"]]
        assert len(chaves) == len(set(chaves))                                                   # nenhum custo contado duas vezes
        assert sum(i["valor"] for i in c["itens"] if i["incluido"]) == s["investimento_total"]    # soma dos itens = investimento
        assert s["valor_venda"] - s["corretagem_venda"] - s["tributo_venda"] - s["investimento_total"] == s["resultado_liquido"]
        assert s["roi"] == (s["resultado_liquido"] / s["investimento_total"]).quantize(Decimal("0.0001"))
        assert c["conferencia"] == {"itens_somam_investimento": True, "resultado_reproduz": True}
        assert c["despesas_financeiras"]["valor"] == 0 and c["formula"]


def test_base_do_ir_usa_so_custo_de_aquisicao_dedutivel_e_desconta_a_corretagem():
    dividas = [{"category": "Condomínio", "amount": Decimal("1000"), "status": "PENDENTE"}]
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_completo(), debts=dividas))
    base = out["cenarios"][1]
    itens = {i["chave"]: i for i in base["composicao"]["itens"]}
    dedutivel = sum(itens[k]["valor"] for k in ("aquisicao", "comissao", "itbi", "registro", "reforma"))
    assert base["composicao"]["custo_aquisicao_dedutivel_ir"] == dedutivel
    assert base["base_ir"] == base["valor_venda"] - base["corretagem_venda"] - dedutivel
    assert not itens["manutencao_posse"]["dedutivel_ir"] and not itens["condominio_atraso"]["dedutivel_ir"] and not itens["iptu_posse"]["dedutivel_ir"]
    assert itens["iptu_posse"]["valor"] == Decimal("600.00")       # 12 meses × R$ 600/ano


def test_margem_de_seguranca_vem_da_venda_de_equilibrio():
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_completo()))
    base = out["cenarios"][1]
    equilibrio = base["venda_equilibrio"]
    assert base["margem_seguranca"] == (1 - equilibrio / base["valor_venda"]).quantize(Decimal("0.0001"))
    from backend.app.viability import _scenario   # vender pelo equilíbrio zera o resultado (±1 centavo de arredondamento)
    c = base["composicao"]
    deducao = c["custo_aquisicao_dedutivel_ir"]
    liquida = equilibrio - (equilibrio * Decimal("0.06")).quantize(Decimal("0.01"))
    ir = (max(liquida - deducao, 0) * Decimal("0.15")).quantize(Decimal("0.01"))
    assert abs(liquida - ir - base["investimento_total"]) <= Decimal("0.02")


def test_custos_e_dividas_cadastrados_fora_das_linhas_padrao_nao_sao_omitidos():
    custos = [{"category": "Honorários advocatícios", "amount": Decimal("2000")}, {"category": "Mudança", "amount": Decimal("400")}]
    dividas = [{"category": "Água", "amount": Decimal("150"), "status": "PENDENTE"}]
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_completo(), costs=custos, debts=dividas))
    linhas = {c["chave"]: c for c in out["custos"]}
    assert linhas["custo_custos_juridicos"]["valor"] == Decimal("2000.00") and linhas["custo_outros"]["valor"] == Decimal("400.00")
    assert linhas["outras_dividas"]["valor"] == Decimal("150.00")
    base = out["cenarios"][1]
    incluidos = {i["chave"] for i in base["composicao"]["itens"] if i["incluido"]}
    assert {"custo_custos_juridicos", "custo_outros", "outras_dividas"} <= incluidos


def test_comissao_do_leilao_nao_e_somada_de_novo_quando_tambem_cadastrada_como_custo():
    custos = [{"category": "Comissão do leiloeiro", "amount": Decimal("6000")}]
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_completo(), costs=custos))
    linhas = [c for c in out["custos"] if "comissao" in c["chave"]]
    assert len(linhas) == 1 and linhas[0]["valor"] == Decimal("0.00")   # o leilão (0% na venda direta) governa


def test_desconto_sobre_avaliacao_e_diferente_do_desconto_sobre_mercado():
    out = market_intelligence(None, fake_property(market_comps(), assumptions={"itbi_aliquota": "0.025"}))
    v = out["valores"]
    assert v["desconto_sobre_avaliacao"] == Decimal("0.3956")
    assert v["desconto_sobre_mercado"] is not None and v["desconto_sobre_mercado"] != v["desconto_sobre_avaliacao"]


def test_risco_juridico_grave_impede_favoravel_mesmo_com_grande_desconto():
    out = market_intelligence(None, fake_property(market_comps(), acquisition="50000", assumptions={"itbi_aliquota": "0.025"},
                                                  risks=[{"severity": "CRITICA", "status": "ATIVO"}]))
    assert out["conclusao"]["resultado"] == DESFAVORAVEL and "desconto não compensa" in out["conclusao"]["motivos"][0]


def test_consolidacao_so_e_favoravel_com_todas_as_dimensoes_completas():
    dims = {"documentacao": {"matricula_anexada": True, "pendencias_documentais": []},
            "risco_juridico": {"severidades": [], "situacao_onus": "INCONCLUSIVO"},
            "mercado": {"confianca": mk.CONF_MEDIA}, "custos": {"criticos_pendentes": []},
            "rentabilidade": {"resultado_base": Decimal("40000"), "preco_acima_do_teto": False, "preco_maximo_provisorio": False},
            "liquidez": {"classificacao": mk.LIQ_MEDIA}}
    assert consolidate(dims)["resultado"] == INCONCLUSIVO          # ônus inconclusivo é informação crítica ausente
    dims["risco_juridico"]["situacao_onus"] = "SEM_ONUS_CONFIRMADO"
    assert consolidate(dims)["resultado"] == FAVORAVEL
    dims["mercado"]["confianca"] = mk.CONF_BAIXA
    assert consolidate(dims)["resultado"] == INCONCLUSIVO
    dims["mercado"]["confianca"] = mk.CONF_MEDIA
    dims["rentabilidade"]["preco_acima_do_teto"] = True
    assert consolidate(dims)["resultado"] == DESFAVORAVEL
    dims["rentabilidade"]["preco_acima_do_teto"] = False
    dims["risco_juridico"]["situacao_onus"] = "EXISTENTE"
    assert consolidate(dims)["resultado"] == DESFAVORAVEL
    dims["risco_juridico"]["situacao_onus"] = "SEM_ONUS_CONFIRMADO"
    dims["rentabilidade"]["cenarios_incompletos"] = ["BASE"]       # custo sem valor fora da soma: nunca FAVORÁVEL
    out = consolidate(dims)
    assert out["resultado"] == INCONCLUSIVO and any("incompleto" in b for b in out["bloqueios"])
    dims["rentabilidade"]["cenarios_incompletos"] = []
    dims["rentabilidade"]["aluguel_indicativo"] = True               # tese de locação não validada: ressalva, não bloqueio da revenda
    out = consolidate(dims)
    assert out["resultado"] == FAVORAVEL and any("indicativo" in r for r in out["ressalvas"])


# ------------------------------------------------------------------ revisão de regras (v1.0.8, itens 1–7)

CAIXA_10 = {"condominio_limite_pct_avaliacao": "0.10", "tributos_limite_pct_avaliacao": "0.10"}   # avaliação 220.000 → teto 22.000


def _linhas(**kw):
    return {c["chave"]: c for c in market_intelligence(None, fake_property(market_comps(), **kw))["custos"]}


@pytest.mark.parametrize("valor, comprador_cond, caixa_cond, comprador_iptu, caixa_iptu", [
    ("5000", "5000.00", "0.00", "5000.00", "0.00"),          # abaixo do limite: comprador paga tudo nos dois
    ("22000", "22000.00", "0.00", "22000.00", "0.00"),       # exatamente no limite: IPTU tratado como do comprador (leitura prudente)
    ("30000", "22000.00", "8000.00", "0.00", "30000.00"),    # acima: condomínio limitado ao teto; IPTU integralmente da Caixa
])
def test_regra_caixa_separa_divida_responsabilidade_do_comprador_e_parte_da_caixa(valor, comprador_cond, caixa_cond, comprador_iptu, caixa_iptu):
    dividas = [{"category": "Condomínio", "amount": Decimal(valor), "status": "PENDENTE"}, {"category": "IPTU", "amount": Decimal(valor), "status": "PENDENTE"}]
    linhas = _linhas(assumptions={"condicoes_caixa": CAIXA_10}, debts=dividas)
    for chave, comprador, caixa in (("condominio_atraso", comprador_cond, caixa_cond), ("tributos_atraso", comprador_iptu, caixa_iptu)):
        l = linhas[chave]
        assert l["status"] == INFORMADO and l["divida_total"] == Decimal(valor) and l["limite_responsabilidade"] == Decimal("22000.00")
        assert l["responsabilidade_comprador"] == Decimal(comprador) == l["valor"] and l["assumido_caixa"] == Decimal(caixa)
        assert l["divida_total"] == l["responsabilidade_comprador"] + l["assumido_caixa"] and l["regra"]


def test_divida_desconhecida_com_regra_caixa_nao_vira_zero_e_sem_regra_e_critica():
    l = _linhas(assumptions={"condicoes_caixa": CAIXA_10})["condominio_atraso"]
    assert l["status"] == PENDENTE and l["divida_total"] is None and l["assumido_caixa"] is None and l["responsabilidade_comprador"] is None
    assert l["valor_conservador"] == Decimal("22000.00") and l["valor_base"] is None and "fora da soma" in l["tratamento_base"]
    sem_regra = _linhas()["tributos_atraso"]
    assert sem_regra["critico"] is True and sem_regra["limite_responsabilidade"] is None and sem_regra["valor_conservador"] is None


def test_pendencia_nunca_entra_como_zero_e_cenario_incompleto_mostra_efeito_do_teto():
    out = market_intelligence(None, fake_property(market_comps(), assumptions={"itbi_aliquota": "0.025", "condicoes_caixa": CAIXA_10}))
    cons, base, otim = out["cenarios"]
    for s in out["cenarios"]:
        itens = {i["chave"]: i for i in s["composicao"]["itens"]}
        for i in itens.values():
            if i["status"] == PENDENTE:
                assert (i["incluido"] and i["valor"] is not None and i["base_valor"]) or (not i["incluido"] and i["valor"] is None)
        assert s["completo"] is (not s["custos_pendentes_nao_incluidos"]) and s["premissas"]["tratamento_pendencias"]
    for s in (base, otim):
        assert s["completo"] is False and "Desocupação" in s["custos_pendentes_nao_incluidos"]
        efeito = s["efeito_pendencias_no_teto"]
        assert efeito["valor"] == Decimal("49000.00")                     # 22.000 + 22.000 + reserva de desocupação 5.000
        assert efeito["resultado_se_no_teto"] == s["resultado_liquido"] - Decimal("49000.00")   # não dedutíveis: efeito 1 para 1
    # Reservas de registro e certidões entram em TODOS os cenários (antes ficavam fora do base).
    for s in out["cenarios"]:
        itens = {i["chave"]: i for i in s["composicao"]["itens"]}
        assert itens["registro"]["incluido"] and itens["certidoes"]["valor"] == Decimal("600.00")
    assert {i["chave"]: i for i in cons["composicao"]["itens"]}["reforma"]["valor"] > {i["chave"]: i for i in base["composicao"]["itens"]}["reforma"]["valor"] > 0


@pytest.mark.parametrize("indice, cenario", [(0, "CONSERVADOR"), (1, "BASE"), (2, "OTIMISTA")])
def test_preco_maximo_de_cada_cenario_entrega_roi_de_20_por_cento(indice, cenario):
    completos = {**_completo(), "goal_kind": "ROI_MINIMO", "goal_value": "0.20"}
    occ = SimpleNamespace(id=1, status="DESOCUPADO", estimated_cost=None)
    debts = [{"category": "Condomínio", "amount": Decimal("1000"), "status": "PENDENTE"}, {"category": "IPTU", "amount": Decimal("800"), "status": "PENDENTE"}]
    out = market_intelligence(None, fake_property(market_comps(), assumptions=completos, debts=debts, occupancy=occ))
    teto = out["preco_maximo"]["por_cenario"][cenario]
    assert teto["preco_maximo"] is not None and teto["definitivo"] is True and teto["roi_no_teto"] == Decimal("0.2000")
    no_teto = market_intelligence(None, fake_property(market_comps(), acquisition=str(teto["preco_maximo"]), assumptions=completos, debts=debts, occupancy=occ))
    s = no_teto["cenarios"][indice]
    assert s["cenario"] == cenario and abs(s["roi"] - Decimal("0.20")) <= Decimal("0.0001")
    um_real_acima = market_intelligence(None, fake_property(market_comps(), acquisition=str(teto["preco_maximo"] + 1), assumptions=completos, debts=debts, occupancy=occ))
    assert um_real_acima["cenarios"][indice]["resultado_liquido"] / um_real_acima["cenarios"][indice]["investimento_total"] < Decimal("0.20")


def test_memoria_do_ir_aparece_em_todos_os_cenarios_inclusive_conservador():
    out = market_intelligence(None, fake_property(market_comps(), assumptions={**_completo(), "condicoes_caixa": CAIXA_10}))
    for s in out["cenarios"]:
        c = s["composicao"]
        dedutiveis = sum(i["valor"] for i in c["itens_dedutiveis_ir"])
        nao = sum(i["valor"] for i in c["itens_nao_dedutiveis_ir"])
        assert dedutiveis == c["custo_aquisicao_dedutivel_ir"] and dedutiveis + nao == s["investimento_total"]
        assert c["base_ir"] == max(c["venda_liquida"] - dedutiveis, 0) and c["venda_liquida"] == s["valor_venda"] - s["corretagem_venda"]
        assert c["ir_ganho_capital"]["valor"] == (c["base_ir"] * Decimal("0.15")).quantize(Decimal("0.01")) == s["tributo_venda"]
        nao_dedutiveis = {i["descricao"] for i in c["itens_nao_dedutiveis_ir"]}
        assert "Certidões" in nao_dedutiveis and {"Preço de aquisição", "ITBI", "Escritura e registro", "Reforma"} <= {i["descricao"] for i in c["itens_dedutiveis_ir"]}
        if s["cenario"] == "CONSERVADOR":   # teto Caixa de condomínio/IPTU entra no investimento, mas não reduz a base do IR
            assert {"Condomínio em atraso", "IPTU e demais tributos em atraso"} <= nao_dedutiveis


def test_aluguel_explicita_vacancia_administracao_e_nao_usa_carregamento_da_revenda():
    comps = market_comps() + [{k: v for k, v in comp(20 + i, None, kind="ALUGUEL", rent=1100 + i * 10).items() if k != "id"} for i in range(4)]
    out = market_intelligence(None, fake_property(comps, assumptions=_completo()))
    base = out["cenarios"][1]
    r = base["rentabilidade_aluguel"]
    itens = {i["chave"]: i for i in base["composicao"]["itens"]}
    assert r["investimento_base"] == base["investimento_total"] - itens["manutencao_posse"]["valor"] - itens["iptu_posse"]["valor"]
    assert r["receita_com_vacancia"] == (r["receita_bruta_anual"] * Decimal("0.90")).quantize(Decimal("0.01"))
    assert r["taxa_administracao"] == (r["receita_com_vacancia"] * Decimal("0.10")).quantize(Decimal("0.01"))
    assert r["condominio_na_vacancia"] == Decimal("420.00") and r["iptu_na_vacancia"] == Decimal("60.00")   # 1,2 mês vago
    assert r["resultado_anual_antes_ir"] == r["receita_com_vacancia"] - r["taxa_administracao"] - r["condominio_na_vacancia"] - r["iptu_na_vacancia"]
    assert r["aluguel_indicativo"] is False and r["completa"] is True and "antes do IR" in r["premissas"]


def test_iptu_igual_ao_limite_e_do_comprador_por_premissa_conservadora_declarada():
    dividas = [{"category": "IPTU", "amount": Decimal("22000"), "status": "PENDENTE"}, {"category": "Condomínio", "amount": Decimal("22000"), "status": "PENDENTE"}]
    linhas = _linhas(assumptions={"condicoes_caixa": CAIXA_10}, debts=dividas)
    iptu, cond = linhas["tributos_atraso"], linhas["condominio_atraso"]
    assert iptu["responsabilidade_comprador"] == Decimal("22000.00") and iptu["assumido_caixa"] == Decimal("0.00")
    assert "Premissa conservadora" in iptu["premissa_conservadora"] and "premissa conservadora" in iptu["observacao"]
    assert cond["premissa_conservadora"] is None            # regra do condomínio é outra (comprador até o teto, Caixa o excedente)


def _reservas(**extra):
    return {**_completo(), "regularizacao": None, "iptu_anual": None, "regularizacao_reserva_base": "1000", "regularizacao_reserva_conservador": "3000",
            "regularizacao_reserva_origem": "orçamento de despachante", "iptu_anual_reserva_base": "600", "iptu_anual_reserva_conservador": "900",
            "iptu_reserva_origem": "carnê de unidade semelhante", **extra}


DIVIDAS_CONHECIDAS = [{"category": "Condomínio", "amount": Decimal("1000"), "status": "PENDENTE"}, {"category": "IPTU", "amount": Decimal("800"), "status": "PENDENTE"}]


def test_reservas_manuais_de_regularizacao_e_iptu_valem_por_cenario_e_seguem_pendentes():
    occ = SimpleNamespace(id=1, status="DESOCUPADO", estimated_cost=None)
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_reservas(), occupancy=occ, debts=DIVIDAS_CONHECIDAS))
    linhas = {c["chave"]: c for c in out["custos"]}
    for chave in ("regularizacao", "iptu_posse"):
        assert linhas[chave]["status"] == PENDENTE and linhas[chave]["valor"] is None and linhas[chave]["reserva_manual"] is True
        assert "reserva manual" in linhas[chave]["origem"]
    cons, base, otim = out["cenarios"]
    itens = lambda s: {i["chave"]: i for i in s["composicao"]["itens"]}
    assert itens(base)["regularizacao"]["valor"] == Decimal("1000.00") and itens(cons)["regularizacao"]["valor"] == Decimal("3000.00")
    assert itens(base)["iptu_posse"]["valor"] == Decimal("600.00")                    # 12 meses × 600/ano
    assert itens(cons)["iptu_posse"]["valor"] == Decimal("1350.00")                   # 18 meses × 900/ano
    assert itens(otim)["iptu_posse"]["valor"] == Decimal("450.00")                    # 9 meses × 600/ano
    assert "orçamento de despachante" in itens(cons)["regularizacao"]["base_valor"]
    assert all(s["completo"] for s in out["cenarios"])                                # tudo com valor ou reserva identificada


def test_impacto_de_cada_reserva_no_investimento_resultado_roi_e_preco_maximo():
    occ = SimpleNamespace(id=1, status="DESOCUPADO", estimated_cost=None)
    out = market_intelligence(None, fake_property(market_comps(), assumptions=_reservas(goal_kind="ROI_MINIMO", goal_value="0.20"), occupancy=occ,
                                                  debts=DIVIDAS_CONHECIDAS))
    for s in out["cenarios"]:
        impactos = {i["chave"]: i for i in s["impacto_reservas"]}
        assert {"regularizacao", "iptu_posse"} <= set(impactos)
        reg = impactos["regularizacao"]
        assert reg["tipo"] == "reserva manual" and reg["efeito_investimento"] == reg["reserva"]
        assert reg["efeito_resultado"] == -reg["reserva"]                             # não dedutível no IR: efeito 1 para 1
        assert reg["efeito_roi"] < 0 and reg["efeito_preco_maximo"] < 0
        # Conferência: retirar a reserva do lado do preço máximo devolve exatamente o teto sem ela.
        assert out["preco_maximo"]["por_cenario"][s["cenario"]]["preco_maximo"] - reg["efeito_preco_maximo"] > 0


def test_sem_reserva_o_custo_fica_pendente_fora_da_soma_e_reserva_nao_completa_cenario_com_outra_pendencia():
    sem = {c["chave"]: c for c in market_intelligence(None, fake_property(market_comps(), assumptions={**_completo(), "regularizacao": None, "iptu_anual": None}))["custos"]}
    for chave in ("regularizacao", "iptu_posse"):
        assert sem[chave]["status"] == PENDENTE and sem[chave]["valor_base"] is None and sem[chave]["valor_conservador"] is None   # sem valor padrão
    so_cons = market_intelligence(None, fake_property(market_comps(), assumptions=_reservas(regularizacao_reserva_base=None)))
    cons, base, _ = so_cons["cenarios"]
    assert not {i["chave"]: i for i in base["composicao"]["itens"]}["regularizacao"]["incluido"]
    assert {i["chave"]: i for i in cons["composicao"]["itens"]}["regularizacao"]["valor"] == Decimal("3000.00")
    # Ocupação não verificada: mesmo com as reservas de regularização e IPTU, base e otimista seguem incompletos.
    assert base["completo"] is False and "Desocupação" in base["custos_pendentes_nao_incluidos"]
    assert so_cons["conclusao"]["resultado"] != FAVORAVEL


def test_imovel7_efeito_das_pendencias_no_teto_detalha_cada_item_sem_diferenca_implicita():
    out = market_intelligence(None, imovel7())
    for s in out["cenarios"][1:]:                                    # base e otimista
        e = s["efeito_pendencias_no_teto"]
        detalhe = {d["chave"]: d for d in e["detalhe"]}
        assert set(detalhe) == {"condominio_atraso", "tributos_atraso", "desocupacao"}   # os R$ 5.000 são a reserva de desocupação
        assert detalhe["desocupacao"]["valor"] == Decimal("5000.00") and detalhe["desocupacao"]["tipo"] == "RESERVA"
        assert detalhe["condominio_atraso"]["tipo"] == detalhe["tributos_atraso"]["tipo"] == "TETO_CAIXA"
        assert sum(d["valor"] for d in e["detalhe"]) == e["valor"] == Decimal("49000.00")
        assert e["ir_adicional"] == 0                                # nenhum dos três reduz a base do IR
        assert e["resultado_se_no_teto"] == e["resultado_atual"] - e["valor"] - e["ir_adicional"]
        assert e["sem_teto_conhecido"] == ["Regularização", "IPTU durante a posse"]
    assert out["cenarios"][1]["efeito_pendencias_no_teto"]["resultado_se_no_teto"] == Decimal("-6529.35")
    assert out["cenarios"][2]["efeito_pendencias_no_teto"]["resultado_se_no_teto"] == Decimal("12048.98")


@pytest.mark.parametrize("indice, cenario, teto", [(0, "CONSERVADOR", "68214.91"), (1, "BASE", "144816.84"), (2, "OTIMISTA", "161939.94")])
def test_imovel7_teto_da_20_por_cento_e_um_real_a_mais_fica_abaixo(indice, cenario, teto):
    out = market_intelligence(None, imovel7())
    assert out["preco_maximo"]["por_cenario"][cenario]["preco_maximo"] == Decimal(teto)
    data = {k: IMOVEL7[k] for k in ("city", "neighborhood", "property_type", "bedrooms", "parking_spots", "area_m2", "private_area_m2")}
    roi = lambda preco: (lambda s: s["resultado_liquido"] / s["investimento_total"])(
        market_intelligence(None, fake_property(COMPARAVEIS_VENDA + COMPARAVEIS_ALUGUEL, acquisition=str(preco), assumptions=PREMISSAS_IMOVEL7, **data))["cenarios"][indice])
    assert roi(Decimal(teto)) >= Decimal("0.20") > roi(Decimal(teto) + 1)


def test_imovel7_teto_com_pendencias_no_teto_fica_abaixo_da_aquisicao_e_bloqueia():
    out = market_intelligence(None, imovel7())
    base = out["preco_maximo"]["por_cenario"]["BASE"]
    assert base["com_pendencias_no_teto"]["preco_maximo"] == Decimal("89988.20") and base["com_pendencias_no_teto"]["roi_no_teto"] == Decimal("0.2000")
    assert "CONSERVADOR" not in [k for k, v in out["preco_maximo"]["por_cenario"].items() if v.get("com_pendencias_no_teto")]
    assert any("cai para R$ 89.988,20" in b for b in out["conclusao"]["bloqueios"])
    tipos = {i["chave"]: i["tipo_valor"] for i in out["cenarios"][0]["composicao"]["itens"]}
    assert tipos["condominio_atraso"] == "TETO_CAIXA" and tipos["reforma"] == "RESERVA" and tipos["aquisicao"] == "CONFIRMADO"
    assert tipos["regularizacao"] == "FORA_DA_SOMA" and tipos["itbi"] == "ESTIMADO"


def test_imovel7_expoe_limitacoes_da_amostra_e_continua_inconclusivo():
    out = market_intelligence(None, imovel7())
    lim = " ".join(out["venda"]["limitacoes"])
    assert "ÁREA TOTAL" in lim and "sem base de área declarada" in lim and "Nenhum negócio fechado" in lim
    assert out["conclusao"]["resultado"] == INCONCLUSIVO
    assert any("incompleto" in b for b in out["conclusao"]["bloqueios"]) and any("indicativo" in r for r in out["conclusao"]["ressalvas"])
    assert set(out["preco_maximo"]["por_cenario"]) == {"CONSERVADOR", "BASE", "OTIMISTA"}
    for teto in out["preco_maximo"]["por_cenario"].values():
        assert teto["provisorio"] is True and teto["roi_no_teto"] == Decimal("0.2000")


# ------------------------------------------------------------------ validação: imóvel 7 com os comparáveis reais

def imovel7():
    data = {k: IMOVEL7[k] for k in ("city", "neighborhood", "property_type", "bedrooms", "parking_spots", "area_m2", "private_area_m2")}
    return fake_property(COMPARAVEIS_VENDA + COMPARAVEIS_ALUGUEL, assumptions=PREMISSAS_IMOVEL7, **data)


def test_imovel7_exclui_o_proprio_anuncio_e_duplicatas_e_nao_forca_conclusao():
    out = market_intelligence(None, imovel7())
    venda = {r["id"]: r for r in out["venda"]["comparaveis"]}
    refs = {i + 1: c["listing_ref"] for i, c in enumerate(COMPARAVEIS_VENDA + COMPARAVEIS_ALUGUEL)}
    by_ref = {refs[i]: r for i, r in venda.items()}
    assert not by_ref["zap-08"]["usado"] and not by_ref["zap-15"]["usado"]                       # o próprio imóvel
    assert by_ref["zap-04"]["motivo"].startswith("Provável duplicata") and by_ref["zap-10"]["motivo"].startswith("Provável duplicata")
    assert by_ref["zap-12"]["motivo"].startswith("Provável duplicata")
    assert out["venda"]["quantidade_usada"] == 13 and out["venda"]["confianca"] == mk.CONF_MEDIA   # só anúncios: no máximo MÉDIA
    assert out["aluguel"]["quantidade_usada"] == 1 and out["valores"]["aluguel_indicativo"] is True
    assert out["valores"]["valor_mercado_estimado"] is not None
    custos = {c["chave"]: c for c in out["custos"]}
    assert custos["itbi"]["status"] == "ESTIMADO" and custos["itbi"]["valor"] == Decimal("3545.64")
    assert custos["condominio_atraso"]["valor_conservador"] == Decimal("22000.00")
    assert out["conclusao"]["resultado"] == INCONCLUSIVO and out["conclusao"]["bloqueios"]
    assert out["liquidez"]["classificacao"] == mk.LIQ_MEDIA and out["liquidez"]["prazo_estimado_meses"] is None   # só anúncios: no máximo MÉDIA
    assert "R$ 141.825,75" in custos["itbi"]["observacao"]
    assert out["custo_ia_usd"] == 0


# ------------------------------------------------------------------ HTTP + PostgreSQL

@pytest.fixture
def api(postgres_engine):
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from backend.app.database import get_db
    from backend.app.main import app
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    app.dependency_overrides[get_db] = lambda: (yield session)
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def test_api_comparavel_rastreavel_e_inteligencia_de_mercado(api):
    client, session = api
    from backend.app import models
    pid = client.post("/api/imoveis", json={"title": "RESIDENCIAL AMERICA 5 (sintético)", "address": "Rua Macapá", "city": "Fazenda Rio Grande", "state": "PR",
                                            "neighborhood": "Estados", "property_type": "Apartamento", "modality": "VENDA_DIRETA", "area_m2": 48.74,
                                            "private_area_m2": 45.50, "bedrooms": 2, "parking_spots": 1}).json()["id"]
    session.add(models.Auction(property_id=pid, auction_stage="Venda direta", appraisal_value=Decimal("220000"), bid_value=Decimal("132970.97"),
                               acquisition_value=Decimal("132970.97"), commission_percent=Decimal("0"), financial_assumptions=PREMISSAS_IMOVEL7))
    session.flush()
    for c in COMPARAVEIS_VENDA[:6]:
        body = {k: (str(v) if isinstance(v, Decimal) else (v.isoformat() if hasattr(v, "isoformat") else v)) for k, v in c.items() if v is not None}
        r = client.post(f"/api/imoveis/{pid}/comparaveis", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["price_type"] == "ANUNCIADO" and r.json()["collected_at"] == "2026-11-16"
    r = client.get(f"/api/imoveis/{pid}/inteligencia-mercado")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["venda"]["quantidade_total"] == 6 and body["conclusao"]["resultado"] in (INCONCLUSIVO, DESFAVORAVEL, FAVORAVEL)
    assert {c["chave"] for c in body["custos"]} >= {"aquisicao", "itbi", "registro", "condominio_atraso", "tributos_atraso", "reforma", "desocupacao"}
    assert body["preco_maximo"]["criterio"] and body["premissas"]["mercado.desconto_negociacao"]["origem"]
    historico = client.get(f"/api/imoveis/{pid}/comparaveis").json()["historico"]
    assert historico and historico[0]["after_data"]["price_type"] == "ANUNCIADO"
    invalido = client.post(f"/api/imoveis/{pid}/comparaveis", json={"kind": "VENDA", "price": 1, "price_type": "VENDIDO"})
    assert invalido.status_code == 422


def test_api_premissas_v108_sao_gravadas_e_reserva_manual_exige_origem(api):
    client, _ = api
    pid = client.post("/api/imoveis", json={"title": "Premissas v1.0.8", "address": "Rua Macapá", "city": "Fazenda Rio Grande", "state": "PR", "property_type": "Apartamento",
                                            "private_area_m2": 45.5, "bedrooms": 2}).json()["id"]
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "132970.97", "appraisal_value": "220000", "commission_percent": "0"})
    ok = {"itbi_aliquota": "0.025", "itbi_base_minima": "141825.75", "iptu_anual_reserva_base": "600", "iptu_anual_reserva_conservador": "900",
          "iptu_reserva_origem": "carnê 2025 do vizinho de andar (estimativa)", "regularizacao_reserva_conservador": "3000",
          "regularizacao_reserva_origem": "orçamento de despachante", "condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.10", "tributos_limite_pct_avaliacao": "0.10"}}
    r = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json=ok)
    assert r.status_code == 200, r.text
    salvas = client.get(f"/api/imoveis/{pid}/financeiro/premissas").json()["premissas"]
    assert salvas["iptu_anual_reserva_conservador"] == "900" and salvas["condicoes_caixa"]["tributos_limite_pct_avaliacao"] == "0.10"
    custos = {c["chave"]: c for c in client.get(f"/api/imoveis/{pid}/inteligencia-mercado").json()["custos"]}
    assert custos["iptu_posse"]["status"] == PENDENTE and "carnê 2025" in custos["iptu_posse"]["origem"]
    assert custos["regularizacao"]["valor_base"] is None and Decimal(str(custos["regularizacao"]["valor_conservador"])) == Decimal("3000")
    assert Decimal(str(custos["condominio_atraso"]["limite_responsabilidade"])) == Decimal("22000")
    sem_origem = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={"regularizacao_reserva_base": "1000"})
    assert sem_origem.status_code == 422
    invertida = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={"iptu_anual_reserva_base": "900", "iptu_anual_reserva_conservador": "600",
                                                                              "iptu_reserva_origem": "x"})
    assert invertida.status_code == 422
    negativa = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={"itbi_aliquota": "1.5"})
    assert negativa.status_code == 422
