#!/usr/bin/env bash
# Valida uma tag de versão do Radar Leilão: somente vMAJOR.MINOR.PATCH (ex.: v1.0.0).
# Usada pelo workflow de release (gatilho de deploy) e por scripts/prod/release.sh.
# Pré-lançamentos (v1.0.0-rc1), prefixos ausentes (1.0.0) ou lixo são RECUSADOS.
#   scripts/prod/validate-tag.sh v1.2.3   -> imprime v1.2.3, rc=0
set -euo pipefail
TAG="${1:-}"
if printf '%s' "$TAG" | grep -Eq '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'; then
  printf '%s\n' "$TAG"
else
  echo "tag invalida: '$TAG' (use vMAJOR.MINOR.PATCH, ex.: v1.0.0)" >&2
  exit 1
fi
