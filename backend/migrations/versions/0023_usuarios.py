"""Autenticação/RBAC (Onda 11): tabela de usuários.

Cria a tabela ADITIVA ``users`` (identidade local: e-mail + senha com hash bcrypt +
papel). Aditiva e reversível; não toca nenhuma tabela existente. NENHUM usuário/senha
padrão é criado nesta migration — o bootstrap do primeiro administrador é opcional e
feito em runtime a partir do ambiente (ver auth.ensure_bootstrap_admin), de modo que
nunca haja credencial default em produção.

Sequência: migration ``0023`` (down_revision ``0022_consulta_estimativa``).
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_usuarios"
down_revision = "0022_consulta_estimativa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="CONSULTA"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
