"""v1.0.12 — Fase A: fonte única de custos (condomínio e IPTU em atraso) e correções da análise v5.

Dados fictícios. Cobre: regra do documento das condições da venda antes da premissa; dívida confirmada, informada, estimada e
consulta indisponível (nunca zero); mesmo valor na composição, no veredito, na inteligência de mercado e no checklist; item 08 com a
informação do vendedor ("Em tratamento"); pendências do veredito agrupadas por assunto.
"""
from __future__ import annotations

from decimal import Decimal

from backend.app import models
from backend.app.sale_conditions import LEILOES_EM_TRATAMENTO, TEMA_CONDOMINIO, TEMA_LEILOES, read_conditions
from backend.app.verdict_engine import FATOR_INFORMACAO, FATOR_PREMISSA, consolidate_factors, financial_subject
from backend.app.viability import (AVISO_ESTIMATIVA_CONDOMINIO, FONTE_CONFIRMADO, FONTE_ESTIMATIVA, FONTE_INDISPONIVEL, market_intelligence,
                                   verdict_finance)
from tests.test_checklist_evidencias import CONDICOES_FICTICIAS, _analisar, _doc, _evs, _itens, _leilao, _prop
from tests.test_v107_imovel7_regressao import MATRICULA_FICTICIA

CONDICOES_COM_LEILOES = CONDICOES_FICTICIAS + "\nAverbação dos leilões negativos: Em tratamento\n"
TETO = Decimal("22000.00")   # 10% da avaliação fictícia de R$ 220.000


def _linha(intel, chave):
    return next(l for l in intel["custos"] if l["chave"] == chave)


def _imovel_com_condicoes(db, assumptions=None):
    prop = _prop(db)
    _leilao(db, prop, assumptions)
    _doc(db, prop, CONDICOES_COM_LEILOES, "condicoes.txt", "CONDICOES_VENDA")
    db.expire(prop)
    return prop


# ------------------------------------------------------------------ condições da venda: leilões negativos

def test_condicoes_leem_a_averbacao_dos_leiloes_negativos_sem_afetar_as_demais():
    cond = read_conditions([{"chunk_id": 1, "content": CONDICOES_COM_LEILOES, "page": 1, "section": None}], 10)
    leiloes = cond.first(TEMA_LEILOES)
    assert leiloes is not None and leiloes.regra == LEILOES_EM_TRATAMENTO and leiloes.detalhes == ["Em tratamento"]
    assert leiloes.excerpt == "Averbação dos leilões negativos: Em tratamento"
    assert cond.first(TEMA_CONDOMINIO).limite_pct == Decimal("0.1000")


# ------------------------------------------------------------------ regra do documento antes da premissa

def test_sem_premissas_a_regra_vem_do_documento_e_o_teto_e_22_mil(db):
    intel = market_intelligence(db, _imovel_com_condicoes(db))
    for chave in ("condominio_atraso", "tributos_atraso"):
        linha = _linha(intel, chave)
        assert linha["status"] == "PENDENTE" and linha["valor_base"] is None            # sem valor: fora da soma no base (nunca zero)
        assert linha["valor_conservador"] == TETO and linha["limite_responsabilidade"] == TETO
        assert linha["regra_fonte"] == "DOCUMENTO" and "condicoes.txt" in linha["regra_origem"] and linha["regra_trecho"]
        assert not linha["critico"]                                                        # há teto conhecido
        assert linha["exposicao"]["valor_considerado"] == {"base": None, "conservador": TETO}


def test_documento_prevalece_sobre_a_premissa(db):
    premissa = {"condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.05", "tributos_limite_pct_avaliacao": "0.05", "origem": "anúncio"}}
    intel = market_intelligence(db, _imovel_com_condicoes(db, premissa))
    assert _linha(intel, "condominio_atraso")["valor_conservador"] == TETO


def test_sem_documento_a_premissa_continua_valendo(db):
    prop = _prop(db)
    _leilao(db, prop, {"condicoes_caixa": {"condominio_limite_pct_avaliacao": "0.10", "origem": "anúncio"}})
    db.expire(prop)
    linha = _linha(market_intelligence(db, prop), "condominio_atraso")
    assert linha["regra_fonte"] == "PREMISSA" and linha["valor_conservador"] == TETO


# ------------------------------------------------------------------ fonte do valor

def test_divida_confirmada_aplica_a_regra_do_excedente(db):
    prop = _imovel_com_condicoes(db)
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="COTA_CONDOMINIAL", nature="DIVIDA_EXISTENTE", status="CONFIRMADO",
                               updated_amount=Decimal("30000")))
    db.flush(); db.expire(prop)
    linha = _linha(market_intelligence(db, prop), "condominio_atraso")
    assert linha["status"] == "INFORMADO" and linha["fonte_divida"] == FONTE_CONFIRMADO
    assert (linha["divida_total"], linha["responsabilidade_comprador"], linha["assumido_caixa"]) == (Decimal("30000.00"), TETO, Decimal("8000.00"))
    assert linha["valor_base"] == linha["valor_conservador"] == TETO


def test_iptu_acima_do_limite_e_integral_do_vendedor(db):
    prop = _imovel_com_condicoes(db)
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", nature="DIVIDA_EXISTENTE", status="INFORMADO", original_amount=Decimal("25000")))
    db.flush(); db.expire(prop)
    linha = _linha(market_intelligence(db, prop), "tributos_atraso")
    assert linha["responsabilidade_comprador"] == Decimal("0") and linha["assumido_caixa"] == Decimal("25000.00")


def test_consulta_indisponivel_nunca_vira_zero(db):
    prop = _imovel_com_condicoes(db)
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="IPTU", nature="DIVIDA_EXISTENTE", status="INDISPONIVEL"))
    db.flush(); db.expire(prop)
    linha = _linha(market_intelligence(db, prop), "tributos_atraso")
    assert linha["status"] == "PENDENTE" and linha["fonte_divida"] == FONTE_INDISPONIVEL
    assert linha["valor"] is None and linha["valor_base"] is None and "não é zero" in linha["observacao"]


def test_estimativa_condominial_entra_com_a_regra_aplicada_depois(db):
    prop = _imovel_com_condicoes(db)
    db.add(models.CondominiumEstimate(property_id=prop.id, monthly_reference=Decimal("500"), monthly_source="INFORMADO", months_delinquent=40,
                                      scenario_otimista=Decimal("4000"), scenario_provavel=Decimal("10000"), scenario_conservador=Decimal("30000"),
                                      confidence="BAIXA", assumptions={}))
    db.flush(); db.expire(prop)
    intel = market_intelligence(db, prop)
    linha = _linha(intel, "condominio_atraso")
    assert linha["status"] == "ESTIMADO" and linha["fonte_divida"] == FONTE_ESTIMATIVA
    assert linha["valor_base"] == Decimal("10000.00") and linha["valor_conservador"] == TETO      # alto (30 mil) limitado ao teto
    assert linha["exposicao"]["responsabilidade_caixa"] == {"base": Decimal("0.00"), "conservador": Decimal("8000.00")}
    assert linha["aviso_estimativa"] == AVISO_ESTIMATIVA_CONDOMINIO and AVISO_ESTIMATIVA_CONDOMINIO in linha["observacao"]
    fin = verdict_finance(db, prop)
    assert "condominio_atraso" in fin["preco_maximo_detalhe"]["custos_desconhecidos"]              # estimativa deixa o cálculo provisório
    assert any("não é dívida confirmada" in p for p in fin["pendencias"])


def test_mesmo_valor_na_composicao_no_veredito_e_na_inteligencia(db):
    prop = _imovel_com_condicoes(db, {"valor_venda_estimado": "200000"})
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", amount=Decimal("12000"), status="PENDENTE"))
    db.flush(); db.expire(prop)
    intel = market_intelligence(db, prop)
    base = next(s for s in intel["cenarios"] if s["cenario"] == "BASE")
    no_cenario = next(i for i in base["composicao"]["itens"] if i["chave"] == "condominio_atraso")["valor"]
    fin = verdict_finance(db, prop)
    no_veredito = next(c for c in fin["composicao_custos"] if c["chave"] == "condominio_atraso")["valor"]
    assert no_cenario == no_veredito == Decimal("12000.00")


# ------------------------------------------------------------------ checklist: itens 08 e 15

def test_item_08_usa_a_informacao_do_vendedor_sem_confirmar(db):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    _doc(db, prop, CONDICOES_COM_LEILOES, "condicoes.txt", "CONDICOES_VENDA")
    execution, _ = _analisar(db, prop)
    item = _itens(execution)["LEILOES_NEGATIVOS_AVERBADOS"]
    assert item.state == "EM_ANALISE" and item.confidence == "BAIXA"
    assert "Em tratamento" in item.interpretation and "não comprova a averbação" in item.interpretation
    assert any(e.document_version_id is not None and "Em tratamento" in (e.source_excerpt or "") for e in _evs(db, item))


def test_item_15_mostra_o_mesmo_debito_da_composicao(db):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    _doc(db, prop, CONDICOES_COM_LEILOES, "condicoes.txt", "CONDICOES_VENDA")
    db.add(models.PropertyDebt(property_id=prop.id, debt_type_code="COTA_CONDOMINIAL", nature="DIVIDA_EXISTENTE", status="CONFIRMADO",
                               updated_amount=Decimal("1500")))
    db.flush()
    execution, _ = _analisar(db, prop)
    item = _itens(execution)["RESPONSABILIDADE_DEBITOS"]
    assert "condomínio R$ 1.500,00" in (item.answer or "")


# ------------------------------------------------------------------ veredito: pendências agrupadas por assunto

def test_pendencias_financeiras_sem_repeticao_agrupadas_por_assunto():
    faltantes = ["Valor de venda estimado não informado.", "Meta financeira (margem, ROI ou lucro mínimo) não configurada."]
    pendentes = ["Valor de venda estimado ausente: resultado líquido, margem e ROI não calculados.",
                 "Valor de venda estimado (V) é essencial e não foi informado.",
                 "Meta financeira (valor/percentual) é essencial e não foi informada.",
                 "Meta de preço máximo não configurada; preço máximo não calculado.",
                 "Custo de Condomínio em atraso não informado: fora da soma, não é zero (cálculo provisório).",
                 "Custo de IPTU e demais tributos em atraso não informado: fora da soma, não é zero (cálculo provisório).",
                 "Desocupação: valor real não informado; o cálculo usa reserva de R$ 5.000,00."]
    g = consolidate_factors([], [], {"faltantes": faltantes}, pendentes)["grupos"]
    financeiros = [f for grupo in (FATOR_PREMISSA, FATOR_INFORMACAO) for f in g[grupo] if f["origem"] == "FINANCEIRO"]
    assuntos = [f["assunto"] for f in financeiros]
    assert sorted(assuntos) == sorted(["VALOR_VENDA", "META", "DEBITOS", "OCUPACAO"]) and len(set(assuntos)) == len(assuntos)
    venda = next(f for f in financeiros if f["assunto"] == "VALOR_VENDA")
    assert venda in g[FATOR_PREMISSA] and len(venda["detalhes"]) == 2                          # nenhuma mensagem perdida
    total = sum(1 + len(f["detalhes"]) for f in financeiros)
    assert total == len(faltantes) + len(pendentes)


def test_assunto_das_mensagens():
    assert financial_subject("Prazo da operação não informado: o condomínio e o IPTU da posse usam o padrão de 12 meses.") == "PREMISSAS_VENDA"
    assert financial_subject("Custo de Condomínio durante a posse não informado: fora da soma.") == "CUSTOS"
    assert financial_subject("Lance pretendido (valor de arrematação) não informado.") == "LANCE"
