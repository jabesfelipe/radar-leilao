#!/usr/bin/env bash
# Wrapper do docker compose de produção: carrega .env.prod e, se existir, .release.env
# (BACKEND_IMAGE/FRONTEND_IMAGE da versão implantada por tag). Use este script no lugar de
# `docker compose ...` para que comandos manuais usem as MESMAS imagens do deploy.
#
#   scripts/prod/compose.sh ps
#   scripts/prod/compose.sh logs -f --tail=100 backend
#
# Variáveis: ENV_FILE (default .env.prod), RELEASE_ENV_FILE (default .release.env; vazio
# desativa). Caminhos relativos são resolvidos a partir da raiz do repositório.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ENVF="${ENV_FILE:-.env.prod}"
REL="${RELEASE_ENV_FILE-.release.env}"
[ -f "$ENVF" ] || { echo "compose.sh: $ENVF nao encontrado" >&2; exit 1; }
args=(-f docker-compose.prod.yml --env-file "$ENVF")
if [ -n "$REL" ] && [ -f "$REL" ]; then args+=(--env-file "$REL"); fi
exec docker compose "${args[@]}" "$@"
