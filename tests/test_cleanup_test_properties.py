"""Trava de segurança de ``scripts/db/cleanup_test_properties.sql`` (v1.0.9).

O script apaga TODOS os imóveis exceto o 633. A trava só deixa prosseguir se o 633 existir com o título fictício de
referência; qualquer outro caso aborta sem apagar nada.

Isolamento: cada teste roda numa transação (revertida no fim) com um schema temporário que contém cópias vazias
(``LIKE ... INCLUDING DEFAULTS``) de todas as tabelas citadas pelo script, e ``search_path`` apontando para ele. O
script real roda sem alteração e não toca nos dados de outros testes. Se o script citar uma tabela que não existe no
schema atual, o ``LIKE`` falha e o teste também.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "db" / "cleanup_test_properties.sql"
TITULO_REFERENCIA = "COND RESIDENCIAL EXEMPLO GAMA"
SCHEMA = "cleanup_guard_test"


def _sql() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _tables(sql: str) -> list[str]:
    return sorted(set(re.findall(r"\b(?:FROM|JOIN)\s+([a-z_]+)", sql)) - {"properties_to_delete"})


@contextmanager
def _sandbox(engine):
    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(text(f"CREATE SCHEMA {SCHEMA}"))
        for table in _tables(_sql()):
            connection.execute(text(f"CREATE TABLE {SCHEMA}.{table} (LIKE public.{table} INCLUDING DEFAULTS)"))
            # Só no sandbox: colunas NOT NULL sem default do banco (default só no ORM) não bloqueiam os inserts mínimos.
            required = connection.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = :s AND table_name = :t "
                "AND is_nullable = 'NO' AND column_default IS NULL AND column_name <> 'id'"), {"s": SCHEMA, "t": table}).scalars().all()
            for column in required:
                connection.execute(text(f'ALTER TABLE {SCHEMA}.{table} ALTER COLUMN "{column}" DROP NOT NULL'))
        connection.execute(text(f"SET LOCAL search_path TO {SCHEMA}"))
        yield connection
    finally:
        transaction.rollback()
        connection.close()


def _property(conn, pid: int, title: str) -> None:
    conn.execute(text("INSERT INTO properties (id, title, city, state) VALUES (:id, :title, 'Cidade Fictícia', 'PR')"), {"id": pid, "title": title})


def _cost(conn, pid: int) -> None:
    conn.execute(text("INSERT INTO costs (property_id, category, description, amount) VALUES (:pid, 'ITBI', 'teste', 1)"), {"pid": pid})


def _ids(conn, sql: str) -> list[int]:
    return [row[0] for row in conn.execute(text(sql))]


def test_script_cita_o_titulo_ficticio_e_mantem_a_trava():
    sql = _sql()
    assert f"title = '{TITULO_REFERENCIA}'" in sql and "WHERE id = 633" in sql
    assert "RAISE EXCEPTION 'ABORTADO" in sql
    assert "SELECT id FROM properties WHERE id <> 633" in sql


def test_limpeza_preserva_somente_o_imovel_de_referencia_e_seus_dados(postgres_engine):
    with _sandbox(postgres_engine) as conn:
        _property(conn, 633, TITULO_REFERENCIA)
        _property(conn, 900, "Imóvel de teste A")
        _property(conn, 901, "Imóvel de teste B")
        for pid in (633, 900, 901):
            _cost(conn, pid)
        conn.exec_driver_sql(_sql())
        assert _ids(conn, "SELECT id FROM properties ORDER BY id") == [633]
        assert _ids(conn, "SELECT property_id FROM costs") == [633]


@pytest.mark.parametrize("titulo_633", [None, "Outro imóvel qualquer", TITULO_REFERENCIA + " ", TITULO_REFERENCIA.lower()])
def test_trava_aborta_sem_apagar_quando_o_imovel_633_nao_confere(postgres_engine, titulo_633):
    with _sandbox(postgres_engine) as conn:
        if titulo_633 is not None:
            _property(conn, 633, titulo_633)
        _property(conn, 900, "Imóvel de teste A")
        _cost(conn, 900)
        conn.execute(text("SAVEPOINT antes_do_script"))
        with pytest.raises(DBAPIError, match="ABORTADO"):
            conn.exec_driver_sql(_sql())
        conn.execute(text("ROLLBACK TO SAVEPOINT antes_do_script"))
        assert _ids(conn, "SELECT id FROM properties ORDER BY id") == ([900] if titulo_633 is None else [633, 900])
        assert _ids(conn, "SELECT property_id FROM costs") == [900]      # nada foi apagado
