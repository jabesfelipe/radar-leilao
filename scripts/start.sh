#!/usr/bin/env bash
# Inicia o ambiente já configurado (não reconstrói imagens, não apaga dados).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "[start] .env não encontrado. Rode primeiro: ./scripts/setup.sh" >&2
  exit 1
fi

docker compose up -d

FRONTEND_PORT="$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2)"; FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_PORT="$(grep -E '^BACKEND_PORT=' .env 2>/dev/null | cut -d= -f2)"; BACKEND_PORT="${BACKEND_PORT:-8000}"

cat <<EOF

Radar Leilão iniciado.

Frontend:
http://localhost:${FRONTEND_PORT}

Backend:
http://localhost:${BACKEND_PORT}

Swagger:
http://localhost:${BACKEND_PORT}/docs
EOF
