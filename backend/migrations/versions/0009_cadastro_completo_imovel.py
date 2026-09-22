"""Cadastro completo do imóvel de leilão: dados físicos, origem, 1º/2º leilão, item do edital e fontes."""
from alembic import op
import sqlalchemy as sa

revision = "0009_cadastro_completo_imovel"
down_revision = "0008_extracao_documental"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # properties: dados físicos e identificação na origem
    op.add_column("properties", sa.Column("neighborhood", sa.String(120)))
    op.add_column("properties", sa.Column("private_area_m2", sa.Numeric(12, 2)))
    op.add_column("properties", sa.Column("parking_spots", sa.Integer()))
    op.add_column("properties", sa.Column("description", sa.Text()))
    op.add_column("properties", sa.Column("origin", sa.String(120)))
    op.add_column("properties", sa.Column("origin_property_code", sa.String(80)))
    op.add_column("properties", sa.Column("inscription", sa.String(80)))
    op.add_column("properties", sa.Column("modality", sa.String(80)))
    op.add_column("properties", sa.Column("system", sa.String(40)))

    # auctions: 1º e 2º leilão preservados separadamente
    op.add_column("auctions", sa.Column("first_auction_date", sa.Date()))
    op.add_column("auctions", sa.Column("first_auction_value", sa.Numeric(14, 2)))
    op.add_column("auctions", sa.Column("second_auction_date", sa.Date()))
    op.add_column("auctions", sa.Column("second_auction_value", sa.Numeric(14, 2)))

    # auction_notices: item do edital
    op.add_column("auction_notices", sa.Column("item", sa.String(40)))

    # nova tabela de fontes oficiais / links
    op.create_table(
        "property_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False, server_default="OUTRA"),
        sa.Column("url", sa.String(600)),
        sa.Column("description", sa.String(240)),
        sa.Column("origin", sa.String(120)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_property_sources_property_id", "property_sources", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_property_sources_property_id", table_name="property_sources")
    op.drop_table("property_sources")
    op.drop_column("auction_notices", "item")
    op.drop_column("auctions", "second_auction_value")
    op.drop_column("auctions", "second_auction_date")
    op.drop_column("auctions", "first_auction_value")
    op.drop_column("auctions", "first_auction_date")
    op.drop_column("properties", "system")
    op.drop_column("properties", "modality")
    op.drop_column("properties", "inscription")
    op.drop_column("properties", "origin_property_code")
    op.drop_column("properties", "origin")
    op.drop_column("properties", "description")
    op.drop_column("properties", "parking_spots")
    op.drop_column("properties", "private_area_m2")
    op.drop_column("properties", "neighborhood")
