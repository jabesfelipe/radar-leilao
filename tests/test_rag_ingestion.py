"""Testes da Fase 2 (RAG): deduplicação por conteúdo, reprocessamento idempotente,
estados de processamento e backfill de embeddings (dry-run, sem chamadas externas).

Usa o mesmo FakeDb de test_documents.py (unidade, sem PostgreSQL). Dados sintéticos
isolados — NUNCA o imóvel 633.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from backend.app import models
from backend.app.config import settings
from backend.app.documents import dedup, states
from backend.app.documents.pipeline import DocumentPipeline


class FakeDb:
    def __init__(self, prop=None, document=None):
        self.prop = prop; self.document = document; self.added = []
    def get(self, model, identifier):
        return self.document if model is models.Document else self.prop
    def add(self, item):
        if isinstance(item, models.Document) and item.id is None:
            item.id = len([x for x in self.added if isinstance(x, models.Document)]) + 1
            self.document = item
        if isinstance(item, models.DocumentVersion):
            item.id = len([x for x in self.added if isinstance(x, models.DocumentVersion)]) + 1
            document = self.document or (self.prop.documents[-1] if self.prop else None)
            if document is not None and item not in document.versions:
                document.versions.append(item)
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self, item): return None


def _prop():
    return models.Property(id=1, title="Imovel RAG", address="Rua RAG", city="Curitiba", state="PR")


def _doc(prop):
    d = models.Document(id=1, property_id=1, name="edital.txt", document_type="EDITAL", source="Manual")
    prop.documents.append(d)
    return d


@pytest.fixture(autouse=True)
def _fake_normalize(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "backend.app.documents.pipeline.DocumentNormalizer.normalize",
        lambda self, path, document_type: (path.read_text(encoding="utf-8"), {"engine": "fake"}),
    )
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))


# --------------------------------------------------------------------------
# Dedup por conteúdo
# --------------------------------------------------------------------------

def test_conteudo_identico_reaproveita_versao_sem_novos_chunks():
    prop = _prop(); doc = _doc(prop); db = FakeDb(prop, doc)
    v1 = DocumentPipeline(db).ingest(doc, b"conteudo igual", "edital.txt")
    chunks_apos_v1 = [x for x in db.added if isinstance(x, models.DocumentChunk)]
    # Reenvia o MESMO conteúdo: deve reaproveitar a versão, sem criar chunks novos.
    v2 = DocumentPipeline(db).ingest(doc, b"conteudo igual", "edital.txt")
    chunks_apos_v2 = [x for x in db.added if isinstance(x, models.DocumentChunk)]
    assert v2 is v1  # mesma versão reaproveitada
    assert len(chunks_apos_v2) == len(chunks_apos_v1)  # nenhum chunk novo
    assert len([v for v in doc.versions]) == 1  # não criou versão nova
    assert doc.status == states.CONCLUIDO


def test_conteudo_diferente_cria_nova_versao():
    prop = _prop(); doc = _doc(prop); db = FakeDb(prop, doc)
    v1 = DocumentPipeline(db).ingest(doc, b"conteudo A", "edital.txt")
    v2 = DocumentPipeline(db).ingest(doc, b"conteudo B diferente", "edital.txt")
    assert v2 is not v1
    assert [v.version for v in doc.versions] == [1, 2]
    assert v1.content_hash != v2.content_hash


def test_dedup_pode_ser_desabilitado_explicitamente():
    prop = _prop(); doc = _doc(prop); db = FakeDb(prop, doc)
    DocumentPipeline(db).ingest(doc, b"igual", "edital.txt")
    # Com dedup_reuse=False, força nova versão mesmo com conteúdo idêntico.
    v2 = DocumentPipeline(db).ingest(doc, b"igual", "edital.txt", dedup_reuse=False)
    assert v2.version == 2
    assert [v.version for v in doc.versions] == [1, 2]


# --------------------------------------------------------------------------
# Estados de processamento
# --------------------------------------------------------------------------

def test_estado_terminal_concluido_sem_provider():
    prop = _prop(); doc = _doc(prop); db = FakeDb(prop, doc)
    v1 = DocumentPipeline(db).ingest(doc, b"texto", "edital.txt")
    # Sem provider/chave: ingestão por texto => CONCLUIDO (não INDEXADO).
    assert v1.status == states.CONCLUIDO
    assert states.is_ok(v1.status)


def test_estado_erro_ao_falhar_normalizacao(monkeypatch):
    def fail(*a, **k): raise RuntimeError("falha")
    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", fail)
    prop = _prop(); doc = _doc(prop); db = FakeDb(prop, doc)
    with pytest.raises(RuntimeError):
        DocumentPipeline(db).ingest(doc, b"x", "edital.txt")
    assert doc.status == states.ERRO


def test_normalize_legacy_mapeia_processado_para_concluido():
    assert states.normalize_legacy("PROCESSADO") == states.CONCLUIDO
    assert states.is_ok("PROCESSADO")  # legado continua sendo "ok"


# --------------------------------------------------------------------------
# Dedup helpers (puros)
# --------------------------------------------------------------------------

def test_find_reusable_ignora_versao_em_erro():
    doc = models.Document(id=1, property_id=1, name="x", document_type="EDITAL", source="Manual")
    h = dedup.content_digest(b"abc")
    doc.versions.append(models.DocumentVersion(id=1, document_id=1, version=1, content_hash=h, status=states.ERRO, original_path="v1"))
    assert dedup.find_reusable_version(doc, h) is None  # ERRO não é reaproveitável
    doc.versions.append(models.DocumentVersion(id=2, document_id=1, version=2, content_hash=h, status=states.CONCLUIDO, original_path="v2"))
    reusable = dedup.find_reusable_version(doc, h)
    assert reusable is not None and reusable.version == 2


# --------------------------------------------------------------------------
# Backfill de embeddings (dry-run por padrão, sem chamadas externas)
# --------------------------------------------------------------------------

def test_backfill_dry_run_por_padrao_nao_executa(db):
    """Com PostgreSQL real (fixture db): o backfill NÃO deve executar por padrão.
    Apenas relata. Nunca faz chamada externa. Não altera dados históricos."""
    from backend.app.documents.embedding_backfill import backfill_missing_embeddings, coverage_report

    rep = coverage_report(db)
    assert set(["chunks_total", "chunks_com_embedding", "chunks_sem_embedding", "cobertura_pct"]).issubset(rep)
    assert rep["modelo"]  # modelo configurado reportado
    assert rep["dimensao"] >= 1

    plano = backfill_missing_embeddings(db)  # defaults: dry_run=True, enabled=False
    assert plano["dry_run"] is True
    assert plano["enabled"] is False
    assert plano["executado"] is False
    assert plano["embeddings_persistidos"] == 0
    assert "dry-run" in plano["motivo"]


def test_backfill_sem_provider_nao_executa_mesmo_habilitado(db, monkeypatch):
    from backend.app.config import settings as _settings
    from backend.app.documents.embedding_backfill import backfill_missing_embeddings

    monkeypatch.setattr(_settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(_settings, "llm_api_key", None, raising=False)
    plano = backfill_missing_embeddings(db, dry_run=False, enabled=True, limit=1)
    assert plano["executado"] is False
    assert "provider indisponivel" in plano["motivo"]
