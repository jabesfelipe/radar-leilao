"""Classificação do vínculo processo×imóvel: legal_processes.link_origin e correlation_level.

Adiciona duas colunas nullable a ``legal_processes`` para registrar, de forma
rastreável, a classificação do vínculo entre processo e imóvel:

- ``link_origin``: AUTOMATICA | MANUAL | VALIDADA | NAO_CONFIRMADA — como a relação
  passou a existir (consulta automática, vínculo manual, validação ou não confirmada).
- ``correlation_level``: ALTA | MEDIA | BAIXA | NAO_CONFIRMADA — probabilidade de o
  processo se referir ao proprietário/imóvel (determinística; nome não confirma
  identidade).

Reversível e sem tocar em dados existentes (ambas nullable, default nulo).
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_processo_correlacao"
down_revision = "0012_premissas_financeiras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("legal_processes", sa.Column("link_origin", sa.String(length=30), nullable=True))
    op.add_column("legal_processes", sa.Column("correlation_level", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("legal_processes", "correlation_level")
    op.drop_column("legal_processes", "link_origin")
