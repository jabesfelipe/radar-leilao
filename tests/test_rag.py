import pytest

from backend.app.rag.retriever import HybridRetriever, RetrieverFilters, calculate_final_score
from backend.app.rag.service import RAGService


def test_ranking_normaliza_scores_e_aplica_pesos():
    assert calculate_final_score(1.0, 0.0, 1.0) == pytest.approx(0.7)
    assert calculate_final_score(0.0, 10.0, 10.0) == pytest.approx(0.3)
    assert calculate_final_score(0.0, 5.0, 10.0) == pytest.approx(0.15)


def test_ranking_rejeita_pesos_invalidos():
    with pytest.raises(ValueError):
        calculate_final_score(1, 1, 1, 0, 0)


def test_busca_textual_sem_api_key_e_isolada_por_imovel(db, documents, monkeypatch):
    monkeypatch.setattr("backend.app.rag.service.build_gateway", lambda: (_ for _ in ()).throw(RuntimeError("sem chave")))
    result = RAGService(db).retrieve_context("matrícula consolidada", property_id=documents["property_a"])
    assert result.context_found is True
    assert result.text_fallback is True
    assert result.vector_search is False
    assert result.chunk_ids
    assert all(chunk["property_id"] == documents["property_a"] for chunk in result.chunks)
    assert all("beta" not in chunk["content"] for chunk in result.chunks)


def test_busca_vetorial_e_combinacao_texto(db, documents):
    query_embedding = [1.0] + [0.0] * 1535
    results = HybridRetriever(db).search("matrícula consolidada", query_embedding, property_id=documents["property_a"])
    assert results
    assert results[0]["document_id"] == documents["document_a"]
    assert results[0]["vector_score"] > 0
    assert 0 <= results[0]["normalized_text_score"] <= 1
    assert results[0]["final_score"] == pytest.approx(results[0]["vector_score"] * 0.7 + results[0]["normalized_text_score"] * 0.3)


def test_filtros_documento_tipo_versao_e_categoria(db, documents):
    results = HybridRetriever(db).search("matrícula", property_id=documents["property_a"], filters=RetrieverFilters(property_id=documents["property_a"], document_id=documents["document_a"], document_type="Matrícula", document_version=1, category="juridico"))
    assert len(results) == 1
    assert results[0]["document_id"] == documents["document_a"]
    assert results[0]["document_version"] == 1
    assert results[0]["document_type"] == "Matrícula"


def test_limite_e_metadata_completa(db, documents):
    results = HybridRetriever(db).search("matrícula imóvel", property_id=documents["property_a"], limit=1)
    assert len(results) == 1
    required = {"chunk_id", "document_id", "document_version_id", "document_version", "document_type", "property_id", "page", "section", "vector_score", "text_score", "final_score", "metadata_json"}
    assert required.issubset(results[0])


def test_ausencia_de_contexto_e_motivo(db, documents, monkeypatch):
    monkeypatch.setattr("backend.app.rag.service.build_gateway", lambda: (_ for _ in ()).throw(RuntimeError("sem chave")))
    result = RAGService(db).retrieve_context("termo inexistente no dossiê", property_id=documents["property_a"])
    assert result.context_found is False
    assert result.chunks == []
    assert result.chunk_ids == []
    assert result.reason == "evidência insuficiente"


def test_isolamento_impede_documento_de_outro_imovel(db, documents):
    results = HybridRetriever(db).search("matrícula consolidada", property_id=documents["property_a"], limit=8)
    assert {result["property_id"] for result in results} == {documents["property_a"]}
    assert documents["property_b"] not in {result["property_id"] for result in results}


def test_sql_usa_cte_e_preserva_isolamento_com_filtros_combinados():
    class Result:
        def mappings(self): return self
        def all(self): return []

    class CaptureSession:
        def __init__(self): self.statement = ""; self.params = {}
        def execute(self, statement, params):
            self.statement = str(statement)
            self.params = params
            return Result()

    from backend.app.rag.retriever import RetrieverFilters
    session = CaptureSession()
    HybridRetriever(session).search("matrícula", property_id=41, filters=RetrieverFilters(document_type="Matrícula"))
    assert "WITH candidates AS" in session.statement
    assert "ORDER BY final_score" in session.statement
    assert "d.property_id = :property_id" in session.statement
    assert "d.document_type = :document_type" in session.statement
    assert session.params["property_id"] == 41
    assert session.params["document_type"] == "Matrícula"
