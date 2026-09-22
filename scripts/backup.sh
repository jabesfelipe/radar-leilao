#!/usr/bin/env bash
# Backup local do Radar Leilão.
# Inclui: dump completo do PostgreSQL (pg_dump) + arquivos do storage de documentos.
# NÃO inclui: .env, imagens Docker, node_modules, código-fonte.
#
# Uso:   ./scripts/backup.sh [diretorio_destino]
# Padrão: backups/
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PGUSER="$(grep -E '^POSTGRES_USER=' .env 2>/dev/null | cut -d= -f2)"; PGUSER="${PGUSER:-radar}"
PGDB="$(grep -E '^POSTGRES_DB=' .env 2>/dev/null | cut -d= -f2)"; PGDB="${PGDB:-radar_leilao}"

DEST_DIR="${1:-backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${DEST_DIR}/radar-backup-${STAMP}"
mkdir -p "$BACKUP_DIR"

echo "[backup] Destino: ${BACKUP_DIR}"

# 1) Banco (dump SQL comprimido via pg_dump dentro do container)
echo "[backup] Exportando banco PostgreSQL..."
docker exec radar-leilao-postgres pg_dump -U "$PGUSER" -d "$PGDB" | gzip > "${BACKUP_DIR}/postgres.sql.gz"
echo "[backup] Banco salvo em postgres.sql.gz"

# 2) Storage de documentos (volume backend_storage)
echo "[backup] Exportando arquivos de documentos (storage)..."
if docker ps --format '{{.Names}}' | grep -q radar-leilao-backend; then
  # tar do conteúdo de /app/backend/storage a partir do container do backend
  docker exec radar-leilao-backend sh -c 'cd /app/backend && tar czf - storage 2>/dev/null' > "${BACKUP_DIR}/storage.tar.gz" || \
    echo "[backup] (storage vazio ou indisponível — ignorado)"
else
  echo "[backup] (backend não está em execução — storage não incluído)"
fi

# 3) Manifesto
cat > "${BACKUP_DIR}/MANIFEST.txt" <<EOF
Radar Leilão — backup
Gerado em: $(date -Iseconds)
Banco: ${PGDB} (usuário ${PGUSER})
Conteúdo:
  - postgres.sql.gz : dump completo do banco (pg_dump | gzip)
  - storage.tar.gz  : arquivos de documentos (se existirem)
NÃO incluído: .env, imagens Docker, código-fonte.
Restaurar com: ./scripts/restore.sh ${BACKUP_DIR}
EOF

echo "[backup] Concluído: ${BACKUP_DIR}"
echo "[backup] Para restaurar em outro notebook: ./scripts/restore.sh ${BACKUP_DIR}"
