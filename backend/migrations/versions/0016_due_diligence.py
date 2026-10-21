"""Due Diligence integrada (novo): due_diligence_fronts, property_locations.

Evolução reuse-first: NÃO duplica matrícula (PropertyRegistration), processos
(LegalProcess), débitos (Debt) nem eventos (DomainEvent/EntityHistory). As novas
tabelas guardam apenas (1) o ESTADO/rastreabilidade da investigação por frente e
(2) a geolocalização + checklist de localização (que não têm casa hoje). Reversível
e sem tocar em dados existentes (apenas novas tabelas, tudo nullable exceto PKs/
colunas com default).
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_due_diligence"
down_revision = "0015_pos_arrematacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "due_diligence_fronts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("frente", sa.String(length=30), nullable=False, index=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="NAO_INICIADO"),
        sa.Column("source", sa.String(length=240), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=True),
        sa.Column("last_consulted_at", sa.DateTime(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("pendencias", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("property_id", "frente", name="uq_dd_front_property_frente"),
    )
    op.create_table(
        "property_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True, unique=True),
        sa.Column("normalized_address", sa.String(length=400), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("geocode_precision", sa.String(length=40), nullable=True),
        sa.Column("geocode_source", sa.String(length=120), nullable=True),
        sa.Column("geocoded_at", sa.DateTime(), nullable=True),
        sa.Column("coordinates_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("maps_url", sa.String(length=600), nullable=True),
        sa.Column("street_view_url", sa.String(length=600), nullable=True),
        sa.Column("location_checklist", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("inspected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("property_locations")
    op.drop_table("due_diligence_fronts")
