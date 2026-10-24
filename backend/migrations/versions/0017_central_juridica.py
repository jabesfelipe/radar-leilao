"""Central Jurídica (novo): legal_sources, legal_provisions, legal_rules,
legal_rule_checklist_links.

Camada transversal de conhecimento jurídico (reuse-first). NÃO duplica:
  - busca semântica → reaproveita KnowledgeItem (kind=LEGAL_LIBRARY) + RAG;
  - evidências → Evidence/EvidenceLink;
  - rastreabilidade → DomainEvent/EntityHistory;
  - o Checklist Mestre (27 canonical_key) permanece intacto — o vínculo
    legal_rule_checklist_links ENRIQUECE os itens por canonical_key (string),
    sem alterar CHECKLIST_MASTER.

Tudo aditivo (apenas novas tabelas, nenhuma coluna/dado existente é tocado) e
totalmente reversível.
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_central_juridica"
down_revision = "0016_due_diligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False, index=True),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("authority", sa.String(length=160), nullable=True),
        sa.Column("official_url", sa.String(length=600), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("in_force", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="PENDENTE"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_legal_source_slug"),
    )
    op.create_index("ix_legal_sources_slug", "legal_sources", ["slug"], unique=True)

    op.create_table(
        "legal_provisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("legal_sources.id"), nullable=False, index=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("reference", sa.String(length=160), nullable=False),
        sa.Column("heading", sa.String(length=300), nullable=True),
        sa.Column("official_text", sa.Text(), nullable=True),
        sa.Column("practical_note", sa.Text(), nullable=True),
        sa.Column("contexts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="PENDENTE"),
        sa.Column("knowledge_item_id", sa.Integer(), sa.ForeignKey("knowledge_items.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_legal_provision_slug"),
    )
    op.create_index("ix_legal_provisions_slug", "legal_provisions", ["slug"], unique=True)

    op.create_table(
        "legal_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("rule_kind", sa.String(length=30), nullable=False, index=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("contexts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("provision_id", sa.Integer(), sa.ForeignKey("legal_provisions.id"), nullable=True, index=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_legal_rule_slug"),
    )
    op.create_index("ix_legal_rules_slug", "legal_rules", ["slug"], unique=True)

    op.create_table(
        "legal_rule_checklist_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("legal_rules.id"), nullable=False, index=True),
        sa.Column("canonical_key", sa.String(length=80), nullable=False, index=True),
        sa.Column("relevance", sa.String(length=20), nullable=False, server_default="PRINCIPAL"),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("rule_id", "canonical_key", name="uq_legal_rule_checklist"),
    )


def downgrade() -> None:
    op.drop_table("legal_rule_checklist_links")
    op.drop_index("ix_legal_rules_slug", table_name="legal_rules")
    op.drop_table("legal_rules")
    op.drop_index("ix_legal_provisions_slug", table_name="legal_provisions")
    op.drop_table("legal_provisions")
    op.drop_index("ix_legal_sources_slug", table_name="legal_sources")
    op.drop_table("legal_sources")
