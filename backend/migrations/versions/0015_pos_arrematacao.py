"""Módulo Pós-Arrematação (novo): post_auctions, post_auction_stages,
post_auction_costs, occupant_contacts, contact_attempts, consultancies,
consultancy_proposals, notification_drafts, notification_draft_versions.

Acompanha a execução real do investimento após a arrematação, vinculado ao imóvel
existente. Reuso: a etapa de ação judicial referencia legal_processes (FK opcional);
custos pós têm semântica previsto/realizado/pago SEPARADA do modelo Cost da análise
inicial (não sobrescreve o financeiro histórico). Reversível e sem tocar em dados
existentes (apenas novas tabelas, tudo nullable exceto PKs/colunas com default).
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_pos_arrematacao"
down_revision = "0014_leiloeiros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_auctions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True, unique=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="EM_ANDAMENTO"),
        sa.Column("current_stage", sa.String(length=120), nullable=True),
        sa.Column("eviction_mode", sa.String(length=30), nullable=True),
        sa.Column("initial_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("expected_sale_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "post_auction_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("stage_key", sa.String(length=60), nullable=False, index=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDENTE"),
        sa.Column("responsible", sa.String(length=160), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("legal_process_id", sa.Integer(), sa.ForeignKey("legal_processes.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "post_auction_costs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=True),
        sa.Column("planned_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("actual_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PREVISTO"),
        sa.Column("competence_date", sa.Date(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("supplier", sa.String(length=200), nullable=True),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("origin", sa.String(length=120), nullable=True),
        sa.Column("document_version_id", sa.Integer(), sa.ForeignKey("document_versions.id"), nullable=True),
        sa.Column("stage_id", sa.Integer(), sa.ForeignKey("post_auction_stages.id"), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "occupant_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("contact_type", sa.String(length=80), nullable=True),
        sa.Column("relationship_label", sa.String(length=120), nullable=True),
        sa.Column("next_action", sa.String(length=240), nullable=True),
        sa.Column("next_action_date", sa.Date(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "contact_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("occupant_contacts.id"), nullable=False, index=True),
        sa.Column("attempt_date", sa.Date(), nullable=True),
        sa.Column("channel", sa.String(length=60), nullable=True),
        sa.Column("result", sa.String(length=240), nullable=True),
        sa.Column("next_action", sa.String(length=240), nullable=True),
        sa.Column("next_action_date", sa.Date(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "consultancies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("cnpj", sa.String(length=40), nullable=True),
        sa.Column("responsible", sa.String(length=160), nullable=True),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("services", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="EM_AVALIACAO"),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "consultancy_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consultancy_id", sa.Integer(), sa.ForeignKey("consultancies.id"), nullable=False, index=True),
        sa.Column("title", sa.String(length=200), nullable=False, server_default="Proposta"),
        sa.Column("fixed_fee", sa.Numeric(14, 2), nullable=True),
        sa.Column("variable_fee", sa.String(length=240), nullable=True),
        sa.Column("additional_costs", sa.Numeric(14, 2), nullable=True),
        sa.Column("payment_schedule", sa.Text(), nullable=True),
        sa.Column("included_scope", sa.Text(), nullable=True),
        sa.Column("excluded_scope", sa.Text(), nullable=True),
        sa.Column("deadline_days", sa.Integer(), nullable=True),
        sa.Column("document_version_id", sa.Integer(), sa.ForeignKey("document_versions.id"), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "notification_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False, index=True),
        sa.Column("template_key", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("recipient", sa.String(length=200), nullable=True),
        sa.Column("notifier", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="RASCUNHO"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delivery_channel", sa.String(length=80), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("receipt_status", sa.String(length=60), nullable=True),
        sa.Column("receipt_reference", sa.String(length=240), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "notification_draft_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("notification_drafts.id"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="RASCUNHO"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("draft_id", "version", name="uq_notification_draft_version"),
    )


def downgrade() -> None:
    op.drop_table("notification_draft_versions")
    op.drop_table("notification_drafts")
    op.drop_table("consultancy_proposals")
    op.drop_table("consultancies")
    op.drop_table("contact_attempts")
    op.drop_table("occupant_contacts")
    op.drop_table("post_auction_costs")
    op.drop_table("post_auction_stages")
    op.drop_table("post_auctions")
