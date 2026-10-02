"""TASK 75 — testes de backend: break-even, leiloeiros/portais/credencial (não
exposição de senha), hubs de agregação e associação leiloeiro↔leilão.

Usa a fixture `client` (TestClient + savepoint/rollback — não toca dados reais) e
testes unitários puros do finance. Sem LLM, sem DataJud real.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app
from backend.app.finance import SaleAssumptions, calculate_break_even

# TASK 75.1: chave/token usados apenas no ambiente de teste (nunca versionados em
# produção). A chave habilita a criptografia reversível; o token protege o endpoint.
_TEST_PORTAL_KEY = "chave-de-teste-portal-75-1"
_TEST_ADMIN_TOKEN = "token-admin-teste-75-1"

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

REQUIRED_TABLES = {"properties", "auctioneers", "portal_accesses"}


# ---------------------------------------------------------------- break-even
def test_break_even_base_venda():
    # CT=100000, corretagem 5%, tributo 0, base VENDA → V* = 100000/(1-0.05) = 105263.15...
    r = calculate_break_even(total_cost=Decimal("100000"), sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0"), tax_base="VENDA"))
    assert r["razao"] == "OK"
    assert abs(r["break_even"] - (Decimal("100000") / Decimal("0.95"))) < Decimal("0.01")


def test_break_even_base_ganho():
    # base GANHO: V* = CT*(1-t)/(1-c-t)
    r = calculate_break_even(total_cost=Decimal("100000"), sale=SaleAssumptions(corretagem_pct=Decimal("0.05"), tributo_pct=Decimal("0.15"), tax_base="GANHO"))
    esperado = (Decimal("100000") * (Decimal("1") - Decimal("0.15"))) / (Decimal("1") - Decimal("0.05") - Decimal("0.15"))
    assert abs(r["break_even"] - esperado) < Decimal("0.01")


def test_break_even_custo_desconhecido():
    r = calculate_break_even(total_cost=None, sale=SaleAssumptions())
    assert r["break_even"] is None
    assert r["razao"] == "CUSTO_TOTAL_DESCONHECIDO"


def test_break_even_custos_saida_inviabilizam():
    # corretagem + tributo >= 1 → denominador <= 0 → indefinido
    r = calculate_break_even(total_cost=Decimal("100000"), sale=SaleAssumptions(corretagem_pct=Decimal("0.6"), tributo_pct=Decimal("0.5"), tax_base="VENDA"))
    assert r["break_even"] is None
    assert r["razao"] == "CUSTOS_SAIDA_INVIABILIZAM"


# ---------------------------------------------------------------- fixture HTTP
@pytest.fixture
def client(postgres_engine, monkeypatch):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations 0014 (leiloeiros) ainda não aplicadas")
    # Habilita criptografia + proteção do endpoint só para o teste (restaurado ao fim).
    monkeypatch.setattr(settings, "portal_secret_key", _TEST_PORTAL_KEY, raising=False)
    monkeypatch.setattr(settings, "portal_admin_token", _TEST_ADMIN_TOKEN, raising=False)
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
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------- leiloeiros
def test_cadastro_leiloeiro_e_portal(client):
    resp = client.post("/api/leiloeiros", json={"name": "Leiloeiro Teste", "company": "LT Ltda"})
    assert resp.status_code == 201, resp.text
    aid = resp.json()["id"]
    resp = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "Caixa", "username": "user@x", "secret": "senha-super-secreta", "two_factor_enabled": True})
    assert resp.status_code == 201, resp.text
    portal = resp.json()
    # SEGURANÇA: a resposta do POST do portal NUNCA inclui o secret.
    assert "secret" not in portal
    assert portal["has_secret"] is True
    assert portal["two_factor_enabled"] is True


def test_senha_nao_aparece_em_listagem(client):
    resp = client.post("/api/leiloeiros", json={"name": "Sigiloso"})
    aid = resp.json()["id"]
    client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P", "secret": "TOP-SECRET-123"})
    # Listagem global e detalhe não podem vazar o secret em lugar nenhum do payload.
    listagem = client.get("/api/leiloeiros").text
    detalhe = client.get(f"/api/leiloeiros/{aid}").text
    assert "TOP-SECRET-123" not in listagem
    assert "TOP-SECRET-123" not in detalhe
    assert "secret" not in detalhe or "has_secret" in detalhe


def test_credencial_so_via_endpoint_dedicado(client):
    resp = client.post("/api/leiloeiros", json={"name": "Com Portal"})
    aid = resp.json()["id"]
    portal = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P", "username": "u", "secret": "REVELAR-123"}).json()
    pid = portal["id"]
    # O endpoint dedicado retorna a credencial (ação explícita/auditável), MAS exige
    # o token de administração no header X-Portal-Admin-Token (TASK 75.1).
    reveal = client.get(f"/api/leiloeiros/{aid}/portais/{pid}/credencial", headers={"X-Portal-Admin-Token": _TEST_ADMIN_TOKEN})
    assert reveal.status_code == 200
    assert reveal.json()["secret"] == "REVELAR-123"


# ---------------------------------------------------- TASK 75.1 — segurança
def test_secret_persistido_e_cifrado_nao_texto_puro(client):
    """A credencial NUNCA é gravada em texto puro: o valor no banco é um token
    cifrado (prefixo enc:v1:) e não contém a senha original."""
    aid = client.post("/api/leiloeiros", json={"name": "Cripto"}).json()["id"]
    portal = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P", "secret": "SENHA-CLARA-999"}).json()
    pid = portal["id"]
    # Inspeção direta do valor armazenado (não via API).
    session = next(iter(app.dependency_overrides[get_db]()))
    stored = session.get(models.PortalAccess, pid).secret
    assert stored is not None
    assert stored.startswith("enc:v1:")
    assert "SENHA-CLARA-999" not in stored


def test_credencial_sem_token_e_recusada(client):
    """Sem o header de administração, o endpoint de recuperação falha fechada (401)."""
    aid = client.post("/api/leiloeiros", json={"name": "Protegido"}).json()["id"]
    pid = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P", "secret": "X-123"}).json()["id"]
    sem_token = client.get(f"/api/leiloeiros/{aid}/portais/{pid}/credencial")
    assert sem_token.status_code == 401
    token_errado = client.get(f"/api/leiloeiros/{aid}/portais/{pid}/credencial", headers={"X-Portal-Admin-Token": "errado"})
    assert token_errado.status_code == 401


def test_credencial_sem_protecao_configurada_falha_fechada(client, monkeypatch):
    """Se o PORTAL_ADMIN_TOKEN não está configurado, o acesso é negado (503) — nunca público."""
    aid = client.post("/api/leiloeiros", json={"name": "SemToken"}).json()["id"]
    pid = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P", "secret": "Y-123"}).json()["id"]
    monkeypatch.setattr(settings, "portal_admin_token", None, raising=False)
    resp = client.get(f"/api/leiloeiros/{aid}/portais/{pid}/credencial", headers={"X-Portal-Admin-Token": "qualquer"})
    assert resp.status_code == 503


def test_update_portal_troca_credencial_cifrada(client):
    """PATCH do portal edita dados e, opcionalmente, troca a credencial (cifrada).
    A resposta nunca inclui o secret."""
    aid = client.post("/api/leiloeiros", json={"name": "Edita Portal"}).json()["id"]
    pid = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P0", "secret": "antiga"}).json()["id"]
    resp = client.patch(f"/api/leiloeiros/{aid}/portais/{pid}", json={"portal": "P1", "username": "novo@x", "secret": "nova-senha"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "secret" not in body
    assert body["portal"] == "P1" and body["username"] == "novo@x" and body["has_secret"] is True
    # A nova credencial é a que o endpoint protegido devolve.
    reveal = client.get(f"/api/leiloeiros/{aid}/portais/{pid}/credencial", headers={"X-Portal-Admin-Token": _TEST_ADMIN_TOKEN})
    assert reveal.json()["secret"] == "nova-senha"


def test_documento_e_associacao_leilao(client):
    aid = client.post("/api/leiloeiros", json={"name": "Doc"}).json()["id"]
    doc = client.post(f"/api/leiloeiros/{aid}/documentos", json={"doc_type": "CONTRATO", "name": "Credenciamento.pdf"})
    assert doc.status_code == 201

    pid = client.post("/api/imoveis", json={"title": "Imóvel L75", "address": "R", "city": "SP", "state": "SP", "property_type": "Apto", "area_m2": 60}).json()["id"]
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "100000", "appraisal_value": "150000"})
    link = client.post(f"/api/imoveis/{pid}/leilao/leiloeiro", json={"auctioneer_id": aid})
    assert link.status_code == 200, link.text
    assert link.json()["auctioneer_id"] == aid


# ---------------------------------------------------------------- hubs
def test_dashboard_e_hubs_respondem(client):
    for path in ["/api/dashboard", "/api/imoveis-resumo", "/api/financeiro", "/api/juridico",
                 "/api/riscos", "/api/veredito", "/api/mercado", "/api/ocupacao",
                 "/api/documentos", "/api/historico", "/api/checklist-global"]:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path}: {resp.text}"


def test_dashboard_kpis_estrutura(client):
    body = client.get("/api/dashboard").json()
    assert "kpis" in body and "imoveis" in body["kpis"]
    assert "pipeline" in body and "alertas" in body


def test_imoveis_resumo_inclui_break_even(client):
    pid = client.post("/api/imoveis", json={"title": "Resumo BE", "address": "R", "city": "SP", "state": "SP", "property_type": "Apto", "area_m2": 60}).json()["id"]
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "100000", "appraisal_value": "150000"})
    client.post(f"/api/imoveis/{pid}/custos", json={"category": "ITBI", "description": "i", "amount": "3000"})
    client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={"corretagem_pct": "0.05", "tributo_pct": "0.0", "tax_base": "VENDA", "valor_venda_estimado": "200000"})
    itens = client.get("/api/imoveis-resumo").json()
    alvo = next((r for r in itens if r["id"] == pid), None)
    assert alvo is not None
    assert "break_even" in alvo
