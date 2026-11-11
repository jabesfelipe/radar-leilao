#!/usr/bin/env bash
# Valida metadados x arquivos após restauração: todo original_path/normalized_path do banco
# informado precisa existir no volume informado. Somente leitura.
#
# Uso: scripts/prod/verify-restore-paths.sh <BANCO> <VOLUME>
# Ex.: scripts/prod/verify-restore-paths.sh radar_restore_check radar_restore_check_storage
set -euo pipefail
DB="${1:?banco}"; VOL="${2:?volume}"
PGC="${PG_CONTAINER:-radar-prod-postgres}"; PGUSER="${POSTGRES_USER:-radar}"
# A lista é passada por stdin (evita /tmp privado do docker em snap).
docker exec "$PGC" psql -U "$PGUSER" -d "$DB" -t -A -c \
  "SELECT original_path FROM document_versions UNION SELECT normalized_path FROM document_versions WHERE normalized_path IS NOT NULL" \
| docker run --rm -i -v "$VOL":/app/backend/storage:ro alpine sh -c '
  n=0; f=0
  while read -r p; do
    [ -z "$p" ] && continue
    n=$((n+1))
    [ -f "$p" ] || { echo "FALTA: $p"; f=$((f+1)); }
  done
  echo "paths=$n faltando=$f"
  [ "$f" -eq 0 ]'
