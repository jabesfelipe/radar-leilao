"""Módulo Pós-Arrematação — testes de CRUD, histórico/evento, consolidação
financeira e persistência (critérios de aceite 1-11).

Reutiliza a fixture `client` (TestClient + savepoint/rollback; não toca dados reais)
e valida que: o fluxo é ativado sob demanda; custos previsto/pago/pendente não
duplicam; contatos/tentativas; minuta com versões; consultoria/proposta; a visão
financeira consolidada NÃO sobrescreve o financeiro histórico da análise; e todos
os eventos entram na linha do tempo /historico existente.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app
from backend.app.services import post_auction_cost_summary, POST_AUCTION_DEFAULT_STAGES

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

REQUIRED_TABLES = {"properties", "post_auctions", "post_auction_stages", "post_auction_costs",
                   "occupant_contacts", "contact_attempts", "consultancies", "consultancy_proposals",
                   "notification_drafts", "notification_draft_versions", "entity_history", "domain_events"}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations do pós-arrematação ainda não aplicadas")
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
    resp = client.post("/api/imoveis", json={"title": "Imóvel Pós", "address": "R", "city": "SP", "state": "SP", "property_type": "Apto", "area_m2": 60})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _activate(client, pid, **payload):
    resp = client.post(f"/api/imoveis/{pid}/pos-arrematacao/ativar", json=payload or {"seed_default_stages": True})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---- Aceite 1: ativação sob demanda -----------------------------------------
def test_imovel_so_analisado_nao_tem_pos_arrematacao(client):
    pid = _new_property(client)
    overview = client.get(f"/api/imoveis/{pid}/pos-arrematacao").json()
    assert overview["ativado"] is False
    assert overview["pos_arrematacao"] is None
    # financeiro da análise segue disponível (não depende do módulo).
    assert "financeiro_analise" in overview


def test_ativacao_cria_estado_e_etapas_padrao(client):
    pid = _new_property(client)
    out = _activate(client, pid)
    assert out["ativado"] is True
    overview = client.get(f"/api/imoveis/{pid}/pos-arrematacao").json()
    assert overview["ativado"] is True
    # Todas as 16 etapas padrão foram semeadas.
    assert len(overview["etapas"]) == len(POST_AUCTION_DEFAULT_STAGES)
    # Ativação é idempotente (não duplica).
    again = client.post(f"/api/imoveis/{pid}/pos-arrematacao/ativar", json={})
    assert again.json().get("ja_ativo") is True


# ---- Aceite 2 + 9: custos previsto/pago/pendente sem duplicidade e consolidação
def test_custos_previsto_pago_pendente_consolidacao(client):
    pid = _new_property(client)
    _activate(client, pid)
    # Previsto 1000 pendente
    c1 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/custos", json={"category": "ITBI", "planned_amount": "1000", "status": "PENDENTE"})
    assert c1.status_code == 201, c1.text
    # Previsto 2000, pago 1800
    c2 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/custos", json={"category": "REFORMA", "planned_amount": "2000", "actual_amount": "1800", "status": "PAGO"})
    assert c2.status_code == 201, c2.text
    resumo = c2.json()["resumo_financeiro"]
    # previsto_total = 1000 + 2000 = 3000; realizado = 1800; pendente = 1000 (c1).
    assert Decimal(str(resumo["previsto_total"])) == Decimal("3000")
    assert Decimal(str(resumo["realizado_total"])) == Decimal("1800")
    assert Decimal(str(resumo["pendente_total"])) == Decimal("1000")


def test_custo_cancelado_nao_entra_no_previsto(client):
    pid = _new_property(client)
    _activate(client, pid)
    client.post(f"/api/imoveis/{pid}/pos-arrematacao/custos", json={"category": "X", "planned_amount": "500", "status": "PREVISTO"})
    c = client.post(f"/api/imoveis/{pid}/pos-arrematacao/custos", json={"category": "Y", "planned_amount": "900", "status": "CANCELADO"})
    resumo = c.json()["resumo_financeiro"]
    assert Decimal(str(resumo["previsto_total"])) == Decimal("500")  # cancelado fora


def test_custo_pos_nao_sobrescreve_financeiro_da_analise(client):
    pid = _new_property(client)
    # custo da análise inicial
    client.post(f"/api/imoveis/{pid}/custos", json={"category": "ITBI", "amount": "8000"})
    fin_antes = client.get(f"/api/imoveis/{pid}/financeiro").json()["financeiro"]["custo_total"]
    _activate(client, pid)
    client.post(f"/api/imoveis/{pid}/pos-arrematacao/custos", json={"category": "REFORMA", "planned_amount": "5000", "actual_amount": "5000", "status": "PAGO"})
    fin_depois = client.get(f"/api/imoveis/{pid}/financeiro").json()["financeiro"]["custo_total"]
    # O financeiro da análise inicial NÃO muda com custos pós-arrematação.
    assert Decimal(str(fin_antes)) == Decimal(str(fin_depois))


# ---- Aceite 3: contatos + histórico de tentativas ---------------------------
def test_contato_e_tentativas(client):
    pid = _new_property(client)
    _activate(client, pid)
    ct = client.post(f"/api/imoveis/{pid}/pos-arrematacao/contatos", json={"name": "Fulano", "phone": "11999"})
    assert ct.status_code == 201, ct.text
    cid = ct.json()["id"]
    r1 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/contatos/{cid}/tentativas", json={"channel": "TELEFONE", "result": "Sem resposta"})
    assert r1.status_code == 201, r1.text
    r2 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/contatos/{cid}/tentativas", json={"channel": "WHATSAPP", "result": "Respondeu"})
    assert len(r2.json()["tentativas"]) == 2  # histórico preservado


# ---- Aceite 4: minuta de notificação com versões ----------------------------
def test_minuta_com_versoes_editaveis(client):
    pid = _new_property(client)
    _activate(client, pid)
    d = client.post(f"/api/imoveis/{pid}/pos-arrematacao/notificacoes", json={"title": "Notificação", "body": "Texto v1"})
    assert d.status_code == 201, d.text
    did = d.json()["id"]
    assert d.json()["current_version"] == 1
    v2 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/notificacoes/{did}/versoes", json={"body": "Texto v2 revisado", "status": "REVISADO"})
    assert v2.status_code == 201, v2.text
    assert v2.json()["current_version"] == 2
    assert v2.json()["status"] == "REVISADO"
    # Histórico de versões preservado (v1 e v2).
    full = client.get(f"/api/imoveis/{pid}/pos-arrematacao/notificacoes/{did}").json()
    versoes = {v["version"]: v["body"] for v in full["versoes"]}
    assert versoes[1] == "Texto v1"
    assert versoes[2] == "Texto v2 revisado"


# ---- Aceite 5/6: modalidade + consultoria/proposta --------------------------
def test_modalidade_e_consultoria_com_proposta(client):
    pid = _new_property(client)
    _activate(client, pid, eviction_mode="TERCEIRIZADA", seed_default_stages=False)
    pa = client.patch(f"/api/imoveis/{pid}/pos-arrematacao", json={"eviction_mode": "TERCEIRIZADA"})
    assert pa.status_code == 200, pa.text
    co = client.post(f"/api/imoveis/{pid}/pos-arrematacao/consultorias", json={"company_name": "Desocupa LTDA", "cnpj": "00.000.000/0001-00"})
    assert co.status_code == 201, co.text
    coid = co.json()["id"]
    p1 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/consultorias/{coid}/propostas", json={"title": "Proposta A", "fixed_fee": "3000"})
    p2 = client.post(f"/api/imoveis/{pid}/pos-arrematacao/consultorias/{coid}/propostas", json={"title": "Proposta B", "fixed_fee": "2500"})
    assert p2.status_code == 201, p2.text
    assert len(p2.json()["propostas"]) == 2  # permite comparar


# ---- Aceite 7: etapa de ação judicial reusa LegalProcess --------------------
def test_etapa_vincula_processo_juridico_existente(client):
    pid = _new_property(client)
    _activate(client, pid, seed_default_stages=False)
    proc = client.post(f"/api/imoveis/{pid}/processos", json={"number": "0001234-56.2026.8.26.0100"})
    assert proc.status_code == 200, proc.text
    proc_id = proc.json()["id"]
    stage = client.post(f"/api/imoveis/{pid}/pos-arrematacao/etapas", json={"stage_key": "ACAO_JUDICIAL_IMISSAO", "title": "Imissão", "legal_process_id": proc_id})
    assert stage.status_code == 201, stage.text
    assert stage.json()["legal_process_id"] == proc_id  # reuso, sem duplicar cadastro processual


# ---- Aceite 8 + 10: eventos entram na linha do tempo existente --------------
def test_eventos_pos_entram_na_linha_do_tempo(client):
    pid = _new_property(client)
    _activate(client, pid)
    client.post(f"/api/imoveis/{pid}/pos-arrematacao/custos", json={"category": "ITBI", "planned_amount": "1000"})
    historico = client.get(f"/api/imoveis/{pid}/historico").json()
    tipos = {e["event_type"] for e in historico["eventos"]}
    assert "POS_ARREMATACAO_ATIVADA" in tipos
    assert "POS_CUSTO_ADICIONADO" in tipos
    # EntityHistory registrado para o custo pós-arrematação.
    assert any(h["entity_type"] == "PostAuctionCost" for h in historico["alteracoes"])


# ---- Aceite 11: persistência do estado consolidado --------------------------
def test_edicao_etapa_gera_historico_before_after(client):
    pid = _new_property(client)
    _activate(client, pid)
    overview = client.get(f"/api/imoveis/{pid}/pos-arrematacao").json()
    stage_id = overview["etapas"][0]["id"]
    upd = client.patch(f"/api/imoveis/{pid}/pos-arrematacao/etapas/{stage_id}", json={"status": "CONCLUIDA", "responsible": "Investidor"})
    assert upd.status_code == 200, upd.text
    historico = client.get(f"/api/imoveis/{pid}/historico").json()
    alt = [h for h in historico["alteracoes"] if h["entity_type"] == "PostAuctionStage" and h["action"] == "UPDATE"]
    assert alt, "faltou EntityHistory UPDATE da etapa"
    assert alt[-1]["before_data"]["status"] == "PENDENTE"
    assert alt[-1]["after_data"]["status"] == "CONCLUIDA"
