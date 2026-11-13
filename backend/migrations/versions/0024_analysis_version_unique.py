"""Integridade: uma análise por (imóvel, oportunidade, versão).

Hardening de segurança/concorrência: ``create_analysis`` calcula a próxima versão com
``max(version)+1``; duas requisições simultâneas podiam gerar a MESMA versão. Esta
migration adiciona o índice único ``uq_analysis_property_opp_version`` sobre
``(property_id, COALESCE(opportunity_id, 0), version)`` como defesa em profundidade (a
serialização principal é um advisory lock em ``POST /analisar``).

Por que ``COALESCE(opportunity_id, 0)``: o domínio permite mais de uma Oportunidade por
imóvel, cada uma com sua própria sequência de análises (isolamento da Onda 1); e
``opportunity_id`` é NULL para o histórico legado — em um índice único comum, NULLs são
distintos e o legado ficaria sem proteção.

Segurança da migration:
- Banco novo: o índice NÃO existe ao chegar aqui. A 0001 monta o schema com os modelos
  atuais (que declaram o índice), mas em seguida remove ``analyses.opportunity_id`` — e o
  PostgreSQL derruba junto o índice que depende da coluna —; a 0019 recria a coluna sem o
  índice. Quem cria o índice, em banco novo e em banco existente, é esta migration.
- Idempotente e validada: se já existir um índice com esse nome NO SCHEMA da tabela
  ``analyses``, ele só é aceito se for exatamente o esperado (da tabela ``analyses``,
  único, não parcial, ``(property_id, COALESCE(opportunity_id, 0), version)``). Um índice
  homônimo com outra definição, ou em outra tabela do mesmo schema, ABORTA a migration
  com erro claro, sem alterar nada. Índices homônimos em OUTROS schemas não colidem (o
  nome é por schema) e são ignorados.
- Não destrutiva: se houver duplicidades em dados existentes, a migration ABORTA com
  mensagem clara — nunca apaga nem renumera histórico. Resolva manualmente (após
  backup) e reaplique.
- Reversível e restrita ao que criou: ``downgrade`` remove apenas o índice esperado, com
  schema qualificado, da tabela ``analyses``; nunca um homônimo de outro schema/objeto nem
  um índice com definição diferente (esse é preservado e registrado em log). Remove também
  a restrição de uma versão anterior desta migration, caso exista.

Sequência: migration ``0024`` (down_revision ``0023_usuarios``).
"""
import logging

from alembic import op
import sqlalchemy as sa

revision = "0024_analysis_version_unique"
down_revision = "0023_usuarios"
branch_labels = None
depends_on = None

INDEX = "uq_analysis_property_opp_version"
LEGACY_CONSTRAINT = "uq_analysis_property_version"
EXPECTED_TAIL = "USING btree (property_id, COALESCE(opportunity_id, 0), version)"

_log = logging.getLogger("alembic.runtime.migration")


def _analyses_schema(bind) -> str | None:
    """Schema onde a tabela ``analyses`` (a do search_path) está; ``None`` se não existir."""
    return bind.execute(sa.text(
        "SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE c.oid = to_regclass('analyses')"
    )).scalar()


def _indexes_named(bind) -> list:
    """Todos os índices chamados ``INDEX`` (em qualquer schema), com a tabela a que pertencem."""
    return list(bind.execute(sa.text(
        "SELECT n.nspname AS index_schema, tn.nspname AS table_schema, t.relname AS table_name, "
        "       i.indisunique AS is_unique, (i.indpred IS NOT NULL) AS is_partial, "
        "       pg_get_indexdef(i.indexrelid) AS definition, (i.indrelid = to_regclass('analyses')) AS on_analyses "
        "FROM pg_class c "
        "JOIN pg_index i ON i.indexrelid = c.oid "
        "JOIN pg_class t ON t.oid = i.indrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "JOIN pg_namespace tn ON tn.oid = t.relnamespace "
        "WHERE c.relname = :n AND c.relkind = 'i'"
    ), {"n": INDEX}).mappings().all())


def _is_expected(row) -> bool:
    return bool(row["on_analyses"] and row["is_unique"] and not row["is_partial"] and row["definition"].endswith(EXPECTED_TAIL))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _analyses_schema(bind)
    if schema is None:
        raise RuntimeError("Migration 0024 abortada: a tabela 'analyses' não foi encontrada. Nada foi alterado.")
    quoted_schema = bind.dialect.identifier_preparer.quote(schema)

    same_schema = [r for r in _indexes_named(bind) if r["index_schema"] == schema]
    if same_schema:
        row = same_schema[0]
        if _is_expected(row):
            return      # já aplicada (idempotente)
        raise RuntimeError(
            f"Migration 0024 abortada: já existe um índice chamado '{schema}.{INDEX}' em "
            f"{row['table_schema']}.{row['table_name']} que não é o esperado ({row['definition']}). "
            f"Esperado: índice ÚNICO, não parcial, em {schema}.analyses {EXPECTED_TAIL}. "
            "Nada foi alterado. Faça backup, remova ou renomeie esse índice manualmente e reaplique."
        )

    duplicates = bind.execute(sa.text(
        "SELECT property_id, COALESCE(opportunity_id, 0), version, count(*) FROM analyses "
        "GROUP BY property_id, COALESCE(opportunity_id, 0), version HAVING count(*) > 1"
    )).fetchall()
    if duplicates:
        sample = ", ".join(f"(imóvel {p}, oportunidade {o}, versão {v}, {c}x)" for p, o, v, c in duplicates[:5])
        raise RuntimeError(
            "Migration 0024 abortada: existem análises duplicadas por (imóvel, oportunidade, versão): "
            f"{sample}. Faça backup, resolva as duplicidades manualmente e reaplique. Nada foi alterado."
        )
    op.execute(f"CREATE UNIQUE INDEX {INDEX} ON {quoted_schema}.analyses (property_id, (COALESCE(opportunity_id, 0)), version)")


def downgrade() -> None:
    bind = op.get_bind()
    schema = _analyses_schema(bind)
    if schema is None:
        return
    quoted_schema = bind.dialect.identifier_preparer.quote(schema)

    if bind.execute(sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n AND conrelid = to_regclass('analyses')"), {"n": LEGACY_CONSTRAINT}).first():
        op.drop_constraint(LEGACY_CONSTRAINT, "analyses", type_="unique", schema=schema)

    same_schema = [r for r in _indexes_named(bind) if r["index_schema"] == schema]
    if not same_schema:
        return
    row = same_schema[0]
    if _is_expected(row):
        op.execute(f"DROP INDEX {quoted_schema}.{INDEX}")
    else:
        _log.warning(
            "Migration 0024 (downgrade): o índice '%s.%s' existe mas não é o criado por esta migration (%s); mantido.",
            schema, INDEX, row["definition"],
        )
