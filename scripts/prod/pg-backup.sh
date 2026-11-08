#!/usr/bin/env bash
# Backup de PRODUÇÃO do PostgreSQL do Radar Leilão — formato CUSTOM (pg_dump -Fc).
#
# Características:
# - pg_dump em formato customizado (-Fc): compressão + restauração seletiva/paralela.
# - Nome com data/hora; verificação do dump (pg_restore -l) após gerar.
# - Retenção configurável (RETENTION_DAYS): backups antigos são MOVIDOS para um
#   subdiretório archive/ — NUNCA excluídos automaticamente (regra de preservação).
# - Log de execução.
# - NÃO altera o banco. Somente leitura (pg_dump).
#
# Uso:
#   scripts/prod/pg-backup.sh [DEST_DIR]
# Variáveis (ou .env): POSTGRES_USER, POSTGRES_DB, PG_CONTAINER, RETENTION_DAYS.
# Recomenda-se guardar DEST_DIR em disco/volume SEPARADO do banco.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PG_CONTAINER="${PG_CONTAINER:-radar-prod-postgres}"
PGUSER="${POSTGRES_USER:-radar}"
PGDB="${POSTGRES_DB:-radar_leilao}"
DEST_DIR="${1:-${BACKUP_DEST:-backups}}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${DEST_DIR}/radar-${PGDB}-${STAMP}.dump"
LOG="${DEST_DIR}/backup.log"

mkdir -p "$DEST_DIR" "${DEST_DIR}/archive"
echo "[$(date -Iseconds)] backup iniciado -> ${OUT}" | tee -a "$LOG"

# Dump em formato custom direto do container (pg_dump -Fc). Sem expor senha no log.
docker exec "$PG_CONTAINER" pg_dump -U "$PGUSER" -d "$PGDB" -Fc > "$OUT"

# Verificação: pg_restore -l deve listar o conteúdo sem erro.
if docker exec -i "$PG_CONTAINER" pg_restore -l < "$OUT" >/dev/null 2>&1; then
  SIZE="$(wc -c < "$OUT")"
  echo "[$(date -Iseconds)] backup OK (${SIZE} bytes) e verificado (pg_restore -l)" | tee -a "$LOG"
else
  echo "[$(date -Iseconds)] ERRO: verificacao do backup falhou (${OUT})" | tee -a "$LOG" >&2
  exit 1
fi

# Retenção NÃO destrutiva: move dumps mais antigos que RETENTION_DAYS para archive/.
find "$DEST_DIR" -maxdepth 1 -name "radar-${PGDB}-*.dump" -type f -mtime "+${RETENTION_DAYS}" -print0 2>/dev/null \
  | while IFS= read -r -d '' f; do
      mv "$f" "${DEST_DIR}/archive/" && echo "[$(date -Iseconds)] arquivado (retencao): $(basename "$f")" | tee -a "$LOG"
    done

echo "[$(date -Iseconds)] backup concluido: ${OUT}" | tee -a "$LOG"
echo "$OUT"
