"""Testes da cobertura municipal e fontes (Etapa B).

Cobre: seed da matriz de cobertura como DADO, cobertura por categoria independente,
ativação/desativação, validação de referências e vocabulário, ausência de duplicidade,
cadastro/edição de fontes, compatibilidade com a Etapa A e segurança das rotas admin.
PostgreSQL real (fixture ``db``) + TestClient HTTP.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models, debts_service, coverage_service
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


# --------------------------------------------------------------------------
# Seed da cobertura (como dado, idempotente) + independência por tipo
# --------------------------------------------------------------------------

def test_seed_cobertura_idempotente_e_como_dado(db):
    debts_service.seed_all(db); db.flush()
    r2 = coverage_service.seed_coverage(db); db.flush()
    assert r2 == 0  # segunda passada não recria
    rows = db.scalars(select(models.MunicipalityCoverage)).all()
    assert len(rows) >= 4  # ao menos IPTU de cada município
    # IPTU é AUTOMATIZAVEL/portal; demais semeados permanecem NAO_INVESTIGADA.
    iptu = [c for c in rows if c.debt_type_code == "IPTU"]
    assert iptu and all(c.level == "AUTOMATIZAVEL" and c.method == "PORTAL_PUBLICO" for c in iptu)
    assert any(c.level == "NAO_INVESTIGADA" for c in rows)


def test_cobertura_independente_por_municipio_e_tipo(db):
    debts_service.seed_all(db); db.flush()
    curitiba = db.scalar(select(models.Municipality).where(models.Municipality.name == "Curitiba"))
    assis = db.scalar(select(models.Municipality).where(models.Municipality.name == "Assis"))
    # Cada município tem a sua própria linha de IPTU (não compartilham estado).
    ct = db.scalar(select(models.MunicipalityCoverage).where(
        models.MunicipalityCoverage.municipality_id == curitiba.id,
        models.MunicipalityCoverage.debt_type_code == "IPTU"))
    asx = db.scalar(select(models.MunicipalityCoverage).where(
        models.MunicipalityCoverage.municipality_id == assis.id,
        models.MunicipalityCoverage.debt_type_code == "IPTU"))
    assert ct is not None and asx is not None and ct.id != asx.id


# --------------------------------------------------------------------------
# create/update: validação de referências, vocabulário, duplicidade
# --------------------------------------------------------------------------

def test_create_coverage_valida_municipio_e_tipo(db):
    debts_service.seed_all(db); db.flush()
    with pytest.raises(coverage_service.CoverageError):
        coverage_service.create_coverage(db, {"municipality_id": 999999, "debt_type_code": "IPTU"})
    muni = db.scalar(select(models.Municipality).where(models.Municipality.name == "Curitiba"))
    with pytest.raises(coverage_service.CoverageError):
        coverage_service.create_coverage(db, {"municipality_id": muni.id, "debt_type_code": "TIPO_INEXISTENTE"})


def test_create_coverage_recusa_duplicidade(db):
    debts_service.seed_all(db); db.flush()
    muni = db.scalar(select(models.Municipality).where(models.Municipality.name == "Assis"))
    # IPTU de Assis já foi semeado → nova criação deve falhar por unicidade.
    with pytest.raises(coverage_service.CoverageError):
        coverage_service.create_coverage(db, {"municipality_id": muni.id, "debt_type_code": "IPTU"})


def test_create_coverage_valida_vocabulario(db):
    debts_service.seed_all(db); db.flush()
    muni = db.scalar(select(models.Municipality).where(models.Municipality.name == "Curitiba"))
    with pytest.raises(coverage_service.CoverageError):
        coverage_service.create_coverage(db, {"municipality_id": muni.id, "debt_type_code": "TAXA_MUNICIPAL", "level": "NIVEL_INVALIDO"})


def test_update_coverage_ativa_desativa_e_valida(db):
    debts_service.seed_all(db); db.flush()
    cov = db.scalars(select(models.MunicipalityCoverage).where(models.MunicipalityCoverage.debt_type_code == "IPTU")).first()
    assert cov.active is True and cov.last_validated_at is None
    coverage_service.update_coverage(db, cov, {"active": False}); db.flush()
    assert cov.active is False
    coverage_service.update_coverage(db, cov, {"mark_validated": True}); db.flush()
    assert cov.last_validated_at is not None


def test_coverage_matrix_expoe_nao_investigados(db):
    debts_service.seed_all(db); db.flush()
    muni = db.scalar(select(models.Municipality).where(models.Municipality.name == "Curitiba"))
    m = coverage_service.coverage_matrix(db, municipality_id=muni.id)
    assert m["total"] >= 1
    # Tipos ativos sem cobertura registrada aparecem como "não investigados".
    assert isinstance(m["nao_investigados"], list)
    assert "ressalva" in m


# --------------------------------------------------------------------------
# Compatibilidade com a Etapa A (nada quebrado)
# --------------------------------------------------------------------------

def test_etapa_a_preservada_seed_all_inclui_coverage(db):
    r = debts_service.seed_all(db); db.flush()
    # Etapa C/D acrescentou o seed de parâmetros; cobertura e catálogo preservados.
    assert {"debt_types", "municipalities", "coverage"}.issubset(set(r.keys()))
    # Debt/Cost/PropertyDebt continuam existindo e utilizáveis.
    assert db.scalars(select(models.DebtType)).first() is not None


# --------------------------------------------------------------------------
# HTTP: matriz, segurança e cadastro de fonte
# --------------------------------------------------------------------------

@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("httpx/TestClient indisponível")
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close(); transaction.rollback(); connection.close()


@pytest.fixture
def admin_token(monkeypatch):
    """Configura um token admin real para exercitar a ESCRITA protegida."""
    monkeypatch.setattr(settings, "admin_api_token", "token-teste-b", raising=False)
    return "token-teste-b"


def test_http_matriz_cobertura_aberta_e_semeada(client):
    resp = client.get("/api/admin/cobertura")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 4
    assert "nao_investigados" in body and "ressalva" in body


def test_http_cobertura_escrita_sem_token_recusada(client):
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "TAXA_MUNICIPAL"})
    assert resp.status_code in (401, 503)


def test_http_cobertura_criacao_e_ativacao_com_token(client, admin_token):
    assert client.get("/api/admin/cobertura").status_code == 200  # semeia
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    headers = {"X-Admin-Token": admin_token}
    # OUTRO_DEBITO_MUNICIPAL não é semeado → criação deve passar.
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "OUTRO_DEBITO_MUNICIPAL", "level": "MANUAL"}, headers=headers)
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]
    r2 = client.patch(f"/api/admin/cobertura/{cid}", json={"active": False}, headers=headers)
    assert r2.status_code == 200 and r2.json()["active"] is False


def test_http_fonte_cadastro_valida_categoria(client, admin_token):
    assert client.get("/api/admin/tipos-debito").status_code == 200  # semeia catálogo
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    headers = {"X-Admin-Token": admin_token}
    # Categoria desconhecida → 400.
    bad = client.post("/api/admin/fontes", json={"municipality_id": muni["id"], "name": "Fonte X", "debt_category": "NAO_EXISTE"}, headers=headers)
    assert bad.status_code == 400, bad.text
    # Categoria válida → 201.
    ok = client.post("/api/admin/fontes", json={"municipality_id": muni["id"], "name": "Portal IPTU", "debt_category": "IPTU", "source_type": "PORTAL_PUBLICO", "situation": "DISPONIVEL"}, headers=headers)
    assert ok.status_code == 201, ok.text
    sid = ok.json()["id"]
    # Edição: marca situação.
    patched = client.patch(f"/api/admin/fontes/{sid}", json={"situation": "EM_INVESTIGACAO"}, headers=headers)
    assert patched.status_code == 200 and patched.json()["situation"] == "EM_INVESTIGACAO"
