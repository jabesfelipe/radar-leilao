#!/usr/bin/env bash
# Para os containers SEM apagar dados (volumes são preservados).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 'docker compose down' (sem -v) remove os containers mas PRESERVA os volumes.
docker compose down
echo "[stop] Ambiente parado. Os dados foram preservados (volumes intactos)."
echo "[stop] Para iniciar novamente: ./scripts/start.sh"
