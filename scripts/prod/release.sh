#!/usr/bin/env bash
# Passo executado NA VPS pelo GitHub Actions (via SSH), depois do checkout da tag.
#
#   printf '%s\n%s\n' "$GHCR_USER" "$GHCR_TOKEN" | scripts/prod/release.sh vX.Y.Z ghcr.io/<owner>/<repo>
#
# 1. valida a tag; 2. lê usuário/token do GHCR da STDIN (nunca por argumento/ambiente do
# processo remoto); 3. login em um DOCKER_CONFIG temporário (apagado ao sair: nenhuma
# credencial fica em disco) e pull das duas imagens da tag; 4. chama deploy.sh em modo
# `auto` (first/update decidido pelo estado do banco, com backup obrigatório em update).
#
# RELEASE_OFFLINE=1 pula login/pull (imagens já presentes; uso em testes locais).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

TAG="$(bash scripts/prod/validate-tag.sh "${1:-}")"
REPO="${2:-}"
printf '%s' "$REPO" | grep -Eq '^ghcr\.io/[a-z0-9._-]+/[a-z0-9._-]+$' \
  || { echo "ERRO: repositório de imagens inválido: '$REPO' (esperado ghcr.io/<owner>/<repo>)" >&2; exit 1; }
ENVF="${ENV_FILE:-.env.prod}"
[ -f "$ENVF" ] || { echo "ERRO: $ENVF não existe. Rode o bootstrap da VPS (scripts/prod/bootstrap-vps.sh) uma vez." >&2; exit 1; }

echo "== release $TAG ($(git rev-parse --short HEAD 2>/dev/null || echo sem-git)) repo=$REPO"
BACKEND="$REPO/backend:$TAG"; FRONTEND="$REPO/frontend:$TAG"

if [ "${RELEASE_OFFLINE:-0}" = "1" ]; then
  echo "RELEASE_OFFLINE=1: usando imagens locais, sem login/pull"
else
  IFS= read -r GH_USER || true
  IFS= read -r GH_TOKEN || true
  [ -n "${GH_USER:-}" ] && [ -n "${GH_TOKEN:-}" ] || { echo "ERRO: credencial do GHCR ausente na stdin (usuário e token, uma por linha)" >&2; exit 1; }
  CFG="$(mktemp -d)"
  trap 'rm -rf "$CFG"' EXIT
  printf '%s' "$GH_TOKEN" | DOCKER_CONFIG="$CFG" docker login ghcr.io -u "$GH_USER" --password-stdin >/dev/null \
    || { echo "ERRO: login no GHCR falhou (token sem permissão de leitura do pacote?)" >&2; exit 1; }
  unset GH_TOKEN
  for img in "$BACKEND" "$FRONTEND"; do
    echo "pull $img"
    DOCKER_CONFIG="$CFG" docker pull --quiet "$img" >/dev/null \
      || { echo "ERRO: pull falhou para $img (a publicação rodou? o pacote concede leitura ao token?)" >&2; exit 1; }
  done
  rm -rf "$CFG"; trap - EXIT
fi

export RADAR_IMAGE_TAG="$TAG" RADAR_IMAGE_REPO="$REPO"
exec bash scripts/prod/deploy.sh "${DEPLOY_MODE:-auto}"
