"""Testes da API operacional de workflow/oportunidade (Onda 2).

Cobre: criação, estado, transições válidas/inválidas, hard stops (modalidade
indefinida), isolamento, histórico append-only e autorização. Usa dados sintéticos
isolados — NUNCA o imóvel 633. JWT via JWT_SECRET_KEY de teste.
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
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-wf-teste", raising=False)
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
    email = email or f"{role.lower()}@wf.com"
    u = models.User(email=email, name=role, password_hash=auth.hash_password("senha-forte-123"), role=role, active=True)
    session.add(u); session.flush(); return u


def _prop(session, titulo="Imóvel WF"):
    p = models.Property(title=titulo, address="Rua WF", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    session.add(p); session.flush(); return p


def _login(client, email, password="senha-forte-123"):
    return client.post("/api/auth/login", json={"email": email, "password": password}).json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _concluir(client, oid, tok, phase=None):
    """Conclui o gate de saída de uma fase (habilita o AVANÇO). Espelha a operação
    real: o operador marca a fase como CONCLUIDA antes de avançar."""
    body = {"state": "CONCLUIDA"}
    if phase:
        body["phase"] = phase
    return client.post(f"/api/oportunidades/{oid}/fase/estado", json=body, headers=_h(tok))


# --------------------------------------------------------------------------
# Autorização
# --------------------------------------------------------------------------

def test_criar_oportunidade_sem_token_401(client):
    # Escrita operacional exige usuário autenticado real (ator da auditoria) além da
    # permissão analysis:write. Sem Bearer => 401, nunca 2xx.
    s = _session(); p = _prop(s); s.flush()
    assert client.post("/api/oportunidades", json={"property_id": p.id}).status_code == 401


def test_consulta_exige_autenticacao_401(client):
    assert client.get("/api/oportunidades").status_code == 401


def test_consulta_403_para_consulta_sem_escrita(client):
    s = _session(); _user(s, "CONSULTA", "leitor@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "leitor@wf.com")
    # CONSULTA pode listar (read) mas NÃO criar (analysis:write).
    assert client.get("/api/oportunidades", headers=_h(tok)).status_code == 200
    assert client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).status_code == 403


# --------------------------------------------------------------------------
# Ciclo de vida + hard stops
# --------------------------------------------------------------------------

def test_criar_e_consultar_oportunidade(client):
    s = _session(); _user(s, "ANALISTA", "ana@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana@wf.com")
    resp = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok))
    assert resp.status_code == 201, resp.text
    oid = resp.json()["oportunidade"]["id"]
    det = client.get(f"/api/oportunidades/{oid}", headers=_h(tok))
    assert det.status_code == 200
    assert det.json()["workflow"]["current_phase"] == "F0_INTAKE"


def test_avanco_valido_f0_para_f1(client):
    s = _session(); _user(s, "ANALISTA", "ana2@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana2@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    assert _concluir(client, oid, tok).status_code == 200  # conclui gate de F0
    out = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F1_TRIAGEM", "transition_type": "AVANCO"}, headers=_h(tok))
    assert out.status_code == 200, out.text
    assert out.json()["decision"]["allowed"] is True
    assert out.json()["workflow"]["current_phase"] == "F1_TRIAGEM"


def test_hard_stop_modalidade_indefinida_bloqueia_f1_para_f2(client):
    s = _session(); _user(s, "ANALISTA", "ana3@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana3@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    _concluir(client, oid, tok)  # conclui F0
    client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F1_TRIAGEM"}, headers=_h(tok))
    _concluir(client, oid, tok)  # conclui gate de F1 (ainda assim o hard stop bloqueia)
    # F1 tem hard stop MODALIDADE_INDEFINIDA (modality=INDEFINIDO) → bloqueia avanço.
    out = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F2_DOCUMENTOS"}, headers=_h(tok))
    assert out.status_code == 200
    assert out.json()["decision"]["allowed"] is False
    assert "MODALIDADE_INDEFINIDA" in out.json()["decision"]["active_hard_stops"]


def test_classificar_modalidade_remove_hard_stop(client):
    s = _session(); _user(s, "ANALISTA", "ana4@wf.com"); p = _prop(s); s.flush()
    ev = models.Evidence(property_id=p.id, category="DOCUMENTAL", fact="alienação fiduciária Lei 9.514", source_excerpt="edital")
    s.add(ev); s.flush()
    tok = _login(client, "ana4@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    _concluir(client, oid, tok)  # conclui F0
    client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F1_TRIAGEM"}, headers=_h(tok))
    # Classifica com evidência → modalidade confirmada → hard stop some.
    cls = client.post(f"/api/oportunidades/{oid}/modalidade/classificar", json={"signals_text": "alienação fiduciária Lei 9.514", "evidence_id": ev.id, "confirm": True}, headers=_h(tok))
    assert cls.status_code == 200 and cls.json()["modality"] == "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"
    hs = client.get(f"/api/oportunidades/{oid}/hard-stops", headers=_h(tok))
    codes = [h["code"] for h in hs.json()["hard_stops"]]
    assert "MODALIDADE_INDEFINIDA" not in codes


def test_transicao_invalida_fora_da_matriz(client):
    s = _session(); _user(s, "ANALISTA", "ana5@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana5@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    out = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F9_LANCE_PAGAMENTO"}, headers=_h(tok))
    assert out.status_code == 200 and out.json()["decision"]["allowed"] is False


def test_descarte_exige_justificativa(client):
    s = _session(); _user(s, "ANALISTA", "ana6@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana6@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    out = client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F0_INTAKE", "transition_type": "DESCARTE"}, headers=_h(tok))
    assert out.status_code == 422  # sem justificativa


def test_historico_append_only(client):
    s = _session(); _user(s, "ANALISTA", "ana7@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana7@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    _concluir(client, oid, tok)  # conclui F0 (não é transição)
    client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F1_TRIAGEM"}, headers=_h(tok))  # permitida
    client.post(f"/api/oportunidades/{oid}/transicao", json={"target_phase": "F2_DOCUMENTOS"}, headers=_h(tok))  # bloqueada mas registrada
    hist = client.get(f"/api/oportunidades/{oid}/historico", headers=_h(tok))
    assert hist.status_code == 200 and len(hist.json()["historico"]) == 2


def test_isolamento_por_oportunidade(client):
    s = _session(); _user(s, "ANALISTA", "ana8@wf.com"); p1 = _prop(s, "A"); p2 = _prop(s, "B"); s.flush()
    tok = _login(client, "ana8@wf.com")
    o1 = client.post("/api/oportunidades", json={"property_id": p1.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    o2 = client.post("/api/oportunidades", json={"property_id": p2.id}, headers=_h(tok)).json()["oportunidade"]["id"]
    _concluir(client, o1, tok)  # conclui F0 apenas de o1
    client.post(f"/api/oportunidades/{o1}/transicao", json={"target_phase": "F1_TRIAGEM"}, headers=_h(tok))
    # o2 não é afetada pela transição de o1.
    assert client.get(f"/api/oportunidades/{o2}", headers=_h(tok)).json()["workflow"]["current_phase"] == "F0_INTAKE"
    assert client.get(f"/api/oportunidades/{o1}", headers=_h(tok)).json()["workflow"]["current_phase"] == "F1_TRIAGEM"


def test_checklist_aplicavel_por_modalidade(client):
    s = _session(); _user(s, "ANALISTA", "ana9@wf.com"); p = _prop(s); s.flush()
    tok = _login(client, "ana9@wf.com")
    oid = client.post("/api/oportunidades", json={"property_id": p.id, "modality": "JUDICIAL"}, headers=_h(tok)).json()["oportunidade"]["id"]
    resp = client.get(f"/api/oportunidades/{oid}/checklist-aplicavel", headers=_h(tok))
    assert resp.status_code == 200
    itens = {i["canonical_key"]: i["aplicabilidade"] for i in resp.json()["itens"]}
    assert len(itens) == 27  # catálogo preservado
    assert itens["CONSOLIDACAO_REGISTRADA"] == "NAO_APLICAVEL"
