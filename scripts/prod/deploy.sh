#!/usr/bin/env bash
# Deploy controlado do Radar Leilão na VPS (executar a partir da raiz do repositório).
#
#   scripts/prod/deploy.sh auto     # decide pelo ESTADO do banco (usado pelo deploy por tag)
#   scripts/prod/deploy.sh first    # 1º deploy: EXIGE banco vazio (sem alembic_version)
#   scripts/prod/deploy.sh update   # atualização: EXIGE instalação existente + backup OK
#
# ORIGEM DAS IMAGENS
#   - Pull mode (deploy por tag): RADAR_IMAGE_TAG=vX.Y.Z e RADAR_IMAGE_REPO=ghcr.io/<owner>/<repo>.
#     As imagens publicadas JÁ DEVEM estar no Docker local (scripts/prod/release.sh faz o
#     pull). Nada é construído na VPS.
#   - Build local (sem RADAR_IMAGE_TAG): constrói do código. Só para simulação/desenvolvimento.
#
# Fluxo: valida .env -> (build | confere imagens) -> sobe postgres -> resolve o modo pelo
#        estado do banco -> [update: backup banco+documentos; falhou => ABORTA antes de migrar]
#        -> migrate -> sobe serviços (sem build) -> smoke (inclui conferência de versão).
# Os modos se recusam mutuamente: `first` em instalação existente aborta (evita pular o
# backup); `update` em banco vazio aborta (evita "atualizar" o nada sem perceber); `auto`
# aborta se o banco está vazio mas já houve um deploy (.release.env): possível perda de dados.
# Nada aqui usa down -v, DROP, TRUNCATE ou remove volumes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
MODE="${1:-}"
case "$MODE" in first|update|auto) ;; *) echo "Uso: $0 auto|first|update" >&2; exit 1 ;; esac
ENVF="${ENV_FILE:-.env.prod}"
[ -f "$ENVF" ] || { echo "Arquivo $ENVF nao encontrado (copie de .env.prod.example)" >&2; exit 1; }
export ENV_FILE="$ENVF"
# Chamadas entre scripts via `bash`: não dependem do bit de execução no checkout.
DC="bash scripts/prod/compose.sh"
PG_CONTAINER="radar-prod-postgres"
RELFILE=".release.env"

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

# --- Origem das imagens ---------------------------------------------------------
IMG_TAG="${RADAR_IMAGE_TAG:-}"
PULL_MODE=0
if [ -n "$IMG_TAG" ]; then
  PULL_MODE=1
  bash scripts/prod/validate-tag.sh "$IMG_TAG" >/dev/null || fail=1
  REPO="${RADAR_IMAGE_REPO:-}"
  if ! printf '%s' "$REPO" | grep -Eq '^ghcr\.io/[a-z0-9._-]+/[a-z0-9._-]+$'; then
    echo "ERRO: RADAR_IMAGE_REPO invalido ('$REPO'); esperado ghcr.io/<owner>/<repo> em minusculas" >&2; fail=1
  fi
  export BACKEND_IMAGE="$REPO/backend:$IMG_TAG" FRONTEND_IMAGE="$REPO/frontend:$IMG_TAG"
elif [ -f "$RELFILE" ]; then
  echo "ERRO: $RELFILE existe: esta instalação é gerenciada por tags (imagens publicadas)." >&2
  echo "      Defina RADAR_IMAGE_TAG/RADAR_IMAGE_REPO (use scripts/prod/release.sh) em vez de build local." >&2
  fail=1
fi
[ "$fail" -eq 0 ] || exit 1
[ "$(stat -c %a "$ENVF" 2>/dev/null || echo 600)" = "600" ] || echo "AVISO: rode chmod 600 $ENVF" >&2
if [ "$BIND" = "0.0.0.0" ]; then
  echo "AVISO: modo IP PÚBLICO por HTTP (ALLOW_PUBLIC_HTTP=1) na porta $PORT — ambiente TEMPORÁRIO de testes."
  echo "       Senha, token, cookie do portão e documentos trafegam sem criptografia."
fi

if [ "$PULL_MODE" = "1" ]; then
  echo "== [1/6] Imagens publicadas $IMG_TAG (sem build na VPS)"
  for img in "$BACKEND_IMAGE" "$FRONTEND_IMAGE"; do
    docker image inspect "$img" >/dev/null 2>&1 || { echo "ERRO: imagem ausente no Docker local: $img (rode scripts/prod/release.sh ou docker pull)" >&2; exit 1; }
    echo "imagem ok: $img ($(docker image inspect -f '{{.Id}}' "$img" | cut -c1-19))"
  done
  UPFLAGS="--no-build"
else
  echo "== [1/6] Build local das imagens (modo desenvolvimento/simulação)"
  $DC build
  UPFLAGS=""
fi

echo "== [2/6] Subindo apenas o PostgreSQL"
$DC up -d --wait $UPFLAGS postgres
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

# Resolve `auto` pelo estado real do banco.
if [ "$MODE" = "auto" ]; then
  if [ -n "$REV" ]; then
    MODE=update
  elif [ "${TABLES:-0}" -eq 0 ]; then
    if [ -f "$RELFILE" ]; then
      echo "ERRO: banco VAZIO, mas $RELFILE indica que esta VPS já recebeu um deploy." >&2
      echo "      Possível perda do volume do banco. NÃO vou recriar do zero automaticamente." >&2
      echo "      Restaure o último backup (docs/BACKUP-RESTORE.md) ou, se for intencional, apague $RELFILE." >&2
      exit 2
    fi
    MODE=first
  else
    echo "ERRO: banco sem alembic_version mas com $TABLES tabela(s): estado desconhecido. Investigue antes." >&2
    exit 2
  fi
  echo "modo resolvido: $MODE (alembic='${REV:-nenhum}', tabelas=$TABLES)"
fi

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
  # set -e: qualquer falha aqui ABORTA o deploy antes de qualquer migration.
  POSTGRES_USER="$PGUSER" POSTGRES_DB="$PGDB" bash scripts/prod/pg-backup.sh "$DEST"
  bash scripts/prod/storage-backup.sh "$DEST"
fi

echo "== [4/6] Migração controlada"
$DC --profile migrate run --rm migrate

echo "== [5/6] Subindo serviços"
if [ "$PULL_MODE" = "1" ]; then
  # Ponto sem volta: migrations aplicadas. Registra a versão (e guarda a anterior p/ rollback).
  [ -f "$RELFILE" ] && cp -p "$RELFILE" "$RELFILE.prev"
  ( umask 077; printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\nRADAR_RELEASE_TAG=%s\n' \
      "$BACKEND_IMAGE" "$FRONTEND_IMAGE" "$IMG_TAG" > "$RELFILE" )
fi
$DC up -d $UPFLAGS
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
# Versão em execução == versão pedida (só em pull mode).
ver="n/a"
if [ "$PULL_MODE" = "1" ]; then
  ver="ok"
  for pair in "radar-prod-backend:$BACKEND_IMAGE" "radar-prod-worker:$BACKEND_IMAGE" "radar-prod-frontend:$FRONTEND_IMAGE"; do
    got="$(docker inspect -f '{{.Config.Image}}' "${pair%%:*}" 2>/dev/null || true)"
    [ "$got" = "${pair#*:}" ] || { ver="DIVERGENTE(${pair%%:*}=$got)"; }
  done
fi
if [ "$ok" = "1" ] && [ "$nogate" = "403" ] && { [ "$ext" = "n/a" ] || [ "$ext" = "200" ]; } && { [ "$ver" = "n/a" ] || [ "$ver" = "ok" ]; }; then
  echo "health=200 sem_cookie=$nogate interface_externa=$ext versao=${IMG_TAG:-build-local}($ver) modo=$MODE"; echo "DEPLOY_OK"
  if [ "$BIND" = "0.0.0.0" ]; then
    SUF=""; [ "$PORT" = "80" ] || SUF=":$PORT"
    echo "AMBIENTE TEMPORÁRIO DE TESTES (HTTP sem TLS; não use dados sensíveis)."
    echo "1º acesso em cada dispositivo: http://${PUBIP:-IP_DA_VPS}${SUF}/acesso?k=<GATE_KEY do $ENVF>"
    echo "Depois: http://${PUBIP:-IP_DA_VPS}${SUF}"
  fi
else
  echo "SMOKE_FALHOU (health ok=$ok, sem_cookie=$nogate, interface_externa=$ext, versao=$ver). Veja: scripts/prod/compose.sh logs --tail=100 backend proxy" >&2
  echo "Rollback de código/imagem: scripts/prod/rollback.sh | dados: docs/BACKUP-RESTORE.md" >&2
  exit 1
fi
