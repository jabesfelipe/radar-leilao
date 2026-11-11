#!/usr/bin/env bash
# Restauração de documentos para um volume ISOLADO e VAZIO, com verificação por hash.
#
# Segurança: recusa restaurar sobre volume com conteúdo (nunca sobrescreve) e exige
# confirmação digitada, a menos que ASSUME_YES=true (uso em teste automatizado).
# O volume padrão de produção NÃO é aceito como destino de verificação.
#
# Uso: scripts/prod/storage-restore.sh <storage-STAMP.tar.gz> <VOLUME_DESTINO>
set -euo pipefail
TAR="${1:-}"; TARGET="${2:-}"
[ -f "$TAR" ] || { echo "Uso: $0 <storage-STAMP.tar.gz> <VOLUME_DESTINO>" >&2; exit 1; }
[ -n "$TARGET" ] || { echo "Informe o volume de destino" >&2; exit 1; }
MANIFEST="${TAR%.tar.gz}.sha256"
[ -f "$MANIFEST" ] || { echo "Manifesto nao encontrado: $MANIFEST" >&2; exit 1; }

case "$TARGET" in
  radar-prod_backend_storage|radar-leilao_backend_storage)
    echo "[storage-restore] RECUSADO: '$TARGET' e um volume em uso. Use um volume novo (ex.: radar_restore_check_storage)." >&2; exit 2 ;;
esac

if docker volume inspect "$TARGET" >/dev/null 2>&1; then
  N=$(docker run --rm -v "$TARGET":/s alpine sh -c 'find /s -mindepth 1 | wc -l')
  [ "$N" = "0" ] || { echo "[storage-restore] RECUSADO: volume '$TARGET' nao esta vazio ($N itens)." >&2; exit 2; }
else
  docker volume create "$TARGET" >/dev/null
fi

if [ "${ASSUME_YES:-false}" != "true" ]; then
  read -r -p "Restaurar $TAR no volume '$TARGET'? Digite RESTAURAR: " ans
  [ "$ans" = "RESTAURAR" ] || { echo "Cancelado. Nada foi alterado."; exit 0; }
fi

TAR_ABS="$(cd "$(dirname "$TAR")" && pwd)/$(basename "$TAR")"
MAN_ABS="$(cd "$(dirname "$MANIFEST")" && pwd)/$(basename "$MANIFEST")"
docker run --rm -v "$TARGET":/s -v "$TAR_ABS":/in.tar.gz:ro -v "$MAN_ABS":/in.sha256:ro alpine sh -c "
  tar xzf /in.tar.gz -C /s &&
  cd /s && sha256sum -c -s /in.sha256 && echo \"hashes conferidos: \$(wc -l < /in.sha256) arquivo(s)\""
echo "[storage-restore] OK: arquivos restaurados em '$TARGET' e hashes conferidos."
