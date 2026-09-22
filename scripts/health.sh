#!/usr/bin/env bash
# Verificação simples de saúde dos componentes do Radar Leilão.
# Mostra OK / FALHA por componente. Não altera nada.
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Carrega portas do .env (com defaults)
PGUSER="$(grep -E '^POSTGRES_USER=' .env 2>/dev/null | cut -d= -f2)"; PGUSER="${PGUSER:-radar}"
PGDB="$(grep -E '^POSTGRES_DB=' .env 2>/dev/null | cut -d= -f2)"; PGDB="${PGDB:-radar_leilao}"
BACKEND_PORT="$(grep -E '^BACKEND_PORT=' .env 2>/dev/null | cut -d= -f2)"; BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="$(grep -E '^FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2)"; FRONTEND_PORT="${FRONTEND_PORT:-5173}"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
line() { printf '%-16s %b\n' "$1" "$2"; }
oks=0; fails=0
pass() { line "$1" "${GREEN}OK${NC}"; oks=$((oks+1)); }
fail() { line "$1" "${RED}FALHA${NC}"; fails=$((fails+1)); }

# PostgreSQL
if docker exec radar-leilao-postgres pg_isready -U "$PGUSER" -d "$PGDB" >/dev/null 2>&1; then
  pass "PostgreSQL"
else
  fail "PostgreSQL"
fi

# pgvector (extensão instalada)
if docker exec radar-leilao-postgres psql -U "$PGUSER" -d "$PGDB" -tAc "select 1 from pg_extension where extname='vector'" 2>/dev/null | grep -q 1; then
  pass "pgvector"
else
  fail "pgvector"
fi

# Migrations (alembic_version na versão head 0008)
if docker exec radar-leilao-postgres psql -U "$PGUSER" -d "$PGDB" -tAc "select version_num from alembic_version" 2>/dev/null | grep -q .; then
  pass "Migrations"
else
  fail "Migrations"
fi

# Backend /health
if curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
  pass "Backend"
else
  fail "Backend"
fi

# Frontend (responde na porta)
if curl -fsS "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1; then
  pass "Frontend"
else
  fail "Frontend"
fi

echo "------------------------------------"
echo "OK: ${oks}   FALHAS: ${fails}"
if [ "$fails" -gt 0 ]; then
  echo "Dica: veja os logs com 'docker compose logs <servico>' (postgres|backend|frontend)."
  exit 1
fi
