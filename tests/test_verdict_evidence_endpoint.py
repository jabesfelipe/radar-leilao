"""Testes do GET /api/imoveis/{id} (TASK 70).

- Veredito mais recente é escolhido por analysis_version (não pela ordem incidental
  do relacionamento ORM): V7 + V8 -> API retorna V8.
- Evidências vinculadas ao veredito são expostas de forma legível (documento/tipo/
  versão/categoria/página/seção/fato), sem depender de IDs internos.
- Evidência sem metadados opcionais não quebra a API.
- evidence_ids continuam preservados para rastreabilidade.
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


REQUIRED_TABLES = {"properties", "documents", "document_versions", "evidences", "verdicts"}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient (httpx) indisponível")
    if not REQUIRED_TABLES.issubset(set(inspect(postgres_engine).get_table_names())):
        pytest.skip("Migrations do Radar ainda não aplicadas no banco de testes")
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _seed(session: Session):
    prop = models.Property(title="COND PARQUE ARVOREDO", address="Rua X", city="Curitiba", state="PR")
    session.add(prop); session.flush()
    # documento + versão para as evidências legíveis
    document = models.Document(property_id=prop.id, name="EL00440226CPARE.pdf", document_type="EDITAL", source="Cadastro")
    session.add(document); session.flush()
    version = models.DocumentVersion(document_id=document.id, version=2, content_hash="c" * 64, original_path="edital.pdf")
    session.add(version); session.flush()
    # evidência COM metadados
    ev_full = models.Evidence(property_id=prop.id, document_version_id=version.id, category="CHECKLIST",
                              fact="Responsabilidade por débitos descrita no edital.", confidence="ALTA",
                              page=8, section="Condições", source_excerpt="...responsabilidade por IPTU e condomínio...")
    # evidência SEM metadados opcionais (sem página/seção/source_excerpt e sem documento)
    ev_min = models.Evidence(property_id=prop.id, category="MERCADO", fact="Sem metadados opcionais.")
    session.add_all([ev_full, ev_min]); session.flush()
    # V7 (mais antiga) e V8 (mais recente) — inseridas fora de ordem de versão de propósito
    v8 = models.Verdict(property_id=prop.id, analysis_version=8, overall="ATENCAO", summary="V8", evidence_ids=[ev_full.id, ev_min.id])
    session.add(v8); session.flush()
    v7 = models.Verdict(property_id=prop.id, analysis_version=7, overall="INCONCLUSIVO", summary="V7", evidence_ids=[])
    session.add(v7); session.flush()
    return prop.id, ev_full.id, ev_min.id


def test_veredito_mais_recente_e_por_analysis_version(client):
    api, session = client
    property_id, _, _ = _seed(session)
    resp = api.get(f"/api/imoveis/{property_id}")
    assert resp.status_code == 200, resp.text
    veredito = resp.json()["veredito"]
    # Deve retornar a MAIOR analysis_version (V8), não a ordem incidental do ORM.
    assert veredito["analysis_version"] == 8
    assert veredito["overall"] == "ATENCAO"
    assert veredito["summary"] == "V8"


def test_evidencias_legiveis_com_dados_reais(client):
    api, session = client
    property_id, ev_full_id, _ = _seed(session)
    corpo = api.get(f"/api/imoveis/{property_id}").json()
    evidencias = corpo["veredito_evidencias"]
    assert isinstance(evidencias, list) and evidencias
    principal = next(e for e in evidencias if e["id"] == ev_full_id)
    assert principal["documento"] == "EL00440226CPARE.pdf"
    assert principal["document_type"] == "EDITAL"
    assert principal["version"] == 2
    assert principal["category"] == "CHECKLIST"
    assert principal["page"] == 8
    assert principal["section"] == "Condições"
    assert principal["fact"].startswith("Responsabilidade por débitos")
    assert "source_excerpt" in principal


def test_evidencia_sem_metadados_opcionais_nao_quebra(client):
    api, session = client
    property_id, _, ev_min_id = _seed(session)
    corpo = api.get(f"/api/imoveis/{property_id}").json()
    minima = next(e for e in corpo["veredito_evidencias"] if e["id"] == ev_min_id)
    # Campos ausentes são omitidos (não inventados) e a API não quebra.
    assert minima["category"] == "MERCADO"
    assert minima["fact"] == "Sem metadados opcionais."
    assert "documento" not in minima
    assert "page" not in minima
    assert "section" not in minima
    assert "source_excerpt" not in minima


def test_evidence_ids_preservados_para_rastreabilidade(client):
    api, session = client
    property_id, ev_full_id, ev_min_id = _seed(session)
    veredito = api.get(f"/api/imoveis/{property_id}").json()["veredito"]
    assert veredito["evidence_ids"] == [ev_full_id, ev_min_id]
