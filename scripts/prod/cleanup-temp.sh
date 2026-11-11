#!/usr/bin/env bash
# Limpeza CONTROLADA de temporários de processamento (apenas <volume>/tmp).
# Nunca toca documents/. Remove somente arquivos com mais de N dias (default 1).
# Dry-run por padrão; use APPLY=true para remover.
set -euo pipefail
VOL="${STORAGE_VOLUME:-${COMPOSE_PROJECT_NAME:-radar-prod}_backend_storage}"
DAYS="${DAYS:-1}"
MODE=$([ "${APPLY:-false}" = "true" ] && echo "-delete" || echo "-print")
docker run --rm -v "$VOL":/s alpine sh -c "[ -d /s/tmp ] && find /s/tmp -type f -mtime +$DAYS $MODE || echo '(sem tmp)'"
[ "${APPLY:-false}" = "true" ] || echo "[cleanup-temp] dry-run: nada removido (use APPLY=true)."
