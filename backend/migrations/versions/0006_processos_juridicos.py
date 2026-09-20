"""Campos de cadastro e rastreabilidade de processos jurídicos."""
from alembic import op
import sqlalchemy as sa

revision = "0006_processos_juridicos"
down_revision = "0005_ocupacao_historico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("legal_processes", "court", existing_type=sa.String(160), nullable=True, server_default=None)
    op.alter_column("legal_processes", "subject", existing_type=sa.String(240), nullable=True, server_default=None)
    op.alter_column("legal_processes", "status", existing_type=sa.String(80), nullable=True, server_default=None)
    op.alter_column("legal_processes", "source", existing_type=sa.String(240), nullable=True, server_default=None)
    op.alter_column("legal_processes", "impact", existing_type=sa.Text(), nullable=True, server_default=None)
    op.add_column("legal_processes", sa.Column("comarca", sa.String(160), nullable=True))
    op.add_column("legal_processes", sa.Column("nature", sa.String(120), nullable=True))
    op.add_column("legal_processes", sa.Column("polo_active", sa.Text(), nullable=True))
    op.add_column("legal_processes", sa.Column("polo_passive", sa.Text(), nullable=True))
    op.add_column("legal_processes", sa.Column("distribution_date", sa.Date(), nullable=True))
    op.add_column("legal_processes", sa.Column("observations", sa.Text(), nullable=True))
    op.add_column("legal_processes", sa.Column("evidence_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_legal_processes_evidence", "legal_processes", "evidences", ["evidence_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_legal_processes_evidence", "legal_processes", type_="foreignkey")
    for column in ("evidence_id", "observations", "distribution_date", "polo_passive", "polo_active", "nature", "comarca"):
        op.drop_column("legal_processes", column)
