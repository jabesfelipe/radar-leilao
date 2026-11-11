#!/usr/bin/env bash
# Backup do volume de documentos (somente leitura sobre o volume).
# Gera: storage-<STAMP>.tar.gz + storage-<STAMP>.sha256 (manifesto por arquivo) e
# verifica o tar.gz. Exclui o diretório tmp/ (temporários). Nunca apaga nada.
#
# Uso: scripts/prod/storage-backup.sh [DEST_DIR]
# Variáveis: STORAGE_VOLUME (default radar-prod_backend_storage)
set -euo pipefail
VOL="${STORAGE_VOLUME:-radar-prod_backend_storage}"
DEST="${1:-${BACKUP_DEST:-backups}}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"
DEST_ABS="$(cd "$DEST" && pwd)"

docker volume inspect "$VOL" >/dev/null 2>&1 || { echo "[storage-backup] volume '$VOL' nao existe" >&2; exit 1; }

echo "[storage-backup] volume=$VOL -> $DEST_ABS/storage-$STAMP.tar.gz"
docker run --rm -v "$VOL":/s:ro -v "$DEST_ABS":/b alpine sh -c "
  cd /s &&
  find . -type f -not -path './tmp/*' -exec sha256sum {} + | sort -k2 > /b/storage-$STAMP.sha256 &&
  tar czf /b/storage-$STAMP.tar.gz --exclude=./tmp . &&
  tar tzf /b/storage-$STAMP.tar.gz > /dev/null"
FILES=$(wc -l < "$DEST_ABS/storage-$STAMP.sha256")
echo "[storage-backup] OK: $FILES arquivo(s); tar.gz verificado; manifesto sha256 gerado"
echo "$DEST_ABS/storage-$STAMP.tar.gz"
