"""Entradas determinísticas do motor financeiro."""
from alembic import op
import sqlalchemy as sa

revision = "0004_financeiro_entradas"
down_revision = "0003_checklist_mestre"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auctions", sa.Column("acquisition_value", sa.Numeric(14, 2), nullable=True))
    op.add_column("auctions", sa.Column("commission_percent", sa.Numeric(8, 4), nullable=True))
    op.add_column("auctions", sa.Column("commission_fixed", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("auctions", "commission_fixed")
    op.drop_column("auctions", "commission_percent")
    op.drop_column("auctions", "acquisition_value")
