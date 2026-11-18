"""Integração da análise de VENDA DIRETA (regra modality-v2): checklist por finalidade do item, inteligência de mercado
como sugestão para as premissas e veredito com fatores separados.

Caso de referência: imóvel 7 (venda direta Caixa, matrícula com alienação fiduciária e consolidação). A matrícula usada
aqui é a FICTÍCIA de ``test_v107_imovel7_regressao`` (mesma estrutura, nenhum dado real). Nenhuma chamada externa.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app import models, modality_rules
from backend.app.checklist import STATUS_INCONCLUSIVO, master_items, standard_status
from backend.app.config import settings
from backend.app.verdict_engine import (FATOR_IMPEDIMENTO, FATOR_INFORMACAO, FATOR_NAO_APLICAVEL, FATOR_PREMISSA, FATOR_RISCO_CONFIANCA,
                                        FATORES_ORDEM, VerdictEngine, consolidate_factors)
from tests.mercado_imovel7_dados import COMPARAVEIS_ALUGUEL, COMPARAVEIS_VENDA, IMOVEL7, PREMISSAS_IMOVEL7
from tests.test_v107_imovel7_regressao import MATRICULA_FICTICIA

VD = "VENDA_DIRETA"
A, C, NA = modality_rules.APPLICABILITY_APLICAVEL, modality_rules.APPLICABILITY_CONDICIONAL, modality_rules.APPLICABILITY_NAO_APLICAVEL

# Tabela esperada dos 27 itens em VENDA_DIRETA (ordem do catálogo), com o motivo de cada decisão.
TABELA_VENDA_DIRETA = {
    "INTIMACAO_PESSOAL": C,            # 01 validade da execução de origem (pode ser questionada pelo ex-devedor)
    "INTIMACAO_EDITAL": C,             # 02 idem
    "NOTIFICACAO_DOIS_LEILOES": C,     # 03 idem
    "QUITACAO_80": C,                  # 04 idem
    "GARANTIA_DIVIDA_TERCEIRO": C,     # 05 idem
    "LANCE_MENOR_50_AVALIACAO": NA,    # 06 não há lance nem 2º leilão
    "ACAO_QUESTIONAMENTO": A,          # 07 ação judicial contra a execução/vendedor
    "LEILOES_NEGATIVOS_AVERBADOS": C,  # 08 situação registral quando o título vem de consolidação
    "CONSOLIDACAO_REGISTRADA": A,      # 09 situação registral (não etapa de leilão)
    "PENHORA_INDISPONIBILIDADE": A,    # 10 ônus atual na matrícula
    "TERCEIRO_OCUPANTE": A,            # 11 ocupação
    "LOCACAO_REGISTRADA": A,           # 12 ocupação
    "EDITAL_LIDO": NA,                 # 13 sem edital (volta a ser aplicável se um edital for anexado)
    "EVICCAO": A,                      # 14 condições da venda
    "RESPONSABILIDADE_DEBITOS": A,     # 15 condições oficiais da venda, mesmo sem edital
    "VAGA_MATRICULA": A, "ILIQUIDEZ": A, "CONDOMINIO_ALTO": A, "COMPARAVEIS_SUFFICIENTES": A, "REGIAO_SERVICOS": A,
    "REFORMA_GRANDE": A, "RETORNO_SELIC": A, "PRAZO_DOIS_ANOS": A, "DISTANCIA_USUARIO": A, "REFORMA_LIQUIDEZ": A,
    "CONDOMINIO_PORTARIA": A, "ETICA_OCUPACAO": A,   # 16-27
}


# =============================================================== regra por item (pura)

def test_tabela_dos_27_itens_em_venda_direta():
    catalogo = {item["canonical_key"] for item in master_items()}
    assert catalogo == set(TABELA_VENDA_DIRETA) and len(catalogo) == 27
    assert set(modality_rules.ITEM_PURPOSE) == catalogo                  # todo item tem finalidade e ação
    for chave, esperado in TABELA_VENDA_DIRETA.items():
        assert modality_rules.checklist_applicability(VD, chave) == esperado, chave


def test_extrajudicial_e_indefinido_nao_mudam():
    for chave in TABELA_VENDA_DIRETA:
        assert modality_rules.checklist_applicability("INDEFINIDO", chave) == A
        extra = modality_rules.checklist_applicability("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", chave)
        assert extra == (C if chave == "LANCE_MENOR_50_AVALIACAO" else A), chave
    # judicial preservado (itens do rito fiduciário seguem fora)
    assert modality_rules.checklist_applicability("JUDICIAL", "CONSOLIDACAO_REGISTRADA") == NA


def test_toda_excecao_de_venda_direta_tem_justificativa_e_regra_versionada():
    assert modality_rules.MODALITY_RULESET_VERSION == "modality-v2"
    for chave in TABELA_VENDA_DIRETA:
        regra = modality_rules.item_rule(VD, chave)
        assert regra["regra"] == f"modality-v2:{VD}:{chave}" and regra["grupo"] and regra["acao"]
        if regra["aplicabilidade"] != A or chave in ("CONSOLIDACAO_REGISTRADA", "PENHORA_INDISPONIBILIDADE", "RESPONSABILIDADE_DEBITOS", "EVICCAO"):
            assert len(regra["justificativa"]) > 40, chave
    assert modality_rules.item_rule("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", "EDITAL_LIDO")["justificativa"] == ""


# =============================================================== PostgreSQL: execução do checklist

@pytest.fixture(autouse=True)
def _sem_chave(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _prop(db, modality=VD, titulo="Venda direta v2 (fictício)"):
    prop = models.Property(title=titulo, address="Rua Fictícia, 999", city="Cidade Fictícia", state="PR", modality=modality,
                           area_m2=Decimal("55.90"), private_area_m2=Decimal("52.30"), bedrooms=2)
    db.add(prop); db.flush()
    return prop


def _doc(db, prop, texto, nome, tipo):
    from backend.app.documents.pipeline import DocumentPipeline
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    return DocumentPipeline(db).ingest(doc, texto.encode(), nome)


def _por_chave(execution):
    return {r.item.canonical_key: r for r in execution.results}


def _registro(db, prop, textos):
    """Ingere a matrícula, cria análise e execução e roda a leitura determinística da cadeia registral."""
    from backend.app.registry_chain import registry_for_property
    from backend.app.services import create_analysis, create_execution, persist_registry_findings
    _doc(db, prop, "\n".join(textos), "matricula.txt", "MATRICULA")
    analysis = create_analysis(db, prop, "teste", ["juridico"], [], "teste", [])
    execution = create_execution(db, prop, "TESTE", analysis.version)
    ids = persist_registry_findings(db, prop, analysis, registry_for_property(db, prop.id), execution)
    return execution, ids


def _evidencias(db, result):
    links = db.query(models.ChecklistEvidence).filter(models.ChecklistEvidence.checklist_result_id == result.id).all()
    return [db.get(models.Evidence, link.evidence_id) for link in links]


def test_execucao_preserva_status_justificativa_e_regra_de_cada_item(db):
    from backend.app.services import create_execution
    itens = _por_chave(create_execution(db, _prop(db), "TESTE", 1))
    for chave, esperado in TABELA_VENDA_DIRETA.items():
        r = itens[chave]
        if esperado == NA:
            assert (r.applicable, r.state, r.resolution_origin) == (False, "NAO_APLICAVEL", "REGRA_MODALIDADE"), chave
            assert "modality-v2" in r.answer and len(r.answer) > 60 and f"modality-v2:{VD}:{chave}" in r.interpretation
        else:
            # CONDICIONAL e APLICÁVEL continuam pendentes: nada vira resposta por regra de modalidade
            assert (r.applicable, r.state) == (True, "PENDENTE"), chave
            assert r.answer == ""
    for chave in ("INTIMACAO_PESSOAL", "LEILOES_NEGATIVOS_AVERBADOS"):
        assert itens[chave].interpretation.startswith(f"Aplicável sob condição (modality-v2:{VD}:{chave})")
    assert itens["CONSOLIDACAO_REGISTRADA"].interpretation.startswith("Aplicável (modality-v2:")


def test_edital_anexado_torna_edital_lido_aplicavel_na_venda_direta(db):
    from backend.app.services import create_execution
    prop = _prop(db)
    _doc(db, prop, "EDITAL FICTÍCIO DE VENDA. Condições gerais da venda.", "edital.txt", "EDITAL")
    edital = _por_chave(create_execution(db, prop, "TESTE", 1))["EDITAL_LIDO"]
    assert (edital.applicable, edital.state) == (True, "PENDENTE") and "edital anexado" in edital.interpretation


def test_item09_confirmado_pela_matricula_com_alienacao_e_consolidacao(db):
    prop = _prop(db)
    execution, ids = _registro(db, prop, MATRICULA_FICTICIA)
    item = _por_chave(execution)["CONSOLIDACAO_REGISTRADA"]
    assert item.state == "CONFIRMADO" and item.applicable and item.resolution_origin == "REGRA_DETERMINISTICA"
    assert "R-3" in item.answer and "Av-5" in item.answer and "BANCO FICTÍCIO S.A" in item.answer
    assert "não equivale a baixa" in item.interpretation
    evs = _evidencias(db, item)
    assert len(evs) >= 2 and {e.id for e in evs} <= set(ids)
    assert all(e.chunk_id is not None and e.source_excerpt for e in evs)                 # trecho da matrícula
    textos = " ".join(e.fact for e in evs)
    assert "Alienação fiduciária registrada (R-3)" in textos and "Av-5" in textos
    # v1.0.11 (evidencias-v1): matrícula lida em sequência contínua (Av-1 a Av-5) sem penhora → "sem restrição identificada",
    # com o limite da conclusão explícito; nunca "inexistência" e nunca CONFIRMADO.
    penhora = _por_chave(execution)["PENHORA_INDISPONIBILIDADE"]
    assert penhora.state == "NAO_IDENTIFICADO" and "não é garantia de inexistência" in penhora.interpretation


def test_item09_so_com_alienacao_fica_inconclusivo(db):
    so_af = ["PROPRIETÁRIO: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
             "R-2 - Matrícula nº 1 - ALIENAÇÃO FIDUCIÁRIA. O devedor alienou fiduciariamente o imóvel em favor do BANCO EXEMPLO S.A., para garantia.\n"]
    execution, _ = _registro(db, _prop(db), so_af)
    item = _por_chave(execution)["CONSOLIDACAO_REGISTRADA"]
    assert item.state == "EM_ANALISE" and item.confidence == "BAIXA" and item.answer == ""
    assert item.interpretation.startswith("INCONCLUSIVO") and standard_status(item.state, item.applicable) == STATUS_INCONCLUSIVO
    assert _evidencias(db, item)


def test_item10_penhora_na_matricula_e_risco_identificado(db):
    penhora = ["PROPRIETÁRIO: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
               "R-2 - Matrícula nº 1 - COMPRA E VENDA. A construtora vendeu o imóvel a COMPRADOR TESTE FICTÍCIO pelo preço de R$ 1,00.\n",
               "Av-3 - Matrícula nº 1 - PENHORA. Penhora do imóvel nos autos de execução fiscal fictícia.\n"]
    execution, _ = _registro(db, _prop(db), penhora)
    item = _por_chave(execution)["PENHORA_INDISPONIBILIDADE"]
    assert item.state == "RISCO_IDENTIFICADO" and "penhora" in item.answer.lower() and _evidencias(db, item)


def test_item15_sem_edital_usa_condicoes_da_venda_e_fica_inconclusivo(db):
    from backend.app.services import create_execution, resolve_checklist_from_data
    prop = _prop(db)
    db.add(models.Auction(property_id=prop.id, auction_stage="Venda direta", financial_assumptions=PREMISSAS_IMOVEL7)); db.flush()
    db.expire(prop, ["auctions"])
    execution = create_execution(db, prop, "TESTE", 1)
    assert "RESPONSABILIDADE_DEBITOS" in resolve_checklist_from_data(db, prop, execution)
    item = _por_chave(execution)["RESPONSABILIDADE_DEBITOS"]
    assert item.state == "EM_ANALISE" and standard_status(item.state, item.applicable) == STATUS_INCONCLUSIVO   # nunca CONFIRMADO sem documento
    assert "10% da avaliação" in item.interpretation and "anúncio do imóvel" in item.interpretation and "Anexar o edital ou as condições" in item.interpretation


def test_item15_sem_condicoes_informadas_continua_pendente(db):
    from backend.app.services import create_execution, resolve_checklist_from_data
    prop = _prop(db)
    db.add(models.Auction(property_id=prop.id, auction_stage="Venda direta", financial_assumptions={"itbi_aliquota": "0.025"})); db.flush()
    db.expire(prop, ["auctions"])
    execution = create_execution(db, prop, "TESTE", 1)
    resolve_checklist_from_data(db, prop, execution)
    assert _por_chave(execution)["RESPONSABILIDADE_DEBITOS"].state == "PENDENTE"


# =============================================================== veredito: fatores (puro)

def _item(chave, estado="PENDENTE", aplicavel=True, interpretacao=None, resposta=""):
    return SimpleNamespace(item=SimpleNamespace(canonical_key=chave, question=f"Pergunta {chave}", category="JURIDICO"), state=estado,
                           applicable=aplicavel, interpretation=interpretacao, answer=resposta, id=None)


def test_fatores_separam_os_cinco_grupos_com_acao():
    resultados = [_item("PENHORA_INDISPONIBILIDADE", "RISCO_IDENTIFICADO", resposta="Sim. Consta na matrícula: penhora (Av-3)."),
                  _item("RESPONSABILIDADE_DEBITOS", "EM_ANALISE", interpretacao="INCONCLUSIVO: condições da venda informadas"),
                  _item("RETORNO_SELIC"), _item("INTIMACAO_PESSOAL", interpretacao="Aplicável sob condição"),
                  _item("EDITAL_LIDO", "NAO_APLICAVEL", aplicavel=False, resposta="Não aplicável à modalidade VENDA_DIRETA")]
    risco = SimpleNamespace(severity="ALTA", description="[CHECKLIST_PENHORA_INDISPONIBILIDADE_RISCO_IDENTIFICADO] penhora", status="ATIVO",
                            origin="RiskEngine:ChecklistResult:CHECKLIST_PENHORA_INDISPONIBILIDADE_RISCO_IDENTIFICADO")
    fat = consolidate_factors([risco], resultados, {"faltantes": ["Meta financeira não configurada."]}, ["Custo de reforma não informado."])
    g = fat["grupos"]
    assert tuple(g) == FATORES_ORDEM and set(fat["titulos"]) == set(FATORES_ORDEM)
    [impedimento] = g[FATOR_IMPEDIMENTO]                                   # risco + item do checklist: um fator só
    assert impedimento["chave"] == "PENHORA_INDISPONIBILIDADE" and impedimento["gravidade"] == "ALTA" and "Av-3" in impedimento["justificativa"]
    assert [f["chave"] for f in g[FATOR_INFORMACAO] if f["origem"] == "CHECKLIST"] == ["RESPONSABILIDADE_DEBITOS"]
    assert any(f["descricao"] == "Custo de reforma não informado." for f in g[FATOR_INFORMACAO])
    assert [f.get("chave") for f in g[FATOR_PREMISSA]] == ["RETORNO_SELIC", None]
    assert [f["chave"] for f in g[FATOR_RISCO_CONFIANCA]] == ["INTIMACAO_PESSOAL"]
    assert [f["chave"] for f in g[FATOR_NAO_APLICAVEL]] == ["EDITAL_LIDO"] and g[FATOR_NAO_APLICAVEL][0]["acao"] is None
    for grupo in (FATOR_IMPEDIMENTO, FATOR_INFORMACAO, FATOR_PREMISSA, FATOR_RISCO_CONFIANCA):
        assert all(f["acao"] for f in g[grupo]), grupo
    assert fat["contagem"] == {k: len(v) for k, v in g.items()}


def test_fatores_nao_perdem_pendencia_e_nao_mudam_a_decisao():
    resultados = [_item(k) for k in TABELA_VENDA_DIRETA if TABELA_VENDA_DIRETA[k] != NA] + \
                 [_item(k, "NAO_APLICAVEL", aplicavel=False) for k in TABELA_VENDA_DIRETA if TABELA_VENDA_DIRETA[k] == NA]
    decisao = VerdictEngine().evaluate(1, 3, checklist_results=resultados, evidence_ids=[1], financial={"pendencias": ["Valor de venda não informado."]})
    assert decisao.overall == "INCONCLUSIVO"
    g = decisao.financial["decisao"]["fatores"]["grupos"]
    chaves_pendentes = {f["chave"] for grupo in (FATOR_IMPEDIMENTO, FATOR_INFORMACAO, FATOR_PREMISSA, FATOR_RISCO_CONFIANCA) for f in g[grupo] if f.get("chave")}
    assert chaves_pendentes == {k for k, v in TABELA_VENDA_DIRETA.items() if v != NA}        # 25 itens, nenhum perdido
    assert {f["chave"] for f in g[FATOR_NAO_APLICAVEL]} == {"LANCE_MENOR_50_AVALIACAO", "EDITAL_LIDO"}
    total_checklist = sum(1 for grupo in FATORES_ORDEM if grupo != FATOR_NAO_APLICAVEL for f in g[grupo] if f["origem"] == "CHECKLIST")
    assert total_checklist == len([p for p in decisao.pending_items if p.startswith("Pergunta ")])
    assert any(f["descricao"] == "Valor de venda não informado." for f in g[FATOR_PREMISSA])           # premissa do investidor


# =============================================================== premissas: alias do IR (puro)

def test_tributo_da_tela_e_a_premissa_de_ir_do_motor_de_viabilidade():
    from backend.app.viability import ORIGEM_PADRAO, resolve_premises
    ganho = resolve_premises(None, {"tributo_pct": "0.22", "tax_base": "GANHO"})["venda.tributo_ganho_pct"]
    assert ganho["valor"] == Decimal("0.22") and ganho["origem"] == "premissa do imóvel"
    sobre_venda = resolve_premises(None, {"tributo_pct": "0.05", "tax_base": "VENDA"})["venda.tributo_ganho_pct"]
    assert sobre_venda["valor"] == Decimal("0.15") and sobre_venda["origem"] == ORIGEM_PADRAO   # outro significado: não reaproveita
    assert resolve_premises(None, {})["venda.tributo_ganho_pct"]["origem"] == ORIGEM_PADRAO


# =============================================================== HTTP: mercado → premissas → recálculo → veredito → versões

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


def _json(valor):
    return str(valor) if isinstance(valor, Decimal) else (valor.isoformat() if hasattr(valor, "isoformat") else valor)


def _imovel7_api(client):
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    assert client.post(f"/api/imoveis/{pid}/leilao", json={"auction_stage": "Venda direta", "appraisal_value": "220000", "bid_value": "132970.97",
                                                           "commission_percent": "0"}).status_code < 300
    for c in COMPARAVEIS_VENDA + COMPARAVEIS_ALUGUEL:
        r = client.post(f"/api/imoveis/{pid}/comparaveis", json={k: _json(v) for k, v in c.items() if v is not None})
        assert r.status_code == 200, r.text
    r = client.post(f"/api/imoveis/{pid}/documentos", files={"file": ("matricula.txt", "\n".join(MATRICULA_FICTICIA).encode(), "text/plain")},
                    data={"document_type": "MATRICULA"})
    assert r.status_code < 300, r.text
    return pid


def test_api_sem_premissas_mercado_sugere_mas_nada_e_gravado_nem_inventado(api):
    client, _ = api
    pid = _imovel7_api(client)
    intel = client.get(f"/api/imoveis/{pid}/inteligencia-mercado").json()
    assert intel["valores"]["valor_mercado_estimado"] is not None and intel["venda"]["quantidade_usada"] == 13   # base da sugestão
    for chave in ("venda.corretagem_pct", "venda.tributo_ganho_pct", "venda.prazo_meses"):
        assert intel["premissas"][chave]["origem"]                                                  # sugestão sempre com origem
    carregamento = intel["carregamento_mensal"]                                                     # dos comparáveis, com origem
    assert carregamento["valor"] is not None and carregamento["origem"].startswith("mediana do condomínio de")
    premissas = client.get(f"/api/imoveis/{pid}/financeiro/premissas").json()["premissas"] or {}
    assert premissas.get("valor_venda_estimado") is None and premissas.get("goal_kind") is None     # nada aplicado sozinho


def test_api_premissas_do_usuario_preservadas_recalculo_veredito_e_versoes(api):
    client, session = api
    pid = _imovel7_api(client)
    # o usuário informa venda e corretagem próprias; as premissas v1.0.8 (ITBI, condições Caixa) vão no mesmo objeto
    usuario = {**PREMISSAS_IMOVEL7, "valor_venda_estimado": "200000", "corretagem_pct": "0.05", "tax_base": "GANHO"}
    r = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json=usuario)
    assert r.status_code == 200, r.text
    salvas = r.json()["premissas"]
    assert salvas["condicoes_caixa"]["origem"] == "condições da venda direta Caixa (anúncio do imóvel)"   # origem não é mais descartada
    assert salvas["valor_venda_estimado"] == "200000" and salvas["itbi_aliquota"] == "0.025"
    intel = client.get(f"/api/imoveis/{pid}/inteligencia-mercado").json()
    assert Decimal(str(intel["premissas"]["venda.corretagem_pct"]["valor"])) == Decimal("0.05")
    assert intel["premissas"]["venda.corretagem_pct"]["origem"] == "premissa do imóvel"                 # valor do usuário prevalece

    v1 = client.post(f"/api/imoveis/{pid}/analisar", json={}).json()
    assert v1["versao"] == 1
    fatores = v1["financeiro"]["decisao"]["fatores"]["grupos"]
    assert {f["chave"] for f in fatores[FATOR_NAO_APLICAVEL]} == {"LANCE_MENOR_50_AVALIACAO", "EDITAL_LIDO"}
    pendentes_fatores = {f["chave"] for g in (FATOR_IMPEDIMENTO, FATOR_INFORMACAO, FATOR_PREMISSA, FATOR_RISCO_CONFIANCA) for f in fatores[g] if f.get("chave")}
    detalhe = client.get(f"/api/imoveis/{pid}").json()
    itens = {i["canonical_key"]: i for i in detalhe["checklist"]}
    assert itens["CONSOLIDACAO_REGISTRADA"]["state"] == "CONFIRMADO"                                   # item 09 pela matrícula
    assert itens["RESPONSABILIDADE_DEBITOS"]["status_padrao"] == "INCONCLUSIVO"                        # item 15 pelas condições
    abertos = {k for k, i in itens.items() if i["applicable"] and i["state"] in ("PENDENTE", "EM_ANALISE")}
    assert abertos <= pendentes_fatores and "CONSOLIDACAO_REGISTRADA" not in pendentes_fatores        # nenhuma pendência some
    assert "INTIMACAO_PESSOAL" in {f["chave"] for f in fatores[FATOR_RISCO_CONFIANCA]}
    assert any("meta" in f["descricao"].lower() for f in fatores[FATOR_PREMISSA])                       # sem meta: pendência explícita

    # o usuário define a meta: o PUT recalcula na hora e a nova análise usa a meta
    r = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={**salvas, "goal_kind": "ROI_MINIMO", "goal_value": "0.20"})
    assert r.status_code == 200 and r.json()["premissas"]["condicoes_caixa"]["tributos_limite_pct_avaliacao"] == "0.10"
    v2 = client.post(f"/api/imoveis/{pid}/analisar", json={}).json()
    assert v2["versao"] == 2
    premissas_v2 = v2["financeiro"]["decisao"]["fatores"]["grupos"][FATOR_PREMISSA]
    assert not any("meta" in f["descricao"].lower() for f in premissas_v2)
    vereditos = session.query(models.Verdict).filter(models.Verdict.property_id == pid).order_by(models.Verdict.analysis_version).all()
    assert [v.analysis_version for v in vereditos] == [1, 2]                                           # versão anterior preservada
    assert any("meta" in f["descricao"].lower() for f in vereditos[0].financial["decisao"]["fatores"]["grupos"][FATOR_PREMISSA])
