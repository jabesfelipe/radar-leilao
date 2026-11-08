"""Fase 3 (RAG): isolamento de recuperação por oportunidade.

Garante que, quando o escopo é restrito a uma oportunidade, a busca não traz chunks
de outra oportunidade. O vínculo é feito por ``metadata_json ->> 'opportunity_id'``
(aditivo, sem schema novo). Dados sintéticos — NUNCA o imóvel 633.
"""
from __future__ import annotations

from backend.app import models
from backend.app.config import settings
from backend.app.rag.retriever import HybridRetriever, RetrieverFilters


def test_filtro_opportunity_id_gera_sql_isolado():
    """Teste puro (sem DB): o filtro de oportunidade entra no WHERE com o parâmetro."""
    class Result:
        def mappings(self): return self
        def all(self): return []

    class CaptureSession:
        def __init__(self): self.statement = ""; self.params = {}
        def execute(self, statement, params):
            self.statement = str(statement); self.params = params; return Result()

    session = CaptureSession()
    HybridRetriever(session).search("matricula", property_id=10, filters=RetrieverFilters(property_id=10, opportunity_id=77))
    assert "c.metadata_json ->> 'opportunity_id' = :opportunity_id" in session.statement
    assert session.params["opportunity_id"] == "77"  # comparado como texto (JSON ->>)


def _seed_two_opportunities(db):
    """Cria 1 imóvel, 1 documento/versão e 2 chunks com opportunity_id distintos."""
    prop = models.Property(title="Imovel ISO", address="Rua ISO", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(prop); db.flush()
    doc = models.Document(property_id=prop.id, name="edital-iso.pdf", document_type="Edital", source="Manual")
    db.add(doc); db.flush()
    ver = models.DocumentVersion(document_id=doc.id, version=1, content_hash="c" * 64, original_path="iso.pdf", normalized_markdown="# ISO", status="CONCLUIDO")
    db.add(ver); db.flush()
    db.add(models.DocumentChunk(
        document_version_id=ver.id, chunk_index=0, content="clausula de arrematacao alfa unica",
        metadata_json={"property_id": prop.id, "document_id": doc.id, "opportunity_id": 101}, embedding=None,
    ))
    db.add(models.DocumentChunk(
        document_version_id=ver.id, chunk_index=1, content="clausula de arrematacao beta unica",
        metadata_json={"property_id": prop.id, "document_id": doc.id, "opportunity_id": 202}, embedding=None,
    ))
    db.flush()
    return prop.id


def test_busca_restrita_por_oportunidade_nao_vaza_outra(db):
    prop_id = _seed_two_opportunities(db)
    r = HybridRetriever(db).search(
        "clausula arrematacao", property_id=prop_id,
        filters=RetrieverFilters(property_id=prop_id, opportunity_id=101),
    )
    assert r, "esperado ao menos 1 chunk da oportunidade 101"
    assert all(str(c["metadata_json"].get("opportunity_id")) == "101" for c in r)
    assert all("beta" not in c["content"] for c in r)


def test_busca_sem_filtro_de_oportunidade_mantem_comportamento(db):
    prop_id = _seed_two_opportunities(db)
    r = HybridRetriever(db).search("clausula arrematacao", property_id=prop_id)
    # Sem o filtro de oportunidade, ambos os chunks do imóvel podem aparecer.
    op_ids = {str(c["metadata_json"].get("opportunity_id")) for c in r}
    assert op_ids == {"101", "202"}
