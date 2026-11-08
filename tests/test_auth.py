"""Testes de autenticação/RBAC (Onda 11): login, me, gestão de usuários, permissões
por papel, proteção de endpoints e compatibilidade do X-Admin-Token.

PostgreSQL real (fixture ``db``) + TestClient HTTP. Usa JWT_SECRET_KEY de teste via
monkeypatch (falha-fechada sem segredo).
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
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-de-teste-123", raising=False)
    monkeypatch.setattr(settings, "access_token_expire_minutes", 60, raising=False)
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


def _seed_user(db, email="admin@teste.com", password="senha-forte-123", role="ADMIN", active=True):
    u = models.User(email=email, name="Teste", password_hash=auth.hash_password(password), role=role, active=active)
    db.add(u); db.flush()
    return u


# --------------------------------------------------------------------------
# Hashing / JWT (unidade)
# --------------------------------------------------------------------------

def test_hash_e_verify_senha(db):
    h = auth.hash_password("senha-forte-123")
    assert h and h != "senha-forte-123"
    assert auth.verify_password("senha-forte-123", h) is True
    assert auth.verify_password("errada", h) is False


def test_hash_recusa_senha_curta(db):
    with pytest.raises(auth.AuthError):
        auth.hash_password("curta")


def test_jwt_roundtrip(db, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-de-teste-123", raising=False)
    user = _seed_user(db)
    tok = auth.create_access_token(user)
    payload = auth.decode_token(tok["access_token"])
    assert payload["sub"] == str(user.id) and payload["role"] == "ADMIN"


def test_jwt_sem_segredo_falha_fechada(db, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", None, raising=False)
    user = _seed_user(db)
    with pytest.raises(auth.AuthError) as exc:
        auth.create_access_token(user)
    assert exc.value.status_code == 503


# --------------------------------------------------------------------------
# HTTP: login / me
# --------------------------------------------------------------------------

def test_login_sucesso_e_me(client):
    # Semeia usuário via a sessão do client (get_db override).
    gen = app.dependency_overrides[get_db]()
    session = next(gen)
    _seed_user(session, email="ana@teste.com", password="senha-forte-123", role="ANALISTA")
    session.flush()
    resp = client.post("/api/auth/login", json={"email": "ana@teste.com", "password": "senha-forte-123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == "ana@teste.com" and body["user"]["role"] == "ANALISTA"
    assert "analysis:write" in body["permissions"] and "read" in body["permissions"]


def test_login_credencial_invalida_401(client):
    gen = app.dependency_overrides[get_db](); session = next(gen)
    _seed_user(session, email="x@teste.com", password="senha-forte-123"); session.flush()
    bad = client.post("/api/auth/login", json={"email": "x@teste.com", "password": "errada"})
    assert bad.status_code == 401


def test_login_usuario_inativo_401(client):
    gen = app.dependency_overrides[get_db](); session = next(gen)
    _seed_user(session, email="inativo@teste.com", password="senha-forte-123", active=False); session.flush()
    resp = client.post("/api/auth/login", json={"email": "inativo@teste.com", "password": "senha-forte-123"})
    assert resp.status_code == 401


def test_me_sem_token_401(client):
    assert client.get("/api/auth/me").status_code == 401


# --------------------------------------------------------------------------
# HTTP: gestão de usuários (somente ADMIN)
# --------------------------------------------------------------------------

def _login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def test_admin_cria_usuario_e_lista(client):
    gen = app.dependency_overrides[get_db](); session = next(gen)
    _seed_user(session, email="admin@teste.com", password="senha-forte-123", role="ADMIN"); session.flush()
    tok = _login(client, "admin@teste.com", "senha-forte-123")
    h = {"Authorization": f"Bearer {tok}"}
    resp = client.post("/api/auth/usuarios", json={"email": "novo@teste.com", "password": "outra-senha-123", "role": "CONSULTA"}, headers=h)
    assert resp.status_code == 201, resp.text
    lst = client.get("/api/auth/usuarios", headers=h)
    assert lst.status_code == 200 and lst.json()["total"] >= 2


def test_consulta_nao_gerencia_usuarios_403(client):
    gen = app.dependency_overrides[get_db](); session = next(gen)
    _seed_user(session, email="leitor@teste.com", password="senha-forte-123", role="CONSULTA"); session.flush()
    tok = _login(client, "leitor@teste.com", "senha-forte-123")
    resp = client.get("/api/auth/usuarios", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 403


# --------------------------------------------------------------------------
# RBAC: endpoint admin protegido aceita JWT de ADMIN e recusa CONSULTA
# --------------------------------------------------------------------------

def test_admin_endpoint_aceita_jwt_admin(client):
    gen = app.dependency_overrides[get_db](); session = next(gen)
    _seed_user(session, email="admin2@teste.com", password="senha-forte-123", role="ADMIN"); session.flush()
    client.get("/api/admin/cobertura")  # semeia catálogo/municípios
    tok = _login(client, "admin2@teste.com", "senha-forte-123")
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "COTA_CONDOMINIAL", "level": "MANUAL"}, headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 201, resp.text


def test_admin_endpoint_recusa_jwt_consulta_403(client):
    gen = app.dependency_overrides[get_db](); session = next(gen)
    _seed_user(session, email="leitor2@teste.com", password="senha-forte-123", role="CONSULTA"); session.flush()
    client.get("/api/admin/cobertura")
    tok = _login(client, "leitor2@teste.com", "senha-forte-123")
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "COTA_CONDOMINIAL"}, headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 403


def test_compat_x_admin_token_preservado(client, monkeypatch):
    # O mecanismo de compatibilidade (X-Admin-Token) continua válido durante a transição.
    monkeypatch.setattr(settings, "admin_api_token", "token-compat", raising=False)
    client.get("/api/admin/cobertura")
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "OUTRO_DEBITO_MUNICIPAL", "level": "MANUAL"}, headers={"X-Admin-Token": "token-compat"})
    assert resp.status_code == 201, resp.text


def test_bootstrap_admin_idempotente(db, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "s", raising=False)
    monkeypatch.setattr(settings, "auth_bootstrap_admin_email", "boot@teste.com", raising=False)
    monkeypatch.setattr(settings, "auth_bootstrap_admin_password", "senha-forte-123", raising=False)
    assert auth.ensure_bootstrap_admin(db) is True
    db.flush()
    assert auth.ensure_bootstrap_admin(db) is False  # já existe usuário
