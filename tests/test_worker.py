"""Fase 6: worker de processamento assíncrono (DB-backed, idempotente).

Sem provider/chave: o worker NUNCA chama OpenAI; apenas mantém o estado pendente e
preserva a extração. Dados sintéticos — NUNCA o imóvel 633.
"""
from __future__ import annotations

from backend.app import models
from backend.app.config import settings
from backend.app.documents import states, worker


def _seed_version_with_pending_chunks(db, n=3):
    prop = models.Property(title="Imovel WK", address="Rua WK", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(prop); db.flush()
    doc = models.Document(property_id=prop.id, name="wk.pdf", document_type="Edital", source="Manual")
    db.add(doc); db.flush()
    ver = models.DocumentVersion(document_id=doc.id, version=1, content_hash="d" * 64, original_path="wk.pdf",
                                 normalized_markdown="# WK", status=states.AGUARDANDO_EMBEDDING, extraction_metadata={})
    db.add(ver); db.flush()
    for i in range(n):
        db.add(models.DocumentChunk(document_version_id=ver.id, chunk_index=i, content=f"clausula wk {i}",
                                    metadata_json={"document_version_id": ver.id}, embedding=None))
    db.flush()
    return ver


def test_pending_versions_encontra_versao_com_chunks_sem_vetor(db):
    ver = _seed_version_with_pending_chunks(db)
    pend = worker.pending_versions(db)
    assert ver.id in pend


def test_process_version_sem_provider_preserva_pendente(db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    ver = _seed_version_with_pending_chunks(db)
    out = worker.process_version(db, ver.id)
    assert out["status"] == states.AGUARDANDO_EMBEDDING
    assert "sem provider" in out["motivo"]
    # Nenhum vetor foi gerado (sem chamada externa); chunks seguem sem embedding.
    restantes = db.scalar(
        __import__("sqlalchemy").select(models.DocumentChunk.id)
        .where(models.DocumentChunk.document_version_id == ver.id, models.DocumentChunk.embedding.is_(None)).limit(1)
    )
    assert restantes is not None


def test_run_once_sem_provider_nao_falha(db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    _seed_version_with_pending_chunks(db)
    result = worker.run_once(db, limit=5)
    assert result["processadas"] >= 1
    assert all(r["status"] in (states.AGUARDANDO_EMBEDDING, states.INDEXADO) for r in result["resultados"])


def test_max_attempts_remove_da_fila(db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    ver = _seed_version_with_pending_chunks(db)
    # Simula tentativas esgotadas no metadata.
    ver.extraction_metadata = {"embedding_attempts": 5}
    db.flush()
    pend = worker.pending_versions(db, max_attempts=5)
    assert ver.id not in pend  # excedeu tentativas => sai da fila
