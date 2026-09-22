"""Fundação do Radar com PostgreSQL, pgvector e histórico.

Revision ID: 0001_fundacao_radar
Revises:

Cria o schema BASE do Radar (estado histórico anterior às migrations 0002+).

Correção da cadeia de migrations:
`Base.metadata.create_all` reflete os modelos ATUAIS, que já contêm todas as
colunas/tabelas adicionadas por 0002..0008. Isso colidia com as migrations
incrementais (`DuplicateColumn` em `llm_runs.total_tokens`, tabelas já
existentes, etc.), impedindo `alembic upgrade head` do zero.

Solução mínima e sem tocar em modelos/contratos: após criar todo o schema via
`create_all` (que já configura corretamente pgvector, índices GIN/ivfflat e
constraints), o schema é **reduzido ao estado da fundação**, removendo as
tabelas e colunas que as migrations 0002..0008 voltam a criar/adicionar. Assim
0002..0008 aplicam exatamente como escritas, do zero, sem conflito.
"""
from alembic import op

from app.database import Base
from app import models  # noqa: F401  (registra as tabelas na metadata)

revision = "0001_fundacao_radar"
down_revision = None
branch_labels = None
depends_on = None


# Tabelas criadas por migrations posteriores (não devem existir no schema base).
TABLES_ADDED_LATER = (
    "llm_pricing",             # 0002_llm_usage_pricing
    "property_registrations",  # 0007_matricula_edital
    "auction_notices",         # 0007_matricula_edital
    "property_sources",        # 0009_cadastro_completo_imovel
)

# Colunas adicionadas por migrations posteriores (removidas do schema base).
COLUMNS_ADDED_LATER = {
    "llm_runs": (  # 0002_llm_usage_pricing
        "total_tokens", "input_cost", "output_cost", "total_cost",
        "input_price_per_1m", "output_price_per_1m",
        "request_id", "error_type", "error_message",
    ),
    "checklist_items": (  # 0003_checklist_mestre
        "description", "domain", "expected_evidence", "potential_impact",
        "related_rules", "agents", "risk_categories",
    ),
    "checklist_results": (  # 0003_checklist_mestre
        "item_version", "applicable", "previous_result_id",
    ),
    "auctions": (  # 0004_financeiro_entradas + 0009_cadastro_completo_imovel
        "acquisition_value", "commission_percent", "commission_fixed",
        "first_auction_date", "first_auction_value",
        "second_auction_date", "second_auction_value",
    ),
    "legal_processes": (  # 0006_processos_juridicos
        "comarca", "nature", "polo_active", "polo_passive",
        "distribution_date", "observations", "evidence_id",
    ),
    "properties": (  # 0009_cadastro_completo_imovel
        "neighborhood", "private_area_m2", "parking_spots", "description",
        "origin", "origin_property_code", "inscription", "modality", "system",
    ),
    # auction_notices.item também é de 0009, mas auction_notices é recriada por 0007
    # (está em TABLES_ADDED_LATER), então o DROP da tabela já remove a coluna.
}


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    bind = op.get_bind()

    # 1) Cria todo o schema (pgvector, índices e constraints corretos).
    Base.metadata.create_all(bind=bind)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # 2) Reduz ao estado da fundação: as migrations 0002..0008 recriarão isto.
    for table in TABLES_ADDED_LATER:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for table, columns in COLUMNS_ADDED_LATER.items():
        for column in columns:
            op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column} CASCADE")


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
