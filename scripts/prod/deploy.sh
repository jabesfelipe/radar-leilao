#!/usr/bin/env bash
# Deploy controlado do Radar Leilão na VPS (executar DENTRO do diretório do projeto).
#
#   scripts/prod/deploy.sh first    # 1º deploy: EXIGE banco vazio (sem alembic_version)
#   scripts/prod/deploy.sh update   # atualização: EXIGE instalação existente + backup OK
#
# first : valida .env -> build -> sobe postgres -> confirma banco VAZIO -> migrate -> up -> smoke
# update: valida .env -> build -> sobe postgres -> confirma instalação EXISTENTE ->
#         backup banco+documentos (aborta se falhar) -> migrate -> up -> smoke
# Os modos se recusam mutuamente: `first` em instalação existente aborta (evita pular o
# backup); `update` em banco vazio aborta (evita "atualizar" o nada sem perceber).
# Nada aqui usa down -v, DROP, TRUNCATE ou remove volumes.
set -euo pipefail
MODE="${1:-}"
[ "$MODE" = "first" ] || [ "$MODE" = "update" ] || { echo "Uso: $0 first|update" >&2; exit 1; }
ENVF="${ENV_FILE:-.env.prod}"
[ -f "$ENVF" ] || { echo "Arquivo $ENVF nao encontrado (copie de .env.prod.example)" >&2; exit 1; }
DC="docker compose -f docker-compose.prod.yml --env-file $ENVF"
PG_CONTAINER="radar-prod-postgres"

# Lê UMA chave do .env sem executar o arquivo (valor pode conter '=').
envval() { grep -E "^$1=" "$ENVF" | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true; }

echo "== [0/6] Validando $ENVF"
fail=0
for k in POSTGRES_PASSWORD JWT_SECRET_KEY GATE_KEY; do
  [ -n "$(envval "$k")" ] || { echo "ERRO: $k vazio em $ENVF" >&2; fail=1; }
done
GATE="$(envval GATE_KEY)"
if ! printf '%s' "$GATE" | grep -Eq '^[0-9a-f]{48,}$'; then
  echo "ERRO: GATE_KEY deve ter >= 48 caracteres hexadecimais (openssl rand -hex 24)" >&2; fail=1
fi
JWT="$(envval JWT_SECRET_KEY)"
if [ -n "$JWT" ] && [ "${#JWT}" -lt 32 ]; then
  echo "ERRO: JWT_SECRET_KEY curto (< 32). Use openssl rand -base64 48" >&2; fail=1
fi
unset JWT
BIND="$(envval PROXY_BIND)"; BIND="${BIND:-127.0.0.1}"
PORT="$(envval PROXY_PORT)"; PORT="${PORT:-8080}"
if [ "$BIND" = "0.0.0.0" ] && [ "$(envval ALLOW_PUBLIC_HTTP)" != "1" ]; then
  echo "ERRO: PROXY_BIND=0.0.0.0 expõe HTTP sem TLS na internet (o Docker ignora o UFW)." >&2
  echo "      Use o modo Tailscale (PROXY_BIND=127.0.0.1) ou confirme com ALLOW_PUBLIC_HTTP=1." >&2
  fail=1
fi
[ -n "$(envval ADMIN_API_TOKEN)" ] && echo "AVISO: ADMIN_API_TOKEN definido; não é repassado ao backend pelo compose." >&2
[ "$fail" -eq 0 ] || exit 1
[ "$(stat -c %a "$ENVF" 2>/dev/null || echo 600)" = "600" ] || echo "AVISO: rode chmod 600 $ENVF" >&2
if [ "$BIND" = "0.0.0.0" ]; then
  echo "AVISO: modo IP PÚBLICO por HTTP (ALLOW_PUBLIC_HTTP=1) na porta $PORT — ambiente TEMPORÁRIO de testes."
  echo "       Senha, token, cookie do portão e documentos trafegam sem criptografia."
fi

echo "== [1/6] Build das imagens"
$DC build

echo "== [2/6] Subindo apenas o PostgreSQL"
$DC up -d --wait postgres
PGUSER="$(envval POSTGRES_USER)"; PGUSER="${PGUSER:-radar}"
PGDB="$(envval POSTGRES_DB)"; PGDB="${PGDB:-radar_leilao}"
# Duas consultas: o PostgreSQL valida a tabela de uma subconsulta mesmo num ramo de CASE
# não executado, então ler alembic_version num banco vazio daria erro.
HAS_ALEMBIC="$(docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$PGDB" -tAc \
  "select to_regclass('public.alembic_version') is not null" | tr -d '[:space:]')"
REV=""
if [ "$HAS_ALEMBIC" = "t" ]; then
  REV="$(docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$PGDB" -tAc \
    "select coalesce(max(version_num),'') from alembic_version" | tr -d '[:space:]')"
fi
TABLES="$(docker exec "$PG_CONTAINER" psql -U "$PGUSER" -d "$PGDB" -tAc \
  "select count(*) from information_schema.tables where table_schema='public'" | tr -d '[:space:]')"

if [ "$MODE" = "first" ]; then
  if [ -n "$REV" ] || [ "${TABLES:-0}" -gt 0 ]; then
    echo "ERRO: banco NÃO está vazio (alembic='${REV:-nenhum}', tabelas=$TABLES)." >&2
    echo "      Isto é uma instalação existente: use '$0 update' (faz backup antes)." >&2
    exit 2
  fi
  echo "== [3/6] Primeiro deploy: banco vazio confirmado (nada a salvar)"
else
  if [ -z "$REV" ]; then
    echo "ERRO: nenhuma instalação encontrada (sem alembic_version). Use '$0 first'." >&2
    exit 2
  fi
  echo "== [3/6] Atualização: schema atual=$REV. Backup obrigatório (banco + documentos)"
  DEST="$(envval BACKUP_DEST)"; DEST="${DEST:-backups}"
  POSTGRES_USER="$PGUSER" POSTGRES_DB="$PGDB" scripts/prod/pg-backup.sh "$DEST"
  scripts/prod/storage-backup.sh "$DEST"
fi

echo "== [4/6] Migração controlada"
$DC --profile migrate run --rm migrate

echo "== [5/6] Subindo serviços"
$DC up -d
# O template do nginx é um arquivo montado: mudança nele (ou na GATE_KEY já aplicada) não
# recria o container. Reiniciar refaz o envsubst e recarrega a config.
$DC restart proxy

echo "== [6/6] Smoke (via proxy, com o cookie do portão; sem gravar a chave em disco/argv)"
HOST="$BIND"; [ "$HOST" = "0.0.0.0" ] && HOST="127.0.0.1"
URL="http://${HOST}:${PORT}"
ok=0
for _ in $(seq 1 24); do
  code="$(printf 'header = "Cookie: radar_gate=%s"\n' "$GATE" | curl -s -o /dev/null -w '%{http_code}' -K - "$URL/health" || true)"
  [ "$code" = "200" ] && { ok=1; break; }
  sleep 5
done
nogate="$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/imoveis" || true)"
ext="n/a"
if [ "$BIND" = "0.0.0.0" ]; then
  # Modo IP público: confirma que o proxy responde também pela interface externa.
  PUBIP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [ -n "$PUBIP" ]; then
    ext="$(curl -s -o /dev/null -w '%{http_code}' "http://${PUBIP}:${PORT}/_proxy_health" || true)"
  fi
fi
if [ "$ok" = "1" ] && [ "$nogate" = "403" ] && { [ "$ext" = "n/a" ] || [ "$ext" = "200" ]; }; then
  echo "health=200 sem_cookie=$nogate interface_externa=$ext"; echo "DEPLOY_OK"
  if [ "$BIND" = "0.0.0.0" ]; then
    SUF=""; [ "$PORT" = "80" ] || SUF=":$PORT"
    echo "AMBIENTE TEMPORÁRIO DE TESTES (HTTP sem TLS; não use dados sensíveis)."
    echo "1º acesso em cada dispositivo: http://${PUBIP:-IP_DA_VPS}${SUF}/acesso?k=<GATE_KEY do $ENVF>"
    echo "Depois: http://${PUBIP:-IP_DA_VPS}${SUF}"
  fi
else
  echo "SMOKE_FALHOU (health ok=$ok, sem_cookie=$nogate, interface_externa=$ext). Veja: $DC logs --tail=100 backend proxy" >&2
  echo "Rollback: docs/DOCKER-DEPLOYMENT.md §Rollback (código anterior + restore do backup recém-gerado)." >&2
  exit 1
fi
