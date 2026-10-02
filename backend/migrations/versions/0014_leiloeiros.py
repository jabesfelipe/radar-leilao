"""Domínio Leiloeiros (TASK 75): auctioneers, portal_accesses, auctioneer_documents
+ auctions.auctioneer_id (FK opcional, preserva o texto auctioneer).

A credencial do portal (``portal_accesses.secret``) fica numa coluna separada e
nunca é exposta em listagens (regra de segurança da API). Reversível e sem tocar
em dados existentes (tudo nullable/novas tabelas).
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_leiloeiros"
down_revision = "0013_processo_correlacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auctioneers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("document", sa.String(length=40), nullable=True),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("registration", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=60), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("website", sa.String(length=300), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ATIVO"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "portal_accesses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auctioneer_id", sa.Integer(), sa.ForeignKey("auctioneers.id"), nullable=False, index=True),
        sa.Column("portal", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("username", sa.String(length=200), nullable=True),
        sa.Column("secret", sa.Text(), nullable=True),
        sa.Column("access_type", sa.String(length=80), nullable=True),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ATIVO"),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "auctioneer_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auctioneer_id", sa.Integer(), sa.ForeignKey("auctioneers.id"), nullable=False, index=True),
        sa.Column("doc_type", sa.String(length=80), nullable=False, server_default="OUTROS"),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("auctions", sa.Column("auctioneer_id", sa.Integer(), sa.ForeignKey("auctioneers.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("auctions", "auctioneer_id")
    op.drop_table("auctioneer_documents")
    op.drop_table("portal_accesses")
    op.drop_table("auctioneers")
