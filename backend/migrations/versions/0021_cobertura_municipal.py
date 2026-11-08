"""Cobertura municipal por tipo de débito (Etapa B).

Cria a tabela ADITIVA ``municipality_coverage`` — a matriz operacional de cobertura
município × tipo de débito. Independente por combinação; vive como DADO (não há
condicional fixa no código). Não toca ``Debt``/``Cost``/``PropertyDebt``/``debt_sources``
(Etapa A), que permanecem intactos. Sem backfill (Gate 2 não autorizado). Totalmente
reversível (drop simples; a tabela é folha).

Sequência: esta é a migration ``0021`` (down_revision ``0020_central_debitos``).
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_cobertura_municipal"
down_revision = "0020_central_debitos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipality_coverage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("municipality_id", sa.Integer(), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("debt_type_code", sa.String(length=60), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False, server_default="NAO_INVESTIGADA"),
        sa.Column("situation", sa.String(length=30), nullable=False, server_default="NAO_INVESTIGADA"),
        sa.Column("method", sa.String(length=30), nullable=False, server_default="INDEFINIDO"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("debt_sources.id"), nullable=True),
        sa.Column("identifier_required", sa.String(length=160), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("municipality_id", "debt_type_code", name="uq_coverage_municipality_type"),
    )
    op.create_index("ix_municipality_coverage_municipality_id", "municipality_coverage", ["municipality_id"])
    op.create_index("ix_municipality_coverage_debt_type_code", "municipality_coverage", ["debt_type_code"])
    op.create_index("ix_municipality_coverage_level", "municipality_coverage", ["level"])
    op.create_index("ix_municipality_coverage_active", "municipality_coverage", ["active"])
    op.create_index("ix_coverage_municipality_type", "municipality_coverage", ["municipality_id", "debt_type_code"])


def downgrade() -> None:
    for idx in ("ix_coverage_municipality_type", "ix_municipality_coverage_active",
                "ix_municipality_coverage_level", "ix_municipality_coverage_debt_type_code",
                "ix_municipality_coverage_municipality_id"):
        op.drop_index(idx, table_name="municipality_coverage")
    op.drop_table("municipality_coverage")
