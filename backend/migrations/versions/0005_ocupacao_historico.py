"""Preserva ausência de custo/prazo na ocupação."""
from alembic import op
import sqlalchemy as sa

revision = "0005_ocupacao_historico"
down_revision = "0004_financeiro_entradas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("occupancy_analyses", "estimated_cost", existing_type=sa.Numeric(14, 2), nullable=True, server_default=None)
    op.alter_column("occupancy_analyses", "estimated_months", existing_type=sa.Integer(), nullable=True, server_default=None)


def downgrade() -> None:
    op.execute("UPDATE occupancy_analyses SET estimated_cost = 0 WHERE estimated_cost IS NULL")
    op.execute("UPDATE occupancy_analyses SET estimated_months = 0 WHERE estimated_months IS NULL")
    op.alter_column("occupancy_analyses", "estimated_cost", existing_type=sa.Numeric(14, 2), nullable=False, server_default="0")
    op.alter_column("occupancy_analyses", "estimated_months", existing_type=sa.Integer(), nullable=False, server_default="0")
