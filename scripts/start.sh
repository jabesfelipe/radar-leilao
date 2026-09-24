#!/usr/bin/env bash
# Inicia o ambiente reconstruindo as imagens de backend/frontend quando o código
# ou o Dockerfile mudou (--build). NÃO apaga volumes/dados.
#   - postgres_data  (banco PostgreSQL)  -> PRESERVADO
#   - backend_storage (documentos)       -> PRESERVADO
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "[start] .env não encontrado. Rode primeiro: ./scripts/setup.sh" >&2
  exit 1
fi

echo "[start] Subindo a stack com rebuild de backend/frontend (volumes preservados)..."
# up -d --build: reconstrói imagens desatualizadas e recria containers cujo build
# mudou, SEM tocar nos volumes (postgres_data e backend_storage permanecem intactos).
docker compose up -d --build

FRONTEND_PORT="$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2)"; FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="$(grep -E '^BACKEND_PORT=' .env 2>/dev/null | cut -d= -f2)"; BACKEND_PORT="${BACKEND_PORT:-8000}"

cat <<EOF

Radar Leilão iniciado (imagens atualizadas; dados preservados).

Frontend:
http://localhost:${FRONTEND_PORT}

Backend:
http://localhost:${BACKEND_PORT}

Swagger:
http://localhost:${BACKEND_PORT}/docs

Saúde:  ./scripts/health.sh
Logs:   ./scripts/logs.sh status
EOF
