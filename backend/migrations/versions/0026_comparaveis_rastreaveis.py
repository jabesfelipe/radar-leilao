"""Comparáveis rastreáveis para a inteligência de mercado (v1.0.8).

``market_comparables`` passa a registrar, além de tipo/preço/aluguel/área/fonte/URL:

- ``price_type``: ANUNCIADO (preço pedido no anúncio) ou TRANSACIONADO (venda/locação efetivamente fechada);
- ``collected_at`` (data da consulta) e ``listing_date`` (data do anúncio, quando conhecida);
- localização e características: ``address``, ``neighborhood``, ``city``, ``state``, ``property_type``,
  ``bedrooms``, ``parking_spots``, ``condition``, ``condo_fee``, ``iptu``;
- ``area_basis``: a que área o anúncio se refere (PRIVATIVA, UTIL, TOTAL, DESCONHECIDA);
- ``distance_km``: distância aproximada ao imóvel analisado, só quando medida (nunca estimada pelo sistema);
- ``listing_ref``, ``notes``; ``excluded`` + ``exclusion_reason`` (ex.: o próprio imóvel anunciado, duplicata).

Todas as colunas são OPCIONAIS; registros anteriores continuam válidos (``price_type`` nulo = ANUNCIADO, que é o
caso de todo comparável cadastrado manualmente até aqui). Idempotente (``ADD COLUMN IF NOT EXISTS``).

Sequência: ``0026`` (down_revision ``0025_evidencia_origem_forca``).
"""
from alembic import op

revision = "0026_comparaveis_rastreaveis"
down_revision = "0025_evidencia_origem_forca"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("price_type", "VARCHAR(20)"),
    ("collected_at", "DATE"),
    ("listing_date", "DATE"),
    ("address", "VARCHAR(240)"),
    ("neighborhood", "VARCHAR(120)"),
    ("city", "VARCHAR(120)"),
    ("state", "VARCHAR(2)"),
    ("property_type", "VARCHAR(60)"),
    ("bedrooms", "INTEGER"),
    ("parking_spots", "INTEGER"),
    ("condition", "VARCHAR(60)"),
    ("condo_fee", "NUMERIC(14, 2)"),
    ("iptu", "NUMERIC(14, 2)"),
    ("area_basis", "VARCHAR(20)"),
    ("distance_km", "NUMERIC(8, 2)"),
    ("listing_ref", "VARCHAR(160)"),
    ("notes", "TEXT"),
    ("excluded", "BOOLEAN DEFAULT FALSE"),
    ("exclusion_reason", "VARCHAR(240)"),
)


def upgrade() -> None:
    for column, ddl in _COLUMNS:
        op.execute(f"ALTER TABLE market_comparables ADD COLUMN IF NOT EXISTS {column} {ddl}")


def downgrade() -> None:
    for column, _ddl in reversed(_COLUMNS):
        op.execute(f"ALTER TABLE market_comparables DROP COLUMN IF EXISTS {column}")
