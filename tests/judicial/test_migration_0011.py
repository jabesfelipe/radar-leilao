"""TASK FINAL — testa a migration 0011 (tabelas judicial_*) de forma reversível.

Aplica upgrade() e downgrade() da migration DENTRO de uma transação isolada, que é
revertida ao final (não altera o schema real do banco de teste). Verifica:
- em banco "com o schema atual do Radar": upgrade cria todas as tabelas judicial_*;
- downgrade remove todas elas;
- a migration não toca em nenhuma tabela do Radar.

Pula sem PostgreSQL (RAG_TEST_DATABASE_URL).
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

_JUDICIAL_TABLES = {
    "judicial_searches",
    "judicial_search_sources",
    "judicial_processes",
    "judicial_process_parties",
    "judicial_process_subjects",
    "judicial_process_movements",
    "judicial_signals",
    "judicial_search_events",
}

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "backend" / "migrations" / "versions" / "0011_judicial_persistence.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_0011", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def engine_ddl():
    url = os.getenv("RAG_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RAG_TEST_DATABASE_URL não configurada; teste de migration exige PostgreSQL")
    eng = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    try:
        with eng.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponível: {exc}")
    return eng


def test_0011_upgrade_downgrade_reversivel(engine_ddl):
    migration = _load_migration()
    assert migration.down_revision == "0010_leilao_data_hora"

    # Garante estado limpo: se as tabelas já existirem (migration aplicada no banco),
    # o teste ainda é válido pois roda tudo dentro de uma transação revertida.
    connection = engine_ddl.connect()
    trans = connection.begin()
    try:
        # Se as tabelas já existem no banco de teste, removê-las dentro da transação
        # para exercitar o upgrade a partir do "schema atual do Radar" sem judicial_*.
        insp = inspect(connection)
        existentes = set(insp.get_table_names())
        radar_antes = existentes - _JUDICIAL_TABLES

        ctx = MigrationContext.configure(connection)
        op = Operations(ctx)
        import alembic.op as alembic_op

        # Injeta o proxy global usado pela migration (op.create_table etc.).
        alembic_op._proxy = op
        try:
            if _JUDICIAL_TABLES & existentes:
                migration.downgrade()  # limpa para simular banco sem judicial_*
            # UPGRADE: cria as tabelas judicial_*.
            migration.upgrade()
            depois_up = set(inspect(connection).get_table_names())
            assert _JUDICIAL_TABLES.issubset(depois_up), "upgrade deve criar todas as judicial_*"
            # Radar intacto.
            assert radar_antes.issubset(depois_up), "migration não pode remover tabelas do Radar"

            # DOWNGRADE: remove apenas as judicial_*.
            migration.downgrade()
            depois_down = set(inspect(connection).get_table_names())
            assert not (_JUDICIAL_TABLES & depois_down), "downgrade deve remover todas as judicial_*"
            assert radar_antes.issubset(depois_down), "downgrade não pode remover tabelas do Radar"
        finally:
            alembic_op._proxy = None
    finally:
        trans.rollback()  # nada é persistido no banco real
        connection.close()
