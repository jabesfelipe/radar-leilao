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
- Idempotente: o índice também é criado pela migration 0001 (que usa os modelos atuais)
  em bancos novos; aqui só é criado se ainda não existir.
- Não destrutiva: se houver duplicidades em dados existentes, a migration ABORTA com
  mensagem clara — nunca apaga nem renumera histórico. Resolva manualmente (após
  backup) e reaplique.
- Reversível: ``downgrade`` remove o índice (e a restrição de uma versão anterior desta
  migration, caso exista).

Sequência: migration ``0024`` (down_revision ``0023_usuarios``).
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_analysis_version_unique"
down_revision = "0023_usuarios"
branch_labels = None
depends_on = None

INDEX = "uq_analysis_property_opp_version"
LEGACY_CONSTRAINT = "uq_analysis_property_version"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"), {"n": INDEX}).first():
        return
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
    op.execute(f"CREATE UNIQUE INDEX {INDEX} ON analyses (property_id, (COALESCE(opportunity_id, 0)), version)")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": LEGACY_CONSTRAINT}).first():
        op.drop_constraint(LEGACY_CONSTRAINT, "analyses", type_="unique")
    op.execute(f"DROP INDEX IF EXISTS {INDEX}")
