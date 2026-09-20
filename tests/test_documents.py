import asyncio
from io import BytesIO
from pathlib import Path
import pytest
from fastapi import HTTPException, UploadFile

from backend.app import models
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.config import settings

class FakeDb:
    def __init__(self, prop=None, document=None): self.prop = prop; self.document = document; self.added = []
    def get(self, model, identifier):
        if model is models.Document: return self.document
        return self.prop
    def add(self, item):
        if isinstance(item, models.Document) and item.id is None:
            item.id = len([x for x in self.added if isinstance(x, models.Document)]) + 1
            if self.prop is not None and item not in self.prop.documents: self.prop.documents.append(item)
            self.document = item
        if isinstance(item, models.DocumentVersion):
            item.id = len([x for x in self.added if isinstance(x, models.DocumentVersion)]) + 1
            document = self.document or self.prop.documents[-1]
            if item not in document.versions: document.versions.append(item)
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self, item): return None
    def scalars(self, statement):
        class Result:
            def __init__(self, values): self.values = values
            def all(self): return self.values
        return Result(self.prop.documents if self.prop else [])

def property_stub():
    prop = models.Property(id=1, title="Imóvel Documento", address="Rua Documento", city="São Paulo", state="SP")
    return prop

def upload(name, content):
    return UploadFile(filename=name, file=BytesIO(content))

def test_pipeline_cria_primeira_e_segunda_versao_com_hash(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", lambda self, path, document_type: (path.read_text(encoding="utf-8"), {"engine": "fake"}))
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    db = FakeDb(property_stub())
    document = models.Document(id=1, property_id=1, name="edital.txt", document_type="EDITAL", source="Manual")
    db.prop.documents.append(document)
    first = DocumentPipeline(db).ingest(document, b"versao um", "edital.txt")
    second = DocumentPipeline(db).ingest(document, b"versao dois", "edital.txt")
    assert first.version == 1
    assert second.version == 2
    assert first.content_hash != second.content_hash
    assert Path(first.original_path).exists()
    assert Path(second.original_path).exists()
    assert first.original_path != second.original_path
    assert document.status == "PROCESSADO"

def test_upload_com_tipo_source_evento_e_historico(monkeypatch, tmp_path):
    from backend.app.main import upload_document
    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", lambda self, path, document_type: (path.read_text(encoding="utf-8"), {"engine": "fake"}))
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    prop = property_stub(); prop.documents = []
    db = FakeDb(prop)
    result = asyncio.run(upload_document(1, upload("matricula.txt", b"matricula"), "MATRICULA", "Cartorio", db))
    assert result["document_type"] == "MATRICULA"
    assert result["source"] == "Cartorio"
    assert result["versions"][0]["version"] == 1
    assert result["versions"][0]["content_hash"]
    event = next(item for item in db.added if isinstance(item, models.DomainEvent))
    assert event.event_type == "DOCUMENTO_ADICIONADO"
    assert event.affected_domains == ["documental", "juridico", "checklist"]
    history = next(item for item in db.added if isinstance(item, models.EntityHistory))
    assert history.entity_type == "DocumentVersion"

def test_nova_versao_preserva_tipo_source_e_anteriores(monkeypatch, tmp_path):
    from backend.app.main import add_document_version
    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", lambda self, path, document_type: (path.read_text(encoding="utf-8"), {"engine": "fake"}))
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    prop = property_stub(); document = models.Document(id=1, property_id=1, name="edital.txt", document_type="EDITAL", source="Manual")
    db = FakeDb(prop, document); prop.documents.append(document)
    result = asyncio.run(add_document_version(1, upload("edital.txt", b"dois"), None, None, db))
    assert result["document_type"] == "EDITAL"
    assert result["source"] == "Manual"
    assert [version["version"] for version in result["versions"]] == [1, 2]
    assert result["versions"][0]["content_hash"] != result["versions"][1]["content_hash"]

def test_extensao_invalida():
    from backend.app.main import upload_document
    prop = property_stub(); db = FakeDb(prop)
    with pytest.raises(HTTPException) as error:
        asyncio.run(upload_document(1, upload("arquivo.exe", b"conteudo"), None, None, db))
    assert error.value.status_code == 400

def test_documento_inexistente_na_nova_versao():
    from backend.app.main import add_document_version
    with pytest.raises(HTTPException) as error:
        asyncio.run(add_document_version(999, upload("doc.txt", b"conteudo"), None, None, FakeDb(property_stub(), None)))
    assert error.value.status_code == 404

def test_get_documentos_sem_documentos():
    from backend.app.main import list_documents
    prop = property_stub(); prop.documents = []
    result = list_documents(1, FakeDb(prop))
    assert result["documentos"] == []
