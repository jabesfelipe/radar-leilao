"""Cadastro estruturado de matrícula e edital."""
from alembic import op
import sqlalchemy as sa

revision = "0007_matricula_edital"
down_revision = "0006_processos_juridicos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("property_registrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("registration_number", sa.String(80), nullable=False),
        sa.Column("registry_office", sa.String(160)), sa.Column("comarca", sa.String(160)),
        sa.Column("consultation_date", sa.Date()), sa.Column("holder", sa.String(240)),
        sa.Column("observations", sa.Text()), sa.Column("document_version_id", sa.Integer(), sa.ForeignKey("document_versions.id")),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidences.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_property_registrations_property_id", "property_registrations", ["property_id"])
    op.create_table("auction_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("identifier", sa.String(160), nullable=False), sa.Column("notice_date", sa.Date()),
        sa.Column("auction_stage", sa.String(80)), sa.Column("appraisal_value", sa.Numeric(14, 2)),
        sa.Column("minimum_value", sa.Numeric(14, 2)), sa.Column("auction_date", sa.Date()),
        sa.Column("auctioneer", sa.String(160)), sa.Column("observations", sa.Text()),
        sa.Column("document_version_id", sa.Integer(), sa.ForeignKey("document_versions.id")),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidences.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_auction_notices_property_id", "auction_notices", ["property_id"])


def downgrade() -> None:
    op.drop_index("ix_auction_notices_property_id", table_name="auction_notices")
    op.drop_table("auction_notices")
    op.drop_index("ix_property_registrations_property_id", table_name="property_registrations")
    op.drop_table("property_registrations")
