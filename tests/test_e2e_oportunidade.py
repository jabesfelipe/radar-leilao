"""Teste de integração ponta-a-ponta (sintético) do ciclo operacional (Fase 8).

Exercita, via API, o fluxo: criar oportunidade -> classificar modalidade com
evidência -> concluir gate -> avançar fase -> hard stop bloqueia sem gate ->
histórico append-only -> dashboard reflete -> monitoramento RAG responde.

Dados sintéticos isolados — NUNCA o imóvel 633. Sem chamadas externas (sem chave de
LLM; embeddings ficam pendentes, o que é o comportamento esperado).
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
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-e2e-teste", raising=False)
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


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_fluxo_ponta_a_ponta_sintetico(client):
    s = _session()
    # Usuário ANALISTA (analysis:write) + imóvel + evidência sintéticos.
    s.add(models.User(email="e2e@teste.com", name="E2E", password_hash=auth.hash_password("senha-forte-123"), role="ANALISTA", active=True))
    prop = models.Property(title="Imovel E2E", address="Rua E2E", city="Londrina", state="PR", area_m2=80, bedrooms=3)
    s.add(prop); s.flush()
    ev = models.Evidence(property_id=prop.id, category="DOCUMENTAL", fact="alienação fiduciária Lei 9.514", source_excerpt="edital")
    s.add(ev); s.flush()
    tok = client.post("/api/auth/login", json={"email": "e2e@teste.com", "password": "senha-forte-123"}).json()["access_token"]

    # 1) Criar oportunidade (INDEFINIDO por padrão).
    oid = client.post("/api/oportunidades", json={"property_id": prop.id}, headers=_h(tok)).json()["oportunidade"]["id"]

    # 2) Classificar modalidade COM evidência -> confirmada (determinística).
    cls = client.post(f"/api/oportunidades/{oid}/modalidade/classificar",
                      json={"signals_text": "alienação fiduciária Lei 9.514", "evidence_id": ev.id, "confirm": True}, headers=_h(tok))
    assert cls.status_code == 200 and cls.json()["modality"] == "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"

    # 3) Concluir gate de F0 e avançar F0 -> F1.
    assert client.post(f"/api/oportunidades/{oid}/fase/estado", json={"state": "CONCLUIDA"}, headers=_h(tok)).status_code == 200
    adv = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F1_TRIAGEM"}, headers=_h(tok))
    assert adv.status_code == 200 and adv.json()["decision"]["allowed"] is True
    assert adv.json()["workflow"]["current_phase"] == "F1_TRIAGEM"

    # 4) Tentar avançar F1 -> F2 SEM concluir o gate de F1 -> bloqueado (determinístico).
    blocked = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F2_DOCUMENTOS"}, headers=_h(tok))
    assert blocked.status_code == 200 and blocked.json()["decision"]["allowed"] is False

    # 5) Histórico append-only: 2 transições registradas (permitida + bloqueada).
    hist = client.get(f"/api/oportunidades/{oid}/historico", headers=_h(tok)).json()
    assert len(hist["historico"]) == 2

    # 6) Dashboard reflete a oportunidade real.
    dash = client.get("/api/dashboard/oportunidades", headers=_h(tok)).json()
    assert dash["total_oportunidades"] >= 1
    assert dash["por_modalidade"].get("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", 0) >= 1
    assert dash["por_municipio"].get("Londrina", 0) >= 1

    # 7) Monitoramento RAG responde (sem provider, cobertura é número real).
    rag = client.get("/api/monitoring/rag", headers=_h(tok)).json()
    assert "embeddings" in rag and "cobertura_pct" in rag["embeddings"]


def test_transicao_proibida_fora_da_matriz_e_bloqueada(client):
    s = _session()
    s.add(models.User(email="e2e2@teste.com", name="E2E2", password_hash=auth.hash_password("senha-forte-123"), role="ANALISTA", active=True))
    prop = models.Property(title="Imovel E2E2", address="Rua E2E2", city="Curitiba", state="PR", area_m2=60, bedrooms=2)
    s.add(prop); s.flush()
    tok = client.post("/api/auth/login", json={"email": "e2e2@teste.com", "password": "senha-forte-123"}).json()["access_token"]
    oid = client.post("/api/oportunidades", json={"property_id": prop.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    # F0 -> F9 é inválido (fora da matriz de avanço): bloqueado.
    out = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F9_LANCE_PAGAMENTO"}, headers=_h(tok))
    assert out.status_code == 200 and out.json()["decision"]["allowed"] is False
