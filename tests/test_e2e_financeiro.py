"""TASK 5 — Validação E2E do fluxo financeiro pela camada HTTP real.

Exercita o fluxo de ponta a ponta do BACKEND via ``TestClient`` (FastAPI):
requisição HTTP → rota → sessão PostgreSQL (override de get_db com savepoint,
isolado por transação; NÃO toca dados reais) → serialização JSON de resposta.

Cobre os 10 cenários obrigatórios da Task 5:
1. Todas as premissas materiais preenchidas → preço máximo pode ser DEFINITIVO.
2. ITBI desconhecido → provisório + pendência.
3. Registro desconhecido → provisório + pendência.
4. Comissão de arrematação desconhecida → provisório + pendência.
5. Corretagem de venda desconhecida → provisório + pendência.
6. Tributo de venda desconhecido → provisório + pendência.
7. Salvar premissas, recarregar o imóvel e confirmar persistência.
8. Nova análise NÃO altera o snapshot de uma análise anterior (histórico).
9. Metas de lucro, margem e ROI, incluindo cenário inviável.
10. Erros de validação apresentados corretamente (HTTP 4xx).

NÃO usa LLM/rede/serviços externos. NÃO valida o navegador (browser E2E permanece
manual — ver docs/PROJECT-STATUS). NÃO altera o imóvel 633 nem dados reais.
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


REQUIRED_TABLES = {"properties", "auctions", "financial_analyses"}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient (httpx) indisponível")
    if not REQUIRED_TABLES.issubset(set(inspect(postgres_engine).get_table_names())):
        pytest.skip("Migrations do Radar ainda não aplicadas no banco de testes")
    if "financial_assumptions" not in {c["name"] for c in inspect(postgres_engine).get_columns("auctions")}:
        pytest.skip("Migration 0012 (financial_assumptions) ainda não aplicada")

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


def _criar_imovel_com_leilao(client, *, bid="200000", appraisal="300000"):
    resp = client.post("/api/imoveis", json={
        "title": "Imóvel E2E Financeiro", "address": "Rua E2E, 1",
        "city": "São Paulo", "state": "SP", "property_type": "Apartamento", "area_m2": 70,
    })
    assert resp.status_code == 200, resp.text
    pid = resp.json()["id"]
    resp = client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": bid, "appraisal_value": appraisal})
    assert resp.status_code == 200, resp.text
    return pid


def _add_custo(client, pid, categoria, valor):
    resp = client.post(f"/api/imoveis/{pid}/custos", json={"category": categoria, "description": categoria, "amount": valor})
    assert resp.status_code == 200, resp.text


# Premissas completas materiais: corretagem e tributo informados; ITBI/registro via custos.
_PREMISSAS_COMPLETAS = {
    "goal_kind": "LUCRO_MINIMO", "goal_value": 40000,
    "corretagem_pct": 0.05, "tributo_pct": 0.0, "tax_base": "VENDA",
    "valor_venda_estimado": 320000,
}


def _set_premissas(client, pid, **overrides):
    payload = dict(_PREMISSAS_COMPLETAS)
    payload.update(overrides)
    resp = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --------------------------------------------------------------------------
# Cenário 1 — premissas materiais completas → preço máximo DEFINITIVO
# --------------------------------------------------------------------------

def test_c1_premissas_completas_preco_maximo_definitivo(client):
    pid = _criar_imovel_com_leilao(client)
    _add_custo(client, pid, "ITBI", "10000")
    _add_custo(client, pid, "REGISTRO", "20000")
    # comissão informada no leilão para não ser desconhecida:
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "200000", "appraisal_value": "300000", "commission_percent": "5"})
    fin = _set_premissas(client, pid)["financeiro"]
    assert fin["preco_maximo"] is not None
    assert fin["preco_maximo_definitivo"] is True
    assert fin["preco_maximo_provisorio"] is False


def _preco_maximo_provisorio_por_custo_ausente(client, pid, expect_unknown):
    fin = client.get(f"/api/imoveis/{pid}/financeiro").json()["financeiro"]
    assert fin["preco_maximo"] is not None, "valor parcial deve ser calculado"
    assert fin["preco_maximo_provisorio"] is True
    assert fin["preco_maximo_definitivo"] is False
    assert expect_unknown in fin["preco_maximo_detalhe"]["custos_desconhecidos"]


# --------------------------------------------------------------------------
# Cenários 2-6 — cada custo material desconhecido → provisório + pendência
# --------------------------------------------------------------------------

def test_c2_itbi_desconhecido_provisorio(client):
    pid = _criar_imovel_com_leilao(client)
    _add_custo(client, pid, "REGISTRO", "20000")
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "200000", "appraisal_value": "300000", "commission_percent": "5"})
    _set_premissas(client, pid)
    _preco_maximo_provisorio_por_custo_ausente(client, pid, "itbi")


def test_c3_registro_desconhecido_provisorio(client):
    pid = _criar_imovel_com_leilao(client)
    _add_custo(client, pid, "ITBI", "10000")
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "200000", "appraisal_value": "300000", "commission_percent": "5"})
    _set_premissas(client, pid)
    _preco_maximo_provisorio_por_custo_ausente(client, pid, "registro")


def test_c4_comissao_desconhecida_provisorio(client):
    pid = _criar_imovel_com_leilao(client)  # leilão sem comissão informada
    _add_custo(client, pid, "ITBI", "10000")
    _add_custo(client, pid, "REGISTRO", "20000")
    _set_premissas(client, pid)
    _preco_maximo_provisorio_por_custo_ausente(client, pid, "comissao_arrematacao")


def test_c5_corretagem_desconhecida_provisorio(client):
    pid = _criar_imovel_com_leilao(client)
    _add_custo(client, pid, "ITBI", "10000")
    _add_custo(client, pid, "REGISTRO", "20000")
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "200000", "appraisal_value": "300000", "commission_percent": "5"})
    # corretagem_pct omitida (None):
    _set_premissas(client, pid, corretagem_pct=None, tributo_pct=0.0)
    _preco_maximo_provisorio_por_custo_ausente(client, pid, "corretagem_venda")


def test_c6_tributo_desconhecido_provisorio(client):
    pid = _criar_imovel_com_leilao(client)
    _add_custo(client, pid, "ITBI", "10000")
    _add_custo(client, pid, "REGISTRO", "20000")
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "200000", "appraisal_value": "300000", "commission_percent": "5"})
    _set_premissas(client, pid, corretagem_pct=0.05, tributo_pct=None)
    _preco_maximo_provisorio_por_custo_ausente(client, pid, "tributo_venda")


# --------------------------------------------------------------------------
# Cenário 7 — persistência: salvar, recarregar e confirmar
# --------------------------------------------------------------------------

def test_c7_premissas_persistem_apos_recarregar(client):
    pid = _criar_imovel_com_leilao(client)
    _set_premissas(client, pid, valor_venda_estimado=321000, prazo_meses=9, carregamento_mensal=450)

    # "Recarregar o imóvel": novo GET do dossiê e das premissas.
    premissas = client.get(f"/api/imoveis/{pid}/financeiro/premissas").json()["premissas"]
    assert premissas["valor_venda_estimado"] == "321000"
    assert premissas["prazo_meses"] == 9
    assert premissas["carregamento_mensal"] == "450"

    dossie = client.get(f"/api/imoveis/{pid}/financeiro").json()
    assert dossie["premissas"]["valor_venda_estimado"] == "321000"


# --------------------------------------------------------------------------
# Cenário 8 — nova análise não altera snapshot anterior (histórico)
# --------------------------------------------------------------------------

def test_c8_nova_analise_preserva_snapshot_anterior(client):
    pid = _criar_imovel_com_leilao(client)
    _set_premissas(client, pid, goal_value=40000)
    v1 = client.post(f"/api/imoveis/{pid}/financeiro/analisar").json()
    assert v1["analysis_version"] == 1

    _set_premissas(client, pid, goal_value=60000)
    v2 = client.post(f"/api/imoveis/{pid}/financeiro/analisar").json()
    assert v2["analysis_version"] == 2

    historico = client.get(f"/api/imoveis/{pid}/financeiro").json()["historico"]
    versoes = {h["analysis_version"]: h for h in historico}
    assert versoes[1]["inputs"]["premissas"]["goal_value"] == "40000"  # inalterado
    assert versoes[2]["inputs"]["premissas"]["goal_value"] == "60000"


# --------------------------------------------------------------------------
# Cenário 9 — metas lucro/margem/ROI + inviável
# --------------------------------------------------------------------------

def test_c9_metas_lucro_margem_roi_e_inviavel(client):
    pid = _criar_imovel_com_leilao(client)
    _add_custo(client, pid, "ITBI", "10000")
    _add_custo(client, pid, "REGISTRO", "20000")
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "200000", "appraisal_value": "300000", "commission_percent": "5"})

    for kind, value in (("LUCRO_MINIMO", 40000), ("MARGEM_MINIMA", 0.2), ("ROI_MINIMO", 0.25)):
        fin = _set_premissas(client, pid, goal_kind=kind, goal_value=value)["financeiro"]
        assert fin["preco_maximo"] is not None, f"{kind} deveria calcular"
        assert fin["preco_maximo_definitivo"] is True

    # Meta inviável: lucro maior do que o valor de venda permite → sem preço máximo.
    fin = _set_premissas(client, pid, goal_kind="LUCRO_MINIMO", goal_value=1000000)["financeiro"]
    assert fin["preco_maximo"] is None
    assert fin["preco_maximo_detalhe"]["razao"] == "META_INATINGIVEL"


# --------------------------------------------------------------------------
# Cenário 10 — erros de validação apresentados corretamente
# --------------------------------------------------------------------------

def test_c10_validacao_percentual_invalido_422(client):
    pid = _criar_imovel_com_leilao(client)
    resp = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={"corretagem_pct": 1.5})
    assert resp.status_code == 422  # fora do intervalo 0..1


def test_c10_validacao_meta_incompleta_422(client):
    pid = _criar_imovel_com_leilao(client)
    resp = client.put(f"/api/imoveis/{pid}/financeiro/premissas", json={"goal_kind": "LUCRO_MINIMO"})
    assert resp.status_code == 422  # goal_kind sem goal_value


def test_c10_imovel_inexistente_404(client):
    resp = client.get("/api/imoveis/999999/financeiro/premissas")
    assert resp.status_code == 404
