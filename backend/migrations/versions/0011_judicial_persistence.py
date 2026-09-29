"""Persistência PostgreSQL da Judicial API: tabelas judicial_*.

Cria as tabelas do módulo Judicial API no MESMO banco do Radar (schema public,
prefixo ``judicial_``), sem tocar em nenhuma tabela existente do Radar. Totalmente
reversível: ``downgrade`` remove apenas as tabelas judicial_*.

Chaves e constraints de idempotência (evitam duplicação no retry):
- judicial_searches.search_id UNIQUE;
- judicial_search_sources UNIQUE(search_pk, tribunal);
- judicial_processes UNIQUE(search_pk, tribunal, process_number).
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_judicial_persistence"
down_revision = "0010_leilao_data_hora"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "judicial_searches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_id", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(120), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("request_json", sa.JSON(), nullable=True),
        sa.Column("completeness_json", sa.JSON(), nullable=True),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("reanalyze_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_judicial_searches_search_id", "judicial_searches", ["search_id"])
    op.create_index("ix_judicial_searches_search_id", "judicial_searches", ["search_id"])
    op.create_index("ix_judicial_searches_request_hash", "judicial_searches", ["request_hash"])

    op.create_table(
        "judicial_search_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_pk", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("tribunal", sa.String(40), nullable=False),
        sa.Column("justice_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["search_pk"], ["judicial_searches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("search_pk", "tribunal", name="uq_judicial_source_search_tribunal"),
    )
    op.create_index("ix_judicial_search_sources_search_pk", "judicial_search_sources", ["search_pk"])

    op.create_table(
        "judicial_processes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_pk", sa.Integer(), nullable=False),
        sa.Column("process_number", sa.String(60), nullable=False),
        sa.Column("tribunal", sa.String(40), nullable=False),
        sa.Column("justice_type", sa.String(20), nullable=False),
        sa.Column("jurisdiction", sa.String(120), nullable=True),
        sa.Column("court", sa.String(240), nullable=True),
        sa.Column("class_code", sa.String(40), nullable=True),
        sa.Column("class_name", sa.String(240), nullable=True),
        sa.Column("priority_json", sa.JSON(), nullable=True),
        sa.Column("electronic", sa.Boolean(), nullable=True),
        sa.Column("last_movement_at", sa.String(40), nullable=True),
        sa.Column("source_identifier", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(["search_pk"], ["judicial_searches.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "search_pk", "tribunal", "process_number",
            name="uq_judicial_process_search_tribunal_number",
        ),
    )
    op.create_index("ix_judicial_processes_search_pk", "judicial_processes", ["search_pk"])

    op.create_table(
        "judicial_process_parties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_pk", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("document", sa.String(40), nullable=True),
        sa.Column("document_type", sa.String(10), nullable=True),
        sa.Column("role", sa.String(60), nullable=True),
        sa.Column("party_type", sa.String(20), nullable=True),
        sa.Column("representation", sa.Text(), nullable=True),
        sa.Column("source_identifier", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(["process_pk"], ["judicial_processes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_judicial_process_parties_process_pk", "judicial_process_parties", ["process_pk"])

    op.create_table(
        "judicial_process_subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_pk", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(40), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("source_identifier", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(["process_pk"], ["judicial_processes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_judicial_process_subjects_process_pk", "judicial_process_subjects", ["process_pk"])

    op.create_table(
        "judicial_process_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("process_pk", sa.Integer(), nullable=False),
        sa.Column("movement_date", sa.String(40), nullable=True),
        sa.Column("code", sa.String(40), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("complement", sa.Text(), nullable=True),
        sa.Column("source_identifier", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(["process_pk"], ["judicial_processes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_judicial_process_movements_process_pk", "judicial_process_movements", ["process_pk"])

    op.create_table(
        "judicial_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_pk", sa.Integer(), nullable=False),
        sa.Column("signal_code", sa.String(60), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("process_number", sa.String(60), nullable=True),
        sa.Column("tribunal", sa.String(40), nullable=True),
        sa.Column("source_identifier", sa.String(120), nullable=True),
        sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["search_pk"], ["judicial_searches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_judicial_signals_search_pk", "judicial_signals", ["search_pk"])

    op.create_table(
        "judicial_search_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("search_pk", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("tribunal", sa.String(40), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=True),
        sa.Column("at", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["search_pk"], ["judicial_searches.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_judicial_event_search_pk", "judicial_search_events", ["search_pk"])


def downgrade() -> None:
    op.drop_table("judicial_search_events")
    op.drop_table("judicial_signals")
    op.drop_table("judicial_process_movements")
    op.drop_table("judicial_process_subjects")
    op.drop_table("judicial_process_parties")
    op.drop_table("judicial_processes")
    op.drop_table("judicial_search_sources")
    op.drop_index("ix_judicial_searches_request_hash", table_name="judicial_searches")
    op.drop_index("ix_judicial_searches_search_id", table_name="judicial_searches")
    op.drop_constraint("uq_judicial_searches_search_id", "judicial_searches", type_="unique")
    op.drop_table("judicial_searches")
