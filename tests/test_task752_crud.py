"""TASK 75.2 — CRUD padronizado, edição e histórico.

Cobre o ciclo CREATE → GET → UPDATE → GET → HISTORY (e DELETE onde permitido) para
dados cadastrais/factuais, validando: valor anterior preservado no histórico
(before_data), valor novo persistido (after_data), DomainEvent criado, financeiro
recalculado, análises imutáveis e NENHUM segredo em histórico/evento.

Usa a mesma fixture `client` do test_task75 (TestClient + savepoint/rollback; não
toca dados reais) e testes unitários puros do motor financeiro (comissão canônica).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app
from backend.app.finance import calculate_financial, canonical_cost_key

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

REQUIRED_TABLES = {"properties", "costs", "debts", "market_comparables", "entity_history", "domain_events"}
_TEST_PORTAL_KEY = "chave-de-teste-portal-75-2"
_TEST_ADMIN_TOKEN = "token-admin-teste-75-2"


# ---------------------------------------------------------------- motor: comissão canônica
def test_comissao_via_custo_cadastrado_e_reconhecida():
    """GAP crítico: 'Comissão do arrematante' cadastrada como custo é reconhecida
    como comissão de arrematação (não fica DESCONHECIDA nem cai em 'outros')."""
    r = calculate_financial(
        bid=Decimal("100000"),
        costs=[{"category": "Comissão do arrematante", "amount": Decimal("11100")}],
    )
    assert canonical_cost_key("Comissão do arrematante") == "comissao"
    assert r["custos"]["comissao"] == Decimal("11100")
    assert r["custos"]["outros"] == Decimal("0")  # NÃO caiu em outros
    assert r["comissao_detalhe"]["informada"] is True
    assert r["comissao_detalhe"]["origem"] == "CUSTO_CADASTRADO"
    assert r["comissao_detalhe"]["status"] == "INFORMADO"


def test_comissao_auction_tem_precedencia_sem_dupla_contagem():
    """Comissão parametrizada no Auction tem precedência; um custo de comissão NÃO
    é somado de novo (sem dupla contagem)."""
    r = calculate_financial(
        bid=Decimal("100000"),
        commission_fixed=Decimal("5000"),
        costs=[{"category": "Comissão do arrematante", "amount": Decimal("11100")}],
    )
    assert r["custos"]["comissao"] == Decimal("5000")  # Auction governa
    assert r["comissao_detalhe"]["origem"] == "AUCTION_FIXO"
    # O custo de comissão não entra em outros nem duplica a comissão.
    assert r["custos"]["outros"] == Decimal("0")


def test_comissao_desconhecida_sem_auction_e_sem_custo():
    r = calculate_financial(bid=Decimal("100000"))
    assert r["comissao_detalhe"]["informada"] is False
    assert r["comissao_detalhe"]["status"] == "DESCONHECIDO"


# ---------------------------------------------------------------- fixture HTTP
@pytest.fixture
def client(postgres_engine, monkeypatch):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations necessárias ainda não aplicadas")
    monkeypatch.setattr(settings, "portal_secret_key", _TEST_PORTAL_KEY, raising=False)
    monkeypatch.setattr(settings, "portal_admin_token", _TEST_ADMIN_TOKEN, raising=False)
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
        session.close()
        transaction.rollback()
        connection.close()


def _new_property(client) -> int:
    resp = client.post("/api/imoveis", json={"title": "Imóvel 75.2", "address": "R", "city": "SP", "state": "SP", "property_type": "Apto", "area_m2": 60})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------- CUSTOS
def test_custo_ciclo_crud_e_historico(client):
    pid = _new_property(client)
    # CREATE
    cost = client.post(f"/api/imoveis/{pid}/custos", json={"category": "REFORMA", "description": "Obra", "amount": "1000"}).json()
    cid = cost["id"]
    # UPDATE
    upd = client.patch(f"/api/imoveis/{pid}/custos/{cid}", json={"amount": "1500", "description": "Obra ampliada"})
    assert upd.status_code == 200, upd.text
    assert "financeiro" in upd.json()  # financeiro recalculado
    # GET reflete novo valor
    custos = client.get(f"/api/imoveis/{pid}/custos").json()["custos"]
    alvo = next(c for c in custos if c["id"] == cid)
    assert Decimal(str(alvo["amount"])) == Decimal("1500")
    # HISTORY: before preservado, after novo
    hist = client.get(f"/api/imoveis/{pid}/custos").json()["historico"]
    upd_hist = [h for h in hist if h["action"] == "UPDATE" and h["entity_id"] == cid]
    assert upd_hist, "faltou EntityHistory UPDATE"
    assert Decimal(str(upd_hist[-1]["before_data"]["amount"])) == Decimal("1000")
    assert Decimal(str(upd_hist[-1]["after_data"]["amount"])) == Decimal("1500")
    # DELETE preserva histórico
    dele = client.delete(f"/api/imoveis/{pid}/custos/{cid}")
    assert dele.status_code == 200, dele.text
    restante = client.get(f"/api/imoveis/{pid}/custos").json()
    assert all(c["id"] != cid for c in restante["custos"])
    assert any(h["action"] == "DELETE" and h["entity_id"] == cid for h in restante["historico"])


def test_custo_recalcula_financeiro_na_edicao(client):
    pid = _new_property(client)
    cost = client.post(f"/api/imoveis/{pid}/custos", json={"category": "ITBI", "description": "i", "amount": "3000"}).json()
    r = client.patch(f"/api/imoveis/{pid}/custos/{cost['id']}", json={"amount": "4000"}).json()
    assert Decimal(str(r["financeiro"]["custos"]["itbi"])) == Decimal("4000")


# ---------------------------------------------------------------- DÍVIDAS
def test_divida_ciclo_crud_e_historico(client):
    pid = _new_property(client)
    debt = client.post(f"/api/imoveis/{pid}/dividas", json={"category": "IPTU", "creditor": "Município", "amount": "500"}).json()
    did = debt["id"]
    upd = client.patch(f"/api/imoveis/{pid}/dividas/{did}", json={"amount": "800", "status": "PENDENTE"})
    assert upd.status_code == 200, upd.text
    hist = client.get(f"/api/imoveis/{pid}/dividas").json()["historico"]
    upd_hist = [h for h in hist if h["action"] == "UPDATE" and h["entity_id"] == did]
    assert Decimal(str(upd_hist[-1]["before_data"]["amount"])) == Decimal("500")
    assert Decimal(str(upd_hist[-1]["after_data"]["amount"])) == Decimal("800")
    dele = client.delete(f"/api/imoveis/{pid}/dividas/{did}")
    assert dele.status_code == 200
    restante = client.get(f"/api/imoveis/{pid}/dividas").json()
    assert all(d["id"] != did for d in restante["dividas"])
    assert any(h["action"] == "DELETE" and h["entity_id"] == did for h in restante["historico"])


# ---------------------------------------------------------------- MERCADO (comparáveis)
def test_comparavel_ciclo_crud_historico_e_mercado(client):
    pid = _new_property(client)
    comp = client.post(f"/api/imoveis/{pid}/comparaveis", json={"kind": "VENDA", "price": "200000", "area_m2": "60"}).json()
    cid = comp["id"]
    # CREATE agora grava histórico (antes não gravava).
    lst = client.get(f"/api/imoveis/{pid}/comparaveis").json()
    assert any(h["action"] == "CREATE" and h["entity_id"] == cid for h in lst["historico"])
    upd = client.patch(f"/api/imoveis/{pid}/comparaveis/{cid}", json={"price": "250000"})
    assert upd.status_code == 200, upd.text
    assert "mercado" in upd.json()  # mercado recalculado
    hist = client.get(f"/api/imoveis/{pid}/comparaveis").json()["historico"]
    upd_hist = [h for h in hist if h["action"] == "UPDATE" and h["entity_id"] == cid]
    assert Decimal(str(upd_hist[-1]["before_data"]["price"])) == Decimal("200000")
    assert Decimal(str(upd_hist[-1]["after_data"]["price"])) == Decimal("250000")
    dele = client.delete(f"/api/imoveis/{pid}/comparaveis/{cid}")
    assert dele.status_code == 200


# ---------------------------------------------------------------- MATRÍCULA / EDITAL
def test_matricula_edicao_metadados_com_historico(client):
    pid = _new_property(client)
    reg = client.post(f"/api/imoveis/{pid}/matricula", json={"registration_number": "123", "holder": "Fulano"}).json()
    rid = reg["id"]
    upd = client.patch(f"/api/imoveis/{pid}/matricula/{rid}", json={"holder": "Beltrano", "observations": "retificado"})
    assert upd.status_code == 200, upd.text
    alt = client.get(f"/api/imoveis/{pid}/matricula").json()["alteracoes"]
    upd_hist = [h for h in alt if h["action"] == "UPDATE" and h["entity_id"] == rid]
    assert upd_hist[-1]["before_data"]["holder"] == "Fulano"
    assert upd_hist[-1]["after_data"]["holder"] == "Beltrano"


def test_edital_edicao_metadados_com_historico(client):
    pid = _new_property(client)
    notice = client.post(f"/api/imoveis/{pid}/edital", json={"identifier": "Edital 1", "auction_stage": "1º leilão"}).json()
    nid = notice["id"]
    upd = client.patch(f"/api/imoveis/{pid}/edital/{nid}", json={"auction_stage": "2º leilão", "minimum_value": "180000"})
    assert upd.status_code == 200, upd.text
    alt = client.get(f"/api/imoveis/{pid}/edital").json()["alteracoes"]
    upd_hist = [h for h in alt if h["action"] == "UPDATE" and h["entity_id"] == nid]
    assert upd_hist[-1]["before_data"]["auction_stage"] == "1º leilão"
    assert upd_hist[-1]["after_data"]["auction_stage"] == "2º leilão"


# ---------------------------------------------------------------- JURÍDICO
def test_processo_edicao_e_movimentacao_append_only(client):
    pid = _new_property(client)
    proc = client.post(f"/api/imoveis/{pid}/processos", json={"number": "0001", "status": "ATIVO"}).json()
    prid = proc["id"]
    upd = client.patch(f"/api/imoveis/{pid}/processos/{prid}", json={"status": "SUSPENSO", "subject": "Usucapião"})
    assert upd.status_code == 200, upd.text
    hist = client.get(f"/api/imoveis/{pid}/processos").json()["historico"]
    upd_hist = [h for h in hist if h["action"] == "UPDATE" and h["entity_id"] == prid]
    assert upd_hist[-1]["before_data"]["status"] == "ATIVO"
    assert upd_hist[-1]["after_data"]["status"] == "SUSPENSO"
    # Movimentação é append-only (novo registro).
    mov = client.post(f"/api/imoveis/{pid}/processos/{prid}/movimentacoes", json={"description": "Audiência designada"})
    assert mov.status_code == 200, mov.text
    assert mov.json()["movimentacao"]["description"] == "Audiência designada"


# ---------------------------------------------------------------- IMÓVEL / LEILÃO
def test_imovel_edicao_cadastral_sem_nova_analise(client):
    pid = _new_property(client)
    antes = client.get("/api/imoveis/" + str(pid)).json()
    n_analises_antes = len(antes["analises"])
    upd = client.patch(f"/api/imoveis/{pid}", json={"title": "Imóvel 75.2 (editado)", "status": "EM_ANALISE"})
    assert upd.status_code == 200, upd.text
    depois = client.get("/api/imoveis/" + str(pid)).json()
    assert depois["imovel"]["title"] == "Imóvel 75.2 (editado)"
    # Edição cadastral NÃO cria nova análise.
    assert len(depois["analises"]) == n_analises_antes
    # Histórico de alteração do imóvel registrado em entity_history.
    hist = client.get(f"/api/imoveis/{pid}/historico").json()["alteracoes"]
    assert any(h["entity_type"] == "Property" and h["action"] == "UPDATE" for h in hist)


def test_leilao_edicao_recalcula_financeiro(client):
    pid = _new_property(client)
    client.post(f"/api/imoveis/{pid}/leilao", json={"bid_value": "100000", "appraisal_value": "150000"})
    detalhe = client.get("/api/imoveis/" + str(pid)).json()
    aid = detalhe["leilao"]["id"]
    upd = client.patch(f"/api/imoveis/{pid}/leilao/{aid}", json={"commission_fixed": "5000"})
    assert upd.status_code == 200, upd.text
    assert Decimal(str(upd.json()["financeiro"]["custos"]["comissao"])) == Decimal("5000")


# ---------------------------------------------------------------- LEILOEIROS / PORTAIS (sem segredo no histórico)
def test_leiloeiro_portal_historico_nunca_vaza_segredo(client):
    aid = client.post("/api/leiloeiros", json={"name": "Leiloeiro 75.2"}).json()["id"]
    # Portal com credencial.
    portal = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "Caixa", "username": "u@x", "secret": "SENHA-SECRETA-752"}).json()
    pid_portal = portal["id"]
    # Edita (troca a credencial).
    upd = client.patch(f"/api/leiloeiros/{aid}/portais/{pid_portal}", json={"username": "novo@x", "secret": "OUTRA-SENHA-752"})
    assert upd.status_code == 200, upd.text
    assert "secret" not in upd.json()
    # Histórico do leiloeiro: NUNCA contém o valor da senha, só has_secret.
    hist = client.get(f"/api/leiloeiros/{aid}/historico").json()
    blob = str(hist)
    assert "SENHA-SECRETA-752" not in blob
    assert "OUTRA-SENHA-752" not in blob
    assert "has_secret" in blob
    # A credencial corrente continua recuperável só via endpoint protegido.
    reveal = client.get(f"/api/leiloeiros/{aid}/portais/{pid_portal}/credencial", headers={"X-Portal-Admin-Token": _TEST_ADMIN_TOKEN})
    assert reveal.json()["secret"] == "OUTRA-SENHA-752"


def test_leiloeiro_e_portal_delete(client):
    aid = client.post("/api/leiloeiros", json={"name": "Para Excluir"}).json()["id"]
    portal = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P"}).json()
    dele_portal = client.delete(f"/api/leiloeiros/{aid}/portais/{portal['id']}")
    assert dele_portal.status_code == 200
    dele_auc = client.delete(f"/api/leiloeiros/{aid}")
    assert dele_auc.status_code == 200
    assert client.get(f"/api/leiloeiros/{aid}").status_code == 404


# ---------------------------------------------------------------- TASK 75.2.1 — fechamento final
def test_documento_leiloeiro_patch_e_delete_com_historico(client):
    aid = client.post("/api/leiloeiros", json={"name": "Com Doc"}).json()["id"]
    doc = client.post(f"/api/leiloeiros/{aid}/documentos", json={"doc_type": "CONTRATO", "name": "Credenciamento", "file_path": "/x/doc.pdf", "version": 2}).json()
    did = doc["id"]
    # PATCH edita só metadados; NÃO sobrescreve conteúdo/versionamento (file_path/version).
    upd = client.patch(f"/api/leiloeiros/{aid}/documentos/{did}", json={"name": "Credenciamento v2", "observations": "revisado"})
    assert upd.status_code == 200, upd.text
    body = upd.json()
    assert body["name"] == "Credenciamento v2"
    assert body["file_path"] == "/x/doc.pdf" and body["version"] == 2  # preservados
    # Histórico before/after presente no histórico do leiloeiro.
    hist = client.get(f"/api/leiloeiros/{aid}/historico").json()["alteracoes"]
    upd_hist = [h for h in hist if h["entity_type"] == "AuctioneerDocument" and h["action"] == "UPDATE" and h["entity_id"] == did]
    assert upd_hist, "faltou EntityHistory UPDATE do documento"
    assert upd_hist[-1]["before_data"]["name"] == "Credenciamento"
    assert upd_hist[-1]["after_data"]["name"] == "Credenciamento v2"
    # DELETE preserva histórico.
    dele = client.delete(f"/api/leiloeiros/{aid}/documentos/{did}")
    assert dele.status_code == 200
    hist2 = client.get(f"/api/leiloeiros/{aid}/historico").json()["alteracoes"]
    assert any(h["entity_type"] == "AuctioneerDocument" and h["action"] == "DELETE" and h["entity_id"] == did for h in hist2)


def test_fonte_ciclo_crud_e_historico(client):
    pid = _new_property(client)
    src = client.post(f"/api/imoveis/{pid}/fontes", json={"source_type": "EDITAL", "url": "http://x", "description": "orig"}).json()
    sid = src["id"]
    created_at = src["created_at"]
    # PATCH
    upd = client.patch(f"/api/imoveis/{pid}/fontes/{sid}", json={"description": "retificado", "origin": "Caixa"})
    assert upd.status_code == 200, upd.text
    assert upd.json()["description"] == "retificado"
    assert upd.json()["created_at"] == created_at  # created_at preservado
    assert upd.json()["id"] == sid  # mesmo id
    # HISTORY before/after
    alt = client.get(f"/api/imoveis/{pid}/fontes/historico").json()["alteracoes"]
    upd_hist = [h for h in alt if h["action"] == "UPDATE" and h["entity_id"] == sid]
    assert upd_hist[-1]["before_data"]["description"] == "orig"
    assert upd_hist[-1]["after_data"]["description"] == "retificado"
    # DELETE preserva histórico
    dele = client.delete(f"/api/imoveis/{pid}/fontes/{sid}")
    assert dele.status_code == 200
    restante = client.get(f"/api/imoveis/{pid}/fontes").json()
    assert all(s["id"] != sid for s in restante)
    alt2 = client.get(f"/api/imoveis/{pid}/fontes/historico").json()["alteracoes"]
    assert any(h["action"] == "DELETE" and h["entity_id"] == sid for h in alt2)


def test_portal_delete_evento_sem_segredo(client):
    """DELETE de portal gera evento/histórico, e o segredo nunca aparece neles."""
    aid = client.post("/api/leiloeiros", json={"name": "Del Portal"}).json()["id"]
    portal = client.post(f"/api/leiloeiros/{aid}/portais", json={"portal": "P", "secret": "SENHA-DELETE-7521"}).json()
    client.delete(f"/api/leiloeiros/{aid}/portais/{portal['id']}")
    blob = str(client.get(f"/api/leiloeiros/{aid}/historico").json())
    assert "SENHA-DELETE-7521" not in blob
    assert "has_secret" in blob


def test_crud_cadastral_nao_cria_analise(client):
    """Nenhum dos CRUDs cadastrais (fonte/leilão/custo) cria nova análise."""
    pid = _new_property(client)
    antes = len(client.get(f"/api/imoveis/{pid}").json()["analises"])
    src = client.post(f"/api/imoveis/{pid}/fontes", json={"source_type": "OUTRA", "url": "http://y"}).json()
    client.patch(f"/api/imoveis/{pid}/fontes/{src['id']}", json={"description": "d"})
    client.delete(f"/api/imoveis/{pid}/fontes/{src['id']}")
    depois = len(client.get(f"/api/imoveis/{pid}").json()["analises"])
    assert depois == antes
