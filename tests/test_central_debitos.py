"""Testes da Central de Débitos/Despesas (Etapa A): domínio normalizado,
consolidação por natureza, compatibilidade com Debt/Cost/build_finance e segurança
das rotas administrativas. PostgreSQL real (fixture ``db``) + TestClient HTTP.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models, debts_service, services
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


def _prop(db, titulo="Imóvel Débitos"):
    p = models.Property(title=titulo, address="Rua D", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(p); db.flush()
    return p


# --------------------------------------------------------------------------
# Seed idempotente de catálogo + municípios
# --------------------------------------------------------------------------

def test_seed_tipos_e_municipios_idempotente(db):
    r1 = debts_service.seed_all(db); db.flush()
    r2 = debts_service.seed_all(db); db.flush()
    assert r1["municipalities"] == 4  # Curitiba, SJP, Fazenda Rio Grande, Assis
    assert r1["debt_types"] > 0
    assert r2["municipalities"] == 0 and r2["debt_types"] == 0  # idempotente
    nomes = {m.name for m in db.scalars(select(models.Municipality)).all()}
    assert {"Curitiba", "São José dos Pinhais", "Fazenda Rio Grande", "Assis"}.issubset(nomes)


# --------------------------------------------------------------------------
# Normalização + invariantes
# --------------------------------------------------------------------------

def test_normalizacao_exige_tipo_conhecido(db):
    debts_service.seed_debt_types(db); db.flush()
    with pytest.raises(ValueError):
        debts_service.normalize_debt_payload(db, {"debt_type_code": "TIPO_INEXISTENTE"})


def test_estimado_nunca_vira_oficial(db):
    debts_service.seed_debt_types(db); db.flush()
    out = debts_service.normalize_debt_payload(db, {"debt_type_code": "IPTU", "status": "ESTIMADO", "reliability": "OFICIAL"})
    assert out["status"] == "ESTIMADO" and out["reliability"] == "ESTIMADO"


def test_natureza_default_vem_do_tipo(db):
    debts_service.seed_debt_types(db); db.flush()
    out = debts_service.normalize_debt_payload(db, {"debt_type_code": "ITBI"})
    assert out["nature"] == "CUSTO_AQUISICAO"


# --------------------------------------------------------------------------
# Consolidação por natureza (totais separados; sem dupla contagem)
# --------------------------------------------------------------------------

def test_consolidacao_separa_naturezas(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    db.add_all([
        models.PropertyDebt(property_id=p.id, debt_type_code="IPTU", nature="DIVIDA_EXISTENTE", status="CONFIRMADO", updated_amount=Decimal("1000")),
        models.PropertyDebt(property_id=p.id, debt_type_code="IPTU", nature="DIVIDA_EXISTENTE", status="INFORMADO", original_amount=Decimal("500")),
        models.PropertyDebt(property_id=p.id, debt_type_code="COTA_CONDOMINIAL", nature="ESTIMATIVA_OPERACIONAL", status="ESTIMADO", updated_amount=Decimal("3000")),
        models.PropertyDebt(property_id=p.id, debt_type_code="ITBI", nature="CUSTO_AQUISICAO", status="INFORMADO", updated_amount=Decimal("2000")),
        models.PropertyDebt(property_id=p.id, debt_type_code="IPTU", status="INDISPONIVEL"),
    ])
    db.flush()
    c = debts_service.consolidate(db, p.id)
    tot = c["totais"]
    assert tot["confirmados"] == Decimal("1000")
    assert tot["informados"] == Decimal("500")
    assert tot["estimados"] == Decimal("3000")
    assert tot["despesas_previstas"] == Decimal("2000")
    assert c["contagens"]["nao_apurados"] == 1
    # Exposição de passivo = confirmados + informados (estimativa NÃO entra).
    assert c["exposicao_passivo_com_ressalva"] == Decimal("1500")


def test_consolidacao_nao_conta_duas_vezes_original_e_atualizado(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    # Tem original E atualizado: conta só o atualizado (não soma os dois).
    db.add(models.PropertyDebt(property_id=p.id, debt_type_code="IPTU", status="CONFIRMADO", original_amount=Decimal("800"), updated_amount=Decimal("1000")))
    db.flush()
    c = debts_service.consolidate(db, p.id)
    assert c["totais"]["confirmados"] == Decimal("1000")


def test_consolidacao_inclui_legado_debt_sem_dupla_contagem(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    db.add(models.Debt(property_id=p.id, category="IPTU", amount=Decimal("700"), status="CONFIRMADO"))
    db.add(models.PropertyDebt(property_id=p.id, debt_type_code="IPTU", status="CONFIRMADO", updated_amount=Decimal("300")))
    db.flush()
    c = debts_service.consolidate(db, p.id)
    # Legado (700) + normalizado (300) = 1000, cada um contado uma vez.
    assert c["totais"]["confirmados"] == Decimal("1000")
    assert c["contagens"]["confirmados"] == 2


# --------------------------------------------------------------------------
# Compatibilidade: Debt/Cost e build_finance inalterados
# --------------------------------------------------------------------------

def test_build_finance_continua_consumindo_debt_legado(db):
    p = _prop(db)
    auction = models.Auction(property_id=p.id, bid_value=Decimal("200000"), appraisal_value=Decimal("300000"))
    db.add(auction)
    db.add(models.Debt(property_id=p.id, category="IPTU", amount=Decimal("1500"), status="PENDENTE"))
    db.flush()
    fin = services.build_finance(p)
    # O Debt legado (não QUITADO) continua somado no breakdown 'custos.debitos'.
    assert fin["custos"]["debitos"] == Decimal("1500")


# --------------------------------------------------------------------------
# HTTP: criação normalizada + segurança admin
# --------------------------------------------------------------------------

@pytest.fixture
def client(postgres_engine, monkeypatch):
    if TestClient is None:
        pytest.skip("httpx/TestClient indisponível")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")  # garante estado; admin exige token real via settings
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


def _criar_imovel(client):
    resp = client.post("/api/imoveis", json={"title": "Imóvel Déb HTTP", "address": "Rua", "city": "Curitiba", "state": "PR", "property_type": "Apartamento", "area_m2": 70})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_http_cria_debito_normalizado_e_consolida(client):
    # Semeia o catálogo via a sessão do próprio client (GET admin é idempotente/seed).
    assert client.get("/api/admin/tipos-debito").status_code == 200
    pid = _criar_imovel(client)
    resp = client.post(f"/api/imoveis/{pid}/debitos", json={"debt_type_code": "IPTU", "status": "CONFIRMADO", "reliability": "OFICIAL", "updated_amount": "1200.50"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["debito"]["debt_type_code"] == "IPTU"
    assert float(body["consolidacao"]["totais"]["confirmados"]) == 1200.50


def test_http_debito_tipo_invalido_422(client):
    assert client.get("/api/admin/tipos-debito").status_code == 200
    pid = _criar_imovel(client)
    resp = client.post(f"/api/imoveis/{pid}/debitos", json={"debt_type_code": "NAO_EXISTE"})
    assert resp.status_code == 422


def test_http_admin_escrita_sem_token_recusada(client):
    # ADMIN_API_TOKEN não configurado (settings.admin_api_token None) => 503 (falha-fechada).
    resp = client.post("/api/admin/parametros", json={"key": "x.y", "category": "t", "data_type": "INTEGER", "value": "1"})
    assert resp.status_code in (401, 503)


def test_http_admin_leitura_municipios_aberta(client):
    resp = client.get("/api/admin/municipios")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 4  # seed dos 4 municípios
