#!/usr/bin/env bash
# Deploy controlado do Radar Leilão na VPS (executar DENTRO do diretório do projeto).
#
#   scripts/prod/deploy.sh first    # 1º deploy: banco vazio
#   scripts/prod/deploy.sh update   # atualização de instalação existente
#
# Fluxo "update": backup (banco+documentos) -> build -> migrate -> up -> smoke.
# Fluxo "first" : build -> sobe postgres -> migrate -> up -> smoke.
# Se o smoke falhar, imprime como voltar (ver docs/DOCKER-DEPLOYMENT.md §Rollback).
# Nada aqui usa down -v, DROP, TRUNCATE.
set -euo pipefail
MODE="${1:-}"
[ "$MODE" = "first" ] || [ "$MODE" = "update" ] || { echo "Uso: $0 first|update" >&2; exit 1; }
ENVF="${ENV_FILE:-.env.prod}"
[ -f "$ENVF" ] || { echo "Arquivo $ENVF nao encontrado (copie de .env.prod.example)" >&2; exit 1; }
DC="docker compose -f docker-compose.prod.yml --env-file $ENVF"

echo "== [1/5] Build das imagens"
$DC build

if [ "$MODE" = "update" ]; then
  echo "== [2/5] Backup obrigatorio (banco + documentos)"
  scripts/prod/pg-backup.sh "${BACKUP_DEST:-backups}"
  scripts/prod/storage-backup.sh "${BACKUP_DEST:-backups}"
else
  echo "== [2/5] Primeiro deploy: sem backup (banco vazio). Subindo apenas o postgres"
  $DC up -d postgres
fi

echo "== [3/5] Migracao controlada"
$DC --profile migrate run --rm migrate

echo "== [4/5] Subindo servicos"
$DC up -d

echo "== [5/5] Smoke"
sleep 10
PROXY_PORT_VAL="$(grep -E '^PROXY_PORT=' "$ENVF" | cut -d= -f2 || true)"
GATE="$(grep -E '^GATE_KEY=' "$ENVF" | cut -d= -f2 || true)"
URL="http://localhost:${PROXY_PORT_VAL:-80}"
if curl -fsS -c /tmp/radar_gate.jar -o /dev/null "$URL/acesso?k=$GATE" -L && curl -fsS -b /tmp/radar_gate.jar "$URL/health"; then
  echo; echo "DEPLOY_OK"
else
  echo "SMOKE_FALHOU. Veja: $DC logs --tail=100 backend proxy" >&2
  echo "Rollback: git checkout <tag/commit anterior> && $0 update  (restore: docs/BACKUP-RESTORE.md)" >&2
  exit 1
fi
