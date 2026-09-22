#!/usr/bin/env bash
# Reinicia o ambiente sem apagar volumes/dados.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[restart] Parando containers (dados preservados)..."
docker compose down
echo "[restart] Subindo novamente..."
docker compose up -d
echo "[restart] Concluído. Verifique a saúde com: ./scripts/health.sh"
