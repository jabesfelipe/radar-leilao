"""Rastreabilidade de uso e pricing das execuções LLM.

Revision ID: 0002_llm_usage_pricing
Revises: 0001_fundacao_radar
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_llm_usage_pricing"
down_revision = "0001_fundacao_radar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("llm_runs", "input_tokens", existing_type=sa.Integer(), nullable=True, server_default=None)
    op.alter_column("llm_runs", "output_tokens", existing_type=sa.Integer(), nullable=True, server_default=None)
    op.add_column("llm_runs", sa.Column("total_tokens", sa.Integer(), nullable=True))
    op.add_column("llm_runs", sa.Column("input_cost", sa.Numeric(14, 8), nullable=True))
    op.add_column("llm_runs", sa.Column("output_cost", sa.Numeric(14, 8), nullable=True))
    op.add_column("llm_runs", sa.Column("total_cost", sa.Numeric(14, 8), nullable=True))
    op.add_column("llm_runs", sa.Column("input_price_per_1m", sa.Numeric(14, 8), nullable=True))
    op.add_column("llm_runs", sa.Column("output_price_per_1m", sa.Numeric(14, 8), nullable=True))
    op.add_column("llm_runs", sa.Column("request_id", sa.String(240), nullable=True))
    op.add_column("llm_runs", sa.Column("error_type", sa.String(120), nullable=True))
    op.add_column("llm_runs", sa.Column("error_message", sa.Text(), nullable=True))
    pricing = op.create_table(
        "llm_pricing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("input_price_per_1m", sa.Numeric(14, 8), nullable=False, server_default="0"),
        sa.Column("output_price_per_1m", sa.Numeric(14, 8), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "model", name="uq_llm_pricing_provider_model"),
    )
    op.bulk_insert(pricing, [{"provider": "openai", "model": "gpt-4o-mini", "input_price_per_1m": 0.15, "output_price_per_1m": 0.60, "currency": "USD", "active": True}])


def downgrade() -> None:
    op.drop_table("llm_pricing")
    for column in ("error_message", "error_type", "request_id", "output_price_per_1m", "input_price_per_1m", "total_cost", "output_cost", "input_cost", "total_tokens"):
        op.drop_column("llm_runs", column)
    op.alter_column("llm_runs", "input_tokens", existing_type=sa.Integer(), nullable=False, server_default="0")
    op.alter_column("llm_runs", "output_tokens", existing_type=sa.Integer(), nullable=False, server_default="0")
