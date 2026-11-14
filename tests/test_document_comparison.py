"""Confronto documental matrícula × edital (v1.0.4), no PostgreSQL real com o pipeline real de ingestão.

Fato do caso-01 que a IA não conseguia comprovar: área privativa de 62,00 m² na matrícula × 68,00 m² no edital.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.app import models
from backend.app.config import settings
from backend.app.document_comparison import CONFERE, DIVERGENCIA, NAO_COMPARAVEL, compare_documents
from backend.app.documents.pipeline import DocumentPipeline

FIXTURES = Path(__file__).resolve().parents[1] / "e2e" / "fixtures" / "caso-01"


@pytest.fixture(autouse=True)
def _sem_chave(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _imovel(db, titulo="Imóvel"):
    prop = models.Property(title=titulo, address="Rua X", city="São Paulo", state="SP")
    db.add(prop); db.flush()
    return prop


def _doc(db, prop, texto, nome, tipo):
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    DocumentPipeline(db).ingest(doc, texto.encode(), nome)
    db.refresh(prop)


def _por_info(rows):
    return {r["informacao"]: r for r in rows}


def test_caso01_divergencia_de_area_com_as_duas_fontes(db):
    prop = _imovel(db)
    _doc(db, prop, (FIXTURES / "matricula.txt").read_text(encoding="utf-8"), "matricula.txt", "MATRICULA")
    _doc(db, prop, (FIXTURES / "edital.txt").read_text(encoding="utf-8"), "edital.txt", "EDITAL")
    rows = _por_info(compare_documents(prop))
    area = rows["Área privativa (m²)"]
    assert area["resultado"] == DIVERGENCIA
    assert area["matricula"]["valor"] == "62.00" and area["edital"]["valor"] == "68.00"
    assert "62,00" in area["matricula"]["trecho"] and "68,00" in area["edital"]["trecho"]
    assert area["matricula"]["documento"] == "matricula.txt" and area["edital"]["documento"] == "edital.txt"
    assert "não é, por si só, irregularidade" in area["observacao"].lower()
    assert rows["Número da matrícula"]["resultado"] == CONFERE


def test_informacao_ausente_em_um_documento_nao_e_comparavel(db):
    prop = _imovel(db)
    _doc(db, prop, "MATRÍCULA Nº 12.345. Área privativa de 50,00 m².", "m.txt", "MATRICULA")
    _doc(db, prop, "EDITAL. Imóvel objeto da matrícula 12.345.", "e.txt", "EDITAL")
    rows = _por_info(compare_documents(prop))
    assert rows["Área privativa (m²)"]["resultado"] == NAO_COMPARAVEL and rows["Área privativa (m²)"]["edital"] is None
    assert rows["Número da matrícula"]["resultado"] == CONFERE


def test_sem_os_dois_documentos_nao_ha_confronto(db):
    prop = _imovel(db)
    _doc(db, prop, "MATRÍCULA Nº 12.345. Área privativa de 50,00 m².", "m.txt", "MATRICULA")
    assert compare_documents(prop) == []


def test_confronto_usa_somente_documentos_do_proprio_imovel(db):
    a, b = _imovel(db, "A"), _imovel(db, "B")
    _doc(db, a, "MATRÍCULA Nº 11.111. Área privativa de 50,00 m².", "m.txt", "MATRICULA")
    _doc(db, a, "EDITAL. Matrícula 11.111. Área privativa de 50,00 m².", "e.txt", "EDITAL")
    _doc(db, b, "MATRÍCULA Nº 22.222. Área privativa de 99,00 m².", "m.txt", "MATRICULA")
    _doc(db, b, "EDITAL. Matrícula 22.222. Área privativa de 99,00 m².", "e.txt", "EDITAL")
    rows = _por_info(compare_documents(a))
    assert rows["Área privativa (m²)"]["resultado"] == CONFERE and rows["Área privativa (m²)"]["matricula"]["valor"] == "50.00"
    assert all("22.222" not in str(r) and "99,00" not in str(r) for r in rows.values())


def test_api_do_imovel_expoe_o_confronto(db):
    from fastapi.testclient import TestClient
    from backend.app.database import get_db
    from backend.app.main import app
    prop = _imovel(db)
    _doc(db, prop, "MATRÍCULA Nº 12.345. Área privativa de 50,00 m².", "m.txt", "MATRICULA")
    _doc(db, prop, "EDITAL. Matrícula 12.345. Área privativa de 55,00 m².", "e.txt", "EDITAL")
    db.flush(); db.expire_all()
    app.dependency_overrides[get_db] = lambda: db
    try:
        body = TestClient(app).get(f"/api/imoveis/{prop.id}").json()
    finally:
        app.dependency_overrides.pop(get_db, None)
    area = next(r for r in body["confronto_documental"] if r["informacao"].startswith("Área"))
    assert area["resultado"] == "DIVERGENCIA" and area["matricula"]["valor"] == "50.00" and area["edital"]["valor"] == "55.00"
