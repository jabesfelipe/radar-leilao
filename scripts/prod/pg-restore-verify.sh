#!/usr/bin/env bash
# Restauração + verificação de um backup (pg_dump -Fc) em banco ISOLADO.
#
# Segurança: restaura SEMPRE num banco descartável (default: radar_restore_check),
# NUNCA no banco vivo. Valida estrutura e contagens básicas. Ao final, opcionalmente
# DROPA o banco de verificação (DROP_AFTER=true), nunca o banco de produção.
#
# Uso:
#   scripts/prod/pg-restore-verify.sh <arquivo.dump> [DB_VERIFICACAO]
# Variáveis: POSTGRES_USER, PG_CONTAINER, DROP_AFTER (default true).
set -euo pipefail

DUMP="${1:-}"
VERIFY_DB="${2:-radar_restore_check}"
PG_CONTAINER="${PG_CONTAINER:-radar-prod-postgres}"
PGUSER="${POSTGRES_USER:-radar}"
DROP_AFTER="${DROP_AFTER:-true}"

if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
  echo "[restore-verify] Uso: scripts/prod/pg-restore-verify.sh <arquivo.dump> [DB_VERIFICACAO]" >&2
  exit 1
fi

# Proteção: jamais usar o banco de produção como destino de verificação.
case "$VERIFY_DB" in
  radar_leilao|postgres|template0|template1)
    echo "[restore-verify] RECUSADO: '$VERIFY_DB' nao pode ser o destino de verificacao." >&2
    exit 2 ;;
esac

echo "[restore-verify] Recriando banco de verificacao '${VERIFY_DB}' (descartavel)..."
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS ${VERIFY_DB};"
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d postgres -c "CREATE DATABASE ${VERIFY_DB};"
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$VERIFY_DB" -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo "[restore-verify] Restaurando dump (pg_restore)..."
docker exec -i "$PG_CONTAINER" pg_restore -U "$PGUSER" -d "$VERIFY_DB" --no-owner --no-privileges < "$DUMP" 2>/dev/null || true

echo "[restore-verify] Validando estrutura e contagens..."
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$VERIFY_DB" -c \
  "SELECT 'tabelas='||count(*) FROM information_schema.tables WHERE table_schema='public';"
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$VERIFY_DB" -c \
  "SELECT 'alembic='||coalesce((SELECT version_num FROM alembic_version LIMIT 1),'(sem)');"
# Contagens básicas (tolerante a ausência de tabela em backups parciais).
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$VERIFY_DB" -c \
  "SELECT 'properties='||count(*) FROM properties;" 2>/dev/null || echo "[restore-verify] (properties ausente)"
docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$VERIFY_DB" -c \
  "SELECT 'document_chunks='||count(*) FROM document_chunks;" 2>/dev/null || echo "[restore-verify] (document_chunks ausente)"

if [ "$DROP_AFTER" = "true" ]; then
  echo "[restore-verify] Removendo banco de verificacao '${VERIFY_DB}'..."
  docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS ${VERIFY_DB};"
fi
echo "[restore-verify] Concluido."
