#!/usr/bin/env bash
# Reinicia o ambiente reconstruindo backend/frontend (para aplicar mudanças de
# código, Dockerfile ou .env) SEM apagar volumes/dados.
#   - postgres_data  (banco PostgreSQL)  -> PRESERVADO
#   - backend_storage (documentos)       -> PRESERVADO
# NUNCA usa 'down -v' nem remove volumes.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo "[restart] .env não encontrado. Rode primeiro: ./scripts/setup.sh" >&2
  exit 1
fi

echo "[restart] Parando containers (volumes/dados preservados)..."
# 'down' (sem -v) remove apenas os containers; os volumes nomeados permanecem.
docker compose down

echo "[restart] Subindo novamente com rebuild e recarregando o .env..."
# --build garante que a imagem atualizada seja usada; ao recriar os containers,
# o .env é relido, aplicando a configuração atual (ex.: OPENAI_API_KEY).
docker compose up -d --build

echo "[restart] Concluído. Dados preservados. Verifique a saúde com: ./scripts/health.sh"
