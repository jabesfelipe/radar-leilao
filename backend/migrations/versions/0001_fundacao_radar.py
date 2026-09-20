"""Fundação do Radar com PostgreSQL, pgvector e histórico.

Revision ID: 0001_fundacao_radar
Revises:
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0001_fundacao_radar"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
