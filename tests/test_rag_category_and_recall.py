"""RAG: persistência de ``category``/``domains`` nos chunks e recuperação contextual (P0 — homologação v1.0.2).

Bug original (reproduzido na homologação): o retriever filtrava ``metadata_json->>'category'``, mas a
ingestão nunca gravava ``category``; toda busca por domínio retornava 0 chunks. Além disso, a consulta
padrão ("análise documental do imóvel") exigia TODOS os termos (AND) e não achava a matrícula.
Pipeline e PostgreSQL reais; sem chave (busca por texto).
"""
from __future__ import annotations

import pytest

from backend.app import models
from backend.app.ai.graph import DEFAULT_RAG_QUERY
from backend.app.config import settings
from backend.app.documents import categories
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.rag.retriever import HybridRetriever, RetrieverFilters, build_or_tsquery
from backend.app.rag.service import RAGService

MATRICULA = ("Matrícula consolidada em nome do credor fiduciário, averbação AV-3, sem penhoras. " * 6).encode()


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _ingest(db, tipo, conteudo=MATRICULA, nome="d.txt", prop=None):
    if prop is None:
        prop = models.Property(title="Imóvel RAG", address="Rua R", city="São Paulo", state="SP", area_m2=60, bedrooms=2)
        db.add(prop); db.flush()
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    version = DocumentPipeline(db).ingest(doc, conteudo, nome)
    return prop, doc, version


def _chunks(db, version):
    return db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version.id).all()


def test_mapa_de_dominios_por_tipo_de_documento():
    assert categories.domains_for("MATRICULA")[0] == "documental" and "juridico" in categories.domains_for("Matrícula")
    assert "financeiro" in categories.domains_for("EDITAL")
    assert categories.domains_for("Laudo de avaliação")[0] == "mercado"
    assert categories.domains_for("Foto da fachada") == list(categories.DOMAINS)  # desconhecido: serve a todos
    assert categories.domains_for(None) == list(categories.DOMAINS)


def test_ingestao_grava_category_e_domains_em_todos_os_chunks(db):
    _, _, version = _ingest(db, "MATRICULA")
    chunks = _chunks(db, version)
    assert chunks
    for chunk in chunks:
        assert chunk.metadata_json["category"] == "documental"
        assert "juridico" in chunk.metadata_json["domains"] and "mercado" not in chunk.metadata_json["domains"]


def test_filtro_por_dominio_recupera_chunks_do_dominio_correto(db):
    prop, _, _ = _ingest(db, "MATRICULA")
    r = HybridRetriever(db)
    for dominio in ("juridico", "documental", "checklist"):
        achados = r.search("matrícula consolidada", property_id=prop.id, filters=RetrieverFilters(property_id=prop.id, category=dominio))
        assert achados, f"domínio {dominio} deveria encontrar a matrícula (antes: 0 chunks)"
    # domínio ao qual a matrícula NÃO serve: não retorna
    assert r.search("matrícula consolidada", property_id=prop.id, filters=RetrieverFilters(property_id=prop.id, category="mercado")) == []


def test_chunk_legado_sem_category_continua_visivel_ao_filtro(db):
    prop, _, version = _ingest(db, "MATRICULA")
    for chunk in _chunks(db, version):
        chunk.metadata_json = {"document_type": "MATRICULA"}  # como ingerido ANTES da correção
    db.flush()
    achados = HybridRetriever(db).search("matrícula consolidada", property_id=prop.id, filters=RetrieverFilters(property_id=prop.id, category="juridico"))
    assert achados


def test_consulta_padrao_encontra_documento_com_outras_palavras_via_or(db):
    """Texto sem 'análise'/'documental' mas com 'imóvel': antes (AND) => 0; agora (OR) => encontra por texto."""
    prop, _, _ = _ingest(db, "MATRICULA", ("O imóvel está livre de ônus e gravames conhecidos. " * 8).encode())
    r = RAGService(db).retrieve_context(DEFAULT_RAG_QUERY, property_id=prop.id, filters=RetrieverFilters(property_id=prop.id, category="juridico"), broad=True)
    assert r.context_found and r.positional_fallback is False
    assert {c["match_type"] for c in r.chunks} == {"texto"}


def test_sem_nenhuma_correspondencia_a_contingencia_posicional_e_explicita(db):
    prop, _, _ = _ingest(db, "MATRICULA", ("Cláusula alfa beta gama delta. " * 10).encode())
    r = RAGService(db).retrieve_context(DEFAULT_RAG_QUERY, property_id=prop.id, filters=RetrieverFilters(property_id=prop.id), broad=True)
    assert r.context_found and r.positional_fallback is True
    assert {c["match_type"] for c in r.chunks} == {"posicional"} and all(c["final_score"] == 0 for c in r.chunks)
    assert "contingência" in r.reason and "não é resultado de relevância" in r.reason


def test_consulta_explicita_continua_estrita_e_nao_inventa_contexto(db):
    prop, _, _ = _ingest(db, "MATRICULA", ("Cláusula alfa beta gama delta. " * 10).encode())
    r = RAGService(db).retrieve_context("termo totalmente inexistente xyzqwk", property_id=prop.id)
    assert r.context_found is False and r.chunks == [] and r.reason == "evidência insuficiente"


def test_fallback_posicional_respeita_isolamento_por_imovel_e_dominio(db):
    prop_a, _, _ = _ingest(db, "MATRICULA", ("Cláusula alfa beta gama. " * 10).encode())
    prop_b, _, _ = _ingest(db, "MATRICULA", ("Cláusula alfa beta gama. " * 10).encode(), nome="b.txt")
    r = RAGService(db).retrieve_context(DEFAULT_RAG_QUERY, property_id=prop_a.id, filters=RetrieverFilters(property_id=prop_a.id, category="juridico"), broad=True)
    assert r.chunks and {c["property_id"] for c in r.chunks} == {prop_a.id} and prop_b.id not in {c["property_id"] for c in r.chunks}
    mercado = RAGService(db).retrieve_context(DEFAULT_RAG_QUERY, property_id=prop_a.id, filters=RetrieverFilters(property_id=prop_a.id, category="mercado"), broad=True)
    assert mercado.chunks == []  # matrícula não serve ao domínio mercado, nem na contingência


def test_or_tsquery_e_seguro_contra_operadores():
    assert build_or_tsquery("análise & documental | !imóvel (x) 'y'") == "análise | documental | imóvel"
    assert build_or_tsquery("!!! ()") is None
