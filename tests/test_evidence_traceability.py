"""Rastreabilidade de evidências e do checklist (v1.0.4), no PostgreSQL real e com o pipeline real de ingestão.

Cobre o que a 1ª execução com a OpenAI real (caso-01, sintético) mostrou: dado do snapshot financeiro apresentado
como trecho do edital, pergunta do checklist como "trecho literal" e itens do checklist resolvidos sem origem.
Nenhuma chamada externa: os findings simulam a resposta do modelo (entrada não confiável).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app import models
from backend.app.config import settings
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.services import create_analysis, create_execution, persist_agent_findings, resolve_checklist_from_data

EDITAL = ("EDITAL FICTÍCIO. 3. SITUAÇÃO DO IMÓVEL: o imóvel encontra-se OCUPADO. A desocupação é de responsabilidade "
          "e custo exclusivos do arrematante. Não há visitação interna. O imóvel é vendido em caráter ad corpus.\n"
          "5. PAGAMENTO: à vista, em até 24 horas após o encerramento do leilão. Não se admite parcelamento nem FGTS.\n"
          "6. COMISSÃO DO LEILOEIRO: 5% (cinco por cento) sobre o valor do arremate, marcador EDITALUNICO.")
OUTRO = "Matrícula do imóvel de controle: casa 7, Rua Controle Fictícia, marcador CONTROLEUNICO."


@pytest.fixture(autouse=True)
def _sem_chave(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _imovel(db, titulo):
    prop = models.Property(title=titulo, address="Rua X", city="São Paulo", state="SP", area_m2=60, bedrooms=2)
    db.add(prop); db.flush()
    return prop


def _chunk(db, prop, texto, nome="edital.txt", tipo="EDITAL"):
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    version = DocumentPipeline(db).ingest(doc, texto.encode(), nome)
    return db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version.id).order_by(models.DocumentChunk.chunk_index).first()


@pytest.fixture
def cenario(db):
    a, b = _imovel(db, "Imóvel A"), _imovel(db, "Imóvel B")
    chunk_a = _chunk(db, a, EDITAL)
    chunk_b = _chunk(db, b, OUTRO, "matricula.txt", "MATRICULA")
    analise = create_analysis(db, a, "teste", ["documental"], [], "teste", [])
    execucao = create_execution(db, a, "TESTE", analise.version)
    item = next(r for r in execucao.results if r.applicable and r.item is not None and r.item.question)
    return {"a": a, "b": b, "chunk_a": chunk_a, "chunk_b": chunk_b, "analise": analise, "execucao": execucao, "item": item}


def _persist(db, c, agente, finding, retrieved=None):
    resultado = {"agent": agente, "retrieved_chunk_ids": retrieved if retrieved is not None else [c["chunk_a"].id, c["chunk_b"].id], "facts": [finding]}
    ids = persist_agent_findings(db, c["a"], c["analise"], c["execucao"], [resultado])
    return [db.get(models.Evidence, i) for i in ids]


# ---------------------------------------------------------------- origem das evidências

def test_fato_documental_com_trecho_literal_vira_evidencia_documental_forte(db, cenario):
    [ev] = _persist(db, cenario, "documental", {"kind": "fato", "source": "documento", "statement": "Imóvel ocupado; desocupação por conta do arrematante", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "o imóvel encontra-se OCUPADO. A desocupação é de responsabilidade e custo exclusivos do arrematante"})
    assert ev.origin == "DOCUMENTO" and ev.strength == "FORTE" and ev.agent == "documental"
    assert ev.chunk_id == cenario["chunk_a"].id and ev.document_version_id == cenario["chunk_a"].document_version_id
    assert "OCUPADO" in ev.source_excerpt


def test_dado_do_snapshot_financeiro_nunca_e_atribuido_ao_edital(db, cenario):
    [ev] = _persist(db, cenario, "financeiro", {"kind": "fato", "statement": "O resultado líquido da operação é de R$ -26.550,00", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "resultado_liquido: -26550"})
    assert ev.origin == "CALCULO" and ev.document_version_id is None and ev.chunk_id is None and ev.source_excerpt is None
    assert ev.strength == "INVALIDA"     # a tentativa de citar o edital foi avaliada e recusada


def test_dado_declarado_como_cadastro_fica_com_origem_cadastro_sem_documento(db, cenario):
    [ev] = _persist(db, cenario, "mercado", {"kind": "fato", "source": "cadastro", "statement": "Há 3 comparáveis de venda cadastrados", "chunk_ids": [cenario["chunk_a"].id]})
    assert ev.origin == "CADASTRO" and ev.document_version_id is None and ev.source_excerpt is None and ev.strength is None


def test_pergunta_do_checklist_como_trecho_nao_vira_evidencia_documental(db, cenario):
    pergunta = cenario["item"].item.question
    [ev] = _persist(db, cenario, "juridico", {"kind": "fato", "statement": "Item verificado no edital", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": pergunta})
    assert ev.origin != "DOCUMENTO" and ev.chunk_id is None and ev.source_excerpt is None and ev.strength == "INVALIDA"


def test_interpretacao_sem_citacao_valida_e_inferencia_de_baixa_confianca(db, cenario):
    [ev] = _persist(db, cenario, "juridico", {"kind": "interpretacao", "statement": "O arrematante pode ter dificuldade de registro", "confidence": "ALTA", "chunk_ids": []})
    assert ev.origin == "INFERENCIA_IA" and ev.confidence == "BAIXA" and ev.interpretation and ev.document_version_id is None
    link = db.query(models.EvidenceLink).filter(models.EvidenceLink.evidence_id == ev.id).one()
    assert link.relation == "MENCIONA"


def test_documental_sem_documento_do_imovel_nao_registra_fato(db, cenario):
    assert _persist(db, cenario, "documental", {"kind": "fato", "statement": "Fato sem fonte", "chunk_ids": []}) == []


def test_citacao_de_chunk_de_outro_imovel_e_descartada(db, cenario):
    evs = _persist(db, cenario, "juridico", {"kind": "fato", "statement": "Casa 7 na Rua Controle Fictícia", "chunk_ids": [cenario["chunk_b"].id], "evidence_excerpt": "casa 7, Rua Controle Fictícia"})
    assert all(e.chunk_id != cenario["chunk_b"].id and "CONTROLEUNICO" not in (e.source_excerpt or "") for e in evs)
    assert db.query(models.Evidence).filter(models.Evidence.property_id == cenario["b"].id).count() == 0


def test_trecho_certo_com_chunk_id_errado_do_mesmo_imovel_aponta_para_o_chunk_correto(db, cenario):
    # 1ª execução real v1.0.4: trecho literal do edital citado com o chunk_id de outro trecho do mesmo imóvel.
    outro = _chunk(db, cenario["a"], "MATRÍCULA FICTÍCIA. Área privativa de 62,00 m². Nada mais consta.", "matricula.txt", "MATRICULA")
    [ev] = _persist(db, cenario, "documental", {"kind": "fato", "statement": "Imóvel ocupado; desocupação por conta do arrematante", "chunk_ids": [outro.id], "evidence_excerpt": "o imóvel encontra-se OCUPADO. A desocupação é de responsabilidade e custo exclusivos do arrematante"}, retrieved=[outro.id, cenario["chunk_a"].id])
    assert ev.origin == "DOCUMENTO" and ev.chunk_id == cenario["chunk_a"].id and ev.strength == "FORTE"


def test_finding_que_so_cita_chunk_de_outro_imovel_nao_e_reatribuido(db, cenario):
    evs = _persist(db, cenario, "documental", {"kind": "fato", "statement": "Imóvel ocupado", "chunk_ids": [cenario["chunk_b"].id], "evidence_excerpt": "o imóvel encontra-se OCUPADO"})
    assert evs == []


# ---------------------------------------------------------------- checklist

def _checklist(db, c, finding):
    resultado = {"agent": "checklist", "retrieved_chunk_ids": [c["chunk_a"].id, c["chunk_b"].id], "facts": [finding]}
    return persist_agent_findings(db, c["a"], c["analise"], c["execucao"], [resultado])


def _links(db, item):
    return db.query(models.ChecklistEvidence).filter(models.ChecklistEvidence.checklist_result_id == item.id).all()


def test_item_resolvido_com_evidencia_documental_registra_origem_e_vinculo(db, cenario):
    item = cenario["item"]
    ids = _checklist(db, cenario, {"kind": "fato", "statement": "Pagamento à vista em 24 horas, sem parcelamento nem FGTS", "confidence": "ALTA", "checklist_key": item.item.canonical_key, "checklist_state": "CONFIRMADO", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "à vista, em até 24 horas após o encerramento do leilão. Não se admite parcelamento nem FGTS"})
    assert len(ids) == 1 and item.state == "CONFIRMADO" and item.resolution_origin == "DOCUMENTO"
    [link] = _links(db, item)
    ev = db.get(models.Evidence, link.evidence_id)
    assert ev.origin == "DOCUMENTO" and ev.strength == "FORTE" and ev.agent == "checklist"


@pytest.mark.parametrize("finding_extra", [
    {"chunk_ids": []},                                                      # sem evidência
    {"evidence_excerpt": "texto que não existe no edital deste imóvel"},   # evidência inválida
    {"evidence_excerpt": "__PERGUNTA__"},                                   # pergunta como trecho
    {"statement": "Divergência de área privativa entre documentos", "evidence_excerpt": None},  # inconclusivo (fraco)
])
def test_item_sem_evidencia_suficiente_permanece_pendente(db, cenario, finding_extra):
    item = cenario["item"]
    finding = {"kind": "fato", "statement": "Pagamento à vista", "confidence": "ALTA", "checklist_key": item.item.canonical_key, "checklist_state": "CONFIRMADO", "chunk_ids": [cenario["chunk_a"].id]}
    finding.update(finding_extra)
    if finding.get("evidence_excerpt") == "__PERGUNTA__":
        finding["evidence_excerpt"] = item.item.question
    assert _checklist(db, cenario, finding) == []
    assert item.state == "PENDENTE" and item.resolution_origin is None and _links(db, item) == []


def test_finding_pendente_vincula_evidencia_sem_registrar_resolucao_nem_reabrir_item(db, cenario):
    item = cenario["item"]
    finding = {"kind": "fato", "statement": "Pagamento à vista em 24 horas", "confidence": "MEDIA", "checklist_key": item.item.canonical_key, "checklist_state": "PENDENTE", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "à vista, em até 24 horas após o encerramento do leilão"}
    assert len(_checklist(db, cenario, dict(finding))) == 1
    assert item.state == "PENDENTE" and item.resolution_origin is None and len(_links(db, item)) == 1
    item.state, item.answer, item.resolution_origin = "NAO_IDENTIFICADO", "resolvido antes", "REGRA_DETERMINISTICA"
    _checklist(db, cenario, dict(finding))
    assert item.state == "NAO_IDENTIFICADO" and item.answer == "resolvido antes" and item.resolution_origin == "REGRA_DETERMINISTICA"


def test_item_com_evidencia_de_outro_imovel_permanece_pendente(db, cenario):
    item = cenario["item"]
    assert _checklist(db, cenario, {"kind": "fato", "statement": "Casa 7 na Rua Controle", "confidence": "ALTA", "checklist_key": item.item.canonical_key, "checklist_state": "CONFIRMADO", "chunk_ids": [cenario["chunk_b"].id], "evidence_excerpt": "casa 7, Rua Controle Fictícia"}) == []
    assert item.state == "PENDENTE"


def test_item_nao_aplicavel_exige_evidencia_e_item_nao_aplicavel(db, cenario):
    item = cenario["item"]
    finding = {"kind": "fato", "statement": "Venda ad corpus, sem visitação interna", "confidence": "MEDIA", "checklist_key": item.item.canonical_key, "checklist_state": "NAO_APLICAVEL", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "Não há visitação interna. O imóvel é vendido em caráter ad corpus"}
    assert _checklist(db, cenario, dict(finding)) == []            # item aplicável: NAO_APLICAVEL recusado
    item.applicable = False
    assert len(_checklist(db, cenario, dict(finding))) == 1 and item.state == "NAO_APLICAVEL" and item.resolution_origin == "DOCUMENTO"


def test_agente_nao_checklist_so_altera_item_com_evidencia_documental(db, cenario):
    item = cenario["item"]
    _persist(db, cenario, "financeiro", {"kind": "fato", "statement": "Margem líquida de -7,9%", "checklist_key": item.item.canonical_key, "checklist_state": "RISCO_IDENTIFICADO", "chunk_ids": []})
    assert item.state == "PENDENTE"


def test_ia_nao_altera_item_respondido_por_calculo_deterministico(db, cenario):
    # 1ª execução real v1.0.4: o agente marcou LANCE_MENOR_50_AVALIACAO como CONFIRMADO com lance de 60% da avaliação.
    alvo = next((r for r in cenario["execucao"].results if r.item.canonical_key == "LANCE_MENOR_50_AVALIACAO"), None)
    if alvo is None:
        pytest.skip("checklist mestre sem o item LANCE_MENOR_50_AVALIACAO")
    finding = {"kind": "fato", "statement": "Pagamento à vista em 24 horas", "confidence": "ALTA", "checklist_key": "LANCE_MENOR_50_AVALIACAO", "checklist_state": "CONFIRMADO", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "à vista, em até 24 horas após o encerramento do leilão"}
    assert _checklist(db, cenario, dict(finding)) == []
    _persist(db, cenario, "juridico", dict(finding))
    assert alvo.state == "PENDENTE" and alvo.resolution_origin is None


def test_item_resolvido_por_regra_deterministica_a_partir_do_cadastro(db, cenario):
    prop, execucao = cenario["a"], cenario["execucao"]
    chave = "LANCE_MENOR_50_AVALIACAO"
    alvo = next((r for r in execucao.results if r.item.canonical_key == chave), None)
    if alvo is None:
        pytest.skip("checklist mestre sem o item LANCE_MENOR_50_AVALIACAO")
    db.add(models.Auction(property_id=prop.id, appraisal_value=Decimal("400000"), bid_value=Decimal("240000"), second_auction_value=Decimal("240000"), financial_assumptions={}))
    db.flush(); db.refresh(prop)
    assert chave in resolve_checklist_from_data(db, prop, execucao)
    assert alvo.state == "NAO_IDENTIFICADO" and alvo.resolution_origin == "REGRA_DETERMINISTICA"
    assert "60,0% da avaliação" in alvo.answer


def test_api_expoe_origem_e_vinculos_do_checklist(db, cenario):
    from fastapi.testclient import TestClient
    from backend.app.database import get_db
    from backend.app.main import app
    item = cenario["item"]
    _checklist(db, cenario, {"kind": "fato", "statement": "Pagamento à vista em 24 horas", "confidence": "ALTA", "checklist_key": item.item.canonical_key, "checklist_state": "CONFIRMADO", "chunk_ids": [cenario["chunk_a"].id], "evidence_excerpt": "à vista, em até 24 horas após o encerramento do leilão"})
    db.flush(); db.expire_all()      # como numa requisição nova: sem relacionamentos já carregados nesta sessão
    app.dependency_overrides[get_db] = lambda: db
    try:
        body = TestClient(app).get(f"/api/imoveis/{cenario['a'].id}").json()
    finally:
        app.dependency_overrides.pop(get_db, None)
    linha = next(r for r in body["checklist"] if r["canonical_key"] == item.item.canonical_key)
    assert linha["resolution_origin"] == "DOCUMENTO" and len(linha["evidence_ids"]) == 1
    ev = next(e for e in body["evidencias"] if e["id"] == linha["evidence_ids"][0])
    assert ev["origin"] == "DOCUMENTO" and ev["strength"] == "FORTE"
