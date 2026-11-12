"""Portão de segurança global (security_gate): autenticação, autorização por papel,
rate limit, concorrência, default-deny e proteção das operações críticas/administrativas.

PostgreSQL real + TestClient. Estes testes rodam com o portão REAL (marcador
``security_gate``); os demais testes da suíte usam o bypass do conftest.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from backend.app import auth, models, security
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

pytestmark = pytest.mark.security_gate

SENHA = "senha-forte-123"


@pytest.fixture
def env(postgres_engine, monkeypatch):
    if TestClient is None:
        pytest.skip("httpx/TestClient indisponível")
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-de-teste-123", raising=False)
    monkeypatch.setattr(settings, "access_token_expire_minutes", 60, raising=False)
    monkeypatch.setattr(settings, "admin_api_token", None, raising=False)
    monkeypatch.setattr(settings, "authz_role_tokens", None, raising=False)
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield SimpleNamespace(client=TestClient(app, raise_server_exceptions=False), db=session)
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close(); transaction.rollback(); connection.close()


def _user(env, role="ANALISTA", active=True, email=None):
    email = email or f"{role.lower()}-{time.monotonic_ns()}@seg.test"
    user = models.User(email=email, name="Teste", password_hash=auth.hash_password(SENHA), role=role, active=active)
    env.db.add(user); env.db.flush()
    return user


def _login(env, role="ANALISTA"):
    user = _user(env, role)
    resp = env.client.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _property(env):
    prop = models.Property(title="Imóvel Segurança", address="Rua S", city="São Paulo", state="SP")
    env.db.add(prop); env.db.flush()
    return prop


# --------------------------------------------------------------------------- rotas públicas

def test_health_e_login_sao_publicos(env):
    assert env.client.get("/health").status_code == 200
    bad = env.client.post("/api/auth/login", json={"email": "ninguem@seg.test", "password": "errada-123"})
    assert bad.status_code == 401
    assert "Credenciais inválidas" in bad.json()["detail"]  # chegou ao handler de login (não ao portão)


# --------------------------------------------------------------------------- sem autenticação

ROTAS_PROTEGIDAS = [
    ("GET", "/api/imoveis"),
    ("GET", "/api/dashboard"),
    ("GET", "/api/imoveis/1"),
    ("GET", "/api/checklist"),
    ("GET", "/api/juridico/biblioteca"),
    ("GET", "/api/admin/municipios"),
    ("GET", "/api/leiloeiros"),
    ("GET", "/api/mercado"),
    ("GET", "/api/imoveis/1/debitos"),
    ("GET", "/api/documentos/versoes/1/arquivo"),
    ("POST", "/api/imoveis"),
    ("POST", "/api/imoveis/1/analisar"),
    ("POST", "/api/imoveis/1/analises/1/agents/documental"),
    ("POST", "/api/imoveis/1/analises/1/agents/checklist"),
    ("POST", "/api/imoveis/1/documentos"),
    ("POST", "/api/documentos/1/versoes"),
    ("POST", "/api/imoveis/1/documentos/1/extrair"),
    ("POST", "/api/imoveis/1/eventos/1/reanalisar"),
    ("POST", "/api/imoveis/1/processos/consultar"),
    ("POST", "/api/imoveis/1/localizacao/geocodificar"),
    ("POST", "/api/monitoring/rag/reprocess"),
    ("POST", "/api/admin/parametros"),
    ("PATCH", "/api/imoveis/1"),
    ("DELETE", "/api/leiloeiros/1"),
    ("GET", "/api/leiloeiros/1/portais/1/credencial"),
]


@pytest.mark.parametrize("method,path", ROTAS_PROTEGIDAS)
def test_sem_autenticacao_401(env, method, path):
    resp = env.client.request(method, path)
    assert resp.status_code == 401, f"{method} {path}: {resp.status_code} {resp.text}"
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_token_invalido_401(env):
    for header in ("Bearer abc.def.ghi", "Bearer", "Basic dXNlcjpzZW5oYQ==", "bearer "):
        resp = env.client.get("/api/imoveis", headers={"Authorization": header})
        assert resp.status_code == 401, header


def test_token_assinado_com_outro_segredo_401(env):
    user = _user(env)
    forjado = jwt.encode({"sub": str(user.id), "role": "ADMIN", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "outro-segredo", algorithm="HS256")
    assert env.client.get("/api/imoveis", headers={"Authorization": f"Bearer {forjado}"}).status_code == 401


def test_sessao_expirada_401(env):
    user = _user(env)
    expirado = jwt.encode({"sub": str(user.id), "role": user.role, "exp": datetime.now(timezone.utc) - timedelta(minutes=5)}, settings.jwt_secret_key, algorithm="HS256")
    assert env.client.get("/api/imoveis", headers={"Authorization": f"Bearer {expirado}"}).status_code == 401


def test_usuario_inativo_ou_removido_perde_acesso_401(env):
    user = _user(env)
    token = env.client.post("/api/auth/login", json={"email": user.email, "password": SENHA}).json()["access_token"]
    assert env.client.get("/api/imoveis", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    user.active = False; env.db.flush()
    assert env.client.get("/api/imoveis", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_sem_jwt_secret_falha_fechada(env, monkeypatch):
    headers = _login(env)
    monkeypatch.setattr(settings, "jwt_secret_key", None, raising=False)
    assert env.client.get("/api/imoveis", headers=headers).status_code == 401


# --------------------------------------------------------------------------- autorização por papel

def test_consulta_le_mas_nao_escreve(env):
    headers = _login(env, "CONSULTA")
    assert env.client.get("/api/imoveis", headers=headers).status_code == 200
    escrita = env.client.post("/api/imoveis", headers=headers, json={"title": "X", "address": "Y", "city": "Z", "state": "SP"})
    assert escrita.status_code == 403
    analise = env.client.post("/api/imoveis/1/analisar", headers=headers)
    assert analise.status_code == 403
    upload = env.client.post("/api/imoveis/1/documentos", headers=headers, files={"file": ("a.txt", b"x", "text/plain")})
    assert upload.status_code == 403
    assert env.client.patch("/api/imoveis/1", headers=headers, json={"title": "novo"}).status_code == 403


def test_analista_passa_no_portao_nas_operacoes_de_analise(env):
    headers = _login(env, "ANALISTA")
    # Passou pelo portão: o erro agora é de negócio (imóvel inexistente), não 401/403.
    assert env.client.post("/api/imoveis/987654/analisar", headers=headers).status_code == 404
    assert env.client.post("/api/imoveis/987654/documentos/1/extrair", headers=headers, json={"document_type": "EDITAL"}).status_code == 404


def test_analista_nao_executa_operacoes_administrativas(env):
    headers = _login(env, "ANALISTA")
    assert env.client.post("/api/checklist", headers=headers, json={"canonical_key": "X_TESTE", "question": "q"}).status_code == 403
    assert env.client.patch("/api/checklist/1", headers=headers, json={"question": "q"}).status_code == 403
    assert env.client.post("/api/checklist/1/desativar", headers=headers).status_code == 403
    assert env.client.delete("/api/leiloeiros/1", headers=headers).status_code == 403
    assert env.client.get("/api/leiloeiros/1/portais/1/credencial", headers=headers).status_code == 403
    assert env.client.post("/api/admin/municipios", headers=headers, json={"name": "X", "state": "SP"}).status_code == 403
    assert env.client.get("/api/auth/usuarios", headers=headers).status_code == 403


def test_administrador_acessa_operacoes_administrativas(env):
    headers = _login(env, "ADMIN")
    assert env.client.get("/api/auth/usuarios", headers=headers).status_code == 200
    # Passa no portão administrativo: 404 de negócio (item inexistente), não 403.
    assert env.client.patch("/api/checklist/987654", headers=headers, json={"question": "q"}).status_code == 404
    assert env.client.delete("/api/leiloeiros/987654", headers=headers).status_code in (404, 200)


def test_operador_nao_cria_usuarios(env):
    headers = _login(env, "OPERADOR")
    assert env.client.post("/api/auth/usuarios", headers=headers, json={"email": "n@seg.test", "password": SENHA, "role": "CONSULTA"}).status_code == 403


# --------------------------------------------------------------------------- compat X-Admin-Token

def test_x_admin_token_de_compat_so_vale_quando_configurado(env, monkeypatch):
    assert env.client.get("/api/imoveis", headers={"X-Admin-Token": "qualquer"}).status_code == 401
    monkeypatch.setattr(settings, "admin_api_token", "token-compat-123", raising=False)
    assert env.client.get("/api/imoveis", headers={"X-Admin-Token": "token-compat-123"}).status_code == 200
    assert env.client.get("/api/imoveis", headers={"X-Admin-Token": "errado"}).status_code == 401


# --------------------------------------------------------------------------- leitura de documentos

def test_download_de_documento_exige_autenticacao_e_valida_existencia(env):
    assert env.client.get("/api/documentos/versoes/1/arquivo").status_code == 401
    headers = _login(env, "CONSULTA")
    assert env.client.get("/api/documentos/versoes/987654/arquivo", headers=headers).status_code == 404


# --------------------------------------------------------------------------- rate limit / concorrência

def test_rate_limit_de_operacao_critica_429_com_retry_after(env, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_critical_per_minute", 2, raising=False)
    headers = _login(env, "ANALISTA")
    codigos = [env.client.post("/api/imoveis/987654/analisar", headers=headers).status_code for _ in range(3)]
    assert codigos == [404, 404, 429]
    limitado = env.client.post("/api/imoveis/987654/analisar", headers=headers)
    assert limitado.status_code == 429 and int(limitado.headers["retry-after"]) >= 1


def test_rate_limit_e_por_usuario(env, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_critical_per_minute", 1, raising=False)
    a, b = _login(env, "ANALISTA"), _login(env, "ANALISTA")
    assert env.client.post("/api/imoveis/987654/analisar", headers=a).status_code == 404
    assert env.client.post("/api/imoveis/987654/analisar", headers=a).status_code == 429
    assert env.client.post("/api/imoveis/987654/analisar", headers=b).status_code == 404  # outro usuário não é afetado


def test_leituras_nao_sofrem_rate_limit_de_operacao_critica(env, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_critical_per_minute", 1, raising=False)
    headers = _login(env, "CONSULTA")
    assert all(env.client.get("/api/imoveis", headers=headers).status_code == 200 for _ in range(5))


def test_rate_limit_de_upload(env, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_upload_per_minute", 1, raising=False)
    headers = _login(env, "ANALISTA")
    files = {"file": ("a.txt", b"conteudo", "text/plain")}
    assert env.client.post("/api/imoveis/987654/documentos", headers=headers, files=files).status_code == 404
    assert env.client.post("/api/imoveis/987654/documentos", headers=headers, files=files).status_code == 429


def test_limite_de_concorrencia_por_usuario():
    guard = security.ConcurrencyGuard()
    assert guard.acquire("user:1", 2) and guard.acquire("user:1", 2)
    assert guard.acquire("user:1", 2) is False
    assert guard.acquire("user:2", 2) is True  # outro usuário não é afetado
    guard.release("user:1")
    assert guard.acquire("user:1", 2) is True


def test_janela_deslizante_libera_apos_a_janela():
    limiter = security.SlidingWindowLimiter()
    assert limiter.hit("k", 2, window=10, now=100.0) is None
    assert limiter.hit("k", 2, window=10, now=101.0) is None
    espera = limiter.hit("k", 2, window=10, now=102.0)
    assert espera is not None and 7.0 <= espera <= 8.0
    assert limiter.hit("k", 2, window=10, now=111.0) is None  # o 1º evento expirou


# --------------------------------------------------------------------------- default-deny e inventário

def test_rota_nova_nasce_protegida_default_deny(postgres_engine):
    mini = FastAPI(dependencies=[Depends(security.security_gate)])

    @mini.get("/api/novo-recurso")
    def novo():
        return {"ok": True}

    @mini.post("/api/novo-recurso")
    def novo_post():
        return {"ok": True}

    client = TestClient(mini, raise_server_exceptions=False)
    assert client.get("/api/novo-recurso").status_code == 401
    assert client.post("/api/novo-recurso").status_code == 401


def test_inventario_de_rotas_somente_as_publicas_previstas_sao_abertas():
    publicas = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if security.classify(method, route.path).permission is None:
                publicas.add((method, route.path))
    assert publicas == set(security.PUBLIC_ROUTES)


def test_app_registra_o_portao_como_dependencia_global():
    assert any(dep.dependency is security.security_gate for dep in app.router.dependencies)


def test_toda_regra_de_politica_aponta_para_uma_rota_real():
    """Se uma rota protegida for renomeada, a regra deixaria de casar e ela cairia na
    política padrão (mais fraca para operações críticas/administrativas)."""
    reais = [(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods]
    for methods, pattern, policy in security._RULES:
        assert any(m in methods and pattern.match(path) for m, path in reais), f"regra sem rota correspondente: {pattern.pattern}"


def test_operacoes_criticas_classificadas_com_bucket():
    criticas = [
        ("POST", "/api/imoveis/{property_id}/analisar"),
        ("POST", "/api/imoveis/{property_id}/analises/{analysis_id}/agents/juridico"),
        ("POST", "/api/imoveis/{property_id}/documentos/{document_version_id}/extrair"),
        ("POST", "/api/imoveis/{property_id}/eventos/{event_id}/reanalisar"),
        ("POST", "/api/monitoring/rag/reprocess"),
        ("POST", "/api/imoveis/{property_id}/processos/consultar"),
    ]
    for method, path in criticas:
        policy = security.classify(method, path)
        assert policy.bucket == "critical" and policy.permission == "analysis:write", path
    assert security.classify("POST", "/api/imoveis/{property_id}/documentos").bucket == "upload"
    assert security.classify("GET", "/api/imoveis").permission == "read"
    assert security.classify("DELETE", "/api/imoveis/{property_id}/custos/{cost_id}").permission == "analysis:write"
    assert security.classify("POST", "/api/checklist").permission == "admin:write"


# --------------------------------------------------------------------------- sanitização na borda HTTP

def test_erro_inesperado_devolve_mensagem_generica_com_referencia(env, monkeypatch):
    prop = _property(env)
    headers = _login(env, "CONSULTA")

    def explode(_prop):
        raise ValueError("falha em postgresql://radar:SENHA-SECRETA@postgres:5432/radar com sk-ABCDEF1234567890")

    monkeypatch.setattr("backend.app.main.build_finance", explode)
    resp = env.client.get(f"/api/imoveis/{prop.id}/financeiro", headers=headers)
    assert resp.status_code == 500
    corpo = resp.text
    assert "SENHA-SECRETA" not in corpo and "sk-ABCDEF" not in corpo and "postgresql://" not in corpo and "Traceback" not in corpo
    assert re.search(r"ref: [A-Za-z0-9._-]{8,}", resp.json()["detail"])
    assert resp.headers.get("x-request-id")


def test_erro_da_orquestracao_nao_expoe_detalhe_interno(env, monkeypatch):
    prop = _property(env)
    headers = _login(env, "ANALISTA")

    class Quebra:
        def __init__(self, db): pass
        def run(self, *a, **k):
            raise RuntimeError("Incorrect API key provided: sk-proj-ABCDEF123456; conn=postgresql://u:p@h/db")

    monkeypatch.setattr("backend.app.main.AnalysisOrchestrator", Quebra)
    resp = env.client.post(f"/api/imoveis/{prop.id}/analisar", headers=headers)
    assert resp.status_code == 502
    assert "sk-proj" not in resp.text and "postgresql" not in resp.text and "API key" not in resp.text
    assert "ref:" in resp.json()["detail"]


def test_validacao_422_nao_ecoa_o_valor_enviado(env):
    resp = env.client.post("/api/auth/login", json={"email": "a@seg.test", "password": ["SENHA-ENVIADA-123"]})
    assert resp.status_code == 422
    assert "SENHA-ENVIADA-123" not in resp.text
    detail = resp.json()["detail"]
    assert isinstance(detail, list) and {"loc", "msg", "type"} <= set(detail[0])


def test_correlation_id_do_cliente_e_propagado_e_invalido_e_substituido(env):
    ok = env.client.get("/health", headers={"X-Request-ID": "abc-123-correlacao"})
    assert ok.headers["x-request-id"] == "abc-123-correlacao"
    ruim = env.client.get("/health", headers={"X-Request-ID": "x\ninjetado"})
    assert ruim.headers["x-request-id"] != "x\ninjetado" and re.fullmatch(r"[0-9a-f]{16}", ruim.headers["x-request-id"])


def test_dominios_de_analise_validados(env):
    prop = _property(env)
    headers = _login(env, "ANALISTA")
    assert env.client.post(f"/api/imoveis/{prop.id}/analisar", headers=headers, json={"domains": ["invalido"]}).status_code == 422
    assert env.client.post(f"/api/imoveis/{prop.id}/analisar", headers=headers, json={"query": "x" * 501}).status_code == 422
    assert env.client.post(f"/api/imoveis/{prop.id}/analisar", headers=headers, json={"domains": ["a"] * 6}).status_code == 422
