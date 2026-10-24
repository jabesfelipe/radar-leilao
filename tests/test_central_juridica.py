"""Central Jurídica — testes de integração (biblioteca curada, busca textual sem
API key, referências contextuais por item do checklist e por etapa, visão jurídica
do imóvel enriquecida e preservação dos 27 canonical_key).

Reusa a fixture `client` (TestClient + savepoint/rollback; não toca dados reais) e
NÃO dispara LLM: sem OPENAI_API_KEY a busca cai para o modo textual determinístico.
"""
from __future__ import annotations

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from backend.app import models, legal_service
from backend.app.checklist import CHECKLIST_MASTER
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

REQUIRED_TABLES = {
    "properties", "legal_sources", "legal_provisions", "legal_rules",
    "legal_rule_checklist_links", "knowledge_items", "checklist_items",
    "checklist_executions", "checklist_results",
}


@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    tables = set(inspect(postgres_engine).get_table_names())
    if not REQUIRED_TABLES.issubset(tables):
        pytest.skip("Migrations da Central Jurídica ainda não aplicadas")
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
    resp = client.post("/api/imoveis", json={"title": "Imóvel CJ", "address": "Rua Jurídica, 10", "city": "Curitiba", "state": "PR", "property_type": "Apto", "area_m2": 55})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---- Seed idempotente -------------------------------------------------------
def test_seed_idempotente(client):
    # 1ª leitura materializa o catálogo; 2ª não duplica nada.
    first = client.get("/api/juridico/biblioteca")
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["total_fontes"] >= 5
    assert data["total_dispositivos"] >= 9
    assert data["total_regras"] >= 8

    second = client.get("/api/juridico/biblioteca").json()
    assert second["total_fontes"] == data["total_fontes"]
    assert second["total_dispositivos"] == data["total_dispositivos"]
    assert second["total_regras"] == data["total_regras"]


def test_biblioteca_separa_texto_oficial_de_orientacao(client):
    data = client.get("/api/juridico/biblioteca").json()
    fontes = {f["slug"]: f for f in data["fontes"]}
    assert "lei-9514-1997" in fontes
    art27 = next(p for p in fontes["lei-9514-1997"]["dispositivos"] if p["referencia"] == "Art. 27")
    # Texto oficial e orientação prática são campos SEPARADOS (nunca misturados).
    assert art27["texto_oficial"]
    assert art27["orientacao_pratica"]
    assert art27["texto_oficial"] != art27["orientacao_pratica"]
    assert art27["verificacao"] in models.LEGAL_VERIFICATION_STATUS


# ---- Busca (modo textual sem API key) ---------------------------------------
def test_busca_textual_sem_api_key(client):
    resp = client.get("/api/juridico/biblioteca/busca", params={"q": "taxa de ocupação"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["modo_busca"] == "TEXTUAL"
    assert body["total"] >= 1
    refs = " ".join(r["referencia"] for r in body["resultados"])
    assert "37-A" in refs


def test_busca_filtra_por_contexto(client):
    body = client.get("/api/juridico/biblioteca/busca", params={"q": "imóvel", "contexto": "TRIBUTARIO"}).json()
    for r in body["resultados"]:
        assert "TRIBUTARIO" in [c.upper() for c in r["contextos"]]


# ---- Referências contextuais por item do checklist --------------------------
def test_referencias_por_canonical_key(client):
    body = client.get("/api/juridico/referencias/checklist/NOTIFICACAO_DOIS_LEILOES").json()
    assert body["existe_no_checklist"] is True
    assert body["total"] >= 1
    # A regra dos dois leilões deve estar ancorada no art. 27 da Lei 9.514/97.
    base = body["referencias"][0]["base_legal"]
    assert base is not None
    assert base["referencia"] == "Art. 27"


def test_referencia_para_key_inexistente(client):
    body = client.get("/api/juridico/referencias/checklist/NAO_EXISTE_XYZ").json()
    assert body["existe_no_checklist"] is False
    assert body["total"] == 0


def test_referencias_por_contexto_desocupacao(client):
    body = client.get("/api/juridico/referencias/contexto/DESOCUPACAO").json()
    assert body["contexto"] == "DESOCUPACAO"
    assert body["total"] >= 1
    titulos = [r["titulo"] for r in body["referencias"]]
    assert any("ocupaç" in t.lower() or "posse" in t.lower() for t in titulos)


# ---- Preservação dos 27 canonical_key ---------------------------------------
def test_vinculos_so_apontam_para_keys_existentes(client):
    # Força o seed.
    client.get("/api/juridico/biblioteca")
    overview = client.get("/api/juridico/biblioteca").json()
    cobertura = overview["cobertura_checklist"]
    master_keys = {k for (k, *_rest) in CHECKLIST_MASTER}
    assert master_keys  # sanity
    for key in cobertura:
        assert key in master_keys, f"Vínculo aponta para canonical_key inexistente: {key}"
    # Total de itens do checklist permanece 27 (não foi alterado).
    assert overview["itens_checklist_total"] == len(master_keys) == 27


# ---- Visão jurídica do imóvel enriquecida -----------------------------------
def test_central_do_imovel_reusa_sintese_e_anexa_base_legal(client):
    pid = _new_property(client)
    body = client.get(f"/api/imoveis/{pid}/juridico/central").json()
    assert body["property_id"] == pid
    # Reaproveita a síntese jurídica determinística existente.
    assert "sintese_juridica" in body
    assert "situacao_imovel" in body["sintese_juridica"]
    # A chave de itens com base legal existe (pode ser 0 sem execução de checklist).
    assert "itens_com_base_legal" in body


# ---- Checklist Mestre intacto (unidade, sem HTTP) ---------------------------
def test_checklist_master_nao_foi_alterado():
    assert len(CHECKLIST_MASTER) == 27
    # origin preservado em todos os itens.
    for (_key, _q, _cat, origin) in CHECKLIST_MASTER:
        assert origin == "Método Radar / referência extrajudicial"


def test_seed_so_vincula_regras_a_keys_do_master(db):
    # Teste determinístico direto no serviço (sem HTTP).
    created = legal_service.seed_legal_catalog(db, embed=False)
    db.flush()
    assert created["sources"] >= 0  # idempotente: pode já existir
    links = db.scalars(select(models.LegalRuleChecklistLink)).all()
    master_keys = {k for (k, *_rest) in CHECKLIST_MASTER}
    for link in links:
        assert link.canonical_key in master_keys
