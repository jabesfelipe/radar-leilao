#!/usr/bin/env bash
# Consulta e salva logs dos containers do Radar Leilão (somente leitura).
# Não altera containers, volumes ou dados.
#
# Uso:
#   ./scripts/logs.sh status            # containers, estado, portas e saúde
#   ./scripts/logs.sh tail [servico]    # últimos logs (todos ou de um serviço)
#   ./scripts/logs.sh follow [servico]  # acompanha em tempo real (Ctrl+C encerra)
#   ./scripts/logs.sh save              # salva um snapshot em logs/radar-<timestamp>.log
#
# Serviços válidos: backend | frontend | postgres
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TAIL_LINES="${TAIL_LINES:-200}"
VALID_SERVICES="backend frontend postgres"

usage() {
  sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

valid_service() {
  case " $VALID_SERVICES " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

cmd="${1:-status}"
service="${2:-}"

if [ -n "$service" ] && ! valid_service "$service"; then
  echo "[logs] Serviço inválido: '$service'. Use: ${VALID_SERVICES}" >&2
  exit 2
fi

case "$cmd" in
  status)
    echo "[logs] Containers da stack:"
    docker compose ps
    echo
    echo "[logs] Saúde (quando disponível):"
    for c in radar-leilao-postgres radar-leilao-backend radar-leilao-frontend; do
      if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
        health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}sem healthcheck{{end}}' "$c" 2>/dev/null || echo desconhecido)"
        state="$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null || echo desconhecido)"
        printf '  %-26s %s (%s)\n' "$c" "$state" "$health"
      else
        printf '  %-26s %s\n' "$c" "não está em execução"
      fi
    done
    ;;
  tail)
    if [ -n "$service" ]; then
      docker compose logs --tail "$TAIL_LINES" "$service"
    else
      docker compose logs --tail "$TAIL_LINES"
    fi
    ;;
  follow)
    echo "[logs] Acompanhando logs em tempo real (Ctrl+C para sair; containers não são afetados)."
    if [ -n "$service" ]; then
      docker compose logs -f --tail "$TAIL_LINES" "$service"
    else
      docker compose logs -f --tail "$TAIL_LINES"
    fi
    ;;
  save)
    mkdir -p logs
    stamp="$(date +%Y%m%d-%H%M%S)"
    out="logs/radar-${stamp}.log"
    {
      echo "===== Radar Leilão — snapshot de logs ($(date -Iseconds)) ====="
      echo
      echo "----- docker compose ps -----"
      docker compose ps
      echo
      echo "----- logs (todos os serviços) -----"
      docker compose logs --no-color --tail "${SAVE_LINES:-1000}"
    } > "$out" 2>&1
    echo "[logs] Snapshot salvo em: ${out}"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "[logs] Comando desconhecido: '$cmd'" >&2
    usage
    exit 2
    ;;
esac
