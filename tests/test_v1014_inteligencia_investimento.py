"""v1.0.14 — evolução da inteligência, UX e análise do investimento.

Dados fictícios. Cobre: riscos consolidados em linguagem simples (sem códigos, uma vez por assunto, histórico interno), qualidade
da amostra de mercado, recomendação ao investidor (margem positiva não esconde risco nem dado faltando), situação do IPTU,
condomínio (taxa mensal ≠ dívida, estimativa insuficiente), tipos de data da matrícula e o endpoint do Resumo.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace as NS

from backend.app import debts_service, models
from backend.app.investment_summary import (REC_ATENCAO, REC_DESFAVORAVEL, REC_FAVORAVEL, REC_NAO_ARREMATAR, condo_analysis, recommend)
from backend.app.market import sample_quality
from backend.app.registry_timeline import _typed_dates, certificate_issue
from backend.app.registry_chain import fold
from backend.app.risk_engine import RiskEngine
from backend.app.risk_presenter import consolidate, plain_text
from tests.test_checklist_evidencias import _leilao, _prop
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)

CODIGOS = ("CHECKLIST_", "RiskEngine", "Evidência #", "Versão", "Requer análise do domínio")


def _risk(id_, version, key="TERCEIRO_OCUPANTE", state="ATENCAO", severity="MEDIA", evidence_id=None, category="desocupacao"):
    rk = f"CHECKLIST_{key}_{state}"
    return NS(id=id_, analysis_version=version, category=category, severity=severity, status="ATIVO", evidence_id=evidence_id, impact="x",
              origin=f"RiskEngine:ChecklistResult:{rk}", description=f"[{rk}] Checklist: {key}: pergunta? Estado determinístico: {state}.")


def _result(key, state, interpretation=None):
    return NS(item=NS(canonical_key=key, question="?", category="X"), state=state, applicable=True, interpretation=interpretation, answer="")


def _texto(item) -> str:
    return " ".join(str(item.get(k) or "") for k in ("titulo", "o_que_significa", "detalhe", "situacao_label")) + " ".join(item["o_que_fazer"])


# ------------------------------------------------------------------ riscos consolidados

def test_mesmo_risco_em_varias_versoes_aparece_uma_vez_no_estado_mais_recente():
    risks = [_risk(1, 5), _risk(2, 6), _risk(3, 7, state="RISCO_IDENTIFICADO", severity="ALTA")]
    out = consolidate(risks, latest_version=7)
    [item] = out["itens"]
    assert item["titulo"] == "Imóvel ocupado" and item["categoria"] == "Ocupação e desocupação"
    assert item["situacao"] == "CONFIRMADO" and item["gravidade"] == "ALTA"
    assert [h["versao"] for h in item["rastreabilidade"]["historico"]] == [5, 6, 7]     # histórico só interno
    assert not any(c in _texto(item) for c in CODIGOS)
    assert any("imissão" in a or "locação" in a for a in item["o_que_fazer"])
    assert set(item["impactos"]) == {"financeiro", "prazo", "operacional", "jurídico"}


def test_ocupacao_confirmada_vira_confirmado_e_risco_antigo_vira_resolvido():
    risks = [_risk(1, 7), _risk(2, 6, key="PENHORA_INDISPONIBILIDADE", category="juridico")]
    out = consolidate(risks, latest_version=7, occupancy=NS(status="OCUPADO_CONFIRMADO"))
    by_key = {i["chave"]: i for i in out["itens"]}
    assert by_key["TERCEIRO_OCUPANTE"]["situacao"] == "CONFIRMADO"
    assert by_key["PENHORA_INDISPONIBILIDADE"]["situacao"] == "RESOLVIDO"
    assert out["principal"] == "Imóvel ocupado"


def test_pendencia_essencial_e_item_sem_risco_aparecem_com_a_situacao_certa():
    results = [_result("ACAO_QUESTIONAMENTO", "PENDENTE"), _result("VAGA_MATRICULA", "PENDENTE"), _result("PENHORA_INDISPONIBILIDADE", "NAO_IDENTIFICADO")]
    out = consolidate([], latest_version=1, checklist_results=results)
    by_key = {i["chave"]: i for i in out["itens"]}
    assert by_key["ACAO_QUESTIONAMENTO"]["situacao"] == "PENDENTE_CONFIRMACAO"
    assert "VAGA_MATRICULA" not in by_key                                                # pendência não essencial não polui
    assert by_key["PENHORA_INDISPONIBILIDADE"]["situacao"] == "NAO_IDENTIFICADO"


def test_estimativa_do_risco_vem_do_financeiro_e_desconhecido_nao_vira_zero():
    lines = [{"chave": "desocupacao", "valor": None, "valor_base": Decimal("5000"), "valor_conservador": Decimal("12000"), "status": "PENDENTE",
              "origem": "reserva"}]
    [item] = consolidate([_risk(1, 1)], latest_version=1, cost_lines=lines)["itens"]
    assert "R$ 5.000,00" in item["estimativa"]["texto"] and "R$ 12.000,00" in item["estimativa"]["texto"]
    [sem] = consolidate([_risk(1, 1)], latest_version=1, cost_lines=[])["itens"]
    assert sem["estimativa"]["tipo"] == "DESCONHECIDO" and sem["estimativa"]["valor_base"] is None


def test_texto_legado_perde_os_codigos_e_texto_comum_fica_intacto():
    assert plain_text("[CHECKLIST_X_ATENCAO] Checklist: TERCEIRO_OCUPANTE: Há terceiro? Estado determinístico: ATENCAO.") == "Há terceiro?"
    assert plain_text("Custo de reforma não informado.") == "Custo de reforma não informado."


def test_risk_engine_grava_titulo_e_impacto_em_linguagem_simples():
    result = NS(id=9, state="ATENCAO", confidence="MEDIA", evidences=[NS(id=3, property_id=1)], evidence_links=[],
                item=NS(canonical_key="TERCEIRO_OCUPANTE", category="DESOCUPACAO", question="Há terceiro ocupando o imóvel?"))
    [risk] = RiskEngine().evaluate(1, [result])
    assert risk.title == "Imóvel ocupado" and "Checklist:" not in risk.title
    assert "Requer análise" not in risk.impact and risk.risk_key == "CHECKLIST_TERCEIRO_OCUPANTE_ATENCAO"


# ------------------------------------------------------------------ mercado

def test_qualidade_da_amostra_por_faixa():
    assert sample_quality(0)["nivel"] == "INSUFICIENTE" and sample_quality(2)["nivel"] == "INSUFICIENTE"
    assert sample_quality(3)["nivel"] == "BAIXA" and sample_quality(6)["nivel"] == "BAIXA"
    assert sample_quality(7, Decimal("0.40"))["nivel"] == "MEDIA" and sample_quality(8, Decimal("0.10"))["nivel"] == "ALTA"


# ------------------------------------------------------------------ recomendação

def _risks(*situacoes, gravidade="MEDIA"):
    return {"itens": [{"situacao": s, "situacao_label": s.title(), "titulo": f"Risco {i}", "gravidade": gravidade} for i, s in enumerate(situacoes)]}


def test_margem_positiva_nao_esconde_risco_nem_dado_faltando():
    rec = recommend(verdict_overall="ATENCAO", verdict_code=None, risks=_risks("POSSIVEL"), missing=["IPTU"], acquisition=Decimal("100"),
                    max_price=Decimal("150"), max_price_provisional=True, result=Decimal("30000"))
    assert rec["codigo"] == REC_ATENCAO and rec["label"] == "ATENÇÃO — INVESTIGAR"
    assert rec["aviso_margem"] and "riscos ativos" in rec["aviso_margem"] and "faltam dados" in rec["aviso_margem"]
    assert any("IPTU" in m for m in rec["motivos"])


def test_precedencia_da_recomendacao():
    base = dict(verdict_code=None, acquisition=Decimal("100"), max_price=Decimal("150"), max_price_provisional=False, result=Decimal("10"))
    assert recommend(verdict_overall="ATENCAO", risks=_risks("CONFIRMADO", gravidade="CRITICA"), missing=[], **base)["codigo"] == REC_NAO_ARREMATAR
    assert recommend(verdict_overall="DESFAVORAVEL", risks=_risks(), missing=[], **base)["codigo"] == REC_DESFAVORAVEL
    above = {**base, "acquisition": Decimal("200")}
    assert recommend(verdict_overall="FAVORAVEL", risks=_risks(), missing=[], **above)["codigo"] == REC_DESFAVORAVEL
    assert recommend(verdict_overall="FAVORAVEL", risks=_risks(), missing=["condomínio"], **base)["codigo"] == REC_ATENCAO
    assert recommend(verdict_overall="INCONCLUSIVO", risks=_risks(), missing=[], **base)["codigo"] == REC_ATENCAO
    assert recommend(verdict_overall=None, risks=_risks(), missing=[], **base)["codigo"] == REC_ATENCAO
    fav = recommend(verdict_overall="FAVORAVEL", risks=_risks("RESOLVIDO", "NAO_IDENTIFICADO"), missing=[], **base)
    assert fav["codigo"] == REC_FAVORAVEL and fav["aviso_margem"] is None


# ------------------------------------------------------------------ condomínio

def test_condominio_separa_taxa_mensal_da_divida_e_avisa_estimativa_insuficiente():
    prop = NS(address="Rua A, 1", private_area_m2=Decimal("50"), area_m2=Decimal("55"),
              comparables=[NS(id=1, condo_fee=Decimal("400"), area_m2=Decimal("50"), excluded=False, address="Rua B, 2")])
    intel = {"venda": {"comparaveis": [{"id": 1, "usado": True}]}, "aluguel": {"comparaveis": []}, "carregamento_mensal": {"valor": None, "origem": None},
             "custos": [{"chave": "condominio_atraso", "valor": None, "valor_base": Decimal("3000"), "valor_conservador": Decimal("6000"), "status": "PENDENTE",
                         "origem": "estimativa pela matrícula"}]}
    out = condo_analysis(prop, intel, {})
    assert out["estimativa_insuficiente"] is True and out["taxa_mensal"]["valor"] is None and out["taxa_mensal"]["tipo"] == "DESCONHECIDO"
    assert out["referencias"]["quantidade"] == 1 and out["confianca"] == "INSUFICIENTE"
    assert out["divida_acumulada"]["valor_base"] == Decimal("3000") and out["divida_acumulada"]["tipo"] == "ESTIMATIVA"
    assert out["busca_automatica"]["status"] == "NAO_CONFIGURADO"
    informado = condo_analysis(prop, {**intel, "carregamento_mensal": {"valor": Decimal("380"), "origem": "premissa do imóvel"}}, {"carregamento_mensal": "380"})
    assert informado["taxa_mensal"]["status"] == "CONFIRMADO" and informado["taxa_mensal"]["valor"] == Decimal("380")
    assert informado["divida_acumulada"]["valor_base"] == Decimal("3000")                  # a taxa não muda a dívida


# ------------------------------------------------------------------ matrícula

def test_datas_do_ato_tem_tipo_e_nenhuma_e_inventada():
    texto = ("R-2/100 - Protocolo nº 12.345 de 03/02/2020. COMPRA E VENDA. Instrumento particular datado de 15/01/2020. "
             "Registrado em 10/02/2020. Citada 01/03/2019.")
    datas = _typed_dates(fold(texto), texto, 0, len(texto))
    assert [(d["tipo"], d["data"]) for d in datas] == [("PROTOCOLO", "2020-02-03"), ("DOCUMENTO", "2020-01-15"), ("ATO", "2020-02-10"),
                                                       ("CITADA", "2019-03-01")]
    assert _typed_dates(fold("COMPRA E VENDA sem data"), "COMPRA E VENDA sem data", 0, 23) == []


def test_data_de_emissao_da_certidao_so_quando_o_texto_identifica():
    assert certificate_issue("Certidão... Data/hora: 20/11/2026 10:15")["data"] == "2026-11-20"
    vazio = certificate_issue("R-1 Compra e venda em 10/02/2020")
    assert vazio["data"] is None and "não localizada" in vazio["texto"]


# ------------------------------------------------------------------ API

def test_resumo_sem_comparaveis_nao_inventa_valor_e_pede_investigacao(api):
    client, db = api
    debts_service.seed_all(db)
    prop = _prop(db)
    prop.city, prop.state = "Fazenda Rio Grande", "PR"
    _leilao(db, prop)
    db.flush()
    body = client.get(f"/api/imoveis/{prop.id}/resumo-investimento").json()
    assert body["recomendacao"]["codigo"] == "ATENCAO_INVESTIGAR"
    assert body["numeros"]["valor_venda"]["valor"] is None and body["numeros"]["valor_venda"]["tipo"] == "DESCONHECIDO"
    assert "AMOSTRA INSUFICIENTE" in body["numeros"]["valor_venda"]["texto"]
    assert body["numeros"]["lance"]["tipo"] == "FATO"
    assert body["mercado"]["venda"]["qualidade"]["nivel"] == "INSUFICIENTE"
    assert body["iptu"]["status"] == "NECESSITA_INFORMACAO" and body["iptu"]["portal"]["urls"]        # sem inscrição: diz o que falta
    assert any("IPTU" in p for p in body["pendencias"]) and any("valor de venda" in p for p in body["pendencias"])
    assert body["condominio"]["estimativa_insuficiente"] is True
    assert set(body["financeiro"]) >= {"confirmado", "estimado", "desconhecido", "nao_incluido"}
    risks = client.get(f"/api/imoveis/{prop.id}/riscos-consolidados").json()
    assert risks["property_id"] == prop.id and "itens" in risks


def test_iptu_registrado_na_consulta_assistida_vira_consultado(api):
    client, db = api
    debts_service.seed_all(db)
    prop = _prop(db)
    prop.city, prop.state, prop.inscription = "Fazenda Rio Grande", "PR", "01.02.003.0004"
    _leilao(db, prop)
    db.flush()
    assert client.get(f"/api/imoveis/{prop.id}/iptu/situacao").json()["status"] == "PENDENTE_CONSULTA"
    muni = db.query(models.Municipality).filter(models.Municipality.name == "Fazenda Rio Grande").one()
    r = client.post(f"/api/imoveis/{prop.id}/debitos/consultar", json={"debt_type_code": "IPTU", "municipality_id": muni.id,
                                                                       "itens": [{"updated_amount": "850.00", "competence": "2025"}]})
    assert r.status_code == 201, r.text
    situacao = client.get(f"/api/imoveis/{prop.id}/iptu/situacao").json()
    assert situacao["status"] == "CONSULTADO" and Decimal(str(situacao["debito_em_aberto"]["valor"])) == Decimal("850.00")
    assert situacao["debito_em_aberto"]["tipo"] == "DADO_MANUAL"
    sem = _prop(db)
    sem.city, sem.state, sem.inscription = "Fazenda Rio Grande", "PR", "9"
    db.flush()
    client.post(f"/api/imoveis/{sem.id}/debitos/consultar", json={"debt_type_code": "IPTU", "municipality_id": muni.id, "sem_ocorrencia": True})
    s2 = client.get(f"/api/imoveis/{sem.id}/iptu/situacao").json()
    assert s2["status"] == "CONSULTADO" and s2["sem_debito"] is True
