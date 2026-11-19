"""v1.0.12 — Fase F: IPTU dos 4 municípios. Sem chamada a portal real: o levantamento vive como dado e a consulta segue manual
assistida (provider sem rede). Dados fictícios."""
from __future__ import annotations

import socket

import pytest
from sqlalchemy import select

from backend.app import debt_providers, debt_query_service, debts_service, models
from backend.app.municipal_iptu import IPTU_PORTALS, _SEED_ORIGINAL_OBS, guidance, seed_iptu_sources
from tests.test_checklist_evidencias import _prop
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)

MUNICIPIOS = [("Curitiba", "PR"), ("São José dos Pinhais", "PR"), ("Fazenda Rio Grande", "PR"), ("Assis", "SP")]


@pytest.fixture
def sem_rede(monkeypatch):
    """Qualquer tentativa de abrir conexão falha: prova que nenhum portal é chamado."""
    def _blocked(*args, **kwargs):
        raise AssertionError("tentativa de acesso à rede em teste")
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket.socket, "connect", _blocked)


def _muni(db, name, state):
    return db.scalar(select(models.Municipality).where(models.Municipality.name == name, models.Municipality.state == state))


def test_levantamento_dos_quatro_municipios_sem_automacao():
    assert set(IPTU_PORTALS) == set(MUNICIPIOS)
    for key, info in IPTU_PORTALS.items():
        assert info["nivel"] == "MANUAL" and info["api_publica"] is False and info["urls"] and info["passos"], key
        assert info["motivo_manual"] and info["termos_uso"] and info["identificador"], key
        assert all(u.startswith("https://") for u in info["urls"]), key


def test_seed_cria_fontes_e_reclassifica_so_a_cobertura_nao_editada(db):
    debts_service.seed_all(db); db.flush()
    for name, state in MUNICIPIOS:
        muni = _muni(db, name, state)
        fonte = db.scalar(select(models.DebtSource).where(models.DebtSource.municipality_id == muni.id, models.DebtSource.debt_category == "IPTU"))
        assert fonte is not None and fonte.official_url == IPTU_PORTALS[(name, state)]["urls"][0] and fonte.source_type == "PORTAL_PUBLICO"
        cov = db.scalar(select(models.MunicipalityCoverage).where(models.MunicipalityCoverage.municipality_id == muni.id,
                                                                  models.MunicipalityCoverage.debt_type_code == "IPTU"))
        assert cov.level == "MANUAL"
    assert seed_iptu_sources(db) == {"fontes_iptu": 0, "cobertura_reclassificada": 0}       # idempotente


def test_cobertura_editada_pelo_operador_nunca_e_sobrescrita(db):
    debts_service.seed_debt_types(db); debts_service.seed_municipalities(db)
    from backend.app import coverage_service
    coverage_service.seed_coverage(db); db.flush()
    curitiba = _muni(db, "Curitiba", "PR")
    cov = db.scalar(select(models.MunicipalityCoverage).where(models.MunicipalityCoverage.municipality_id == curitiba.id,
                                                              models.MunicipalityCoverage.debt_type_code == "IPTU"))
    assert cov.observations == _SEED_ORIGINAL_OBS[("Curitiba", "PR")]
    cov.observations = "Editado pelo operador"
    db.flush()
    seed_iptu_sources(db); db.flush()
    assert cov.level == "AUTOMATIZAVEL" and cov.observations == "Editado pelo operador"


def test_consulta_de_iptu_segue_manual_assistida_com_orientacao(db, sem_rede):
    debts_service.seed_all(db); db.flush()
    prop = _prop(db)
    fazenda = _muni(db, "Fazenda Rio Grande", "PR")
    assert debt_providers.select_provider(db, municipality_id=fazenda.id, debt_type_code="IPTU").name == "manual_assistida"
    out = debt_query_service.run_query(db, prop, debt_type_code="IPTU", municipality_id=fazenda.id, identifier="000000000000")
    assert out["consulta"]["status"] == "REQUER_INTERVENCAO_MANUAL"
    assert out["orientacao"]["modo"] == "MANUAL_ASSISTIDA" and out["orientacao"]["automatizado"] is False
    assert "CPF ou CNPJ" in out["orientacao"]["identificador"] and out["orientacao"]["passos"]
    # resultado informado pelo operador (registro simulado) entra como débito informado, nunca oficial automático
    out2 = debt_query_service.run_query(db, prop, debt_type_code="IPTU", municipality_id=fazenda.id,
                                        payload={"itens": [{"original_amount": "350.00", "competence": "2025"}]})
    debito = db.get(models.PropertyDebt, out2["debitos_criados"][0])
    assert debito.status == "INFORMADO" and debito.acquisition_method == "manual_assistida:ASSISTIDA"


def test_orientacao_de_municipio_sem_levantamento(db):
    muni = models.Municipality(name="Cidade Fictícia", state="PR", coverage_active=False)
    db.add(muni); db.flush()
    g = guidance(db, muni.id)
    assert g["modo"] == "MANUAL_ASSISTIDA" and g["urls"] == [] and "sem levantamento" in g["motivo"]
    assert guidance(db, None) is None


def test_api_orientacao_iptu_pelo_municipio_do_imovel(api, sem_rede):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    dados = {**{k: _json(v) for k, v in IMOVEL7.items()}, "city": "Assis", "state": "SP"}
    pid = client.post("/api/imoveis", json=dados).json()["id"]
    body = client.get(f"/api/imoveis/{pid}/debitos/orientacao-iptu").json()
    assert body["orientacao"]["municipio"] == "Assis/SP" and body["orientacao"]["automatizado"] is False
    assert any("assis.sp.gov.br" in u for u in body["orientacao"]["urls"])
