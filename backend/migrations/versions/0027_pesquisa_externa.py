"""Pesquisa externa autorizada (v1.0.14).

Cria ``external_searches``: uma linha por consulta a um provedor de pesquisa web por API (Tavily, Brave) ou por tentativa
sem provedor configurado. Guarda a consulta, o provedor, o status, os resultados brutos (URL, título, trecho, data), a
duração, as tentativas, o custo estimado e a validade do cache. Não guarda credenciais. Tabela nova e aditiva: o rollback
de imagem para a v1.0.13 continua compatível (a tabela fica sem uso).

Sequência: ``0027`` (down_revision ``0026_comparaveis_rastreaveis``).
"""
from alembic import op

revision = "0027_pesquisa_externa"
down_revision = "0026_comparaveis_rastreaveis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS external_searches (
            id SERIAL PRIMARY KEY,
            property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
            kind VARCHAR(30) NOT NULL,
            provider VARCHAR(40) NOT NULL,
            query TEXT NOT NULL,
            cache_key VARCHAR(64) NOT NULL,
            status VARCHAR(30) NOT NULL,
            results_count INTEGER DEFAULT 0,
            results JSON,
            duration_ms INTEGER,
            attempts INTEGER DEFAULT 1,
            cost_estimate_usd NUMERIC(10, 4),
            error TEXT,
            expires_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_external_searches_property_id ON external_searches (property_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_external_searches_cache_key ON external_searches (cache_key)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS external_searches")
