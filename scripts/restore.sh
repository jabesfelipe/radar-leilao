#!/usr/bin/env bash
# Restore local do Radar Leilão a partir de um backup gerado por backup.sh.
# Restaura o banco PostgreSQL e (se houver) os arquivos de storage.
# Pede confirmação antes de sobrescrever dados.
#
# Uso: ./scripts/restore.sh <diretorio_do_backup>
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${1:-}"
if [ -z "$BACKUP_DIR" ] || [ ! -d "$BACKUP_DIR" ]; then
  echo "[restore] Uso: ./scripts/restore.sh <diretorio_do_backup>" >&2
  echo "[restore] Exemplo: ./scripts/restore.sh backups/radar-backup-20260101-120000" >&2
  exit 1
fi

DUMP="${BACKUP_DIR}/postgres.sql.gz"
if [ ! -f "$DUMP" ]; then
  echo "[restore] Arquivo de banco não encontrado: ${DUMP}" >&2
  exit 1
fi

PGUSER="$(grep -E '^POSTGRES_USER=' .env 2>/dev/null | cut -d= -f2)"; PGUSER="${PGUSER:-radar}"
PGDB="$(grep -E '^POSTGRES_DB=' .env 2>/dev/null | cut -d= -f2)"; PGDB="${PGDB:-radar_leilao}"

echo "[restore] Backup: ${BACKUP_DIR}"
echo "[restore] Alvo: banco '${PGDB}' (usuário ${PGUSER})."
echo "ATENÇÃO: o conteúdo atual do banco será substituído pelo backup."
read -r -p "Deseja continuar? [y/N] " resposta
case "${resposta:-N}" in
  y|Y|yes|YES|s|S|sim|SIM) : ;;
  *) echo "[restore] Cancelado. Nada foi alterado."; exit 0 ;;
esac

# Garante que o Postgres está de pé
echo "[restore] Garantindo que o PostgreSQL está em execução..."
docker compose up -d postgres
for i in $(seq 1 30); do
  if docker exec radar-leilao-postgres pg_isready -U "$PGUSER" -d "$PGDB" >/dev/null 2>&1; then break; fi
  sleep 2
done

# 1) Recria o schema public limpo e restaura o dump
echo "[restore] Limpando schema e restaurando o banco..."
docker exec radar-leilao-postgres psql -U "$PGUSER" -d "$PGDB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null
gunzip -c "$DUMP" | docker exec -i radar-leilao-postgres psql -U "$PGUSER" -d "$PGDB" >/dev/null
echo "[restore] Banco restaurado."

# 2) Storage (se houver)
if [ -f "${BACKUP_DIR}/storage.tar.gz" ]; then
  echo "[restore] Restaurando arquivos de documentos (storage)..."
  docker compose up -d backend >/dev/null 2>&1 || true
  # aguarda o container do backend existir
  for i in $(seq 1 30); do docker ps --format '{{.Names}}' | grep -q radar-leilao-backend && break; sleep 2; done
  cat "${BACKUP_DIR}/storage.tar.gz" | docker exec -i radar-leilao-backend sh -c 'cd /app/backend && tar xzf -' \
    && echo "[restore] Storage restaurado." || echo "[restore] (falha ao restaurar storage — verifique manualmente)"
fi

# 3) Migrations (garante schema no head, caso o backup seja de versão anterior)
echo "[restore] Aplicando migrations pendentes (se houver)..."
docker compose up -d backend >/dev/null 2>&1 || true
docker exec radar-leilao-backend sh -c 'cd /app/backend && alembic upgrade head' \
  && echo "[restore] Migrations conferidas." || echo "[restore] (não foi possível rodar migrations agora — rode ./scripts/start.sh)"

echo "[restore] Concluído. Verifique com: ./scripts/health.sh"
