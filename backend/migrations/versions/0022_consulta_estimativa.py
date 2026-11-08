"""Consulta de débito (debt_queries) + estimativa condominial (condominium_estimates).

Etapas C e E da Central de Débitos. Tabelas ADITIVAS e reversíveis (folhas); não
tocam nada da Etapa A/B nem o motor financeiro. ``opportunity_id`` NULLABLE (Gate 1).
Sem backfill. Nenhuma consulta externa é executada — ``debt_queries`` apenas registra
a execução (manual/assistida) e sua rastreabilidade.

Sequência: migration ``0022`` (down_revision ``0021_cobertura_municipal``).
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_consulta_estimativa"
down_revision = "0021_cobertura_municipal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debt_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=True),
        sa.Column("municipality_id", sa.Integer(), sa.ForeignKey("municipalities.id"), nullable=True),
        sa.Column("debt_type_code", sa.String(length=60), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="manual_assistida"),
        sa.Column("provider_version", sa.String(length=40), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDENTE"),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("debt_sources.id"), nullable=True),
        sa.Column("identifier", sa.String(length=160), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("debt_id", sa.Integer(), sa.ForeignKey("property_debts.id"), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidences.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_debt_queries_property_id", "debt_queries", ["property_id"])
    op.create_index("ix_debt_queries_opportunity_id", "debt_queries", ["opportunity_id"])
    op.create_index("ix_debt_queries_municipality_id", "debt_queries", ["municipality_id"])
    op.create_index("ix_debt_queries_debt_type_code", "debt_queries", ["debt_type_code"])
    op.create_index("ix_debt_queries_status", "debt_queries", ["status"])
    op.create_index("ix_debt_queries_property_status", "debt_queries", ["property_id", "status"])

    op.create_table(
        "condominium_estimates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=True),
        sa.Column("monthly_reference", sa.Numeric(14, 2), nullable=True),
        sa.Column("monthly_source", sa.String(length=20), nullable=False, server_default="ESTIMADO"),
        sa.Column("months_delinquent", sa.Integer(), nullable=True),
        sa.Column("safety_margin_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("property_age_years", sa.Integer(), nullable=True),
        sa.Column("condominium_age_years", sa.Integer(), nullable=True),
        sa.Column("financing_age_years", sa.Integer(), nullable=True),
        sa.Column("scenario_conservador", sa.Numeric(14, 2), nullable=True),
        sa.Column("scenario_provavel", sa.Numeric(14, 2), nullable=True),
        sa.Column("scenario_otimista", sa.Numeric(14, 2), nullable=True),
        sa.Column("confidence", sa.String(length=10), nullable=False, server_default="BAIXA"),
        sa.Column("assumptions", sa.JSON(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidences.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_condominium_estimates_property_id", "condominium_estimates", ["property_id"])
    op.create_index("ix_condominium_estimates_opportunity_id", "condominium_estimates", ["opportunity_id"])


def downgrade() -> None:
    op.drop_index("ix_condominium_estimates_opportunity_id", table_name="condominium_estimates")
    op.drop_index("ix_condominium_estimates_property_id", table_name="condominium_estimates")
    op.drop_table("condominium_estimates")

    for idx in ("ix_debt_queries_property_status", "ix_debt_queries_status", "ix_debt_queries_debt_type_code",
                "ix_debt_queries_municipality_id", "ix_debt_queries_opportunity_id", "ix_debt_queries_property_id"):
        op.drop_index(idx, table_name="debt_queries")
    op.drop_table("debt_queries")
