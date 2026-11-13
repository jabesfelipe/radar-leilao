"""Migration 0024 (índice único de análise por imóvel, oportunidade e versão).

Segue o padrão de ``tests/judicial/test_migration_0011.py``: ``upgrade()``/``downgrade()`` da
migration rodam DENTRO de uma transação isolada que é revertida ao final (o DDL do PostgreSQL
é transacional), então nada persiste no banco compartilhado da suíte. A fixture ainda confere,
depois do rollback, que o índice e o conteúdo de ``analyses`` do banco compartilhado ficaram
exatamente como estavam.

Cobertura: upgrade com dados representativos, preservação dos dados, mesma versão em
oportunidades diferentes, rejeição de duplicidade (inclusive legado com ``opportunity_id``
nulo), aborto do upgrade com duplicidades sem alterar dados/schema/``alembic_version``,
idempotência e downgrade.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import alembic.op as alembic_op
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from backend.app import models

INDEX = "uq_analysis_property_opp_version"
_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "backend" / "migrations" / "versions" / "0024_analysis_version_unique.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_0024", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------------------- helpers

def _insert(conn, model, **values) -> int:
    table = model.__table__
    return conn.execute(table.insert().values(**values).returning(table.c.id)).scalar_one()


def _analysis(conn, property_id, opportunity_id, version) -> int:
    return _insert(conn, models.Analysis, property_id=property_id, opportunity_id=opportunity_id, version=version)


def _index_def(conn) -> str | None:
    """Definição do índice ``INDEX`` SOMENTE se ele pertencer à tabela ``analyses`` (a do search_path)."""
    return conn.execute(text(
        "SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
        "WHERE c.relname = :n AND i.indrelid = to_regclass('analyses')"), {"n": INDEX}).scalar()


def _indexes_named(conn) -> list[tuple]:
    """Todos os índices com o nome ``INDEX``, em qualquer schema/tabela."""
    return [tuple(r) for r in conn.execute(text(
        "SELECT schemaname, tablename, indexdef FROM pg_indexes WHERE indexname = :n ORDER BY schemaname, tablename"), {"n": INDEX})]


def _rows(conn) -> list[tuple]:
    return [tuple(r) for r in conn.execute(text("SELECT id, property_id, opportunity_id, version, scope FROM analyses ORDER BY id"))]


def _schema(conn) -> dict:
    """Retrato do schema de ``analyses``: colunas, índices e constraints."""
    return {
        "colunas": [tuple(r) for r in conn.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'analyses' AND table_schema = current_schema() ORDER BY ordinal_position"))],
        "indices": [tuple(r) for r in conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'analyses' ORDER BY indexname"))],
        "constraints": [tuple(r) for r in conn.execute(text(
            "SELECT conname, contype FROM pg_constraint WHERE conrelid = 'analyses'::regclass ORDER BY conname"))],
    }


def _alembic_version(conn) -> list[str] | None:
    if not conn.execute(text("SELECT to_regclass('alembic_version') IS NOT NULL")).scalar():
        return None   # banco de teste criado sem alembic: nada a comparar
    return [r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))]


def _estado_compartilhado(engine) -> tuple:
    with engine.connect() as conn:
        return (_index_def(conn), conn.execute(text("SELECT count(*), coalesce(sum(id), 0) FROM analyses")).first()[:2])


def _seed_representativo(conn) -> SimpleNamespace:
    """2 imóveis; o 1º com histórico legado (oportunidade nula) e duas oportunidades com as
    MESMAS versões entre si; o 2º só com legado."""
    p1 = _insert(conn, models.Property, title="Imóvel 0024 A", address="Rua A", city="São Paulo", state="SP")
    p2 = _insert(conn, models.Property, title="Imóvel 0024 B", address="Rua B", city="Campinas", state="SP")
    opp_a = _insert(conn, models.Opportunity, property_id=p1)
    opp_b = _insert(conn, models.Opportunity, property_id=p1)
    ids = [_analysis(conn, p1, None, v) for v in (1, 2, 3)]
    ids += [_analysis(conn, p1, opp_a, v) for v in (1, 2)]
    ids += [_analysis(conn, p1, opp_b, v) for v in (1, 2)]
    ids += [_analysis(conn, p2, None, 1)]
    return SimpleNamespace(p1=p1, p2=p2, opp_a=opp_a, opp_b=opp_b, ids=ids)


@pytest.fixture
def mig(postgres_engine):
    """Transação isolada, no estado "produção" (sem o índice), com a migration carregada."""
    antes = _estado_compartilhado(postgres_engine)
    migration = _load_migration()
    connection = postgres_engine.connect()
    trans = connection.begin()
    try:
        connection.exec_driver_sql("SET LOCAL lock_timeout = '15s'")   # falha rápido em vez de travar a suíte
        connection.exec_driver_sql(f"DROP INDEX IF EXISTS {INDEX}")     # estado anterior à 0024 (dentro da transação)
        alembic_op._proxy = Operations(MigrationContext.configure(connection))
        assert _index_def(connection) is None
        yield SimpleNamespace(m=migration, conn=connection)
    finally:
        alembic_op._proxy = None
        trans.rollback()
        connection.close()
    # Não contaminou o banco compartilhado: índice e conteúdo de analyses idênticos.
    assert _estado_compartilhado(postgres_engine) == antes


# ----------------------------------------------------------------------------- testes

def test_encadeamento_e_compatibilidade_com_o_modelo(mig):
    assert mig.m.revision == "0024_analysis_version_unique" and mig.m.down_revision == "0023_usuarios"
    assert mig.m.INDEX == INDEX
    indices = {i.name: i for i in models.Analysis.__table__.indexes}
    assert INDEX in indices and indices[INDEX].unique, "o modelo SQLAlchemy deve declarar o mesmo índice único"
    mig.m.upgrade()
    definicao = _index_def(mig.conn)
    assert definicao and "UNIQUE" in definicao
    assert "(property_id, COALESCE(opportunity_id, 0), version)" in definicao


def test_upgrade_com_dados_representativos_preserva_tudo(mig):
    _seed_representativo(mig.conn)
    linhas, versao = _rows(mig.conn), _alembic_version(mig.conn)
    mig.m.upgrade()
    assert _index_def(mig.conn) is not None
    assert _rows(mig.conn) == linhas                      # nenhuma linha criada, alterada ou removida
    assert _alembic_version(mig.conn) == versao           # a função da migration não mexe na versão do alembic


def test_mesma_versao_em_oportunidades_diferentes_e_aceita(mig):
    s = _seed_representativo(mig.conn)
    mig.m.upgrade()
    # v3 nas duas oportunidades (mesma versão entre oportunidades) e uma versão nova no legado
    for opp in (s.opp_a, s.opp_b):
        with mig.conn.begin_nested():
            _analysis(mig.conn, s.p1, opp, 3)
    with mig.conn.begin_nested():
        _analysis(mig.conn, s.p1, None, 4)
    # mesma versão em OUTRO imóvel também é aceita
    with mig.conn.begin_nested():
        _analysis(mig.conn, s.p2, None, 2)


@pytest.mark.parametrize("oportunidade", ["legado", "opp_a"])
def test_duplicidade_e_rejeitada_inclusive_no_legado_com_oportunidade_nula(mig, oportunidade):
    s = _seed_representativo(mig.conn)
    mig.m.upgrade()
    alvo = None if oportunidade == "legado" else s.opp_a
    antes = _rows(mig.conn)
    with pytest.raises(IntegrityError, match=INDEX):
        with mig.conn.begin_nested():       # savepoint: o erro não derruba a transação do teste
            _analysis(mig.conn, s.p1, alvo, 1)
    assert _rows(mig.conn) == antes


@pytest.mark.parametrize("tipo", ["legado_nulo", "mesma_oportunidade"])
def test_upgrade_falha_com_duplicidade_e_nao_altera_dados_schema_nem_alembic_version(mig, tipo):
    s = _seed_representativo(mig.conn)
    _analysis(mig.conn, s.p1, None if tipo == "legado_nulo" else s.opp_a, 1)   # duplicata preexistente (índice ausente)
    linhas, schema, versao = _rows(mig.conn), _schema(mig.conn), _alembic_version(mig.conn)

    with pytest.raises(RuntimeError, match="Migration 0024 abortada") as erro:
        mig.m.upgrade()

    mensagem = str(erro.value)
    assert f"imóvel {s.p1}" in mensagem and "versão 1" in mensagem and "Nada foi alterado" in mensagem
    assert _index_def(mig.conn) is None                  # nenhum índice criado
    assert _rows(mig.conn) == linhas                     # nada apagado nem renumerado
    assert _schema(mig.conn) == schema                   # colunas, índices e constraints idênticos
    assert _alembic_version(mig.conn) == versao
    # a transação segue utilizável (a falha foi lançada antes de qualquer DDL)
    assert mig.conn.execute(text("SELECT 1")).scalar() == 1


def test_upgrade_apos_resolver_a_duplicidade_funciona(mig):
    s = _seed_representativo(mig.conn)
    duplicata = _analysis(mig.conn, s.p1, None, 1)
    with pytest.raises(RuntimeError):
        mig.m.upgrade()
    mig.conn.execute(text("DELETE FROM analyses WHERE id = :i"), {"i": duplicata})   # resolução manual
    mig.m.upgrade()
    assert _index_def(mig.conn) is not None


def test_upgrade_e_idempotente(mig):
    _seed_representativo(mig.conn)
    mig.m.upgrade()
    definicao, schema, linhas = _index_def(mig.conn), _schema(mig.conn), _rows(mig.conn)
    mig.m.upgrade()      # índice correto já existe (reaplicação, ou criado à mão): no-op
    mig.m.upgrade()
    assert _index_def(mig.conn) == definicao and _schema(mig.conn) == schema and _rows(mig.conn) == linhas


def test_downgrade_remove_o_indice_e_preserva_os_dados(mig):
    s = _seed_representativo(mig.conn)
    mig.m.upgrade()
    linhas, versao = _rows(mig.conn), _alembic_version(mig.conn)
    mig.m.downgrade()
    assert _index_def(mig.conn) is None
    assert _rows(mig.conn) == linhas and _alembic_version(mig.conn) == versao
    mig.m.downgrade()    # repetível (DROP INDEX IF EXISTS)
    assert _index_def(mig.conn) is None
    # sem o índice, a unicidade deixa de ser imposta (nenhuma restrição residual)
    with mig.conn.begin_nested():
        _analysis(mig.conn, s.p1, None, 1)
    # e o ciclo completo volta a funcionar quando não há duplicatas
    mig.conn.execute(text("DELETE FROM analyses WHERE id = (SELECT max(id) FROM analyses)"))
    mig.m.upgrade()
    assert _index_def(mig.conn) is not None


# ----------------------------------------------------------------------------- validação do índice (homônimos)

CORRETO = f"CREATE UNIQUE INDEX {INDEX} ON analyses (property_id, (COALESCE(opportunity_id, 0)), version)"


def test_indice_correto_ja_existente_e_aceito_e_o_downgrade_o_remove(mig):
    _seed_representativo(mig.conn)
    mig.conn.exec_driver_sql(CORRETO)                      # criado à mão com a definição esperada
    definicao, schema, linhas = _index_def(mig.conn), _schema(mig.conn), _rows(mig.conn)
    mig.m.upgrade()                                        # reconhece como já aplicado
    assert _index_def(mig.conn) == definicao and _schema(mig.conn) == schema and _rows(mig.conn) == linhas
    mig.m.downgrade()
    assert _index_def(mig.conn) is None and _rows(mig.conn) == linhas


def test_indice_homonimo_em_outro_schema_nao_e_confundido_com_o_correto(mig):
    s = _seed_representativo(mig.conn)
    outro = f"s24_{uuid.uuid4().hex[:8]}"
    mig.conn.exec_driver_sql(f"CREATE SCHEMA {outro}")
    mig.conn.exec_driver_sql(f"CREATE TABLE {outro}.alheia (a int, b int)")
    mig.conn.exec_driver_sql(f"CREATE UNIQUE INDEX {INDEX} ON {outro}.alheia (a)")
    alheio = (outro, "alheia")
    assert _index_def(mig.conn) is None                    # nenhum índice em analyses ainda

    mig.m.upgrade()                                        # o homônimo alheio NÃO conta como "já aplicado"
    assert "COALESCE(opportunity_id, 0)" in _index_def(mig.conn)
    assert {(r[0], r[1]) for r in _indexes_named(mig.conn)} >= {alheio}   # e continua intacto
    with pytest.raises(IntegrityError, match=INDEX):
        with mig.conn.begin_nested():
            _analysis(mig.conn, s.p1, None, 1)             # o índice correto está de fato ativo

    # downgrade com o schema alheio NA FRENTE do search_path: remove só o índice de analyses
    mig.conn.exec_driver_sql(f"SET LOCAL search_path = {outro}, public")
    mig.m.downgrade()
    mig.conn.exec_driver_sql("SET LOCAL search_path = public")
    restantes = {(r[0], r[1]) for r in _indexes_named(mig.conn)}
    assert restantes == {alheio}, f"o downgrade só podia remover o índice de analyses: {restantes}"


@pytest.mark.parametrize("ddl,trecho", [
    (f"CREATE INDEX {INDEX} ON analyses (property_id)", "não é o esperado"),                                # não único
    (f"CREATE UNIQUE INDEX {INDEX} ON analyses (property_id, opportunity_id, version)", "não é o esperado"),  # sem o COALESCE (NULLs distintos)
    (f"CREATE UNIQUE INDEX {INDEX} ON analyses (property_id, (COALESCE(opportunity_id, 0)), version) WHERE version > 0", "não é o esperado"),  # parcial
    (f"CREATE UNIQUE INDEX {INDEX} ON analyses (version, property_id, (COALESCE(opportunity_id, 0)))", "não é o esperado"),                    # ordem errada
])
def test_indice_homonimo_com_definicao_incorreta_aborta_e_o_downgrade_o_preserva(mig, ddl, trecho):
    _seed_representativo(mig.conn)
    mig.conn.exec_driver_sql(ddl)
    definicao, schema, linhas, versao = _index_def(mig.conn), _schema(mig.conn), _rows(mig.conn), _alembic_version(mig.conn)

    with pytest.raises(RuntimeError, match="Migration 0024 abortada") as erro:
        mig.m.upgrade()
    assert trecho in str(erro.value) and "Nada foi alterado" in str(erro.value) and INDEX in str(erro.value)
    assert _index_def(mig.conn) == definicao and _schema(mig.conn) == schema        # nada mudou
    assert _rows(mig.conn) == linhas and _alembic_version(mig.conn) == versao

    mig.m.downgrade()                                      # não remove o que a 0024 não criaria
    assert _index_def(mig.conn) == definicao


def test_indice_homonimo_em_outra_tabela_do_mesmo_schema_aborta_com_erro_claro(mig):
    _seed_representativo(mig.conn)
    mig.conn.exec_driver_sql("CREATE TABLE t24_outra (a int)")
    mig.conn.exec_driver_sql(f"CREATE UNIQUE INDEX {INDEX} ON t24_outra (a)")
    antes = _indexes_named(mig.conn)
    with pytest.raises(RuntimeError, match="Migration 0024 abortada") as erro:
        mig.m.upgrade()
    assert "t24_outra" in str(erro.value) and _index_def(mig.conn) is None
    assert _indexes_named(mig.conn) == antes
    mig.m.downgrade()                                      # o índice da outra tabela é preservado
    assert _indexes_named(mig.conn) == antes


# ----------------------------------------------------------------------------- alembic real: banco novo x banco em 0023

@pytest.fixture
def banco_descartavel(postgres_engine):
    """Banco PostgreSQL novo (criado e removido pelo teste), com URL para o alembic."""
    nome = f"radar_mig24_{uuid.uuid4().hex[:8]}"
    admin = postgres_engine.execution_options(isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.exec_driver_sql(f"CREATE DATABASE {nome}")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"sem permissão para criar banco descartável: {exc}")
    url = postgres_engine.url.set(database=nome)
    engine = create_engine(url)
    try:
        yield SimpleNamespace(engine=engine, url=url.render_as_string(hide_password=False))
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.exec_driver_sql(f"DROP DATABASE IF EXISTS {nome} WITH (FORCE)")


def _alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": os.pathsep.join(filter(None, [str(root), os.environ.get("PYTHONPATH", "")]))}
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=root / "backend", env=env, capture_output=True, text=True, timeout=240)


def test_banco_novo_e_banco_existente_na_0023_com_alembic_real(banco_descartavel):
    url, engine = banco_descartavel.url, banco_descartavel.engine

    # Banco NOVO até a 0023: o índice não existe (a 0001 o perde ao remover analyses.opportunity_id).
    r = _alembic(url, "upgrade", "0023_usuarios")
    assert r.returncode == 0, r.stderr[-800:]
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"), {"n": INDEX}).scalar() == 0
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0023_usuarios"
        # Banco EXISTENTE na 0023, com dados — inclusive uma duplicidade.
        p = _insert(conn, models.Property, title="Imóvel existente", address="Rua E", city="Santos", state="SP")
        opp = _insert(conn, models.Opportunity, property_id=p)
        _analysis(conn, p, None, 1); _analysis(conn, p, None, 2); _analysis(conn, p, opp, 1)
        duplicada = _analysis(conn, p, None, 1)
        conn.commit()
        antes = _rows(conn)

    falha = _alembic(url, "upgrade", "head")      # a 0024 aborta; o alembic reverte a transação inteira
    assert falha.returncode != 0 and "Migration 0024 abortada" in (falha.stderr + falha.stdout)
    with engine.connect() as conn:
        assert _rows(conn) == antes
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0023_usuarios"
        assert conn.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = :n"), {"n": INDEX}).scalar() == 0
        conn.execute(text("DELETE FROM analyses WHERE id = :i"), {"i": duplicada}); conn.commit()
        sem_duplicata = _rows(conn)

    ok = _alembic(url, "upgrade", "head")
    assert ok.returncode == 0, ok.stderr[-800:]
    with engine.connect() as conn:
        assert _rows(conn) == sem_duplicata                                   # dados preservados
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0024_analysis_version_unique"
        definicao = _index_def(conn)
        assert definicao and "UNIQUE" in definicao and "COALESCE(opportunity_id, 0)" in definicao

    volta = _alembic(url, "downgrade", "-1")
    assert volta.returncode == 0, volta.stderr[-800:]
    with engine.connect() as conn:
        assert _index_def(conn) is None and _rows(conn) == sem_duplicata
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0023_usuarios"

    de_novo = _alembic(url, "upgrade", "head")
    assert de_novo.returncode == 0, de_novo.stderr[-800:]
    with engine.connect() as conn:
        assert _index_def(conn) == definicao
