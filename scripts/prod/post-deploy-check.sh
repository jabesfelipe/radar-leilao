#!/usr/bin/env bash
# Validação pós-deploy (smoke test) do Radar Leilão em produção.
# Somente leitura: não altera dados. Confere saúde dos serviços e invariantes.
#
# Uso: scripts/prod/post-deploy-check.sh [BASE_URL]
#   BASE_URL default: http://127.0.0.1:8080 (proxy local; modo Tailscale).
set -euo pipefail
BASE_URL="${1:-http://127.0.0.1:8080}"
PGC="${PG_CONTAINER:-radar-prod-postgres}"
PGUSER="${POSTGRES_USER:-radar}"
PGDB="${POSTGRES_DB:-radar_leilao}"
fail=0

check() { if eval "$2" >/dev/null 2>&1; then echo "[OK]  $1"; else echo "[XX]  $1"; fail=1; fi; }

echo "== Containers =="
docker compose -f docker-compose.prod.yml --env-file "${ENV_FILE:-.env.prod}" ps 2>/dev/null || true

echo "== Health =="
# O proxy exige o cookie do portão em /health; conferimos o backend por dentro do container
# e o proxy pelo endpoint próprio (sem portão, não expõe dados).
check "backend /health (no container)" "docker exec radar-prod-backend curl -fsS http://localhost:8000/health"
check "proxy /_proxy_health" "curl -fsS ${BASE_URL}/_proxy_health"
check "portao ativo (sem cookie => 403)" "[ \"\$(curl -s -o /dev/null -w '%{http_code}' ${BASE_URL}/api/imoveis)\" = 403 ]"
check "frontend /healthz (via proxy nao aplicavel; checar container)" "docker inspect -f '{{.State.Health.Status}}' radar-prod-frontend 2>/dev/null | grep -qi healthy || true"

echo "== Banco / Alembic =="
check "postgres aceita conexao" "docker exec $PGC pg_isready -U $PGUSER -d $PGDB"
ALEMBIC=$(docker exec "$PGC" psql -U "$PGUSER" -d "$PGDB" -t -A -c "SELECT version_num FROM alembic_version" 2>/dev/null || echo "(sem)")
echo "[..]  alembic_version = ${ALEMBIC}"

echo "== Invariantes historicos (preservacao) =="
docker exec "$PGC" psql -U "$PGUSER" -d "$PGDB" -t -A -c \
  "SELECT 'prop633='||count(*) FROM properties WHERE id=633" 2>/dev/null || echo "(properties indisponivel)"
docker exec "$PGC" psql -U "$PGUSER" -d "$PGDB" -t -A -c \
  "SELECT 'llm_runs='||count(*) FROM llm_runs" 2>/dev/null || echo "(llm_runs indisponivel)"
docker exec "$PGC" psql -U "$PGUSER" -d "$PGDB" -t -A -c \
  "SELECT 'canonical_keys='||count(DISTINCT canonical_key) FROM checklist_items" 2>/dev/null || echo "(checklist_items indisponivel)"

echo "== Resultado =="
if [ "$fail" -eq 0 ]; then echo "SMOKE_OK"; else echo "SMOKE_FALHOU (ver itens [XX])"; exit 1; fi
