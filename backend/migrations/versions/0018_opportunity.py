"""Domínio de Oportunidade + Workflow (Ciclo 2 — Onda 1).

Cria as três tabelas novas do domínio de oportunidade:
  - opportunities          (Property 1:N Opportunity)
  - opportunity_workflows  (1:1 com Opportunity; estado vivo do workflow)
  - workflow_transitions   (append-only; trilha imutável de transições)

Tudo ADITIVO (apenas novas tabelas; nenhuma coluna/dado existente é tocado) e
totalmente reversível. Sem backfill (Gate 2 não autorizado). A associação de
registros legados vem na 0019 (coluna opportunity_id NULLABLE); aqui só o
arcabouço do novo domínio.
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_opportunity"
down_revision = "0017_central_juridica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("codigo", sa.String(length=120), nullable=True),
        sa.Column("modality", sa.String(length=40), nullable=False, server_default="INDEFINIDO"),
        sa.Column("modality_evidence_id", sa.Integer(), sa.ForeignKey("evidences.id"), nullable=True),
        sa.Column("origin", sa.String(length=120), nullable=True),
        sa.Column("portal", sa.String(length=120), nullable=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="EM_PROSPECCAO"),
        sa.Column("is_legacy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("close_reason", sa.String(length=240), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False, server_default="sistema"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_opportunities_property_id", "opportunities", ["property_id"])
    op.create_index("ix_opportunities_modality", "opportunities", ["modality"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])
    op.create_index("ix_opportunities_is_legacy", "opportunities", ["is_legacy"])
    op.create_index("ix_opportunities_property_status", "opportunities", ["property_id", "status"])

    op.create_table(
        "opportunity_workflows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("current_phase", sa.String(length=40), nullable=False, server_default="F0_INTAKE"),
        sa.Column("phase_states", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("active_hard_stops", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("ruleset_version", sa.String(length=40), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by", sa.String(length=120), nullable=False, server_default="sistema"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    # UNIQUE (1:1) via índice único — espelha `unique=True, index=True` no modelo.
    op.create_index("ix_opportunity_workflows_opportunity_id", "opportunity_workflows", ["opportunity_id"], unique=True)
    op.create_index("ix_opportunity_workflows_current_phase", "opportunity_workflows", ["current_phase"])
    op.create_index("ix_opportunity_workflows_blocked", "opportunity_workflows", ["blocked"])

    op.create_table(
        "workflow_transitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("from_phase", sa.String(length=40), nullable=True),
        sa.Column("to_phase", sa.String(length=40), nullable=False),
        sa.Column("transition_type", sa.String(length=30), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("phase_state", sa.String(length=30), nullable=False),
        sa.Column("hard_stops", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("gate_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("score_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("decision", sa.String(length=30), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False, server_default="sistema"),
        sa.Column("ruleset_version", sa.String(length=40), nullable=True),
        sa.Column("cause_event_id", sa.Integer(), sa.ForeignKey("domain_events.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_transitions_opportunity_id", "workflow_transitions", ["opportunity_id"])
    op.create_index("ix_workflow_transitions_transition_type", "workflow_transitions", ["transition_type"])
    op.create_index("ix_workflow_transitions_opportunity_to_phase", "workflow_transitions", ["opportunity_id", "to_phase"])


def downgrade() -> None:
    op.drop_index("ix_workflow_transitions_opportunity_to_phase", table_name="workflow_transitions")
    op.drop_index("ix_workflow_transitions_transition_type", table_name="workflow_transitions")
    op.drop_index("ix_workflow_transitions_opportunity_id", table_name="workflow_transitions")
    op.drop_table("workflow_transitions")

    op.drop_index("ix_opportunity_workflows_blocked", table_name="opportunity_workflows")
    op.drop_index("ix_opportunity_workflows_current_phase", table_name="opportunity_workflows")
    op.drop_index("ix_opportunity_workflows_opportunity_id", table_name="opportunity_workflows")
    op.drop_table("opportunity_workflows")

    op.drop_index("ix_opportunities_property_status", table_name="opportunities")
    op.drop_index("ix_opportunities_is_legacy", table_name="opportunities")
    op.drop_index("ix_opportunities_status", table_name="opportunities")
    op.drop_index("ix_opportunities_modality", table_name="opportunities")
    op.drop_index("ix_opportunities_property_id", table_name="opportunities")
    op.drop_table("opportunities")
