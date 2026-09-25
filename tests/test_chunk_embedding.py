"""Testes da geração/persistência de embedding de DocumentChunk na ingestão (TASK 66).

Cobrem o comportamento novo sem enfraquecer os testes existentes:
- chunk novo recebe embedding e ele fica persistido no chunk correto;
- documento com múltiplos chunks;
- ausência de API key (ingestão segue por texto, sem gerar embedding);
- falha do provider não quebra a ingestão;
- idempotência: chunk já vetorizado não gera embedding de novo;
- página/document_version/metadata preservados;
- chunk pode ser recuperado por similaridade vetorial pelo HybridRetriever;
- regressão do pipeline (fluxo existente continua funcionando).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.app import models
from backend.app.config import settings
from backend.app.documents import embedding as embedding_module
from backend.app.documents.embedding import embed_pending_chunks
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.rag.retriever import HybridRetriever


DIM = settings.embedding_dimensions


def _vector(seed: float = 1.0) -> list[float]:
    return [seed] + [0.0] * (DIM - 1)


class FakeGateway:
    """Gateway falso: registra as chamadas e devolve vetores de dimensão correta."""

    def __init__(self, vector_factory=None, fail: bool = False):
        self.calls: list[list[str]] = []
        self.fail = fail
        self.vector_factory = vector_factory or (lambda texts: [_vector(1.0) for _ in texts])

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        if self.fail:
            raise RuntimeError("provider de embedding indisponível")
        return self.vector_factory(texts)


class FakeChunk:
    def __init__(self, content: str, embedding=None):
        self.content = content
        self.embedding = embedding


class FakeQuery:
    """Emula query(DocumentChunk).filter(version==, embedding.is_(None)).all()."""

    def __init__(self, chunks: list[FakeChunk]):
        self._chunks = chunks

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        # Idempotência: só retorna os que ainda não possuem vetor.
        return [chunk for chunk in self._chunks if chunk.embedding is None]


class FakeDb:
    def __init__(self, chunks: list[FakeChunk]):
        self._chunks = chunks
        self.flushed = 0

    def query(self, *args, **kwargs):
        return FakeQuery(self._chunks)

    def flush(self):
        self.flushed += 1


@pytest.fixture(autouse=True)
def _com_api_key(monkeypatch):
    # Por padrão nestes testes há "chave" (o gateway é falso, sem rede).
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-fake", raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)


def test_chunk_novo_recebe_embedding_persistido_dimensao_correta(monkeypatch):
    gateway = FakeGateway()
    monkeypatch.setattr(embedding_module, "build_gateway", lambda: gateway)
    chunk = FakeChunk("registro de imóveis matrícula 25278")
    db = FakeDb([chunk])

    telemetry = embed_pending_chunks(db, version_id=42)

    assert chunk.embedding is not None
    assert len(chunk.embedding) == DIM
    assert telemetry["embeddings_solicitados"] == 1
    assert telemetry["embeddings_persistidos"] == 1
    assert telemetry["embeddings_falhos"] == 0
    assert telemetry["dimensao"] == DIM
    assert db.flushed >= 1


def test_documento_com_multiplos_chunks_todos_recebem_embedding(monkeypatch):
    gateway = FakeGateway()
    monkeypatch.setattr(embedding_module, "build_gateway", lambda: gateway)
    chunks = [FakeChunk(f"conteúdo do chunk {i}") for i in range(4)]
    db = FakeDb(chunks)

    telemetry = embed_pending_chunks(db, version_id=7)

    assert all(chunk.embedding is not None and len(chunk.embedding) == DIM for chunk in chunks)
    assert telemetry["embeddings_solicitados"] == 4
    assert telemetry["embeddings_persistidos"] == 4
    # Uma única chamada em lote ao provider (não multiplica por chunk).
    assert len(gateway.calls) == 1
    assert len(gateway.calls[0]) == 4


def test_sem_api_key_nao_gera_embedding(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)

    def _nao_deve_construir():
        raise AssertionError("gateway não deve ser construído sem API key")

    monkeypatch.setattr(embedding_module, "build_gateway", lambda: _nao_deve_construir())
    chunk = FakeChunk("conteúdo")
    db = FakeDb([chunk])

    telemetry = embed_pending_chunks(db, version_id=1)

    assert chunk.embedding is None
    assert telemetry["provider_disponivel"] is False
    assert telemetry["embeddings_solicitados"] == 0
    assert telemetry["embeddings_persistidos"] == 0


def test_falha_do_provider_nao_persiste_e_nao_levanta(monkeypatch):
    gateway = FakeGateway(fail=True)
    monkeypatch.setattr(embedding_module, "build_gateway", lambda: gateway)
    chunk = FakeChunk("conteúdo")
    db = FakeDb([chunk])

    telemetry = embed_pending_chunks(db, version_id=9)

    assert chunk.embedding is None  # nada persistido
    assert telemetry["embeddings_solicitados"] == 1
    assert telemetry["embeddings_falhos"] == 1
    assert telemetry["embeddings_persistidos"] == 0


def test_dimensao_incompativel_e_descartada_com_seguranca(monkeypatch):
    gateway = FakeGateway(vector_factory=lambda texts: [[0.1, 0.2, 0.3] for _ in texts])
    monkeypatch.setattr(embedding_module, "build_gateway", lambda: gateway)
    chunk = FakeChunk("conteúdo")
    db = FakeDb([chunk])

    telemetry = embed_pending_chunks(db, version_id=5)

    assert chunk.embedding is None  # dimensão errada não é persistida
    assert telemetry["embeddings_falhos"] == 1
    assert telemetry["embeddings_persistidos"] == 0


def test_idempotencia_chunk_ja_vetorizado_nao_regenera(monkeypatch):
    gateway = FakeGateway()
    monkeypatch.setattr(embedding_module, "build_gateway", lambda: gateway)
    vetor_existente = _vector(0.5)
    ja_vetorizado = FakeChunk("já tem vetor", embedding=vetor_existente)
    novo = FakeChunk("sem vetor ainda")
    db = FakeDb([ja_vetorizado, novo])

    telemetry = embed_pending_chunks(db, version_id=3)

    # Só o pendente é processado; o já vetorizado permanece intacto.
    assert ja_vetorizado.embedding is vetor_existente
    assert novo.embedding is not None
    assert telemetry["embeddings_pendentes"] == 1
    assert telemetry["embeddings_solicitados"] == 1
    assert telemetry["embeddings_persistidos"] == 1
    assert len(gateway.calls[0]) == 1  # só um texto enviado ao provider


def _fake_normalize(self, path, document_type):
    return (path.read_text(encoding="utf-8"), {"engine": "fake", "page": 2, "section": "AV-1"})


def test_pipeline_gera_embedding_para_chunks_novos(monkeypatch, tmp_path):
    # Regressão + comportamento novo: a ingestão continua funcionando E agora
    # dispara a geração de embedding dos chunks recém-criados.
    from tests.test_documents import FakeDb as PipelineFakeDb, property_stub

    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", _fake_normalize)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    chamado = {"version_id": None}

    def _fake_embed(db, version_id):
        chamado["version_id"] = version_id
        return {"embeddings_persistidos": 1}

    monkeypatch.setattr("backend.app.documents.pipeline.embed_pending_chunks", _fake_embed)

    db = PipelineFakeDb(property_stub())
    document = models.Document(id=1, property_id=1, name="matricula.txt", document_type="Matrícula", source="Cartorio")
    db.prop.documents.append(document)
    version = DocumentPipeline(db).ingest(document, b"conteudo registral " * 20, "matricula.txt")

    assert version.status == "PROCESSADO"
    assert chamado["version_id"] == version.id  # embedding disparado para a versão criada
    chunks = [item for item in db.added if isinstance(item, models.DocumentChunk)]
    assert chunks and all(chunk.document_version_id == version.id for chunk in chunks)


def test_pipeline_nao_quebra_quando_embedding_falha(monkeypatch, tmp_path):
    from tests.test_documents import FakeDb as PipelineFakeDb, property_stub

    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", _fake_normalize)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    def _boom(db, version_id):
        raise RuntimeError("falha inesperada no embedding")

    monkeypatch.setattr("backend.app.documents.pipeline.embed_pending_chunks", _boom)

    db = PipelineFakeDb(property_stub())
    document = models.Document(id=1, property_id=1, name="edital.txt", document_type="EDITAL", source="Manual")
    db.prop.documents.append(document)

    # Falha do embedding NÃO deve quebrar a ingestão.
    version = DocumentPipeline(db).ingest(document, b"conteudo do edital " * 20, "edital.txt")
    assert version.status == "PROCESSADO"
    assert document.status == "PROCESSADO"


def test_chunk_metadata_pagina_e_version_preservados_apos_embedding(monkeypatch, tmp_path):
    from tests.test_documents import FakeDb as PipelineFakeDb, property_stub

    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", _fake_normalize)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr("backend.app.documents.pipeline.embed_pending_chunks", lambda db, version_id: {"embeddings_persistidos": 0})

    db = PipelineFakeDb(property_stub())
    document = models.Document(id=1, property_id=1, name="matricula.txt", document_type="Matrícula", source="Cartorio")
    db.prop.documents.append(document)
    version = DocumentPipeline(db).ingest(document, b"conteudo " * 50, "matricula.txt")

    chunks = [item for item in db.added if isinstance(item, models.DocumentChunk)]
    assert chunks
    primeiro = chunks[0]
    assert primeiro.document_version_id == version.id
    assert primeiro.metadata_json["document_type"] == "Matrícula"
    assert primeiro.metadata_json["property_id"] == 1
    assert primeiro.metadata_json["document_version_id"] == version.id


def test_chunk_com_embedding_e_recuperado_por_similaridade_vetorial(db, documents):
    # O chunk com embedding vetor_a deve ser recuperável por busca vetorial pura,
    # provando que um chunk vetorizado é surfaçado pelo HybridRetriever.
    query_embedding = _vector(1.0)
    resultados = HybridRetriever(db).search(
        "matrícula consolidada",
        embedding=query_embedding,
        property_id=documents["property_a"],
    )
    assert resultados
    assert resultados[0]["document_id"] == documents["document_a"]
    assert resultados[0]["vector_score"] > 0
