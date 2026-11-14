"""ISOLAMENTO entre imóveis — testes NEGATIVOS (auditoria final de segurança, homologação v1.0.2).

Regra: o agente/consulta do imóvel A nunca recupera, cita ou persiste evidências do imóvel B.
Tudo aqui roda no PostgreSQL real, com o pipeline real de ingestão; nenhuma chamada à OpenAI.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.ai.agents import LegalAgent
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.main import app
from backend.app.privacy_context import aliaser_for_property
from backend.app.rag.checklist_retrieval import retrieve_for_checklist
from backend.app.rag.retriever import HybridRetriever, RetrieverFilters
from backend.app.rag.service import RAGService
from backend.app.services import create_analysis, create_execution, persist_agent_findings

TEXTO_A = ("Matrícula do imóvel alfa: consolidação da propriedade fiduciária registrada, marcador ALFAUNICO. " * 6).encode()
TEXTO_B = ("Matrícula do imóvel bravo: consolidação da propriedade fiduciária registrada, marcador BRAVOUNICO. " * 6).encode()


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _imovel(db, titulo):
    prop = models.Property(title=titulo, address="Rua X", city="São Paulo", state="SP", area_m2=60, bedrooms=2)
    db.add(prop); db.flush()
    return prop


def _doc(db, prop, conteudo, nome="matricula.txt", tipo="MATRICULA"):
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    version = DocumentPipeline(db).ingest(doc, conteudo, nome)
    return doc, version


def _chunks(db, version):
    return db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version.id).order_by(models.DocumentChunk.chunk_index).all()


@pytest.fixture
def dois(db):
    a, b = _imovel(db, "Imóvel A"), _imovel(db, "Imóvel B")
    doc_a, ver_a = _doc(db, a, TEXTO_A)
    doc_b, ver_b = _doc(db, b, TEXTO_B)
    return {"a": a, "b": b, "doc_a": doc_a, "doc_b": doc_b, "ver_a": ver_a, "ver_b": ver_b}


# ---------------------------------------------------------------- retriever

def test_busca_sem_imovel_e_recusada_por_padrao(db, dois):
    with pytest.raises(ValueError, match="property_id"):
        HybridRetriever(db).search("matrícula consolidação")
    with pytest.raises(ValueError):
        RAGService(db).retrieve_context("matrícula consolidação")
    # busca global só com pedido EXPLÍCITO (nenhum código da aplicação faz isso: ver teste estático abaixo)
    achados = HybridRetriever(db).search("matrícula consolidação", allow_global=True, limit=50)
    assert {c["property_id"] for c in achados} >= {dois["a"].id, dois["b"].id}


def test_imovel_a_nao_recupera_texto_exclusivo_do_imovel_b(db, dois):
    r = HybridRetriever(db)
    assert r.search("BRAVOUNICO", property_id=dois["a"].id) == []
    achados = r.search("consolidação fiduciária", property_id=dois["a"].id, limit=50)
    assert achados and {c["property_id"] for c in achados} == {dois["a"].id}
    assert all("BRAVOUNICO" not in c["content"] for c in achados)


def test_filtros_de_documento_e_versao_de_outro_imovel_nao_atravessam(db, dois):
    r = HybridRetriever(db)
    f = RetrieverFilters(property_id=dois["a"].id, document_id=dois["doc_b"].id)
    assert r.search("matrícula", property_id=dois["a"].id, filters=f) == []
    f2 = RetrieverFilters(property_id=dois["a"].id, document_type="MATRICULA", category="juridico", document_version=dois["ver_b"].version)
    achados = r.search("matrícula", property_id=dois["a"].id, filters=f2, limit=50)
    assert {c["property_id"] for c in achados} <= {dois["a"].id}


def test_property_id_do_argumento_prevalece_sobre_filtro_ausente(db, dois):
    achados = HybridRetriever(db).search("matrícula consolidação", property_id=dois["a"].id, filters=RetrieverFilters(category="juridico"), limit=50)
    assert achados and {c["property_id"] for c in achados} == {dois["a"].id}


def test_contingencia_posicional_nao_vaza_chunks_de_outro_imovel(db, dois):
    vazio = _imovel(db, "Imóvel sem documentos")
    r = RAGService(db).retrieve_context("análise documental do imóvel", property_id=vazio.id, filters=RetrieverFilters(property_id=vazio.id), broad=True)
    assert r.chunks == [] and r.positional_fallback is False
    r2 = RAGService(db).retrieve_context("análise documental do imóvel", property_id=dois["a"].id, filters=RetrieverFilters(property_id=dois["a"].id), broad=True)
    assert r2.chunks and {c["property_id"] for c in r2.chunks} == {dois["a"].id}


def test_busca_vetorial_tambem_e_isolada_por_imovel(db, dois):
    vetor = [1.0] + [0.0] * (settings.embedding_dimensions - 1)
    for chunk in _chunks(db, dois["ver_a"]) + _chunks(db, dois["ver_b"]):
        chunk.embedding = vetor          # B é IDÊNTICO ao vetor da consulta: o pior caso para vazamento
    db.flush()
    achados = HybridRetriever(db).search("qualquer coisa", embedding=vetor, property_id=dois["a"].id, limit=50)
    assert achados and {c["property_id"] for c in achados} == {dois["a"].id}


def test_rag_do_checklist_e_isolado_por_imovel(db, dois):
    itens = [{"canonical_key": "X", "question": "BRAVOUNICO marcador", "description": "BRAVOUNICO", "category": None, "expected_evidence": [], "related_rules": []}]
    assert retrieve_for_checklist(db, dois["a"].id, itens).chunk_ids == []
    itens_a = [{"canonical_key": "Y", "question": "consolidação da propriedade fiduciária", "description": "propriedade", "category": None, "expected_evidence": [], "related_rules": []}]
    direcionado = retrieve_for_checklist(db, dois["a"].id, itens_a)
    assert direcionado.chunk_ids and {c["property_id"] for c in direcionado.chunks} == {dois["a"].id}


# ---------------------------------------------------------------- histórico de versões

def test_busca_padrao_usa_so_a_versao_mais_recente_pronta(db):
    prop = _imovel(db, "Imóvel versões")
    doc, v1 = _doc(db, prop, ("Edital: valor de avaliação VALORANTIGO conforme laudo. " * 8).encode(), "edital.txt", "EDITAL")
    db.refresh(doc)
    v2 = DocumentPipeline(db).ingest(doc, ("Edital retificado: valor de avaliação VALORNOVO conforme laudo. " * 8).encode(), "edital.txt")
    assert v2.version == v1.version + 1
    r = HybridRetriever(db)
    achados = r.search("valor de avaliação", property_id=prop.id, limit=50)
    assert achados and {c["document_version"] for c in achados} == {v2.version}
    assert all("VALORANTIGO" not in c["content"] for c in achados)
    # a versão antiga continua acessível quando pedida explicitamente (auditoria/histórico)
    antigas = r.search("valor de avaliação", property_id=prop.id, filters=RetrieverFilters(property_id=prop.id, document_version=v1.version), limit=50)
    assert antigas and {c["document_version"] for c in antigas} == {v1.version}


def test_versao_nova_sem_texto_nao_esconde_a_anterior_pronta(db):
    prop = _imovel(db, "Imóvel versão nova sem texto")
    doc, v1 = _doc(db, prop, ("Matrícula com texto utilizável MARCADORV1 registrado. " * 8).encode())
    db.refresh(doc)
    pdf_sem_texto = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R/Size 4>>\n%%EOF\n"
    v2 = DocumentPipeline(db).ingest(doc, pdf_sem_texto, "matricula.pdf")
    assert v2.status == "OCR_NECESSARIO"
    achados = HybridRetriever(db).search("MARCADORV1 matrícula", property_id=prop.id, limit=50)
    assert achados and {c["document_version"] for c in achados} == {v1.version}


# ---------------------------------------------------------------- oportunidade

def test_filtro_de_oportunidade_exclui_outra_oportunidade_e_chunks_legados(db):
    prop = _imovel(db, "Imóvel oportunidades")
    _, ver = _doc(db, prop, ("Cláusula da oportunidade com termo comum compartilhado. " * 120).encode(), "o.txt")
    chunks = _chunks(db, ver)
    assert len(chunks) >= 3
    chunks[0].metadata_json = {**chunks[0].metadata_json, "opportunity_id": 1}
    chunks[1].metadata_json = {**chunks[1].metadata_json, "opportunity_id": 2}
    chunks[2].metadata_json = {k: v for k, v in chunks[2].metadata_json.items() if k != "opportunity_id"}   # legado
    db.flush()
    achados = HybridRetriever(db).search("termo comum compartilhado", property_id=prop.id, filters=RetrieverFilters(property_id=prop.id, opportunity_id=1), limit=50)
    assert {c["chunk_id"] for c in achados} == {chunks[0].id}


# ---------------------------------------------------------------- persistência de evidências (LLM = entrada não confiável)

def _execucao(db, prop):
    analise = create_analysis(db, prop, "teste", ["documental"], [], "teste", [])
    execucao = create_execution(db, prop, "TESTE", analise.version)
    return analise, execucao


@pytest.mark.parametrize("agente", ["documental", "juridico", "financeiro", "mercado"])
def test_chunk_citado_de_outro_imovel_nunca_vira_evidencia_nem_documento_considerado(db, dois, agente):
    chunk_b = _chunks(db, dois["ver_b"])[0]
    analise, execucao = _execucao(db, dois["a"])
    resultado = {"agent": agente, "retrieved_chunk_ids": [chunk_b.id], "facts": [
        {"kind": "fato", "statement": "afirmação sustentada por um trecho que NÃO é deste imóvel", "confidence": "ALTA", "chunk_ids": [chunk_b.id], "evidence_excerpt": "x"}]}
    persist_agent_findings(db, dois["a"], analise, execucao, [resultado])
    evidencias = db.query(models.Evidence).filter(models.Evidence.property_id == dois["a"].id).all()
    assert all(e.chunk_id != chunk_b.id and e.document_version_id != dois["ver_b"].id for e in evidencias)
    assert all("BRAVOUNICO" not in (e.source_excerpt or "") for e in evidencias)
    assert dois["doc_b"].id not in (analise.documents_considered or [])
    assert db.query(models.Evidence).filter(models.Evidence.property_id == dois["b"].id).count() == 0


def test_chunk_do_proprio_imovel_mas_fora_do_contexto_recuperado_e_descartado(db, dois):
    chunk_a = _chunks(db, dois["ver_a"])[0]
    analise, execucao = _execucao(db, dois["a"])
    fora = {"agent": "documental", "retrieved_chunk_ids": [999999999], "facts": [{"kind": "fato", "statement": "citação fora do contexto", "confidence": "ALTA", "chunk_ids": [chunk_a.id]}]}
    assert persist_agent_findings(db, dois["a"], analise, execucao, [fora]) == []


def test_controle_positivo_chunk_valido_do_imovel_e_do_contexto_gera_evidencia(db, dois):
    chunk_a = _chunks(db, dois["ver_a"])[0]
    analise, execucao = _execucao(db, dois["a"])
    ok = {"agent": "documental", "retrieved_chunk_ids": [chunk_a.id], "facts": [{"kind": "fato", "statement": "fato documentado", "confidence": "ALTA", "chunk_ids": [chunk_a.id]}]}
    ids = persist_agent_findings(db, dois["a"], analise, execucao, [ok])
    assert len(ids) == 1
    ev = db.get(models.Evidence, ids[0])
    assert ev.chunk_id == chunk_a.id and ev.property_id == dois["a"].id
    assert dois["doc_a"].id in analise.documents_considered


# ---------------------------------------------------------------- snapshot e pseudonimização por imóvel

def test_snapshot_dos_agentes_do_imovel_a_nao_contem_dados_do_b(db, dois):
    db.add(models.LegalProcess(property_id=dois["a"].id, number="1111111-11.2026.8.26.0001", polo_active="Condomínio Aurora", polo_passive="Maria Antonieta Souza"))
    db.add(models.LegalProcess(property_id=dois["b"].id, number="9999999-99.2026.8.26.0009", polo_active="Banco Beta S.A.", polo_passive="Joaquim Bernardo Pereira"))
    db.flush()
    db.refresh(dois["a"])
    snapshot = json.dumps(LegalAgent(db)._property_snapshot(dois["a"].id), ensure_ascii=False, default=str)
    assert "1111111-11" in snapshot
    for de_b in ("9999999-99", "Banco Beta", "Joaquim Bernardo", "bravo"):
        assert de_b not in snapshot


def test_apelidos_de_pessoas_sao_por_imovel(db, dois):
    db.add(models.PropertyRegistration(property_id=dois["a"].id, holder="Ana Paula Ferreira Lima"))
    db.add(models.PropertyRegistration(property_id=dois["b"].id, holder="Carlos Eduardo Nunes Prado"))
    db.flush()
    a, b = aliaser_for_property(db, dois["a"].id), aliaser_for_property(db, dois["b"].id)
    assert a.names == ["Ana Paula Ferreira Lima"] and b.names == ["Carlos Eduardo Nunes Prado"]
    assert "Carlos Eduardo" in a.apply("Carlos Eduardo Nunes Prado vendeu") and "Ana Paula" not in a.apply("Ana Paula Ferreira Lima")


# ---------------------------------------------------------------- HTTP (IDOR por rota)

@pytest.fixture
def client(postgres_engine):
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _http_imovel(c, titulo):
    r = c.post("/api/imoveis", json={"title": titulo, "address": "Rua H, 1", "city": "São Paulo", "state": "SP"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _http_documento(c, pid, texto: bytes):
    r = c.post(f"/api/imoveis/{pid}/documentos", files={"file": ("m.txt", texto, "text/plain")}, data={"document_type": "MATRICULA"})
    assert r.status_code == 200, r.text
    return r.json()["versions"][0]["id"]


def test_rotas_nao_aceitam_versao_chunk_ou_analise_de_outro_imovel(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    c, session = client
    a, b = _http_imovel(c, "HTTP A"), _http_imovel(c, "HTTP B")
    ver_b = _http_documento(c, b, TEXTO_B)
    chunk_b = session.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == ver_b).first()
    ver_a = _http_documento(c, a, TEXTO_A)

    assert c.get(f"/api/imoveis/{a}/documentos/{ver_b}/extracao").status_code == 404
    assert c.post(f"/api/imoveis/{a}/documentos/{ver_b}/extrair", json={"document_type": "MATRICULA"}).status_code == 400
    r = c.post(f"/api/imoveis/{a}/evidencias", json={"category": "X", "fact": "f", "document_version_id": ver_b, "chunk_id": chunk_b.id})
    assert r.status_code == 400
    r = c.post(f"/api/imoveis/{a}/evidencias", json={"category": "X", "fact": "f", "chunk_id": chunk_b.id})
    assert r.status_code == 400
    # chunk do próprio imóvel, mas de OUTRA versão do que foi informada => inconsistência recusada
    chunk_a = session.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == ver_a).first()
    r = c.post(f"/api/imoveis/{a}/evidencias", json={"category": "X", "fact": "f", "document_version_id": ver_a + 10_000, "chunk_id": chunk_a.id})
    assert r.status_code == 400
    # análise de B usada na rota de agente de A
    analise_b = c.post(f"/api/imoveis/{b}/analisar", json={}).json()
    hist = c.get(f"/api/imoveis/{b}/historico").json()["analises"][-1]["id"]
    antes = session.query(models.LLMRun).count()
    for agente in ("documental", "juridico", "financeiro", "mercado", "checklist"):
        assert c.post(f"/api/imoveis/{a}/analises/{hist}/agents/{agente}").status_code == 404
    assert session.query(models.LLMRun).count() == antes and analise_b["versao"] >= 1
    assert c.get(f"/api/imoveis/{a}/evidencias/999999").status_code == 404


# ---------------------------------------------------------------- contrato estático

def test_nenhum_codigo_da_aplicacao_faz_busca_global_nem_filtro_sem_imovel():
    raiz = Path(__file__).resolve().parents[1] / "backend" / "app"
    ofensores = []
    for arquivo in raiz.rglob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        if arquivo.name == "retriever.py":
            continue
        if re.search(r"allow_global\s*=\s*True", texto):
            ofensores.append(f"{arquivo.name}: allow_global=True")
        for m in re.finditer(r"RetrieverFilters\(\s*property_id\s*=\s*None", texto):
            if arquivo.name != "graph.py":
                ofensores.append(f"{arquivo.name}: RetrieverFilters(property_id=None)")
    assert ofensores == []
