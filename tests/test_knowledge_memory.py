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
    assert "LLMGateway" not in source
    assert "RAGService" not in source
    assert "embedding=" in source
