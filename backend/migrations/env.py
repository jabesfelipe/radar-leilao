import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.config import settings
from app.database import Base
from app import models

# A raiz do repositório (um nível acima de backend/) precisa estar no sys.path para
# importar o pacote autocontido `judicial_api`, cujas tabelas judicial_* vivem no
# MESMO banco do Radar. Isso permite que o Alembic gerencie ambas as metadatas numa
# única cadeia de migrations / único alembic_version.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from judicial_api.db import JudicialBase  # noqa: E402
from judicial_api.persistence import models as _judicial_models  # noqa: E402,F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)

# Metadata combinada: tabelas do Radar (Base) + tabelas judicial_* (JudicialBase).
# Como as tabelas do judicial usam prefixo próprio no schema public, não há colisão
# com o Radar. Autogenerate/consistência passam a enxergar ambos os conjuntos.
target_metadata = [Base.metadata, JudicialBase.metadata]


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction(): context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    # `connectable.begin()` garante COMMIT ao final (o `connect()` anterior não
    # committava a transação das migrations, deixando o schema vazio apesar do
    # log de sucesso). Extensões são criadas dentro da mesma transação.
    with connectable.begin() as connection:
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
