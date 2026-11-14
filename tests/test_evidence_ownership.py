"""Evidência citada em cadastro tem de ser do MESMO imóvel (v1.0.4).

Regressão da sonda de isolamento da homologação: POST de dívida e de processo no imóvel A aceitava (HTTP 200)
``evidence_id`` de uma evidência do imóvel B, ligando o cadastro de A ao trecho do documento de B.
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


@pytest.fixture
def ambiente(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient (httpx) indisponível")
    if "evidences" not in set(inspect(postgres_engine).get_table_names()):
        pytest.skip("Migrations do Radar ainda não aplicadas no banco de testes")
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        a = models.Property(title="Imóvel A", address="Rua A", city="São Paulo", state="SP")
        b = models.Property(title="Imóvel B", address="Rua B", city="São Paulo", state="SP")
        session.add_all([a, b])
        session.flush()
        ev_a = models.Evidence(property_id=a.id, fact="Evidência do A")
        ev_b = models.Evidence(property_id=b.id, fact="Evidência do B")
        session.add_all([ev_a, ev_b])
        session.flush()
        yield TestClient(app), {"a": a.id, "ev_a": ev_a.id, "ev_b": ev_b.id}
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


CADASTROS = [
    ("dividas", {"category": "IPTU", "amount": 100}),
    ("processos", {"number": "0000001-00.2026.8.26.0000"}),
    ("matricula", {"registration_number": "000.001"}),
    ("edital", {"identifier": "ED-1/2026"}),
    ("ocupacao", {"status": "DESCONHECIDO"}),
]


@pytest.mark.parametrize("rota,corpo", CADASTROS, ids=[c[0] for c in CADASTROS])
def test_cadastro_recusa_evidencia_de_outro_imovel(ambiente, rota, corpo):
    client, ids = ambiente
    resposta = client.post(f"/api/imoveis/{ids['a']}/{rota}", json=corpo | {"evidence_id": ids["ev_b"]})
    assert resposta.status_code == 422, resposta.text


@pytest.mark.parametrize("rota,corpo", CADASTROS, ids=[c[0] for c in CADASTROS])
def test_cadastro_aceita_evidencia_do_proprio_imovel_e_sem_evidencia(ambiente, rota, corpo):
    client, ids = ambiente
    assert client.post(f"/api/imoveis/{ids['a']}/{rota}", json=corpo | {"evidence_id": ids["ev_a"]}).status_code == 200
    assert client.post(f"/api/imoveis/{ids['a']}/{rota}", json=corpo).status_code == 200


def test_cadastro_recusa_evidencia_inexistente(ambiente):
    client, ids = ambiente
    assert client.post(f"/api/imoveis/{ids['a']}/dividas", json={"category": "IPTU", "evidence_id": 999999999}).status_code == 422


def test_edicao_de_divida_recusa_evidencia_de_outro_imovel(ambiente):
    client, ids = ambiente
    criada = client.post(f"/api/imoveis/{ids['a']}/dividas", json={"category": "IPTU", "amount": 100}).json()
    resposta = client.patch(f"/api/imoveis/{ids['a']}/dividas/{criada['id']}", json={"evidence_id": ids["ev_b"]})
    assert resposta.status_code == 422, resposta.text
    assert client.patch(f"/api/imoveis/{ids['a']}/dividas/{criada['id']}", json={"evidence_id": ids["ev_a"]}).status_code == 200
