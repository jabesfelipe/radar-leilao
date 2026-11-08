"""Testes do Dashboard operacional (Onda 2).

Valida a agregação REAL de oportunidades (por fase/modalidade/município/status),
os filtros/paginação da listagem e as exigências de autenticação. Usa dados
sintéticos isolados — NUNCA o imóvel 633. JWT via JWT_SECRET_KEY de teste.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.app import models, auth
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


@pytest.fixture
def client(postgres_engine, monkeypatch):
    if TestClient is None:
        pytest.skip("httpx/TestClient indisponível")
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-dash-teste", raising=False)
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


def _session():
    gen = app.dependency_overrides[get_db](); return next(gen)


def _user(session, role="ANALISTA", email=None):
    email = email or f"{role.lower()}@dash.com"
    u = models.User(email=email, name=role, password_hash=auth.hash_password("senha-forte-123"), role=role, active=True)
    session.add(u); session.flush(); return u


def _prop(session, city="Curitiba", titulo="Imóvel DASH"):
    p = models.Property(title=titulo, address="Rua DASH", city=city, state="PR", area_m2=70, bedrooms=2)
    session.add(p); session.flush(); return p


def _login(client, email, password="senha-forte-123"):
    return client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _criar(client, tok, property_id, modality=None):
    body = {"property_id": property_id}
    if modality:
        body["modality"] = modality
    return client.post("/api/oportunidades", json=body, headers=_h(tok)).json()["oportunidade"]["id"]


# --------------------------------------------------------------------------
# Autenticação
# --------------------------------------------------------------------------

def test_dashboard_exige_autenticacao_401(client):
    assert client.get("/api/dashboard/oportunidades").status_code == 401


# --------------------------------------------------------------------------
# Agregação real
# --------------------------------------------------------------------------

def test_dashboard_vazio_zera_explicitamente(client):
    s = _session(); _user(s, "CONSULTA", "leitor@dash.com"); s.flush()
    tok = _login(client, "leitor@dash.com")
    data = client.get("/api/dashboard/oportunidades", headers=_h(tok)).json()
    assert data["total_oportunidades"] == 0
    assert data["bloqueadas"] == 0
    assert data["por_modalidade"] == {}
    assert data["por_fase"] == {}
    assert data["riscos_criticos_ativos"] == 0


def test_dashboard_agrega_por_modalidade_fase_municipio(client):
    s = _session(); _user(s, "ANALISTA", "ana@dash.com")
    pr1 = _prop(s, city="Curitiba"); pr2 = _prop(s, city="Londrina"); s.flush()
    tok = _login(client, "ana@dash.com")
    o1 = _criar(client, tok, pr1.id, modality="JUDICIAL")
    o2 = _criar(client, tok, pr2.id, modality="JUDICIAL")
    _criar(client, tok, pr1.id)  # INDEFINIDO default
    # Avança o1 para F1_TRIAGEM para diferenciar fases (conclui o gate de F0 antes).
    client.post(f"/api/oportunidades/{o1}/fase/estado", json={"state": "CONCLUIDA"}, headers=_h(tok))
    client.post(f"/api/oportunidades/{o1}/transicao", json={"target_phase": "F1_TRIAGEM"}, headers=_h(tok))

    data = client.get("/api/dashboard/oportunidades", headers=_h(tok)).json()
    assert data["total_oportunidades"] == 3
    assert data["por_modalidade"]["JUDICIAL"] == 2
    assert data["por_modalidade"]["INDEFINIDO"] == 1
    assert data["por_municipio"]["Curitiba"] == 2
    assert data["por_municipio"]["Londrina"] == 1
    assert data["por_fase"]["F1_TRIAGEM"] == 1
    assert data["por_fase"]["F0_INTAKE"] == 2
    # Fontes rastreáveis declaradas.
    assert "opportunities" in data["fontes"]["por_status/por_modalidade"]


def test_dashboard_conta_riscos_criticos_ativos(client):
    s = _session(); _user(s, "ANALISTA", "ana2@dash.com")
    pr = _prop(s); s.flush()
    tok = _login(client, "ana2@dash.com")
    oid = _criar(client, tok, pr.id)
    ses = _session()
    ses.add(models.Risk(property_id=pr.id, opportunity_id=oid, category="JURIDICO",
                         description="risco crítico", severity="CRITICA", status="ATIVO"))
    ses.add(models.Risk(property_id=pr.id, opportunity_id=oid, category="JURIDICO",
                        description="risco médio", severity="MEDIA", status="ATIVO"))
    ses.add(models.Risk(property_id=pr.id, opportunity_id=oid, category="JURIDICO",
                        description="crítico resolvido", severity="CRITICA", status="RESOLVIDO"))
    ses.flush()
    data = client.get("/api/dashboard/oportunidades", headers=_h(tok)).json()
    assert data["riscos_criticos_ativos"] == 1


# --------------------------------------------------------------------------
# Listagem: filtros + paginação
# --------------------------------------------------------------------------

def test_listagem_filtra_por_modalidade_e_municipio(client):
    s = _session(); _user(s, "ANALISTA", "ana3@dash.com")
    pr1 = _prop(s, city="Curitiba"); pr2 = _prop(s, city="Maringa"); s.flush()
    tok = _login(client, "ana3@dash.com")
    _criar(client, tok, pr1.id, modality="JUDICIAL")
    _criar(client, tok, pr2.id, modality="VENDA_DIRETA")

    jud = client.get("/api/oportunidades", params={"modality": "JUDICIAL"}, headers=_h(tok)).json()
    assert jud["total"] == 1 and jud["itens"][0]["modality"] == "JUDICIAL"

    mga = client.get("/api/oportunidades", params={"municipality": "Maringa"}, headers=_h(tok)).json()
    assert mga["total"] == 1 and mga["itens"][0]["municipio"] == "Maringa"


def test_listagem_pagina_resultados(client):
    s = _session(); _user(s, "ANALISTA", "ana4@dash.com")
    pr = _prop(s); s.flush()
    tok = _login(client, "ana4@dash.com")
    for _ in range(5):
        _criar(client, tok, pr.id)
    page = client.get("/api/oportunidades", params={"limit": 2, "offset": 0}, headers=_h(tok)).json()
    assert page["total"] == 5
    assert len(page["itens"]) == 2
    assert page["limit"] == 2 and page["offset"] == 0
    page2 = client.get("/api/oportunidades", params={"limit": 2, "offset": 4}, headers=_h(tok)).json()
    assert len(page2["itens"]) == 1
