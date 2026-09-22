"""Preserva data + hora do 1º e 2º leilão: auctions.first/second_auction_date DATE -> TIMESTAMP."""
from alembic import op
import sqlalchemy as sa

revision = "0010_leilao_data_hora"
down_revision = "0009_cadastro_completo_imovel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Converte DATE -> TIMESTAMP preservando os valores existentes (meia-noite para
    # datas já gravadas). postgresql_using garante o cast seguro em banco existente.
    op.alter_column(
        "auctions", "first_auction_date",
        existing_type=sa.Date(), type_=sa.DateTime(), existing_nullable=True,
        postgresql_using="first_auction_date::timestamp",
    )
    op.alter_column(
        "auctions", "second_auction_date",
        existing_type=sa.Date(), type_=sa.DateTime(), existing_nullable=True,
        postgresql_using="second_auction_date::timestamp",
    )


def downgrade() -> None:
    op.alter_column(
        "auctions", "first_auction_date",
        existing_type=sa.DateTime(), type_=sa.Date(), existing_nullable=True,
        postgresql_using="first_auction_date::date",
    )
    op.alter_column(
        "auctions", "second_auction_date",
        existing_type=sa.DateTime(), type_=sa.Date(), existing_nullable=True,
        postgresql_using="second_auction_date::date",
    )
