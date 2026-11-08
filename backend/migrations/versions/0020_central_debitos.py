"""Central de Débitos/Despesas + catálogo de parâmetros administráveis (Etapa A).

Cria as tabelas do novo domínio (todas ADITIVAS; nenhuma coluna/dado existente é
tocado; `Debt`/`Cost` permanecem intactos):
  - municipalities     (municípios cadastráveis + cobertura)
  - debt_types         (catálogo administrável de tipos de débito/despesa)
  - debt_sources       (fontes por município×tipo — apenas cadastro, sem consulta)
  - property_debts     (débito/despesa NORMALIZADO por imóvel/oportunidade)
  - parameters         (catálogo CENTRAL de parâmetros, transversal)
  - parameter_history  (trilha imutável de alterações de parâmetro)

Sem backfill (Gate 2 não autorizado). `opportunity_id` em property_debts é NULLABLE
(NULL = legado; Gate 1). Totalmente reversível (drop na ordem inversa das FKs).

Observação de sequência: esta é a migration `0020`. A Onda 2 (modalidade), ainda
apenas planejada, deverá tomar o PRÓXIMO número livre (`0021`) para evitar colisão.
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_central_debitos"
down_revision = "0019_opportunity_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipalities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("ibge_code", sa.String(length=7), nullable=True),
        sa.Column("coverage_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ATIVO"),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("ibge_code", name="uq_municipality_ibge"),
        sa.UniqueConstraint("name", "state", name="uq_municipality_name_state"),
    )
    op.create_index("ix_municipalities_name", "municipalities", ["name"])
    op.create_index("ix_municipalities_state", "municipalities", ["state"])
    op.create_index("ix_municipalities_coverage_active", "municipalities", ["coverage_active"])

    op.create_table(
        "debt_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("group", sa.String(length=40), nullable=False),
        sa.Column("default_nature", sa.String(length=30), nullable=False, server_default="DIVIDA_EXISTENTE"),
        sa.Column("canonical_cost_key", sa.String(length=40), nullable=True),
        sa.Column("impacts_finance", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_debt_type_code"),
    )
    op.create_index("ix_debt_types_code", "debt_types", ["code"], unique=True)
    op.create_index("ix_debt_types_group", "debt_types", ["group"])
    op.create_index("ix_debt_types_active", "debt_types", ["active"])

    op.create_table(
        "debt_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("municipality_id", sa.Integer(), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("debt_category", sa.String(length=60), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("authority", sa.String(length=200), nullable=True),
        sa.Column("official_url", sa.String(length=600), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False, server_default="CONSULTA_MANUAL"),
        sa.Column("method", sa.String(length=120), nullable=True),
        sa.Column("situation", sa.String(length=30), nullable=False, server_default="NAO_INVESTIGADA"),
        sa.Column("access_requirements", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_debt_sources_municipality_id", "debt_sources", ["municipality_id"])
    op.create_index("ix_debt_sources_debt_category", "debt_sources", ["debt_category"])
    op.create_index("ix_debt_sources_active", "debt_sources", ["active"])

    op.create_table(
        "property_debts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=True),
        sa.Column("municipality_id", sa.Integer(), sa.ForeignKey("municipalities.id"), nullable=True),
        sa.Column("debt_type_code", sa.String(length=60), nullable=False),
        sa.Column("subcategory", sa.String(length=80), nullable=True),
        sa.Column("nature", sa.String(length=30), nullable=False, server_default="DIVIDA_EXISTENTE"),
        sa.Column("creditor", sa.String(length=200), nullable=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("competence", sa.String(length=20), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("original_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("interest", sa.Numeric(14, 2), nullable=True),
        sa.Column("penalty", sa.Numeric(14, 2), nullable=True),
        sa.Column("correction", sa.Numeric(14, 2), nullable=True),
        sa.Column("updated_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("reference_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDENTE"),
        sa.Column("reliability", sa.String(length=30), nullable=False, server_default="NAO_VERIFICADO"),
        sa.Column("origin", sa.String(length=120), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("debt_sources.id"), nullable=True),
        sa.Column("acquisition_method", sa.String(length=120), nullable=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidences.id"), nullable=True),
        sa.Column("queried_at", sa.DateTime(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_property_debts_property_id", "property_debts", ["property_id"])
    op.create_index("ix_property_debts_opportunity_id", "property_debts", ["opportunity_id"])
    op.create_index("ix_property_debts_municipality_id", "property_debts", ["municipality_id"])
    op.create_index("ix_property_debts_debt_type_code", "property_debts", ["debt_type_code"])
    op.create_index("ix_property_debts_nature", "property_debts", ["nature"])
    op.create_index("ix_property_debts_status", "property_debts", ["status"])
    op.create_index("ix_property_debts_property_status", "property_debts", ["property_id", "status"])

    op.create_table(
        "parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("data_type", sa.String(length=20), nullable=False, server_default="STRING"),
        sa.Column("scope", sa.String(length=30), nullable=False, server_default="GLOBAL"),
        sa.Column("municipality_id", sa.Integer(), sa.ForeignKey("municipalities.id"), nullable=True),
        sa.Column("debt_category", sa.String(length=60), nullable=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("allowed_values", sa.JSON(), nullable=True),
        sa.Column("min_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("max_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ATIVO"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.String(length=120), nullable=False, server_default="sistema"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", "scope", "municipality_id", "debt_category", name="uq_parameter_scope"),
    )
    op.create_index("ix_parameters_key", "parameters", ["key"])
    op.create_index("ix_parameters_category", "parameters", ["category"])
    op.create_index("ix_parameters_scope", "parameters", ["scope"])
    op.create_index("ix_parameters_municipality_id", "parameters", ["municipality_id"])
    op.create_index("ix_parameters_debt_category", "parameters", ["debt_category"])
    op.create_index("ix_parameters_status", "parameters", ["status"])
    op.create_index("ix_parameters_key_scope", "parameters", ["key", "scope"])

    op.create_table(
        "parameter_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parameter_id", sa.Integer(), sa.ForeignKey("parameters.id"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False, server_default="UPDATE"),
        sa.Column("actor", sa.String(length=120), nullable=False, server_default="sistema"),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_parameter_history_parameter_id", "parameter_history", ["parameter_id"])
    op.create_index("ix_parameter_history_key", "parameter_history", ["key"])


def downgrade() -> None:
    op.drop_index("ix_parameter_history_key", table_name="parameter_history")
    op.drop_index("ix_parameter_history_parameter_id", table_name="parameter_history")
    op.drop_table("parameter_history")

    for idx in ("ix_parameters_key_scope", "ix_parameters_status", "ix_parameters_debt_category",
                "ix_parameters_municipality_id", "ix_parameters_scope", "ix_parameters_category",
                "ix_parameters_key"):
        op.drop_index(idx, table_name="parameters")
    op.drop_table("parameters")

    for idx in ("ix_property_debts_property_status", "ix_property_debts_status", "ix_property_debts_nature",
                "ix_property_debts_debt_type_code", "ix_property_debts_municipality_id",
                "ix_property_debts_opportunity_id", "ix_property_debts_property_id"):
        op.drop_index(idx, table_name="property_debts")
    op.drop_table("property_debts")

    for idx in ("ix_debt_sources_active", "ix_debt_sources_debt_category", "ix_debt_sources_municipality_id"):
        op.drop_index(idx, table_name="debt_sources")
    op.drop_table("debt_sources")

    for idx in ("ix_debt_types_active", "ix_debt_types_group", "ix_debt_types_code"):
        op.drop_index(idx, table_name="debt_types")
    op.drop_table("debt_types")

    for idx in ("ix_municipalities_coverage_active", "ix_municipalities_state", "ix_municipalities_name"):
        op.drop_index(idx, table_name="municipalities")
    op.drop_table("municipalities")
