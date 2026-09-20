"""Checklist Mestre configurável, versionado e rastreável.

Revision ID: 0003_checklist_mestre
Revises: 0002_llm_usage_pricing
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_checklist_mestre"
down_revision = "0002_llm_usage_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checklist_items", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("checklist_items", sa.Column("domain", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("checklist_items", sa.Column("expected_evidence", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("checklist_items", sa.Column("potential_impact", sa.Text(), nullable=True))
    op.add_column("checklist_items", sa.Column("related_rules", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("checklist_items", sa.Column("agents", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("checklist_items", sa.Column("risk_categories", sa.JSON(), nullable=False, server_default="[]"))
    op.execute("UPDATE checklist_items SET description = question, domain = json_build_array(category, 'CHECKLIST'), risk_categories = json_build_array(category) WHERE description IS NULL")
    op.add_column("checklist_results", sa.Column("item_version", sa.Integer(), nullable=True))
    op.add_column("checklist_results", sa.Column("applicable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("checklist_results", sa.Column("previous_result_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_checklist_results_previous", "checklist_results", "checklist_results", ["previous_result_id"], ["id"])
    op.execute("UPDATE checklist_results r SET item_version = i.version FROM checklist_items i WHERE r.checklist_item_id = i.id")
    op.alter_column("checklist_results", "item_version", nullable=False)
    op.alter_column("domain_events", "property_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("entity_history", "property_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("entity_history", "property_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("domain_events", "property_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("fk_checklist_results_previous", "checklist_results", type_="foreignkey")
    op.drop_column("checklist_results", "previous_result_id")
    op.drop_column("checklist_results", "applicable")
    op.drop_column("checklist_results", "item_version")
    for column in ("risk_categories", "agents", "related_rules", "potential_impact", "expected_evidence", "domain", "description"):
        op.drop_column("checklist_items", column)
