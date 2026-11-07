"""Coluna opportunity_id NULLABLE nas 9 tabelas de trabalho (Ciclo 2 — Onda 1).

Adiciona `opportunity_id` (FK -> opportunities.id, **NULLABLE**, sem default,
sem alterar cascade) nas 9 tabelas da matriz de impacto (MATRIZ-OPPORTUNITY-ID):
  auctions, auction_notices, analyses, verdicts, financial_analyses,
  checklist_executions, risks, due_diligence_fronts, post_auctions.

`NULL` = oportunidade legada implícita do imóvel (comportamento idêntico ao
atual). **Sem backfill** (Gate 2 não autorizado): nenhum registro existente é
alterado. `post_auctions.property_id UNIQUE` é preservado (Gate 1, opção A):
opportunity_id entra apenas para rastreabilidade, sem nova constraint de
unicidade. costs/debts ficam de fora (decisão do épico financeiro).

Puramente estrutural e aditivo; reversível (drop_column no downgrade).
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_opportunity_fk"
down_revision = "0018_opportunity"
branch_labels = None
depends_on = None

# (tabela, nome do índice) — as 9 tabelas da matriz.
TABLES = (
    "auctions",
    "auction_notices",
    "analyses",
    "verdicts",
    "financial_analyses",
    "checklist_executions",
    "risks",
    "due_diligence_fronts",
    "post_auctions",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("opportunity_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_opportunity_id",
            table,
            "opportunities",
            ["opportunity_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_opportunity_id", table, ["opportunity_id"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_opportunity_id", table_name=table)
        op.drop_constraint(f"fk_{table}_opportunity_id", table, type_="foreignkey")
        op.drop_column(table, "opportunity_id")
