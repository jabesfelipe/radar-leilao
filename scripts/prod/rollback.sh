#!/usr/bin/env bash
# Rollback de CÓDIGO/IMAGEM para a versão anterior (.release.env.prev) SEM tocar nos dados.
#
#   scripts/prod/rollback.sh
#
# Só prossegue se o schema do banco for compatível com a versão anterior (mesmas heads do
# Alembic). Se a versão atual aplicou migration nova, recusa e explica: voltar o código não
# desfaz o schema. Nesses casos o caminho é (a) `alembic downgrade` conferido manualmente ou
# (b) restaurar o backup gerado pelo deploy (docs/BACKUP-RESTORE.md). Nunca restaura dados
# sozinho, nunca usa down -v / DROP / TRUNCATE.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export ENV_FILE="${ENV_FILE:-.env.prod}"
[ -f "$ENV_FILE" ] || { echo "ERRO: $ENV_FILE nao encontrado (defina ENV_FILE ou rode na VPS)." >&2; exit 1; }
DC="bash scripts/prod/compose.sh"
CUR=".release.env"; PREV=".release.env.prev"
[ -f "$CUR" ]  || { echo "ERRO: $CUR ausente: nenhuma versão por tag implantada." >&2; exit 1; }
[ -f "$PREV" ] || { echo "ERRO: $PREV ausente: não há versão anterior registrada (primeiro deploy?)." >&2; exit 1; }
getv() { grep -E "^$2=" "$1" | tail -n1 | cut -d= -f2-; }
PB="$(getv "$PREV" BACKEND_IMAGE)"; PF="$(getv "$PREV" FRONTEND_IMAGE)"; PT="$(getv "$PREV" RADAR_RELEASE_TAG)"
CT="$(getv "$CUR" RADAR_RELEASE_TAG)"
for img in "$PB" "$PF"; do
  docker image inspect "$img" >/dev/null 2>&1 || { echo "ERRO: imagem anterior ausente localmente: $img (foi removida com docker prune?). Re-publique/baixe a tag $PT." >&2; exit 1; }
done
echo "== rollback $CT -> $PT"

echo "== compatibilidade de schema (heads do código anterior x banco)"
export BACKEND_IMAGE="$PB" FRONTEND_IMAGE="$PF"
raw="$($DC run -T --rm --no-deps --entrypoint sh migrate -c 'cd /app/backend && echo HEADS=$(alembic heads | sed "s/ (head)//" | sort | tr "\n" " ") && echo CURRENT=$(alembic current 2>/dev/null | sed "s/ (head)//" | sort | tr "\n" " ")' 2>&1 || true)"
HEADS="$(printf '%s\n' "$raw" | tr -d '\r' | sed -n 's/^HEADS=//p' | xargs)"
CURRENT="$(printf '%s\n' "$raw" | tr -d '\r' | sed -n 's/^CURRENT=//p' | xargs)"
echo "heads(código anterior)='$HEADS' banco='$CURRENT'"
if [ -z "$HEADS" ] || [ -z "$CURRENT" ]; then
  echo "ERRO: não consegui ler as revisões do Alembic. Saída do comando:" >&2
  printf '%s\n' "$raw" | tail -15 >&2
  exit 3
fi
if [ "$HEADS" != "$CURRENT" ]; then
  echo "ERRO: schema do banco ('$CURRENT') != heads da versão anterior ('$HEADS')." >&2
  echo "      A versão atual aplicou migration. Rollback de imagem NÃO é seguro sozinho." >&2
  echo "      Veja docs/DOCKER-DEPLOYMENT.md §6 (downgrade conferido ou restore do backup)." >&2
  exit 3
fi

echo "== subindo versão anterior (sem build)"
$DC up -d --no-build
$DC restart proxy
( umask 077; cp -p "$CUR" "$CUR.rolledback"; cp -p "$PREV" "$CUR" )
ok=0
for _ in $(seq 1 24); do
  st="$(docker inspect -f '{{.State.Health.Status}}' radar-prod-backend 2>/dev/null || true)"
  [ "$st" = "healthy" ] && { ok=1; break; }; sleep 5
done
got="$(docker inspect -f '{{.Config.Image}}' radar-prod-backend 2>/dev/null || true)"
if [ "$ok" = "1" ] && [ "$got" = "$PB" ]; then echo "ROLLBACK_OK versao=$PT"; else echo "ROLLBACK_FALHOU (backend=$st imagem=$got). Veja: $DC logs --tail=100 backend" >&2; exit 1; fi
