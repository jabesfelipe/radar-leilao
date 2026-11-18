"""Checklist Mestre por evidências (regra evidencias-v1, v1.0.11).

Fluxo testado: DOCUMENTO → EXTRAÇÃO (cadeia registral / condições da venda) → EVIDÊNCIA → REGRA → CHECKLIST → VEREDITO.

Todos os documentos são SINTÉTICOS: a matrícula é a fictícia de ``test_v107_imovel7_regressao`` (mesma estrutura do caso
de referência: R-3 alienação fiduciária, Av-5 consolidação, OCR imperfeito) e as condições da venda foram redigidas para o
teste, com as duas formas de limite conhecidas (pagamento do excedente e assunção integral acima do limite). Nenhum dado
pessoal, nenhuma chamada externa, nenhuma IA.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app import models
from backend.app.checklist import (RESULTADO_CONFIRMADO, RESULTADO_INCONCLUSIVO, RESULTADO_NAO_APLICAVEL, RESULTADO_PENDENTE, RESULTADO_RISCO,
                                   RESULTADO_SEM_RESTRICAO, TIPO_CALCULO, TIPO_FATO_DOCUMENTAL, TIPO_NAO_LOCALIZADA, TIPO_REGRA_VENDA, TIPO_USUARIO,
                                   checklist_outcome, evidence_type)
from backend.app.sale_conditions import (EVICCAO_EXCLUIDA, EVICCAO_LIMITADA, EVICCAO_RESPONDE, FGTS_ACEITA, REGRA_AMBIGUA, REGRA_EXCEDENTE,
                                         REGRA_INTEGRAL_ACIMA, TEMA_CONDOMINIO, TEMA_EVICCAO, TEMA_FGTS, TEMA_TRIBUTOS, normalize_doc_type, read_conditions)
from backend.app.verdict_engine import FATOR_IMPEDIMENTO, FATOR_NAO_APLICAVEL
from tests.mercado_imovel7_dados import COMPARAVEIS_ALUGUEL, COMPARAVEIS_VENDA
from tests.test_v107_imovel7_regressao import MATRICULA_FICTICIA
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures: sem chave de IA; cliente HTTP)

VD = "VENDA_DIRETA"

CONDICOES_FICTICIAS = (
    "CONDIÇÕES DA VENDA DIRETA — DOCUMENTO FICTÍCIO PARA TESTE\n"
    "Imóvel: apartamento fictício nº 01.\n\n"
    "Condomínio: sob responsabilidade do comprador, até o limite de 10% do valor de avaliação do imóvel. A CAIXA realizará o pagamento "
    "apenas do valor que exceder o limite de 10% do valor de avaliação.\n\n"
    "IPTU e demais tributos: sob responsabilidade do comprador quando o débito for inferior a 10% do valor de avaliação. Caso o débito "
    "ultrapasse esse limite, a CAIXA assumirá integralmente o pagamento.\n\n"
    "Evicção: a vendedora responde pela evicção de direito, limitada à restituição do valor pago pelo comprador.\n\n"
    "FGTS: é permitida a utilização do FGTS, observadas as regras aplicáveis.\n\n"
    "Formas de pagamento: à vista ou com financiamento habitacional.\n"
)

# Matrícula sintética SEM restrições, com sequência contínua de atos (R-1 a Av-4) e consolidação.
MATRICULA_LIMPA = [
    "Registro de Imóveis Fictício\nMatrícula nº 1.111\nIMÓVEL: apartamento nº 02 do Edifício Exemplo.\n"
    "PROPRIETÁRIA: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
    "R-1 - Matrícula nº 1.111 - COMPRA E VENDA. A CONSTRUTORA EXEMPLO LTDA vendeu o imóvel a COMPRADOR TESTE pelo preço de R$ 1,00.\n"
    "R-2 - Matrícula nº 1.111 - ALIENAÇÃO FIDUCIÁRIA. Consoante contrato de compra e venda e mútuo, o devedor alienou fiduciariamente o "
    "imóvel em favor do BANCO EXEMPLO S.A., para garantia da dívida no valor de R$ 2,00.\n",
    "Av-3 - Matrícula nº 1.111 - CONSOLIDAÇÃO DE PROPRIEDADE. Fica consolidada a propriedade em nome do BANCO EXEMPLO S.A., "
    "após intimação do devedor, que não purgou a mora.\n"
    "Av-4 - Matrícula nº 1.111 - LEILÕES NEGATIVOS. Averba-se que o primeiro e o segundo leilão foram negativos, sem licitantes.\n",
]


# =============================================================== helpers

def _prop(db, modality=VD, parking=1):
    prop = models.Property(title="Venda direta (fictício)", address="Rua Fictícia, 1", city="Cidade Fictícia", state="PR", modality=modality,
                           area_m2=Decimal("55.90"), private_area_m2=Decimal("52.30"), bedrooms=2, parking_spots=parking)
    db.add(prop); db.flush()
    return prop


def _doc(db, prop, texto, nome, tipo):
    from backend.app.documents.pipeline import DocumentPipeline
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    return DocumentPipeline(db).ingest(doc, texto.encode(), nome)


def _leilao(db, prop, assumptions=None):
    db.add(models.Auction(property_id=prop.id, auction_stage="Venda direta", appraisal_value=Decimal("220000"), bid_value=Decimal("132970.97"),
                          financial_assumptions=assumptions or {}))
    db.flush()


def _analisar(db, prop):
    """Mesmo encadeamento de ``POST /analisar``, sem os agentes de IA (que não rodam sem chave)."""
    from backend.app.checklist_evidence import resolve_checklist_evidence
    from backend.app.registry_chain import registry_for_property
    from backend.app.services import (create_analysis, create_execution, create_verdict, persist_registry_findings, recalculate_risks,
                                      resolve_checklist_from_data)
    db.expire(prop)
    analysis = create_analysis(db, prop, "teste", ["juridico", "checklist"], [], "teste", [])
    execution = create_execution(db, prop, "TESTE", analysis.version)
    registry = registry_for_property(db, prop.id)
    persist_registry_findings(db, prop, analysis, registry, execution)
    resolve_checklist_from_data(db, prop, execution)
    resolve_checklist_evidence(db, prop, analysis, execution, registry)
    recalculate_risks(db, prop, analysis.version)
    verdict = create_verdict(db, prop, analysis, None)
    db.flush()
    return execution, verdict


def _itens(execution):
    return {r.item.canonical_key: r for r in execution.results}


def _evs(db, result):
    links = db.query(models.ChecklistEvidence).filter(models.ChecklistEvidence.checklist_result_id == result.id).all()
    return [db.get(models.Evidence, link.evidence_id) for link in links]


def _tipos(db, result):
    return {evidence_type(e.origin, e.category, e.document_version_id is not None) for e in _evs(db, result)}


def _resultado(r):
    return checklist_outcome(r.state, r.applicable)


# =============================================================== parser das condições da venda (puro)

def _cond(texto):
    return read_conditions([{"chunk_id": 1, "content": texto, "page": 1, "section": None}], 10)


def test_condicoes_regras_de_condominio_iptu_eviccao_e_fgts():
    cond = _cond(CONDICOES_FICTICIAS)
    condo, iptu, evic, fgts = (cond.first(t) for t in (TEMA_CONDOMINIO, TEMA_TRIBUTOS, TEMA_EVICCAO, TEMA_FGTS))
    assert (condo.regra, condo.limite_pct, condo.comparador, condo.vendedor) == (REGRA_EXCEDENTE, Decimal("0.1000"), "ATE", "a Caixa")
    assert (iptu.regra, iptu.limite_pct, iptu.comparador) == (REGRA_INTEGRAL_ACIMA, Decimal("0.1000"), "ABAIXO_DE")
    assert evic.regra == EVICCAO_LIMITADA and fgts.regra == FGTS_ACEITA
    assert "exceder o limite de 10%" in condo.excerpt and "IPTU" not in condo.excerpt     # cada trecho é da sua cláusula
    assert condo.chunk_id == 1 and condo.page == 1


@pytest.mark.parametrize("texto,regra", [
    ("Condomínio: sob responsabilidade do comprador, até o limite de 10% do valor de avaliação.", REGRA_AMBIGUA),     # limite sem regra do excedente
    ("Condomínio: débitos por conta do comprador.", "COMPRADOR_INTEGRAL"),
    ("Condomínio: débitos sob responsabilidade da CAIXA.", "VENDEDOR_INTEGRAL"),
])
def test_condicoes_limite_sem_regra_do_excedente_e_ambiguo(texto, regra):
    assert _cond(texto).first(TEMA_CONDOMINIO).regra == regra


@pytest.mark.parametrize("texto,regra", [
    ("Evicção: a vendedora não se responsabiliza pela evicção.", EVICCAO_EXCLUIDA),
    ("O comprador renuncia à garantia da evicção.", EVICCAO_EXCLUIDA),
    ("Evicção: o vendedor responde pela evicção de direito.", EVICCAO_RESPONDE),
    ("Evicção: ver item 7.", REGRA_AMBIGUA),
])
def test_condicoes_eviccao(texto, regra):
    assert _cond(texto).first(TEMA_EVICCAO).regra == regra


def test_clausula_termina_no_proximo_item_mesmo_sem_linha_em_branco():
    edital = ("4. DÉBITOS: correrão por conta do ARREMATANTE todos os débitos de condomínio e de IPTU,\n"
              "inclusive os anteriores à data do leilão.\n"
              "5. PAGAMENTO: à vista. Não se admite parcelamento nem utilização de FGTS.\n"
              "6. COMISSÃO DO LEILOEIRO: 5% (cinco por cento) sobre o valor do arremate.\n")
    cond = _cond(edital)
    for tema in (TEMA_CONDOMINIO, TEMA_TRIBUTOS):
        clause = cond.first(tema)
        assert (clause.regra, clause.limite_pct) == ("COMPRADOR_INTEGRAL", None), tema     # o 5% da comissão não é limite
        assert "COMISSÃO" not in clause.excerpt.upper()
    assert cond.first(TEMA_FGTS).regra == "NAO_ACEITA"


@pytest.mark.parametrize("texto,regra", [
    ("PAGAMENTO: à vista. Não se admite parcelamento nem utilização de FGTS.", "NAO_ACEITA"),
    ("FGTS: não é aceito nesta venda.", "NAO_ACEITA"),
    ("É permitida a utilização do FGTS.", FGTS_ACEITA),
])
def test_condicoes_fgts(texto, regra):
    assert _cond(texto).first(TEMA_FGTS).regra == regra


def test_condicoes_sem_documento_ou_tipo_diferente_nao_inventa():
    assert _cond("Apartamento com 2 quartos no Condomínio Residencial Exemplo.").first(TEMA_CONDOMINIO) is None   # descrição ≠ cláusula
    assert normalize_doc_type("Condições da venda") == "CONDICOES_VENDA" and normalize_doc_type("CONDICOES_VENDA") == "CONDICOES_VENDA"
    assert normalize_doc_type("MATRICULA") is None and normalize_doc_type("EDITAL") == "EDITAL"


# =============================================================== 1, 2. alienação fiduciária e consolidação (imóvel 7 sintético)

def test_matricula_com_af_e_consolidacao_alimenta_os_itens_registrais(db):
    prop = _prop(db)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    assert itens["CONSOLIDACAO_REGISTRADA"].state == "CONFIRMADO"                                         # 09 (preservado)
    # 01/02: a consolidação (Av-5) cita a certidão "pós edital": intimação por edital comprovada; a pessoal não
    assert itens["INTIMACAO_EDITAL"].state == "CONFIRMADO" and "Av-5" in itens["INTIMACAO_EDITAL"].answer
    assert "art. 26, § 4º" in itens["INTIMACAO_EDITAL"].interpretation
    assert itens["INTIMACAO_PESSOAL"].state == "EM_ANALISE" and itens["INTIMACAO_PESSOAL"].interpretation.startswith("INCONCLUSIVO")
    # 05: garantia do financiamento da própria aquisição (R-3 no contrato de compra e venda com mútuo)
    assert itens["GARANTIA_DIVIDA_TERCEIRO"].state == "NAO_IDENTIFICADO" and "R-3" in itens["GARANTIA_DIVIDA_TERCEIRO"].answer
    # 04: segue pendente, com a dívida registrada e o documento que falta
    q80 = itens["QUITACAO_80"]
    assert q80.state == "PENDENTE" and "R$ 99.999,99" in q80.interpretation and "extrato" in q80.interpretation
    for key in ("INTIMACAO_EDITAL", "GARANTIA_DIVIDA_TERCEIRO"):
        assert TIPO_FATO_DOCUMENTAL in _tipos(db, itens[key]), key


def test_itens_01_a_05_tem_justificativas_proprias(db):
    prop = _prop(db)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    textos = [(itens[k].answer or "") + (itens[k].interpretation or "") for k in
              ("INTIMACAO_PESSOAL", "INTIMACAO_EDITAL", "NOTIFICACAO_DOIS_LEILOES", "QUITACAO_80", "GARANTIA_DIVIDA_TERCEIRO")]
    assert len(set(textos)) == 5 and all(len(t) > 80 for t in textos)
    assert "art. 27, § 2º-A" in itens["NOTIFICACAO_DOIS_LEILOES"].interpretation
    # nenhum deles vira risco só por falta de prova
    assert not any(itens[k].state == "RISCO_IDENTIFICADO" for k in ("INTIMACAO_PESSOAL", "NOTIFICACAO_DOIS_LEILOES", "QUITACAO_80"))


# =============================================================== 3 a 6. penhora, indisponibilidade, sem restrição, ambíguo

@pytest.mark.parametrize("ato", ["Av-3 - Matrícula nº 1 - PENHORA. Penhora do imóvel nos autos de execução fictícia.",
                                 "Av-3 - Matrícula nº 1 - INDISPONIBILIDADE. Averba-se a indisponibilidade de bens (ordem fictícia)."])
def test_penhora_ou_indisponibilidade_e_risco(db, ato):
    prop = _prop(db, modality="INDEFINIDO")
    _doc(db, prop, "PROPRIETÁRIO: CONSTRUTORA EXEMPLO LTDA.\nR-1 - Matrícula nº 1 - COMPRA E VENDA. vendeu a COMPRADOR TESTE.\n"
         "R-2 - Matrícula nº 1 - registro fictício.\n" + ato + "\n", "m.txt", "MATRICULA")
    item = _itens(_analisar(db, prop)[0])["PENHORA_INDISPONIBILIDADE"]
    assert item.state == "RISCO_IDENTIFICADO" and "Av-3" in item.answer and TIPO_FATO_DOCUMENTAL in _tipos(db, item)


def test_matricula_sem_restricoes_lida_em_sequencia_e_sem_restricao_identificada(db):
    prop = _prop(db)
    _doc(db, prop, "\n".join(MATRICULA_LIMPA), "m.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    pen, loc = itens["PENHORA_INDISPONIBILIDADE"], itens["LOCACAO_REGISTRADA"]
    assert _resultado(pen) == RESULTADO_SEM_RESTRICAO and _resultado(loc) == RESULTADO_SEM_RESTRICAO
    assert "não é garantia de inexistência" in pen.interpretation and "certidão de ônus" in pen.interpretation
    [nao_localizada] = [e for e in _evs(db, pen) if e.origin == "NAO_LOCALIZADA"]
    assert nao_localizada.document_version_id is not None and nao_localizada.chunk_id is None and "R-1, R-2, Av-3, Av-4" in nao_localizada.fact
    assert _tipos(db, pen) == {TIPO_NAO_LOCALIZADA}
    assert itens["LEILOES_NEGATIVOS_AVERBADOS"].state == "CONFIRMADO" and "Av-4" in itens["LEILOES_NEGATIVOS_AVERBADOS"].answer   # 7


def test_penhora_com_cancelamento_posterior_e_inconclusiva(db):
    prop = _prop(db, modality="INDEFINIDO")
    _doc(db, prop, "R-1 - Matrícula nº 1 - COMPRA E VENDA. vendeu a COMPRADOR TESTE.\nAv-2 - Matrícula nº 1 - PENHORA. Penhora fictícia.\n"
         "Av-3 - Matrícula nº 1 - CANCELAMENTO. Fica cancelada a penhora objeto da Av-2.\n", "m.txt", "MATRICULA")
    item = _itens(_analisar(db, prop)[0])["PENHORA_INDISPONIBILIDADE"]
    assert _resultado(item) == RESULTADO_INCONCLUSIVO and "cancelamento" in item.interpretation


def test_sequencia_de_atos_com_lacuna_nao_permite_afirmar_ausencia(db):
    prop = _prop(db, modality="INDEFINIDO")
    _doc(db, prop, "R-1 - Matrícula nº 1 - COMPRA E VENDA. vendeu a COMPRADOR TESTE.\nAv-4 - Matrícula nº 1 - averbação fictícia.\n", "m.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    assert _resultado(itens["PENHORA_INDISPONIBILIDADE"]) == RESULTADO_INCONCLUSIVO
    assert "lacunas" in itens["PENHORA_INDISPONIBILIDADE"].interpretation and "2, 3" in itens["PENHORA_INDISPONIBILIDADE"].interpretation
    assert itens["LOCACAO_REGISTRADA"].state == "PENDENTE"                                                 # sem leitura completa, sem "não"


# =============================================================== 7, 8. leilões negativos

def test_leilao_mencionado_sem_resultado_e_inconclusivo(db):
    prop = _prop(db)
    texto = "\n".join(MATRICULA_LIMPA).replace("LEILÕES NEGATIVOS. Averba-se que o primeiro e o segundo leilão foram negativos, sem licitantes.",
                                               "LEILÃO. Averba-se a realização do leilão.")
    _doc(db, prop, texto, "m.txt", "MATRICULA")
    item = _itens(_analisar(db, prop)[0])["LEILOES_NEGATIVOS_AVERBADOS"]
    assert _resultado(item) == RESULTADO_INCONCLUSIVO and "sem indicar o resultado" in item.interpretation


def test_sem_matricula_os_itens_registrais_ficam_pendentes_com_motivo(db):
    prop = _prop(db)
    itens = _itens(_analisar(db, prop)[0])
    for key in ("LEILOES_NEGATIVOS_AVERBADOS", "PENHORA_INDISPONIBILIDADE", "CONSOLIDACAO_REGISTRADA", "INTIMACAO_PESSOAL", "LOCACAO_REGISTRADA"):
        assert itens[key].state == "PENDENTE", key
        assert "matrícula não anexada" in itens[key].interpretation and "Fonte necessária" in itens[key].interpretation, key


# =============================================================== 9 a 15. venda direta, condições oficiais, condomínio, IPTU, evicção

def test_venda_direta_sem_edital_e_sem_condicoes_pede_o_documento_certo(db):
    prop = _prop(db)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    assert itens["EDITAL_LIDO"].state == "NAO_APLICAVEL"
    for key in ("EVICCAO", "RESPONSABILIDADE_DEBITOS"):
        assert itens[key].state == "PENDENTE" and "CONDICOES_VENDA" in itens[key].interpretation and "não há edital" in itens[key].interpretation


def test_venda_direta_com_condicoes_oficiais_responde_14_e_15_com_a_fonte(db):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    _doc(db, prop, CONDICOES_FICTICIAS, "condicoes.txt", "CONDICOES_VENDA")
    itens = _itens(_analisar(db, prop)[0])
    evic, deb = itens["EVICCAO"], itens["RESPONSABILIDADE_DEBITOS"]
    assert evic.state == "CONFIRMADO" and evic.answer.startswith("Sim, com limitação") and "condicoes.txt" in evic.interpretation
    assert deb.state == "CONFIRMADO"
    # condomínio: até 10%, a Caixa paga o excedente; IPTU: abaixo de 10%, acima a Caixa assume tudo; limite em reais pela avaliação
    assert "Condomínio: comprador responde até 10% do valor de avaliação; a Caixa paga só o que exceder" in deb.answer
    assert "IPTU/tributos: comprador responde se o débito ficar abaixo de 10%" in deb.answer and "assume o débito integralmente" in deb.answer
    assert "R$ 22.000,00" in deb.answer
    assert "Valores dos débitos não informados" in deb.answer                                              # regra ≠ valor da dívida
    for item in (evic, deb):
        evs = _evs(db, item)
        assert _tipos(db, item) == {TIPO_REGRA_VENDA} and all(e.chunk_id and e.source_excerpt for e in evs)
    assert any("exceder o limite de 10%" in e.source_excerpt for e in _evs(db, deb))                       # trecho original, não a conclusão


def test_debitos_cadastrados_aparecem_separados_da_regra(db):
    prop = _prop(db)
    _leilao(db, prop)
    db.add(models.Debt(property_id=prop.id, category="CONDOMINIO", creditor="Condomínio fictício", amount=Decimal("5000")))
    _doc(db, prop, CONDICOES_FICTICIAS, "condicoes.txt", "CONDICOES_VENDA")
    deb = _itens(_analisar(db, prop)[0])["RESPONSABILIDADE_DEBITOS"]
    assert deb.state == "CONFIRMADO" and "Débitos cadastrados: condomínio R$ 5.000,00" in deb.answer
    assert TIPO_USUARIO in _tipos(db, deb) and TIPO_REGRA_VENDA in _tipos(db, deb)


def test_condicoes_sem_eviccao_e_com_limite_ambiguo_ficam_inconclusivas(db):
    prop = _prop(db)
    _doc(db, prop, "Condomínio: sob responsabilidade do comprador, até o limite de 10% do valor de avaliação.\n\n"
         "IPTU: por conta do comprador.\n", "condicoes.txt", "Condições da venda")
    itens = _itens(_analisar(db, prop)[0])
    evic, deb = itens["EVICCAO"], itens["RESPONSABILIDADE_DEBITOS"]
    assert _resultado(evic) == RESULTADO_INCONCLUSIVO and "não trata de evicção" in evic.interpretation
    assert _tipos(db, evic) == {TIPO_NAO_LOCALIZADA}
    assert _resultado(deb) == RESULTADO_INCONCLUSIVO and "sem a regra do que acontece acima do limite" in deb.interpretation


def test_eviccao_excluida_e_risco(db):
    prop = _prop(db)
    _doc(db, prop, "Evicção: a vendedora não se responsabiliza pela evicção.\n", "condicoes.txt", "CONDICOES_VENDA")
    evic = _itens(_analisar(db, prop)[0])["EVICCAO"]
    assert evic.state == "RISCO_IDENTIFICADO" and "art. 448" in evic.interpretation


def test_premissas_sem_documento_nao_confirmam_o_item_15(db):
    from tests.mercado_imovel7_dados import PREMISSAS_IMOVEL7
    prop = _prop(db)
    _leilao(db, prop, PREMISSAS_IMOVEL7)
    deb = _itens(_analisar(db, prop)[0])["RESPONSABILIDADE_DEBITOS"]
    assert _resultado(deb) == RESULTADO_INCONCLUSIVO and deb.state == "EM_ANALISE"                           # regra v1.0.10 preservada


def test_pergunta_15_adequada_a_venda_direta_sem_mudar_o_catalogo(db):
    from backend.app import modality_rules
    from backend.app.checklist import CHECKLIST_MASTER
    original = dict((k, q) for k, q, _, _ in CHECKLIST_MASTER)["RESPONSABILIDADE_DEBITOS"]
    assert modality_rules.item_question(VD, "RESPONSABILIDADE_DEBITOS", original).startswith("Quais são as responsabilidades do comprador e do vendedor")
    assert modality_rules.item_question("INDEFINIDO", "RESPONSABILIDADE_DEBITOS", original) == original


# =============================================================== 16, 17. ocupação

def test_ocupacao_conhecida_responde_11_e_27(db):
    prop = _prop(db)
    db.add(models.OccupancyAnalysis(property_id=prop.id, status="DESOCUPADO")); db.flush()
    itens = _itens(_analisar(db, prop)[0])
    assert _resultado(itens["TERCEIRO_OCUPANTE"]) == RESULTADO_SEM_RESTRICAO and itens["TERCEIRO_OCUPANTE"].confidence == "BAIXA"
    assert _resultado(itens["ETICA_OCUPACAO"]) == RESULTADO_NAO_APLICAVEL and _tipos(db, itens["TERCEIRO_OCUPANTE"]) == {TIPO_USUARIO}

    prop2 = _prop(db)
    db.add(models.OccupancyAnalysis(property_id=prop2.id, status="OCUPADO", occupant_profile="família")); db.flush()
    itens2 = _itens(_analisar(db, prop2)[0])
    assert itens2["TERCEIRO_OCUPANTE"].state == "ATENCAO" and "família" in itens2["TERCEIRO_OCUPANTE"].answer
    assert itens2["ETICA_OCUPACAO"].state == "PENDENTE" and "ocupado" in itens2["ETICA_OCUPACAO"].interpretation


def test_ocupacao_desconhecida_fica_pendente_com_acao(db):
    prop = _prop(db)
    db.add(models.OccupancyAnalysis(property_id=prop.id, status="DESCONHECIDO")); db.flush()
    item = _itens(_analisar(db, prop)[0])["TERCEIRO_OCUPANTE"]
    assert item.state == "PENDENTE" and "vistoria" in item.interpretation


# =============================================================== 18. vaga

@pytest.mark.parametrize("descricao,estado,inicio", [
    ("Vaga de garagem nº 5, unidade autônoma com matrícula própria nº 2.222.", "CONFIRMADO", "Sim."),
    ("Vaga de garagem vinculada ao apartamento, de uso indeterminado.", "CONFIRMADO", "Não."),
])
def test_vaga_descrita_na_matricula(db, descricao, estado, inicio):
    prop = _prop(db)
    _doc(db, prop, MATRICULA_LIMPA[0] + descricao + "\n" + "".join(MATRICULA_LIMPA[1:]), "m.txt", "MATRICULA")
    item = _itens(_analisar(db, prop)[0])["VAGA_MATRICULA"]
    assert item.state == estado and item.answer.startswith(inicio) and TIPO_FATO_DOCUMENTAL in _tipos(db, item)


def test_vaga_nao_descrita_com_cadastro_de_vaga_e_inconclusiva(db):
    prop = _prop(db, parking=1)
    _doc(db, prop, "\n".join(MATRICULA_LIMPA), "m.txt", "MATRICULA")
    assert _resultado(_itens(_analisar(db, prop)[0])["VAGA_MATRICULA"]) == RESULTADO_INCONCLUSIVO


# =============================================================== 19, 20. mercado e financeiro

def _comparavel(db, prop, dados):
    db.add(models.MarketComparable(property_id=prop.id, **{k: v for k, v in dados.items() if v is not None}))


def test_inteligencia_de_mercado_e_premissas_alimentam_itens_pertinentes(db):
    prop = _prop(db)
    prop.property_type, prop.city, prop.neighborhood, prop.area_m2 = "Apartamento", "Fazenda Rio Grande", "Estados", Decimal("48.74")
    _leilao(db, prop, {"reforma": "20000"})
    for c in COMPARAVEIS_VENDA + COMPARAVEIS_ALUGUEL:
        _comparavel(db, prop, c)
    db.flush()
    itens = _itens(_analisar(db, prop)[0])
    liq = itens["ILIQUIDEZ"]
    assert _resultado(liq) in (RESULTADO_SEM_RESTRICAO, RESULTADO_RISCO) and "liquidez estimada" in liq.answer and _tipos(db, liq) == {TIPO_CALCULO}
    assert itens["CONDOMINIO_ALTO"].state == "PENDENTE" and "mediana do condomínio" in itens["CONDOMINIO_ALTO"].interpretation
    comp = itens["COMPARAVEIS_SUFFICIENTES"]                                                                  # 16 venda (2 excluídos), 2 aluguel
    assert comp.state == "PENDENTE" and "16 comparável(is) de venda e 2 de aluguel" in comp.interpretation
    reforma = itens["REFORMA_GRANDE"]                                                                          # 20.000 / 132.970,97 = 15%
    assert reforma.state == "ATENCAO" and "referência de análise: 10%" in reforma.answer and _tipos(db, reforma) == {TIPO_USUARIO}
    assert "não regra jurídica" in reforma.interpretation and "padrão do sistema" in reforma.interpretation      # natureza e origem explícitas
    assert "Selic de referência não está cadastrada" in itens["RETORNO_SELIC"].interpretation


def test_limite_de_grande_reforma_e_premissa_ajustavel_pelo_usuario(db):
    prop = _prop(db)
    _leilao(db, prop, {"reforma": "20000", "reforma_grande_pct": "0.20"})       # 15% da aquisição, abaixo do limite de 20% do usuário
    reforma = _itens(_analisar(db, prop)[0])["REFORMA_GRANDE"]
    assert reforma.state == "NAO_IDENTIFICADO" and "referência de análise: 20%" in reforma.answer
    assert "premissa do imóvel" in reforma.interpretation


def test_limite_de_grande_reforma_validado_na_api_de_premissas():
    from pydantic import ValidationError
    from backend.app.schemas import FinanceAssumptions
    assert FinanceAssumptions(reforma_grande_pct="0.15").reforma_grande_pct == Decimal("0.15")
    for invalido in ("0", "1.5", "-0.1"):
        with pytest.raises(ValidationError):
            FinanceAssumptions(reforma_grande_pct=invalido)


# =============================================================== 21 a 24. vínculo, histórico, ausência, modalidade x risco

def test_evidencia_vinculada_ao_item_correto(db):
    prop = _prop(db)
    _doc(db, prop, "\n".join(MATRICULA_LIMPA), "m.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    pen = {e.id for e in _evs(db, itens["PENHORA_INDISPONIBILIDADE"])}
    loc = {e.id for e in _evs(db, itens["LOCACAO_REGISTRADA"])}
    cons = {e.id for e in _evs(db, itens["CONSOLIDACAO_REGISTRADA"])}
    assert pen and loc and cons and not (pen & loc) and not (pen & cons)
    assert all("penhora" in db.get(models.Evidence, i).fact for i in pen)


def test_historico_preservado_entre_versoes(db):
    prop = _prop(db)
    primeira, _ = _analisar(db, prop)
    antes = {r.item.canonical_key: (r.state, r.answer, r.interpretation) for r in primeira.results}
    _doc(db, prop, "\n".join(MATRICULA_LIMPA), "m.txt", "MATRICULA")
    segunda, _ = _analisar(db, prop)
    db.refresh(primeira)
    assert {r.item.canonical_key: (r.state, r.answer, r.interpretation) for r in primeira.results} == antes   # v1 intacta
    assert segunda.id != primeira.id and _itens(segunda)["PENHORA_INDISPONIBILIDADE"].state == "NAO_IDENTIFICADO"
    assert _itens(primeira)["PENHORA_INDISPONIBILIDADE"].state == "PENDENTE"


def test_ausencia_de_evidencia_nao_gera_confirmacao(db):
    prop = _prop(db, modality="INDEFINIDO", parking=None)
    itens = _itens(_analisar(db, prop)[0])
    juridicos = [r for r in itens.values() if r.item.category in ("JURIDICO", "DOCUMENTAL")]
    assert juridicos and all(_resultado(r) == RESULTADO_PENDENTE for r in juridicos)
    assert not any(r.state in ("CONFIRMADO", "NAO_IDENTIFICADO", "NAO_APLICAVEL") for r in itens.values())


def test_regra_de_modalidade_nao_apaga_risco_juridico(db):
    prop = _prop(db)
    _doc(db, prop, "\n".join(MATRICULA_LIMPA[:2]) + "\nAv-3 - Matrícula nº 1.111 - PENHORA. Penhora fictícia nos autos de execução.\n"
         "Av-4 - Matrícula nº 1.111 - CONSOLIDAÇÃO DE PROPRIEDADE. Fica consolidada a propriedade em nome do BANCO EXEMPLO S.A.\n", "m.txt", "MATRICULA")
    execution, verdict = _analisar(db, prop)
    itens = _itens(execution)
    assert itens["PENHORA_INDISPONIBILIDADE"].state == "RISCO_IDENTIFICADO"
    assert {k for k, r in itens.items() if r.state == "NAO_APLICAVEL"} == {"LANCE_MENOR_50_AVALIACAO", "EDITAL_LIDO"}
    fatores = verdict.financial["decisao"]["fatores"]["grupos"]
    assert "PENHORA_INDISPONIBILIDADE" in {f.get("chave") for f in fatores[FATOR_IMPEDIMENTO]}
    assert {f["chave"] for f in fatores[FATOR_NAO_APLICAVEL]} == {"LANCE_MENOR_50_AVALIACAO", "EDITAL_LIDO"}
    assert verdict.overall == "ATENCAO"


def test_venda_direta_sem_consolidacao_lida_torna_itens_de_origem_nao_aplicaveis(db):
    prop = _prop(db)
    _doc(db, prop, "R-1 - Matrícula nº 1 - COMPRA E VENDA. A CONSTRUTORA EXEMPLO LTDA vendeu o imóvel ao BANCO EXEMPLO S.A.\n"
         "Av-2 - Matrícula nº 1 - averbação de construção fictícia.\n", "m.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    for key in ("INTIMACAO_PESSOAL", "QUITACAO_80", "LEILOES_NEGATIVOS_AVERBADOS"):
        assert itens[key].state == "NAO_APLICAVEL" and not itens[key].applicable and "não decorre de consolidação" in itens[key].answer, key
        assert _tipos(db, itens[key]) == {TIPO_NAO_LOCALIZADA}, key


# =============================================================== caso do imóvel 7 (sintético): os 27 itens

# Resultado esperado de cada item com a matrícula fictícia (R-3 alienação, Av-5 consolidação pós edital), as condições da venda
# fictícias, o leilão (avaliação e valor de venda) e NADA mais (sem comparáveis, ocupação, localização ou premissas), como em produção.
ESPERADO_IMOVEL7 = {
    "INTIMACAO_PESSOAL": RESULTADO_INCONCLUSIVO,        # 01 edital citado na Av-5: a pessoal não se concretizou; tentativas não aparecem
    "INTIMACAO_EDITAL": RESULTADO_CONFIRMADO,           # 02 Av-5 cita a certidão "pós edital"
    "NOTIFICACAO_DOIS_LEILOES": RESULTADO_PENDENTE,     # 03 não averbada: exige comprovante do vendedor
    "QUITACAO_80": RESULTADO_PENDENTE,                  # 04 matrícula tem a dívida (R-3), não os pagamentos
    "GARANTIA_DIVIDA_TERCEIRO": RESULTADO_SEM_RESTRICAO,  # 05 R-3: mútuo da própria aquisição
    "LANCE_MENOR_50_AVALIACAO": RESULTADO_NAO_APLICAVEL,  # 06 sem lance na venda direta
    "ACAO_QUESTIONAMENTO": RESULTADO_PENDENTE,          # 07 nenhuma ação averbada; certidões dos distribuidores
    "LEILOES_NEGATIVOS_AVERBADOS": RESULTADO_INCONCLUSIVO,  # 08 consolidação sem averbação de leilões
    "CONSOLIDACAO_REGISTRADA": RESULTADO_CONFIRMADO,    # 09 R-3 + Av-5
    "PENHORA_INDISPONIBILIDADE": RESULTADO_SEM_RESTRICAO,  # 10 atos 1 a 5 lidos em sequência, sem restrição
    "TERCEIRO_OCUPANTE": RESULTADO_PENDENTE,            # 11 ocupação não verificada
    "LOCACAO_REGISTRADA": RESULTADO_SEM_RESTRICAO,      # 12 sem locação registrada
    "EDITAL_LIDO": RESULTADO_NAO_APLICAVEL,             # 13 sem edital
    "EVICCAO": RESULTADO_CONFIRMADO,                    # 14 condições: responde, limitada à restituição
    "RESPONSABILIDADE_DEBITOS": RESULTADO_CONFIRMADO,   # 15 condições: condomínio (excedente) e IPTU (integral acima)
    "VAGA_MATRICULA": RESULTADO_INCONCLUSIVO,           # 16 cadastro tem vaga, matrícula não descreve
    **{k: RESULTADO_PENDENTE for k in ("ILIQUIDEZ", "CONDOMINIO_ALTO", "COMPARAVEIS_SUFFICIENTES", "REGIAO_SERVICOS", "REFORMA_GRANDE",
                                        "RETORNO_SELIC", "PRAZO_DOIS_ANOS", "DISTANCIA_USUARIO", "REFORMA_LIQUIDEZ", "CONDOMINIO_PORTARIA",
                                        "ETICA_OCUPACAO")},   # 17-27 sem dados no cadastro
}


def test_caso_imovel7_sintetico_resultado_dos_27_itens(db):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    _doc(db, prop, CONDICOES_FICTICIAS, "condicoes.txt", "CONDICOES_VENDA")
    execution, verdict = _analisar(db, prop)
    itens = _itens(execution)
    assert len(itens) == 27
    assert {k: _resultado(r) for k, r in itens.items()} == ESPERADO_IMOVEL7
    for key, r in itens.items():
        if _resultado(r) in (RESULTADO_CONFIRMADO, RESULTADO_SEM_RESTRICAO, RESULTADO_RISCO):
            assert _evs(db, r), key                                                  # toda resposta tem evidência vinculada
        if r.state == "PENDENTE" and r.applicable:
            assert "regra evidencias-v1:" in (r.interpretation or ""), key           # pendência com justificativa própria
    pendentes = [r.interpretation for r in itens.values() if r.state == "PENDENTE" and r.applicable]
    assert len(set(pendentes)) == len(pendentes)                                    # nenhuma justificativa genérica repetida
    assert verdict.overall == "INCONCLUSIVO"                                        # há pendências e nenhum risco ativo


def test_caso_imovel7_sem_condicoes_anexadas_mantem_14_e_15_pendentes(db):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    itens = _itens(_analisar(db, prop)[0])
    esperado = {**ESPERADO_IMOVEL7, "EVICCAO": RESULTADO_PENDENTE, "RESPONSABILIDADE_DEBITOS": RESULTADO_PENDENTE}
    assert {k: _resultado(r) for k, r in itens.items()} == esperado


# =============================================================== integração HTTP: upload → análise → checklist → evidências

def test_api_documento_ate_o_item_do_checklist_com_trecho_e_tipo(api):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    assert client.post(f"/api/imoveis/{pid}/leilao", json={"auction_stage": "Venda direta", "appraisal_value": "220000", "bid_value": "132970.97"}).status_code < 300
    for nome, texto, tipo in (("matricula.txt", "\n".join(MATRICULA_FICTICIA), "MATRICULA"), ("condicoes.txt", CONDICOES_FICTICIAS, "CONDICOES_VENDA")):
        r = client.post(f"/api/imoveis/{pid}/documentos", files={"file": (nome, texto.encode(), "text/plain")}, data={"document_type": tipo})
        assert r.status_code < 300, r.text
    assert client.post(f"/api/imoveis/{pid}/analisar", json={}).status_code == 200
    execs = client.get(f"/api/imoveis/{pid}/checklist").json()
    analise = max((e for e in execs if e["analysis_version"] is not None), key=lambda e: (e["analysis_version"], e["id"]))   # mesma transação: created_at igual
    itens = {i["canonical_key"]: i for i in analise["results"]}
    deb = itens["RESPONSABILIDADE_DEBITOS"]
    assert deb["resultado"] == RESULTADO_CONFIRMADO and deb["resultado_label"] == "Comprovado" and deb["acao_recomendada"] is None
    assert deb["question"].startswith("Quais são as responsabilidades") and deb["pergunta_catalogo"].startswith("O edital define")
    pen = itens["PENHORA_INDISPONIBILIDADE"]
    assert pen["resultado"] == RESULTADO_SEM_RESTRICAO and pen["resultado_label"] == "Sem restrição identificada" and pen["acao_recomendada"]
    assert itens["QUITACAO_80"]["resultado"] == RESULTADO_PENDENTE and itens["QUITACAO_80"]["fonte_necessaria"].startswith("Extrato")

    evid = client.get(f"/api/imoveis/{pid}/checklist/{deb['id']}/evidencias").json()
    assert evid["canonical_key"] == "RESPONSABILIDADE_DEBITOS" and evid["evidencias"]
    for e in evid["evidencias"]:
        assert e["tipo_evidencia"] == TIPO_REGRA_VENDA and e["tipo_evidencia_label"] == "Regra oficial da venda"
        assert e["documento"] == "condicoes.txt" and e["tem_trecho_documento"] and e["agent"] == "condicoes_venda" and e["created_at"]
    nao = client.get(f"/api/imoveis/{pid}/checklist/{pen['id']}/evidencias").json()["evidencias"]
    assert [e["tipo_evidencia"] for e in nao] == [TIPO_NAO_LOCALIZADA] and nao[0]["documento"] == "matricula.txt"
    # o detalhe do imóvel traz os mesmos campos (fonte única no backend)
    detalhe = {i["canonical_key"]: i for i in client.get(f"/api/imoveis/{pid}").json()["checklist"]}
    assert detalhe["RESPONSABILIDADE_DEBITOS"]["resultado"] == RESULTADO_CONFIRMADO and detalhe["RESPONSABILIDADE_DEBITOS"]["question"] == deb["question"]
    # item de outro imóvel ou inexistente: 404
    assert client.get(f"/api/imoveis/{pid}/checklist/999999/evidencias").status_code == 404
