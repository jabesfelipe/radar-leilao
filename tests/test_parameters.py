"""Testes do catálogo central de parâmetros (Etapa A): tipos, precedência,
vigência, versionamento, histórico imutável. PostgreSQL real (fixture ``db``)."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from backend.app import models, parameters as params


def _municipio(db, nome="Curitiba", uf="PR"):
    m = models.Municipality(name=nome, state=uf, coverage_active=True)
    db.add(m); db.flush()
    return m


# --- Conversão/validação de tipos -------------------------------------------

def test_coerce_tipos_basicos():
    assert params.coerce_value("10", "INTEGER") == 10
    assert params.coerce_value("0.30", "DECIMAL") == Decimal("0.30")
    assert params.coerce_value("true", "BOOLEAN") is True
    assert params.coerce_value('{"a": 1}', "JSON") == {"a": 1}
    assert params.coerce_value(None, "INTEGER") is None


def test_coerce_tipo_invalido_levanta():
    with pytest.raises(params.ParameterError):
        params.coerce_value("abc", "INTEGER")


def test_create_valida_valor_contra_tipo(db):
    with pytest.raises(params.ParameterError):
        params.create_parameter(db, {"key": "x.y", "category": "teste", "data_type": "DECIMAL", "value": "nao-decimal"})
    db.rollback()


def test_create_respeita_min_max(db):
    with pytest.raises(params.ParameterError):
        params.create_parameter(db, {"key": "x.max", "category": "teste", "data_type": "INTEGER", "value": "20", "max_value": Decimal("10")})
    db.rollback()


# --- Precedência -------------------------------------------------------------

def test_precedencia_municipio_sobre_global(db):
    m = _municipio(db)
    params.create_parameter(db, {"key": "mercado.amostra_minima", "category": "mercado", "data_type": "INTEGER", "value": "7", "scope": "GLOBAL"})
    params.create_parameter(db, {"key": "mercado.amostra_minima", "category": "mercado", "data_type": "INTEGER", "value": "5", "scope": "MUNICIPIO", "municipality_id": m.id})
    db.flush()
    assert params.resolve(db, "mercado.amostra_minima") == 7
    assert params.resolve(db, "mercado.amostra_minima", municipality_id=m.id) == 5


def test_precedencia_municipio_categoria_e_a_mais_especifica(db):
    m = _municipio(db)
    params.create_parameter(db, {"key": "deb.tol", "category": "debitos", "data_type": "INTEGER", "value": "1", "scope": "GLOBAL"})
    params.create_parameter(db, {"key": "deb.tol", "category": "debitos", "data_type": "INTEGER", "value": "2", "scope": "CATEGORIA", "debt_category": "IPTU"})
    params.create_parameter(db, {"key": "deb.tol", "category": "debitos", "data_type": "INTEGER", "value": "3", "scope": "MUNICIPIO", "municipality_id": m.id})
    params.create_parameter(db, {"key": "deb.tol", "category": "debitos", "data_type": "INTEGER", "value": "4", "scope": "MUNICIPIO_CATEGORIA", "municipality_id": m.id, "debt_category": "IPTU"})
    db.flush()
    assert params.resolve(db, "deb.tol", municipality_id=m.id, debt_category="IPTU") == 4
    assert params.resolve(db, "deb.tol", municipality_id=m.id) == 3
    assert params.resolve(db, "deb.tol", debt_category="IPTU") == 2
    assert params.resolve(db, "deb.tol") == 1


def test_resolve_usa_default_do_chamador_quando_inexistente(db):
    assert params.resolve(db, "inexistente.param", default=42) == 42


def test_resolve_cai_para_default_value_quando_value_ausente(db):
    params.create_parameter(db, {"key": "k.def", "category": "t", "data_type": "INTEGER", "value": None, "default_value": "9", "scope": "GLOBAL"})
    db.flush()
    assert params.resolve(db, "k.def") == 9


# --- Vigência e status -------------------------------------------------------

def test_parametro_inativo_nao_resolve(db):
    params.create_parameter(db, {"key": "k.inativo", "category": "t", "data_type": "INTEGER", "value": "1", "scope": "GLOBAL", "status": "INATIVO"})
    db.flush()
    assert params.resolve(db, "k.inativo", default="fallback") == "fallback"


def test_vigencia_futura_nao_resolve(db):
    futuro = datetime.utcnow() + timedelta(days=30)
    params.create_parameter(db, {"key": "k.futuro", "category": "t", "data_type": "INTEGER", "value": "1", "scope": "GLOBAL", "valid_from": futuro})
    db.flush()
    assert params.resolve(db, "k.futuro", default=0) == 0


# --- Versionamento e histórico ----------------------------------------------

def test_update_gera_nova_versao_e_historico_imutavel(db):
    p = params.create_parameter(db, {"key": "k.ver", "category": "t", "data_type": "INTEGER", "value": "1"}, actor="admin", justification="inicial")
    db.flush()
    assert p.version == 1
    params.update_parameter(db, p, {"value": "2"}, actor="admin", justification="ajuste")
    db.flush()
    assert p.version == 2 and params.resolve(db, "k.ver") == 2
    hist = db.scalars(
        __import__("sqlalchemy").select(models.ParameterHistory).where(models.ParameterHistory.parameter_id == p.id).order_by(models.ParameterHistory.id)
    ).all()
    assert [h.version for h in hist] == [1, 2]
    assert hist[0].action == "CREATE" and hist[1].action == "UPDATE"
    assert hist[1].previous_value == "1" and hist[1].new_value == "2"


def test_desativar_registra_historico(db):
    p = params.create_parameter(db, {"key": "k.off", "category": "t", "data_type": "INTEGER", "value": "1"})
    db.flush()
    params.update_parameter(db, p, {"status": "INATIVO"}, actor="admin")
    db.flush()
    hist = db.scalars(
        __import__("sqlalchemy").select(models.ParameterHistory).where(models.ParameterHistory.parameter_id == p.id)
    ).all()
    assert any(h.action == "DEACTIVATE" for h in hist)
