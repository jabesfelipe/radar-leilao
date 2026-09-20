"""Permite ausência explícita de identificadores na extração documental."""
from alembic import op
import sqlalchemy as sa

revision = "0008_extracao_documental"
down_revision = "0007_matricula_edital"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("property_registrations", "registration_number", existing_type=sa.String(80), nullable=True)
    op.alter_column("auction_notices", "identifier", existing_type=sa.String(160), nullable=True)


def downgrade() -> None:
    op.alter_column("property_registrations", "registration_number", existing_type=sa.String(80), nullable=False)
    op.alter_column("auction_notices", "identifier", existing_type=sa.String(160), nullable=False)
