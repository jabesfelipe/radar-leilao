"""Premissas financeiras por imóvel: auctions.financial_assumptions (JSON).

Adiciona uma única coluna JSON nullable ao Auction para persistir as premissas
financeiras correntes (meta de preço máximo, corretagem, tributo na venda, valor
de venda estimado, prazo, carregamento mensal e premissas de cenários). Reversível
e sem tocar em dados existentes (coluna nullable, default nulo).
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_premissas_financeiras"
down_revision = "0011_judicial_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auctions", sa.Column("financial_assumptions", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("auctions", "financial_assumptions")
