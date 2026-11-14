"""Rastreabilidade das evidências: origem, força da citação e agente; origem da resolução do checklist.

Homologação v1.0.4 (primeira execução com a OpenAI real): dados do snapshot financeiro apareciam como
"trecho literal" do edital e a pergunta do checklist aparecia como citação. A partir desta versão cada
evidência informa DE ONDE vem a informação e QUANTO a citação sustenta a afirmação:

- ``evidences.origin``: DOCUMENTO, CADASTRO, CALCULO, PESQUISA_JUDICIAL, INFERENCIA_IA ou REGRA_DETERMINISTICA;
- ``evidences.strength``: FORTE, MODERADA, FRACA ou INVALIDA (só para citações de documento);
- ``evidences.agent``: agente/extrator que produziu a evidência;
- ``checklist_results.resolution_origin``: como o item saiu de PENDENTE (DOCUMENTO, REGRA_DETERMINISTICA...).

Todas as colunas são OPCIONAIS (NULL = registro anterior a esta versão, origem não registrada); nenhum dado
existente é alterado. Idempotente: a 0001 monta o schema a partir dos modelos atuais, então em banco novo as
colunas já existem quando esta migration roda (``ADD COLUMN IF NOT EXISTS``).

Sequência: migration ``0025`` (down_revision ``0024_analysis_version_unique``).
"""
from alembic import op

revision = "0025_evidencia_origem_forca"
down_revision = "0024_analysis_version_unique"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("evidences", "origin", "VARCHAR(30)"),
    ("evidences", "strength", "VARCHAR(20)"),
    ("evidences", "agent", "VARCHAR(40)"),
    ("checklist_results", "resolution_origin", "VARCHAR(30)"),
)


def upgrade() -> None:
    for table, column, ddl in _COLUMNS:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}")


def downgrade() -> None:
    for table, column, _ddl in reversed(_COLUMNS):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")
