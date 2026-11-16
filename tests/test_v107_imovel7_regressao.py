"""Regressão v1.0.7: erros observados num teste de venda direta com matrícula lida por OCR.

Na análise v1 (v1.0.6) o checklist exigiu EDITAL_LIDO numa venda direta, e os agentes: (1) deram a área total
como área privativa; (2) afirmaram "não possui ônus averbados" com alienação fiduciária registrada; (3) apontaram
a incorporadora do cabeçalho da matrícula como titular, embora a propriedade tenha sido consolidada depois em nome
do credor fiduciário.

A matrícula abaixo é INTEIRAMENTE FICTÍCIA (número, endereço, condomínio, partes, protocolos, datas e valores),
com a mesma ESTRUTURA que causou os erros: cabeçalho com a proprietária original, R-2 compra e venda, R-3
alienação fiduciária com o nome do credor deslocado pelo OCR para depois do Av-4, e Av-5 consolidação ("Avy-S/M-5"
como sai do OCR). Os defeitos de OCR (letra no lugar de número, data e protocolo truncados, unidade de área
corrompida, nome quebrado em duas linhas) são intencionais. Nenhuma chamada externa: as respostas do modelo são
simuladas. A normalização do nome da Caixa pelo leitor registral tem teste próprio, sintético, mais abaixo.
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from backend.app import models, modality_rules
from backend.app.checklist import (STATUS_INCONCLUSIVO, STATUS_NAO_APLICAVEL, STATUS_PENDENTE, STATUS_RESPONDIDO, master_items,
                                   standard_justification, standard_status)
from backend.app.config import settings
from backend.app.registry_chain import (INCONCLUSIVO, ONUS_EXISTENTE, PESSOA_FISICA, TITULARIDADE_DETERMINADA, conclusions,
                                        read_registry, review_statement)

# Partes e imóvel FICTÍCIOS. A incorporadora não usa a palavra "INCORPORADORA" de propósito: ela é um qualificador
# de titularidade no revisor ("a incorporadora era a titular" não é afirmação de titular atual).
INCORPORADORA = "CONSTRUTORA FICTÍCIA ALFA LTDA"
CREDORA = "BANCO FICTÍCIO S.A"          # como o leitor devolve o nome (pontuação final removida)
COMPRADOR = "COMPRADOR TESTE FICTÍCIO"  # pessoa física: o leitor a minimiza para PESSOA_FISICA
TITULO = "RESIDENCIAL EXEMPLO"
AREA_TOTAL, AREA_PRIVATIVA = Decimal("55.90"), Decimal("52.30")   # comum 3,60 m²

MATRICULA_FICTICIA = [
    "Serviço Registral de Imóveis\nComarca Fictícia de Exemplo\nMatrícula nº 99.999\n"
    "IMÓVEL: APARTAMENTO nº 01, DO BLOCO 99, integrante do Condomínio RESIDENCIAL EXEMPLO, situado Rua Fictícia nº 999.\n"
    "Será do tipo “Z”, e terá a área construída de utilização exclusiva de 52,3000m”, área de uso comum de\n"
    "3,6000m?, perfazendo a área correspondente ou global construída de 55,9000m?, fração ideal do solo.\n"
    "INSCRIÇÃO IMOBILIÁRIA: não consta.\n"
    "PROPRIETÁRIA: CONSTRUTORA FICTÍCIA ALFA LTDA, pessoa jurídica de direito privado.\n",

    "Av-l - Matricula nº 99.999 - Protocolo nº 11,111 datado de 01/0 1 - AFETAÇÃO. Consoante\n"
    "procedo esta averbação para constar que a proprietária CONSTRUTORA FICTÍCIA ALFA LTDA constituiu RET.\n"
    "R-2 - Matrícula nº 99.999 - Protocolo nº 11. datado de 01/02/2001 - COMPRA E VENDA.\n"
    "Consoante Contrato de Compra e Venda de Terreno e Mútuo, Alienação Fiduciária em Garantia, CONSTRUTORA FICTÍCIA ALFA\n"
    f"LTDA, já qualificada, vendeu a {COMPRADOR}, brasileiro, solteiro, o imóvel objeto da presente matrícula, pelo preço de R$ 111.111,11.\n",

    "R-3 - Matrícula nº 99.999 - Protocolo nº 11.111 datado de 01/02/2001 - ALIENAÇÃO\n"
    f"FIDUCIÁRIA. Consoante Contrato de Compra e Venda de Terreno e Mútuo, {COMPRADOR}, já qualificado,\n"
    "FICTÍCIO-BF, instituição financeira fictícia, para garantia da dívida no valor de R$ 99.999,99.\n"
    "Av-4 - Matrícula nº 99.999 - Protocolo nº 22.222 datado de 02/03/2002 - CONCLUSÃO DA\n"
    "OBRA. AVERBA-SE a CONCLUSÃO DA OBRA do empreendimento imobiliário denominado RESIDENCIAL EXEMPLO.\n"
    "FIADORA:  CONSTRUTORA FICTÍCIA ALFA LTDA;  ALIENOU\n"
    "FIDUCIARIAMENTE o imóvel objeto da presente matrícula, em favor do BANCO FICTÍCIO S.A.  \n",

    "Avy-S/M-5 º 33.333 datado de 03/04/2003 - CONSOLIDAÇÃO DE  \n"
    "Título: Requerimento datado de 01 de março de 2003 e Certidão de Não Pagamento Pós Edital.\n"
    "Averbar: que fica consolidada a propriedade do imóvel constante da presente matrícula, em\n"
    "nome da credora BANCO FICTÍCIO S.A., já qualificada.\n",
]


def _chunks(texts=MATRICULA_FICTICIA, start=100):
    return [{"chunk_id": start + i, "content": text, "page": None, "section": f"Página {i + 1}"} for i, text in enumerate(texts)]


# =============================================================== 1. modalidade

@pytest.mark.parametrize("valor,esperado", [
    ("VENDA_DIRETA", "VENDA_DIRETA"), ("Venda direta", "VENDA_DIRETA"), ("COMPRA DIRETA", "VENDA_DIRETA"),
    ("venda-direta", "VENDA_DIRETA"), (None, "INDEFINIDO"), ("", "INDEFINIDO"), ("Leilão", "INDEFINIDO"),
    ("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"), ("JUDICIAL", "JUDICIAL"),
])
def test_modalidade_do_imovel_normalizada_sem_inventar(valor, esperado):
    assert modality_rules.normalize_property_modality(valor) == esperado


def test_edital_lido_nao_aplicavel_so_em_venda_direta():
    assert modality_rules.checklist_applicability("VENDA_DIRETA", "EDITAL_LIDO") == "NAO_APLICAVEL"
    for modalidade in ("INDEFINIDO", "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", "JUDICIAL", "EXTRAJUDICIAL_OUTRA_GARANTIA"):
        assert modality_rules.checklist_applicability(modalidade, "EDITAL_LIDO") == "APLICAVEL"
    # o item continua no catálogo (não é removido globalmente)
    assert "EDITAL_LIDO" in {item["canonical_key"] for item in master_items()}


# =============================================================== 3. status padronizado

@pytest.mark.parametrize("estado,aplicavel,esperado", [
    ("PENDENTE", True, STATUS_PENDENTE), (None, True, STATUS_PENDENTE), ("EM_ANALISE", True, STATUS_INCONCLUSIVO),
    ("CONFIRMADO", True, STATUS_RESPONDIDO), ("NAO_IDENTIFICADO", True, STATUS_RESPONDIDO), ("RISCO_IDENTIFICADO", True, STATUS_RESPONDIDO),
    ("ATENCAO", True, STATUS_RESPONDIDO), ("NAO_APLICAVEL", True, STATUS_NAO_APLICAVEL), ("PENDENTE", False, STATUS_NAO_APLICAVEL),
])
def test_status_padronizado_do_checklist(estado, aplicavel, esperado):
    assert standard_status(estado, aplicavel) == esperado
    assert standard_justification(estado, aplicavel, "", "")   # sempre há justificativa


# =============================================================== 2. cadeia registral

def test_cadeia_registral_do_imovel7_em_ordem_cronologica():
    chain = read_registry(_chunks(), document_version_id=10)
    resumo = chain.to_prompt_dict()
    assert resumo["proprietario_original"] == INCORPORADORA
    assert resumo["proprietarios_intermediarios"] == [PESSOA_FISICA]           # comprador do R-2, minimizado
    assert resumo["titular_atual"] == CREDORA and resumo["titular_atual_situacao"] == TITULARIDADE_DETERMINADA
    assert resumo["titular_atual_ato"] == "Av-5"
    # credor deslocado pelo OCR para depois do Av-4: ainda assim é atribuído ao R-3, e é o mesmo da consolidação
    assert resumo["alienacao_fiduciaria"] == {"ato": "R-3", "credor_fiduciario": CREDORA, "cancelada": False}
    assert resumo["consolidacao"] == {"ato": "Av-5", "em_nome_de": CREDORA}
    # consolidação NÃO é baixa: sem cancelamento averbado, a situação de ônus é inconclusiva (nunca "inexistente")
    assert resumo["onus_e_gravames"] == INCONCLUSIVO
    assert "não equivale a baixa" in resumo["onus_justificativa"]
    assert resumo["area_total_m2"] == 55.9 and resumo["area_privativa_m2"] == 52.3
    assert COMPRADOR not in json.dumps(resumo, ensure_ascii=False)               # sem dado pessoal no resumo


def test_conclusoes_tem_trecho_do_documento_e_conferem_areas_com_o_cadastro():
    chain = read_registry(_chunks(), document_version_id=10)
    itens = conclusions(chain, area_total=AREA_TOTAL, area_private=AREA_PRIVATIVA)
    textos = [item["text"] for item in itens]
    assert any(t.startswith(f"Titular atual pela sequência de atos da matrícula: {CREDORA}") for t in textos)
    assert any(t.startswith(f"Proprietário original (abertura da matrícula): {INCORPORADORA}") for t in textos)
    assert any("Alienação fiduciária registrada (R-3)" in t and "registro histórico" in t for t in textos)
    assert any(t.startswith("Situação de ônus e gravames: INCONCLUSIVA") for t in textos)
    assert "Matrícula: área total de 55,90 m². Confere com o cadastro." in textos
    assert "Matrícula: área privativa de 52,30 m². Confere com o cadastro." in textos
    for item in itens:   # titularidade, ônus e áreas sempre apontam o trecho da matrícula
        assert item["fact"] is not None and item["fact"].chunk_id is not None and item["fact"].excerpt


def test_divergencia_de_area_entre_cadastro_e_matricula_e_registrada_sem_corrigir():
    chain = read_registry(_chunks(), document_version_id=10)
    textos = [item["text"] for item in conclusions(chain, area_total=AREA_TOTAL, area_private=AREA_TOTAL)]
    assert any(t.startswith("Divergência entre cadastro e matrícula na área privativa: cadastro 55,90 m², matrícula 52,30 m²") for t in textos)


@pytest.mark.parametrize("frase,regra", [
    ("O imóvel possui área privativa de 55.90 m².", "AREA_PRIVATIVA_DIVERGENTE"),
    ("O imóvel não possui ônus averbados.", "ONUS_SEM_PROVA_DE_AUSENCIA"),
    (f"A titular do imóvel é {INCORPORADORA}.", "TITULARIDADE_CRONOLOGICA"),
    ("O imóvel está livre e desembaraçado de quaisquer ônus.", "ONUS_SEM_PROVA_DE_AUSENCIA"),
    ("Área total de 52,30 m².", "AREA_TOTAL_DIVERGENTE"),
])
def test_tres_erros_da_analise_v1_sao_rejeitados(frase, regra):
    chain = read_registry(_chunks(), document_version_id=10)
    review = review_statement(frase, chain, area_total=AREA_TOTAL, area_private=AREA_PRIVATIVA)
    assert review.rule == regra and review.rejected == frase and review.statement
    if regra == "AREA_PRIVATIVA_DIVERGENTE":
        assert "(o valor informado é a área total)" in review.statement and "52,30" in review.statement
    if regra == "ONUS_SEM_PROVA_DE_AUSENCIA":
        assert review.statement.startswith("Situação de ônus e gravames INCONCLUSIVA")
    if regra == "TITULARIDADE_CRONOLOGICA":
        assert CREDORA in review.statement and "proprietária original" in review.statement


@pytest.mark.parametrize("frase", [
    "O imóvel possui área privativa de 52,30 m².",
    "A área total do imóvel é de 55,90 m².",
    "A propriedade foi consolidada em nome do BANCO FICTÍCIO S.A.",
    f"{INCORPORADORA} consta como proprietária original na abertura da matrícula.",
    "Não há informações sobre processos judiciais relacionados ao imóvel.",
    "Alienação fiduciária registrada no R-3 em favor do BANCO FICTÍCIO.",
])
def test_afirmacoes_corretas_nao_sao_alteradas(frase):
    chain = read_registry(_chunks(), document_version_id=10)
    assert review_statement(frase, chain, AREA_TOTAL, AREA_PRIVATIVA).statement is None


def test_nome_da_caixa_e_normalizado_e_credor_e_reconhecido_sem_em_favor():
    """Cobertura sintética dos dois ramos do leitor que tratam a Caixa pelo nome (instituição pública, sem
    identificar imóvel): a variação "CAIXA ECONOMICA FEDERAL-CEF" vira o nome canônico, e o credor é reconhecido
    mesmo quando o OCR perde o "em favor da"."""
    from backend.app.registry_chain import canonical_party
    assert canonical_party("CAIXA ECONOMICA FEDERAL-CEF") == canonical_party("Caixa Econômica  ") == "CAIXA ECONÔMICA FEDERAL"
    chain = read_registry(_chunks(["PROPRIETÁRIA: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
                                   "R-2 - Matrícula nº 1 - ALIENAÇÃO FIDUCIÁRIA. O devedor deu o imóvel em garantia à CAIXA ECONOMICA FEDERAL-CEF.\n",
                                   "Av-3 - Matrícula nº 1 - CONSOLIDAÇÃO. Fica consolidada a propriedade do imóvel em nome da credora "
                                   "CAIXA ECONOMICA FEDERAL-CEF, já qualificada.\n"]))
    assert chain.fiduciary.value == "CAIXA ECONÔMICA FEDERAL" and chain.fiduciary.act == "R-2"
    assert chain.holder_name == "CAIXA ECONÔMICA FEDERAL" and chain.current_holder.act == "Av-3"
    assert chain.encumbrance_status()[0] == INCONCLUSIVO          # consolidação não é baixa
    review = review_statement("A titular do imóvel é CONSTRUTORA EXEMPLO LTDA.", chain)
    assert review.rule == "TITULARIDADE_CRONOLOGICA" and "CAIXA ECONÔMICA FEDERAL" in review.statement


def test_sem_ato_legivel_titularidade_e_inconclusiva():
    so_cabecalho = ["Matrícula nº 1.234\nPROPRIETÁRIA: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n"]
    assert read_registry(_chunks(so_cabecalho)).holder_status == INCONCLUSIVO
    ato_ilegivel = so_cabecalho + ["R-2 - Matrícula nº 1.234 - Protocolo nº 9 - COMPRA E VENDA. Consoante escritura, conforme o título.\n"]
    chain = read_registry(_chunks(ato_ilegivel))
    assert chain.holder_status == INCONCLUSIVO and chain.holder_name is None
    review = review_statement("A titular do imóvel é CONSTRUTORA EXEMPLO LTDA.", chain)
    assert review.rule == "TITULARIDADE_INCONCLUSIVA"
    assert any(i["text"].startswith("Titularidade atual INCONCLUSIVA") for i in conclusions(chain))


def test_onus_existente_e_alienacao_vigente_sao_reconhecidos():
    penhora = read_registry(_chunks(["PROPRIETÁRIO: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
                                     "R-4 - Matrícula nº 1 - PENHORA. Penhora do imóvel nos autos de execução fiscal.\n"]))
    assert penhora.encumbrance_status()[0] == ONUS_EXISTENTE
    af = read_registry(_chunks(["PROPRIETÁRIO: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
                                "R-2 - Matrícula nº 1 - ALIENAÇÃO FIDUCIÁRIA. O devedor alienou fiduciariamente o imóvel em favor do BANCO EXEMPLO S.A., para garantia.\n"]))
    assert af.encumbrance_status()[0] == ONUS_EXISTENTE and af.fiduciary.value == "BANCO EXEMPLO S.A"   # pontuação final removida
    cancelada = read_registry(_chunks(["PROPRIETÁRIO: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
                                       "R-2 - Matrícula nº 1 - ALIENAÇÃO FIDUCIÁRIA. alienou fiduciariamente em favor do BANCO EXEMPLO S.A.\n",
                                       "Av-3 - Matrícula nº 1 - CANCELAMENTO. Fica cancelada a alienação fiduciária objeto do R-2.\n"]))
    assert cancelada.fiduciary_cancelled() is True
    assert cancelada.encumbrance_status()[0] == INCONCLUSIVO     # baixa da AF não prova ausência de outros ônus


def test_extracao_da_matricula_usa_titular_atual_e_registra_o_ajuste():
    from backend.app.extraction import CAMPO_EXTRAIDO, ExtractionReference, RegistrationExtraction, reconcile_registration_holder
    chain = read_registry(_chunks(), document_version_id=10)
    saida = RegistrationExtraction(registration_number="99.999", holder=INCORPORADORA, references=[
        ExtractionReference(field="registration_number", value="99.999", chunk_id=100, excerpt="Matrícula nº 99.999"),
        ExtractionReference(field="holder", value=INCORPORADORA, chunk_id=100, excerpt=f"PROPRIETÁRIA: {INCORPORADORA}")])
    campos = {"registration_number": {"status": CAMPO_EXTRAIDO}, "holder": {"status": CAMPO_EXTRAIDO}}
    nova, status = reconcile_registration_holder(saida, campos, chain)
    assert nova.holder == CREDORA
    [ref] = [r for r in nova.references if r.field == "holder"]
    assert ref.chunk_id == 103 and "consolidada a propriedade" in ref.excerpt
    assert status["holder"]["ajuste"].startswith("titular atual pela sequência de atos") and status["holder"]["valor_modelo"] == INCORPORADORA
    assert any(r.field == "registration_number" for r in nova.references)


def test_extracao_sem_titular_determinavel_fica_inconclusiva():
    from backend.app.extraction import CAMPO_INCONCLUSIVO, ExtractionReference, RegistrationExtraction, reconcile_registration_holder
    chain = read_registry(_chunks(["PROPRIETÁRIA: CONSTRUTORA EXEMPLO LTDA, pessoa jurídica.\n",
                                   "R-2 - Matrícula nº 1 - COMPRA E VENDA. Consoante escritura, conforme o título.\n"]))
    saida = RegistrationExtraction(holder="CONSTRUTORA EXEMPLO LTDA", references=[ExtractionReference(field="holder", value="CONSTRUTORA EXEMPLO LTDA", chunk_id=100)])
    nova, status = reconcile_registration_holder(saida, {"holder": {"status": "EXTRAIDO"}}, chain)
    assert nova.holder is None and status["holder"]["status"] == CAMPO_INCONCLUSIVO and nova.references == []


# =============================================================== agentes

class _Provider:
    def __init__(self, content):
        self.content, self.messages = content, []

    def structured_chat(self, schema, messages, **kwargs):
        from backend.app.ai.gateway import ProviderResponse
        self.messages = messages
        return ProviderResponse(content=self.content, input_tokens=10, output_tokens=5, request_id="t")

    def chat(self, *args, **kwargs):
        from backend.app.ai.gateway import ProviderResponse
        return ProviderResponse(content="")

    def embed(self, texts):
        return []


class _NoDb:
    def get(self, *args):
        return None


def test_checklist_agent_nao_recebe_item_nao_aplicavel():
    from backend.app.ai.agents import ChecklistAgent
    from backend.app.ai.contracts import AgentResponse
    from backend.app.ai.gateway import LLMGateway
    provider = _Provider(AgentResponse(findings=[]))
    itens = [{"canonical_key": "EDITAL_LIDO", "question": "O edital do leilão foi lido integralmente?", "applicable": False},
             {"canonical_key": "VAGA_MATRICULA", "question": "A vaga de garagem possui matrícula própria?", "applicable": True}]
    ChecklistAgent(_NoDb(), LLMGateway(provider, "fake", "m")).run(1, "", [], itens)
    enviados = [i["canonical_key"] for i in json.loads(provider.messages[1]["content"])["checklist_mestre"]]
    assert enviados == ["VAGA_MATRICULA"]


def test_prompts_documental_e_juridico_trazem_regras_registrais_e_areas_rotuladas():
    from backend.app.ai.agents import DocumentAgent, LegalAgent
    from backend.app.ai.contracts import AgentResponse
    from backend.app.ai.gateway import LLMGateway

    class Db(_NoDb):
        def get(self, model, identifier):
            return models.Property(id=1, title=TITULO, modality="VENDA_DIRETA", area_m2=AREA_TOTAL, private_area_m2=AREA_PRIVATIVA) if model is models.Property else None

    for agent in (DocumentAgent, LegalAgent):
        provider = _Provider(AgentResponse(findings=[]))
        agent(Db(), LLMGateway(provider, "fake", "m")).run(1, "", [])
        prompt, payload = provider.messages[0]["content"], json.loads(provider.messages[1]["content"])
        assert "ordem cronológica" in prompt and "INCONCLUSIVA" in prompt and "nunca troque" in prompt
        assert payload["imovel"]["area_total_m2"] == 55.9 and payload["imovel"]["area_privativa_m2"] == 52.3
        assert payload["imovel"]["modalidade"] == "VENDA_DIRETA" and "area_m2" not in payload["imovel"]


# =============================================================== PostgreSQL: execução, veredito, oportunidade

@pytest.fixture(autouse=True)
def _sem_chave(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _prop(db, modality, titulo="Imóvel v1.0.7"):
    prop = models.Property(title=titulo, address="Rua Fictícia, 999", city="Cidade Fictícia", state="PR", modality=modality,
                           area_m2=AREA_TOTAL, private_area_m2=AREA_PRIVATIVA, bedrooms=2)
    db.add(prop); db.flush()
    return prop


def _doc(db, prop, texto, nome, tipo):
    from backend.app.documents.pipeline import DocumentPipeline
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    return DocumentPipeline(db).ingest(doc, texto.encode(), nome)


def _por_chave(execution):
    return {r.item.canonical_key: r for r in execution.results}


def _pendencias(prop, execution):
    from backend.app.verdict_engine import VerdictEngine
    return VerdictEngine().evaluate(prop.id, 1, checklist_results=execution.results, evidence_ids=[1], financial={}).pending_items


PERGUNTA_EDITAL = "O edital do leilão foi lido integralmente?"


def test_venda_direta_sem_edital_nao_gera_pendencia_de_edital(db):
    from backend.app.services import create_execution
    prop = _prop(db, "VENDA_DIRETA")
    execution = create_execution(db, prop, "TESTE", 1)
    edital = _por_chave(execution)["EDITAL_LIDO"]
    assert edital.applicable is False and edital.state == "NAO_APLICAVEL" and edital.resolution_origin == "REGRA_MODALIDADE"
    assert standard_status(edital.state, edital.applicable) == STATUS_NAO_APLICAVEL
    assert "VENDA_DIRETA" in edital.answer
    assert PERGUNTA_EDITAL not in _pendencias(prop, execution)
    # itens aplicáveis à venda direta continuam exigidos (ex.: vaga com matrícula própria, ocupação)
    for chave in ("VAGA_MATRICULA", "TERCEIRO_OCUPANTE", "RESPONSABILIDADE_DEBITOS"):
        assert _por_chave(execution)[chave].applicable is True and _por_chave(execution)[chave].state == "PENDENTE"


@pytest.mark.parametrize("modalidade", ["EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", None, "Leilão"])
def test_leilao_com_ou_sem_edital_continua_exigindo_leitura_do_edital(db, modalidade):
    from backend.app.services import create_execution
    com_edital = _prop(db, modalidade, "Leilão com edital")
    _doc(db, com_edital, "EDITAL FICTÍCIO DE LEILÃO. 1º leilão em 10/10/2025.", "edital.txt", "EDITAL")
    sem_edital = _prop(db, modalidade, "Leilão sem edital")
    for prop in (com_edital, sem_edital):
        execution = create_execution(db, prop, "TESTE", 1)
        edital = _por_chave(execution)["EDITAL_LIDO"]
        assert edital.applicable is True and edital.state == "PENDENTE"
        assert PERGUNTA_EDITAL in _pendencias(prop, execution)
        assert all(r.state != "NAO_APLICAVEL" for r in execution.results)   # comportamento anterior preservado


def test_mesma_regra_no_endpoint_de_oportunidades_e_na_analise(db):
    from backend.app import workflow_service
    from backend.app.services import create_execution
    prop = _prop(db, "VENDA_DIRETA")
    opp = workflow_service.create_opportunity(db, {"property_id": prop.id, "modality": "VENDA_DIRETA"})
    visao = {i["canonical_key"]: i["aplicabilidade"] for i in workflow_service.checklist_applicability_view(db, opp)["itens"]}
    execucao = {r.item.canonical_key: r.applicable for r in create_execution(db, prop, "TESTE", 1).results}
    assert visao["EDITAL_LIDO"] == "NAO_APLICAVEL" and execucao["EDITAL_LIDO"] is False
    for chave, aplicavel in execucao.items():
        assert (visao[chave] != "NAO_APLICAVEL") == aplicavel, chave


def test_agente_nao_altera_item_nao_aplicavel(db):
    from backend.app.services import create_analysis, create_execution, persist_agent_findings
    prop = _prop(db, "VENDA_DIRETA")
    version = _doc(db, prop, "EDITAL? Não. Proposta de compra direta Caixa, sem leilão.", "proposta.txt", "OUTRO")
    chunk = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version.id).first()
    analysis = create_analysis(db, prop, "teste", ["juridico"], [], "teste", [])
    execution = create_execution(db, prop, "TESTE", analysis.version)
    finding = {"kind": "fato", "statement": "Proposta de compra direta Caixa, sem leilão", "checklist_key": "EDITAL_LIDO", "checklist_state": "CONFIRMADO",
               "chunk_ids": [chunk.id], "evidence_excerpt": "Proposta de compra direta Caixa, sem leilão"}
    persist_agent_findings(db, prop, analysis, execution, [{"agent": "juridico", "retrieved_chunk_ids": [chunk.id], "facts": [finding]},
                                                           {"agent": "checklist", "retrieved_chunk_ids": [chunk.id], "facts": [finding]}])
    edital = _por_chave(execution)["EDITAL_LIDO"]
    assert edital.state == "NAO_APLICAVEL" and edital.applicable is False


# =============================================================== HTTP: análise completa do imóvel (IA simulada)

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


def _orquestracao_v1(chunk_ids):
    """O que os agentes responderam na análise v1 do imóvel 7 (os três erros), mais um fato correto."""
    agentes = ["documental", "juridico", "financeiro", "mercado", "checklist"]
    erros = {
        "documental": [{"kind": "interpretacao", "source": "inferencia", "statement": "O imóvel possui área privativa de 55.90 m².", "chunk_ids": []},
                       {"kind": "interpretacao", "source": "inferencia", "statement": "O imóvel não possui ônus averbados.", "chunk_ids": []}],
        "juridico": [{"kind": "fato", "source": "documento", "statement": f"A titular do imóvel é {INCORPORADORA}.", "chunk_ids": [chunk_ids[0]],
                      "evidence_excerpt": f"PROPRIETÁRIA: {INCORPORADORA}"},
                     {"kind": "fato", "source": "documento", "statement": "Propriedade consolidada em nome da credora BANCO FICTÍCIO S.A.", "chunk_ids": chunk_ids,
                      "evidence_excerpt": "que fica consolidada a propriedade do imóvel constante da presente matrícula, em nome da credora BANCO FICTÍCIO S.A."}],
    }
    return {
        "agent_results": [{"agent": a, "facts": erros.get(a, []), "evidence_ids": [], "pending": [], "llm_used": True, "model": "m", "retrieved_chunk_ids": chunk_ids} for a in agentes],
        "evidence_ids": [], "retrieved_chunk_ids": chunk_ids, "llm_used": True, "model": "m", "verdict": None,
        "llm_runs": [{"agent": a, "provider": "openai", "model": "m", "status": "CONCLUIDO", "input_tokens": 100, "output_tokens": 10} for a in agentes],
    }


def test_analise_completa_venda_direta_corrige_os_erros_e_preserva_a_versao_anterior(api, monkeypatch):
    client, session = api
    resposta = client.post("/api/imoveis", json={"title": f"{TITULO} (fictício)", "address": "Rua Fictícia, 999", "city": "Cidade Fictícia", "state": "PR",
                                                 "modality": "VENDA_DIRETA", "origin": "CAIXA", "area_m2": 55.90, "private_area_m2": 52.30, "bedrooms": 2})
    assert resposta.status_code == 200, resposta.text
    pid = resposta.json()["id"]
    prop = session.get(models.Property, pid)
    version = _doc(session, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    chunk_ids = [c.id for c in session.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version.id).order_by(models.DocumentChunk.chunk_index)]
    monkeypatch.setattr("backend.app.main.AnalysisOrchestrator.run", lambda self, property_id, domains, query, analysis_id=None: _orquestracao_v1(chunk_ids))

    v1 = client.post(f"/api/imoveis/{pid}/analisar", json={}).json()
    v2 = client.post(f"/api/imoveis/{pid}/analisar", json={}).json()
    assert (v1["versao"], v2["versao"]) == (1, 2) and v2["status"] == "concluida"

    evidencias = [e for e in session.query(models.Evidence).filter(models.Evidence.property_id == pid)]
    fatos = [e.fact for e in evidencias]
    # (1) área: o valor trocado não vira fato; a divergência fica registrada com a afirmação original
    assert not any(f == "O imóvel possui área privativa de 55.90 m²." for f in fatos)
    area = [e for e in evidencias if e.fact.startswith("Divergência de área")]
    assert area and all(e.origin == "INFERENCIA_IA" and e.confidence == "BAIXA" and "55.90" in e.hypothesis for e in area)
    # (2) ônus: nunca "não possui ônus"; a situação é inconclusiva, com a AF como registro histórico
    assert not any("não possui ônus" in f for f in fatos)
    assert any(f.startswith("Situação de ônus e gravames INCONCLUSIVA") for f in fatos)
    # (3) titularidade: a incorporadora não é aceita como titular; o titular atual vem da consolidação, com trecho
    assert not any(f == f"A titular do imóvel é {INCORPORADORA}." for f in fatos)
    registrais = [e for e in evidencias if e.agent == "cadeia_registral"]
    titular = [e for e in registrais if e.fact.startswith(f"Titular atual pela sequência de atos da matrícula: {CREDORA}")]
    assert titular and all(e.origin == "DOCUMENTO" and e.chunk_id in chunk_ids and e.source_excerpt for e in titular)
    assert any(e.fact.startswith(f"Proprietário original (abertura da matrícula): {INCORPORADORA}") for e in registrais)
    assert any("Alienação fiduciária registrada (R-3)" in e.fact for e in registrais)
    assert all(e.document_version_id == version.id for e in registrais if e.origin == "DOCUMENTO")
    # fato correto do agente segue aceito como documento
    assert any(e.fact.startswith("Propriedade consolidada em nome da credora") and e.origin == "DOCUMENTO" for e in evidencias)

    # checklist: edital não aplicável, status padronizado e justificativa na API
    detalhe = client.get(f"/api/imoveis/{pid}").json()
    [edital] = [i for i in detalhe["checklist"] if i["canonical_key"] == "EDITAL_LIDO"]
    assert edital["status_padrao"] == "NAO_APLICAVEL" and edital["applicable"] is False and "VENDA_DIRETA" in edital["justificativa"]
    assert {i["status_padrao"] for i in detalhe["checklist"]} <= {"RESPONDIDO", "PENDENTE", "NAO_APLICAVEL", "INCONCLUSIVO"}
    assert PERGUNTA_EDITAL not in (detalhe["veredito"]["what_is_unknown"] or "")
    assert detalhe["veredito"]["overall"] == "INCONCLUSIVO"   # sem valor de mercado etc.: não força conclusão
    execucoes = client.get(f"/api/imoveis/{pid}/checklist").json()
    assert {e["analysis_version"] for e in execucoes} >= {1, 2}
    assert all("status_padrao" in r and "justificativa" in r and "evidence_ids" in r for e in execucoes for r in e["results"])

    # histórico preservado: as duas versões e suas evidências continuam consultáveis
    analises = session.query(models.Analysis).filter(models.Analysis.property_id == pid).order_by(models.Analysis.version).all()
    assert [a.version for a in analises] == [1, 2] and all(a.evidence_ids for a in analises)
    assert session.query(models.Verdict).filter(models.Verdict.property_id == pid).count() >= 2
    # nenhum documento duplicado
    assert session.query(models.Document).filter(models.Document.property_id == pid).count() == 1
