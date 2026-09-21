from types import SimpleNamespace

import pytest

from backend.app import models
from backend.app.knowledge_memory import KNOWLEDGE_CASE_KINDS, KnowledgeMemoryService


class Db:
    def __init__(self):
        self.items = []
        self.commits = 0

    def add(self, item):
        item.id = len(self.items) + 1
        self.items.append(item)

    def flush(self):
        pass

    def get(self, model, identifier):
        if model is models.KnowledgeItem:
            return next((item for item in self.items if item.id == identifier), None)
        return None

    def scalars(self, statement):
        kind = None
        criteria = getattr(statement, "_where_criteria", ())
        if criteria:
            kind = getattr(getattr(criteria[0], "right", None), "value", None)
        items = [item for item in self.items if kind is None or item.kind == kind]
        class Result:
            def __init__(self, items):
                self.items = items
            def all(self):
                return list(reversed(self.items))
        return Result(items)


def test_adiciona_recupera_e_preserva_case():
    db = Db()
    service = KnowledgeMemoryService(db)
    item = service.add_case("CASE_ANALYSIS", "Análise V1", "Conteúdo estruturado", {"property_id": 1, "analysis_version": 1, "risk_ids": [2]})
    assert item.id == 1
    assert item.kind == "CASE_ANALYSIS"
    assert item.title == "Análise V1"
    assert item.content == "Conteúdo estruturado"
    assert item.metadata_json == {"property_id": 1, "analysis_version": 1, "risk_ids": [2]}
    assert item.embedding is None
    assert service.get_case(1) is item


def test_lista_cases_com_filtro_de_tipo():
    db = Db()
    service = KnowledgeMemoryService(db)
    service.add_case("CASE_ANALYSIS", "A", "a")
    service.add_case("CASE_OUTCOME", "B", "b")
    service.add_case("CASE_ANALYSIS", "C", "c")
    assert [item.title for item in service.list_cases()] == ["C", "B", "A"]
    assert [item.title for item in service.list_cases("CASE_ANALYSIS")] == ["C", "A"]


def test_tipos_permitidos_e_tipo_invalido():
    db = Db()
    service = KnowledgeMemoryService(db)
    for kind in KNOWLEDGE_CASE_KINDS:
        service.add_case(kind, kind, "conteúdo")
    with pytest.raises(ValueError):
        service.add_case("TIPO_INVENTADO", "Título", "Conteúdo")
    with pytest.raises(ValueError):
        service.list_cases("TIPO_INVENTADO")


def test_validacoes_de_conteudo_e_metadata():
    service = KnowledgeMemoryService(Db())
    with pytest.raises(ValueError):
        service.add_case("CASE_ANALYSIS", "", "conteúdo")
    with pytest.raises(ValueError):
        service.add_case("CASE_ANALYSIS", "título", "")
    with pytest.raises(TypeError):
        service.add_case("CASE_ANALYSIS", "título", "conteúdo", ["não", "objeto"])


def test_operacoes_sao_deterministicas_e_nao_dependem_de_ia():
    db = Db()
    service = KnowledgeMemoryService(db)
    first = service.add_case("RULE_LEARNING", "Regra", "Texto", {"state": "ATENCAO"})
    second = service.add_case("RULE_LEARNING", "Regra", "Texto", {"state": "ATENCAO"})
    assert first.title == second.title
    assert first.content == second.content
    import inspect
    from backend.app import knowledge_memory
    source = inspect.getsource(knowledge_memory)
    assert "OpenAIProvider" not in source
    assert "RAGService" not in source
    assert "embedding=" in source


class SearchDb:
    def __init__(self, items):
        self.items = items
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        limit = getattr(getattr(statement, "_limit_clause", None), "value", None)
        items = self.items[:limit] if limit is not None else self.items
        class Result:
            def all(self):
                return items
        return Result()


def search_items():
    return [
        models.KnowledgeItem(id=1, kind="CASE_ANALYSIS", title="Análise Curitiba", content="caso de imóvel", metadata_json={"city": "Curitiba", "state": "PR", "verdict": "ATENCAO", "property_type": "Apartamento", "auction_stage": "2º leilão"}),
        models.KnowledgeItem(id=2, kind="CASE_OUTCOME", title="Resultado São Paulo", content="outcome documentado", metadata_json={"city": "São Paulo", "state": "SP", "verdict": "FAVORAVEL", "property_type": "Casa", "auction_stage": "1º leilão"}),
    ]


def test_search_cases_aplica_filtros_metadata_e_kind():
    db = SearchDb(search_items())
    items = KnowledgeMemoryService(db).search_cases(kind="CASE_ANALYSIS", property_type="Apartamento", city="Curitiba", state="PR", auction_stage="2º leilão", verdict="ATENCAO")
    assert items
    sql = str(db.statement)
    assert "metadata_json" in sql
    assert "CASE_ANALYSIS" in str(db.statement.compile().params.values())


def test_search_cases_busca_textual_em_title_content_e_limita():
    db = SearchDb(search_items())
    items = KnowledgeMemoryService(db).search_cases(query="resultado documentado", limit=1)
    assert len(items) == 1
    assert "to_tsvector" in str(db.statement)
    assert "plainto_tsquery" in str(db.statement)


def test_search_cases_sem_resultado_e_limit_invalido():
    db = SearchDb([])
    assert KnowledgeMemoryService(db).search_cases(query="inexistente") == []
    with pytest.raises(ValueError):
        KnowledgeMemoryService(db).search_cases(limit=0)
    with pytest.raises(ValueError):
        KnowledgeMemoryService(db).search_cases(limit=101)


def test_search_cases_isola_state_e_ordena_deterministicamente():
    db = SearchDb([search_items()[0]])
    items = KnowledgeMemoryService(db).search_cases(state="SP")
    assert items
    assert "SP" in str(db.statement.compile().params.values())
    assert "created_at" in str(db.statement)


class EmbeddingProvider:
    def __init__(self, vectors=None, error=None):
        self.vectors = vectors
        self.error = error
        self.texts = []
    def embed(self, texts):
        self.texts.extend(texts)
        if self.error:
            raise self.error
        return self.vectors


def vector(size=None):
    from backend.app.config import settings
    return [0.25] * (size or settings.embedding_dimensions)


def test_embed_case_gera_persiste_e_usa_title_content():
    db = Db()
    service = KnowledgeMemoryService(db)
    item = service.add_case("CASE_ANALYSIS", "Título", "Conteúdo do caso")
    provider = EmbeddingProvider([vector()])
    updated = service.embed_case(item, provider)
    assert updated is item
    assert item.embedding == vector()
    assert provider.texts == ["Título\n\nConteúdo do caso"]


def test_embed_case_rejeita_dimensao_incorreta_sem_limpar_item():
    db = Db()
    service = KnowledgeMemoryService(db)
    item = service.add_case("CASE_ANALYSIS", "Título", "Conteúdo")
    with pytest.raises(ValueError):
        service.embed_case(item, EmbeddingProvider([vector(3)]))
    assert item in db.items
    assert item.embedding is None


def test_embed_case_preserva_embedding_anterior_se_provider_falhar():
    db = Db()
    service = KnowledgeMemoryService(db)
    item = service.add_case("CASE_ANALYSIS", "Título", "Conteúdo")
    previous = vector()
    item.embedding = previous
    with pytest.raises(RuntimeError):
        service.embed_case(item, EmbeddingProvider(error=RuntimeError("falha provider")))
    assert item.embedding == previous


def test_embed_case_inexistente_retorna_none():
    assert KnowledgeMemoryService(Db()).embed_case(999, EmbeddingProvider([vector()])) is None


def test_embed_case_provider_retorna_quantidade_invalida():
    db = Db()
    item = KnowledgeMemoryService(db).add_case("CASE_OUTCOME", "Título", "Conteúdo")
    with pytest.raises(ValueError):
        KnowledgeMemoryService(db).embed_case(item, EmbeddingProvider([]))


class SimilarDb:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        limit = getattr(getattr(statement, "_limit_clause", None), "value", None)
        rows = self.rows[:limit] if limit is not None else self.rows

        class Result:
            def all(self):
                return rows

        return Result()


def test_search_similar_gera_embedding_retorna_distancia_e_ordena():
    items = [
        models.KnowledgeItem(id=2, kind="CASE_ANALYSIS", title="Mais distante", content="caso", metadata_json={}, embedding=vector()),
        models.KnowledgeItem(id=1, kind="CASE_OUTCOME", title="Mais similar", content="caso", metadata_json={}, embedding=vector()),
    ]
    db = SimilarDb([(items[1], 0.05), (items[0], 0.80)])
    provider = EmbeddingProvider([vector()])

    results = KnowledgeMemoryService(db).search_similar("imóvel ocupado em Curitiba", gateway=provider)

    assert [item.title for item, _ in results] == ["Mais similar", "Mais distante"]
    assert [distance for _, distance in results] == [0.05, 0.80]
    assert provider.texts == ["imóvel ocupado em Curitiba"]
    sql = str(db.statement)
    assert "<=>" in sql
    assert "embedding IS NOT NULL" in sql
    assert "distance" in sql


def test_search_similar_aplica_filtro_state_no_banco_e_ignora_embedding_null():
    item = models.KnowledgeItem(id=1, kind="CASE_ANALYSIS", title="Curitiba", content="caso", metadata_json={"state": "PR"}, embedding=vector())
    db = SimilarDb([(item, 0.1)])
    service = KnowledgeMemoryService(db)

    results = service.search_similar("imóvel ocupado", state="PR", gateway=EmbeddingProvider([vector()]))

    assert results == [(item, 0.1)]
    sql = str(db.statement)
    assert "metadata_json" in sql
    assert "embedding IS NOT NULL" in sql
    assert "PR" in str(db.statement.compile().params.values())


def test_search_similar_combina_filtros_estruturados_e_limita():
    item = models.KnowledgeItem(id=1, kind="CASE_ANALYSIS", title="Apartamento Curitiba", content="caso", metadata_json={"property_type": "Apartamento", "city": "Curitiba", "state": "PR", "auction_stage": "2º leilão", "verdict": "ATENCAO"}, embedding=vector())
    db = SimilarDb([(item, 0.1), (item, 0.2)])

    results = KnowledgeMemoryService(db).search_similar(
        "imóvel ocupado",
        limit=1,
        kind="CASE_ANALYSIS",
        property_type="Apartamento",
        city="Curitiba",
        state="PR",
        auction_stage="2º leilão",
        verdict="ATENCAO",
        gateway=EmbeddingProvider([vector()]),
    )

    assert len(results) == 1
    compiled = db.statement.compile()
    params = str(compiled.params.values())
    assert all(value in params for value in ["CASE_ANALYSIS", "Apartamento", "Curitiba", "PR", "2º leilão", "ATENCAO"])
    assert "ORDER BY" in str(db.statement)
    assert "distance" in str(db.statement)


def test_search_similar_valida_limit_e_dimensao_do_embedding():
    service = KnowledgeMemoryService(SimilarDb([]))
    provider = EmbeddingProvider([vector()])
    with pytest.raises(ValueError):
        service.search_similar("consulta", limit=0, gateway=provider)
    with pytest.raises(ValueError):
        service.search_similar("consulta", limit=101, gateway=provider)
    with pytest.raises(ValueError):
        service.search_similar("consulta", gateway=EmbeddingProvider([vector(3)]))


def test_search_similar_propagates_falha_do_provider_sem_resultados_falsos():
    db = SimilarDb([])
    with pytest.raises(RuntimeError, match="falha provider"):
        KnowledgeMemoryService(db).search_similar(
            "consulta",
            gateway=EmbeddingProvider(error=RuntimeError("falha provider")),
        )
    assert db.statement is None


def test_search_similar_nao_adiciona_rag_llm_de_interpretacao_ou_reranking():
    import inspect
    from backend.app import knowledge_memory

    source = inspect.getsource(knowledge_memory.KnowledgeMemoryService.search_similar)
    assert "RAG" not in source
    assert "LangGraph" not in source
    assert "rerank" not in source.lower()
    assert "plainto_tsquery" not in source
    assert "cosine_distance" in source


class HybridDb:
    def __init__(self, textual_items, semantic_rows):
        self.textual_items = textual_items
        self.semantic_rows = semantic_rows
        self.text_statement = None
        self.semantic_statement = None

    def scalars(self, statement):
        self.text_statement = statement
        limit = getattr(getattr(statement, "_limit_clause", None), "value", None)
        items = self.textual_items[:limit] if limit is not None else self.textual_items

        class Result:
            def all(self):
                return items

        return Result()

    def execute(self, statement):
        self.semantic_statement = statement
        limit = getattr(getattr(statement, "_limit_clause", None), "value", None)
        rows = self.semantic_rows[:limit] if limit is not None else self.semantic_rows

        class Result:
            def all(self):
                return rows

        return Result()


def hybrid_items():
    return [
        models.KnowledgeItem(id=1, kind="CASE_ANALYSIS", title="Somente textual", content="caso textual", metadata_json={"state": "PR"}),
        models.KnowledgeItem(id=2, kind="CASE_OUTCOME", title="Textual e semântico", content="caso combinado", metadata_json={"state": "PR"}),
        models.KnowledgeItem(id=3, kind="CASE_ANALYSIS", title="Somente semântico", content="caso vetorial", metadata_json={"state": "PR"}, embedding=vector()),
    ]


def test_search_hybrid_consolida_origens_e_preserva_distancia():
    items = hybrid_items()
    db = HybridDb(items[:2], [(items[2], 0.10), (items[1], 0.25)])

    results = KnowledgeMemoryService(db).search_hybrid(
        "imóvel ocupado em Curitiba",
        gateway=EmbeddingProvider([vector()]),
    )

    assert [result["item"].id for result in results] == [1, 2, 3]
    assert results[0]["origin"] == "textual"
    assert results[0]["text_match"] is True
    assert results[0]["distance"] is None
    assert results[1]["origin"] == "both"
    assert results[1]["text_match"] is True
    assert results[1]["distance"] == 0.25
    assert results[2]["origin"] == "semantic"
    assert results[2]["text_match"] is False
    assert results[2]["distance"] == 0.10


def test_search_hybrid_aplica_filtros_nas_duas_buscas():
    items = hybrid_items()
    db = HybridDb(items[:1], [(items[2], 0.2)])

    KnowledgeMemoryService(db).search_hybrid(
        "imóvel ocupado",
        kind="CASE_ANALYSIS",
        property_type="Apartamento",
        city="Curitiba",
        state="PR",
        auction_stage="2º leilão",
        verdict="ATENCAO",
        gateway=EmbeddingProvider([vector()]),
    )

    text_params = str(db.text_statement.compile().params.values())
    semantic_params = str(db.semantic_statement.compile().params.values())
    expected = ["CASE_ANALYSIS", "Apartamento", "Curitiba", "PR", "2º leilão", "ATENCAO"]
    assert all(value in text_params for value in expected)
    assert all(value in semantic_params for value in expected)


def test_search_hybrid_valida_limit_e_limita_resultado_consolidado():
    items = hybrid_items()
    db = HybridDb(items, [(items[2], 0.1)])
    service = KnowledgeMemoryService(db)

    assert len(service.search_hybrid("consulta", limit=2, gateway=EmbeddingProvider([vector()]))) == 2
    with pytest.raises(ValueError):
        service.search_hybrid("consulta", limit=0, gateway=EmbeddingProvider([vector()]))
    with pytest.raises(ValueError):
        service.search_hybrid("consulta", limit=101, gateway=EmbeddingProvider([vector()]))


def test_search_hybrid_propagates_erro_de_embedding():
    items = hybrid_items()
    db = HybridDb(items[:1], [])

    with pytest.raises(RuntimeError, match="falha provider"):
        KnowledgeMemoryService(db).search_hybrid(
            "consulta",
            gateway=EmbeddingProvider(error=RuntimeError("falha provider")),
        )


def test_search_hybrid_nao_implementa_rag_score_ou_reranking():
    import inspect
    from backend.app import knowledge_memory

    source = inspect.getsource(knowledge_memory.KnowledgeMemoryService.search_hybrid)
    assert "RAG" not in source
    assert "LangGraph" not in source
    assert "score" not in source.lower()
    assert "rerank" not in source.lower()
    assert "search_cases" in source
    assert "search_similar" in source
