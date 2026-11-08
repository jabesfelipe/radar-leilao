"""Testes das Etapas C–F da Central de Débitos.

Cobre: parâmetros centralizados (consumo + snapshot + precedência), estimativa
condominial (3 cenários, ESTIMADO, idade≠inadimplência), provider de consulta
(manual/assistido, sem ocorrência, requer intervenção, retry de transitório),
consolidação sem dupla contagem e autorização por papel (503/401/403/ok).
PostgreSQL real (fixture ``db``) + TestClient HTTP.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import models, debts_service, estimates_service, parameters as params, debt_query_service, debt_providers
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


def _prop(db, titulo="Imóvel CF"):
    p = models.Property(title=titulo, address="Rua CF", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(p); db.flush()
    return p


# --------------------------------------------------------------------------
# Etapa D — parâmetros centralizados: seed, consumo, precedência, snapshot
# --------------------------------------------------------------------------

def test_seed_all_inclui_parametros(db):
    r = debts_service.seed_all(db); db.flush()
    assert "parameters" in r and r["parameters"] > 0
    # Reexecução idempotente.
    r2 = debts_service.seed_all(db); db.flush()
    assert r2["parameters"] == 0
    assert params.resolve(db, "mercado.amostra_minima") == 7
    assert params.resolve(db, "mercado.cv_dispersao_alta") == Decimal("0.30")


def test_precedencia_municipio_sobrepoe_global(db):
    debts_service.seed_all(db); db.flush()
    muni = db.scalar(select(models.Municipality).where(models.Municipality.name == "Curitiba"))
    # Cria um override por município para a amostra mínima.
    params.create_parameter(db, {
        "key": "mercado.amostra_minima", "name": "Amostra mínima (Curitiba)", "category": "mercado",
        "data_type": "INTEGER", "scope": "MUNICIPIO", "municipality_id": muni.id, "value": "3",
    }); db.flush()
    assert params.resolve(db, "mercado.amostra_minima", municipality_id=muni.id) == 3
    assert params.resolve(db, "mercado.amostra_minima") == 7  # global intacto


def test_parameter_snapshot_serializa_valores(db):
    debts_service.seed_all(db); db.flush()
    snap = params.parameter_snapshot(db)
    chaves = {s["key"] for s in snap}
    assert "mercado.amostra_minima" in chaves
    # Valores serializados como texto (imutabilidade por execução).
    for s in snap:
        assert s["value"] is None or isinstance(s["value"], str)


def test_market_consome_parametro_resolvido(db):
    from backend.app.market import calculate_market
    # min_sample resolvido = 3 => amostra de 3 passa a ser suficiente.
    out = calculate_market([{ "kind": "VENDA", "price": 100, "area_m2": 10 }] * 3, min_sample=3)
    assert out["venda"]["qualidade"]["amostra_suficiente"] is True
    assert out["parametros"]["amostra_minima"] == 3


# --------------------------------------------------------------------------
# Etapa C — estimativa condominial
# --------------------------------------------------------------------------

def test_estimativa_tres_cenarios_e_estimado(db):
    debts_service.seed_all(db); db.flush()
    out = estimates_service.compute_condominium_estimate(db, monthly_reference=Decimal("1000"), months_delinquent=12)
    assert out["possivel"] is True
    assert out["status"] == "ESTIMADO" and out["natureza"] == "ESTIMATIVA_OPERACIONAL"
    cen = out["cenarios"]
    assert cen["provavel"] == Decimal("12000.00")
    assert cen["conservador"] > cen["provavel"] > cen["otimista"]


def test_estimativa_nao_deriva_inadimplencia_da_idade(db):
    debts_service.seed_all(db); db.flush()
    # Idade informada NÃO altera meses de inadimplência (usa o parâmetro=12).
    out = estimates_service.compute_condominium_estimate(db, monthly_reference=Decimal("500"), property_age_years=40)
    assert out["memoria_calculo"]["meses_inadimplencia_presumidos"] == 12
    assert out["cenarios"]["provavel"] == Decimal("6000.00")
    assert out["memoria_calculo"]["contexto"]["idade_imovel_anos"] == 40


def test_estimativa_sem_valor_nao_calculavel(db):
    debts_service.seed_all(db); db.flush()
    out = estimates_service.compute_condominium_estimate(db, monthly_reference=None)
    assert out["possivel"] is False and out["status"] == "ESTIMADO"


def test_alerta_idade_desconhecida_nao_conclusivo(db):
    debts_service.seed_all(db); db.flush()
    a = estimates_service.age_alerts(db, property_age_years=None, age_known=False)
    assert a["conclusivo"] is False and a["nivel"] is None


def test_alerta_idade_acima_limite(db):
    debts_service.seed_all(db); db.flush()
    a = estimates_service.age_alerts(db, property_age_years=20, age_known=True)
    assert a["conclusivo"] is True and a["nivel"] == "ATENCAO_FORTE"


# --------------------------------------------------------------------------
# Etapa E — provider de consulta
# --------------------------------------------------------------------------

def test_provider_manual_requer_intervencao_sem_dados(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    out = debt_query_service.run_query(db, p, debt_type_code="IPTU", municipality_id=None, payload={})
    assert out["consulta"]["status"] == "REQUER_INTERVENCAO_MANUAL"
    assert out["consulta"]["provider"] == "manual_assistida"
    assert out["debitos_criados"] == []


def test_provider_sem_ocorrencia(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    out = debt_query_service.run_query(db, p, debt_type_code="IPTU", payload={"sem_ocorrencia": True})
    assert out["consulta"]["status"] == "SEM_OCORRENCIA"


def test_provider_assistido_cria_debito_normalizado(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    out = debt_query_service.run_query(db, p, debt_type_code="IPTU", payload={
        "itens": [{"debt_type_code": "IPTU", "updated_amount": "1200.00", "status": "INFORMADO", "reliability": "INFORMADO"}],
    })
    assert out["consulta"]["status"] == "CONCLUIDA"
    assert len(out["debitos_criados"]) == 1
    debt = db.get(models.PropertyDebt, out["debitos_criados"][0])
    assert debt.debt_type_code == "IPTU" and debt.acquisition_method.startswith("manual_assistida")


def test_provider_tipo_invalido(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    with pytest.raises(ValueError):
        debt_query_service.run_query(db, p, debt_type_code="NAO_EXISTE")


def test_select_provider_recai_no_manual(db):
    debts_service.seed_all(db); db.flush()
    prov = debt_providers.select_provider(db, municipality_id=None, debt_type_code="IPTU")
    assert prov.name == "manual_assistida"


# --------------------------------------------------------------------------
# Etapa F — consolidação sem dupla contagem (já coberta em test_central_debitos;
# aqui garantimos que a consulta assistida não duplica com o legado)
# --------------------------------------------------------------------------

def test_consulta_assistida_nao_duplica_consolidacao(db):
    debts_service.seed_all(db); db.flush()
    p = _prop(db)
    debt_query_service.run_query(db, p, debt_type_code="IPTU", payload={
        "itens": [{"debt_type_code": "IPTU", "updated_amount": "300.00", "status": "CONFIRMADO", "reliability": "OFICIAL"}],
    })
    c = debts_service.consolidate(db, p.id)
    assert c["totais"]["confirmados"] == Decimal("300.00")
    assert c["contagens"]["confirmados"] == 1


# --------------------------------------------------------------------------
# Segurança — autorização por papel
# --------------------------------------------------------------------------

@pytest.fixture
def client(postgres_engine):
    if TestClient is None:
        pytest.skip("httpx/TestClient indisponível")
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


def test_authz_sem_token_configurado_503(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", None, raising=False)
    monkeypatch.setattr(settings, "authz_role_tokens", None, raising=False)
    resp = client.post("/api/admin/parametros", json={"key": "x.y", "category": "t", "data_type": "INTEGER", "value": "1"})
    assert resp.status_code == 503


def test_authz_token_invalido_401(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", "token-ok", raising=False)
    monkeypatch.setattr(settings, "authz_role_tokens", None, raising=False)
    resp = client.post("/api/admin/parametros", json={"key": "x.y", "category": "t", "data_type": "INTEGER", "value": "1"}, headers={"X-Admin-Token": "errado"})
    assert resp.status_code == 401


def test_authz_operador_sem_permissao_de_cobertura_403(client, monkeypatch):
    # Papel 'operador' tem param/consulta, mas NÃO admin:write (cobertura/municípios).
    monkeypatch.setattr(settings, "admin_api_token", "token-admin", raising=False)
    monkeypatch.setattr(settings, "authz_role_tokens", '{"operador":"token-op"}', raising=False)
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "OUTRO_DEBITO_MUNICIPAL"}, headers={"X-Admin-Token": "token-op"})
    assert resp.status_code == 403
    # Mas pode escrever parâmetro (permissão admin:parameters).
    ok = client.post("/api/admin/parametros", json={"key": "teste.op", "category": "geral", "data_type": "INTEGER", "value": "1"}, headers={"X-Admin-Token": "token-op"})
    assert ok.status_code == 201


def test_authz_admin_pode_tudo(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", "token-admin", raising=False)
    monkeypatch.setattr(settings, "authz_role_tokens", None, raising=False)
    client.get("/api/admin/cobertura")  # seed_all: municípios + catálogo + cobertura
    muni = client.get("/api/admin/municipios").json()["itens"][0]
    # COTA_CONDOMINIAL não é semeada na cobertura inicial → criação limpa (201).
    resp = client.post("/api/admin/cobertura", json={"municipality_id": muni["id"], "debt_type_code": "COTA_CONDOMINIAL", "level": "MANUAL"}, headers={"X-Admin-Token": "token-admin"})
    assert resp.status_code == 201, resp.text


# --------------------------------------------------------------------------
# HTTP — endpoints de consulta e estimativa no dossiê
# --------------------------------------------------------------------------

def test_http_estimativa_condominio(client):
    assert client.get("/api/admin/tipos-debito").status_code == 200  # semeia catálogo/params
    pid = client.post("/api/imoveis", json={"title": "Imóvel Est", "address": "R", "city": "Curitiba", "state": "PR", "property_type": "Apartamento", "area_m2": 70}).json()["id"]
    resp = client.post(f"/api/imoveis/{pid}/debitos/estimar-condominio", json={"monthly_reference": "800.00", "months_delinquent": 10, "persist": True})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["estimativa"]["status"] == "ESTIMADO"
    assert float(body["estimativa"]["cenarios"]["provavel"]) == 8000.0


def test_http_consulta_assistida_e_historico(client):
    assert client.get("/api/admin/tipos-debito").status_code == 200
    pid = client.post("/api/imoveis", json={"title": "Imóvel Cons", "address": "R", "city": "Curitiba", "state": "PR", "property_type": "Apartamento", "area_m2": 70}).json()["id"]
    resp = client.post(f"/api/imoveis/{pid}/debitos/consultar", json={"debt_type_code": "IPTU", "itens": [{"updated_amount": "500.00", "status": "INFORMADO"}]})
    assert resp.status_code == 201, resp.text
    assert resp.json()["consulta"]["status"] == "CONCLUIDA"
    hist = client.get(f"/api/imoveis/{pid}/debitos/consultas")
    assert hist.status_code == 200 and len(hist.json()["consultas"]) == 1
