#!/usr/bin/env bash
# OPERAÇÃO DESTRUTIVA: remove containers E volumes (apaga o banco e o storage).
# Exige confirmação explícita. NÃO faz parte do setup normal.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cat <<'EOF'
ATENÇÃO:
Esta operação pode apagar os dados locais do Radar Leilão
(banco PostgreSQL e arquivos de documentos no volume de storage).

Recomendado: gere um backup antes com ./scripts/backup.sh
EOF

read -r -p "Deseja continuar? [y/N] " resposta
case "${resposta:-N}" in
  y|Y|yes|YES|s|S|sim|SIM)
    echo "[reset] Removendo containers e volumes..."
    docker compose down -v
    echo "[reset] Concluído. Rode ./scripts/setup.sh para recriar o ambiente do zero."
    ;;
  *)
    echo "[reset] Cancelado. Nada foi apagado."
    exit 0
    ;;
esac
