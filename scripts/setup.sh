#!/usr/bin/env bash
# Radar Leilão — setup local completo (WSL2 + Docker).
# Prepara um notebook novo: valida Docker, cria .env, sobe a stack, aplica
# migrations (automaticamente pelo backend) e mostra as URLs.
set -euo pipefail

# Raiz do projeto (um nível acima de scripts/)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info()  { printf '\033[0;36m[setup]\033[0m %s\n' "$*"; }
ok()    { printf '\033[0;32m[ok]\033[0m %s\n' "$*"; }
warn()  { printf '\033[0;33m[aviso]\033[0m %s\n' "$*"; }
err()   { printf '\033[0;31m[erro]\033[0m %s\n' "$*" >&2; }

# 1) Docker instalado?
if ! command -v docker >/dev/null 2>&1; then
  err "Docker não encontrado. Instale o Docker Desktop com integração ao WSL2."
  err "Guia: docs/LOCAL-SETUP.md (seção 'Instalar Docker Desktop')."
  exit 1
fi
ok "Docker encontrado: $(docker --version)"

# 2) Docker Compose (plugin v2)?
if ! docker compose version >/dev/null 2>&1; then
  err "'docker compose' não disponível. Atualize o Docker Desktop."
  exit 1
fi
ok "Docker Compose encontrado: $(docker compose version | head -n1)"

# 3) Docker Engine acessível?
if ! docker info >/dev/null 2>&1; then
  err "O Docker está instalado mas o Engine não respondeu. Abra o Docker Desktop e aguarde ficar 'Running'."
  exit 1
fi
ok "Docker Engine acessível."

# 4) .env
if [ ! -f .env ]; then
  info "Arquivo .env não existe; criando a partir de .env.example..."
  cp .env.example .env
  ok ".env criado. (Rode sem LLM deixando OPENAI_API_KEY vazio.)"
else
  ok ".env já existe (mantido)."
fi

# 5) Subir infraestrutura e aplicar build
info "Subindo a stack (postgres, backend, frontend). O primeiro build pode demorar alguns minutos..."
docker compose up -d --build

# 6) Aguardar backend saudável (o backend já espera o Postgres e aplica migrations)
info "Aguardando o backend ficar saudável (inclui migrations)..."
if docker compose ps --format '{{.Service}}' | grep -q backend; then
  for i in $(seq 1 60); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}nohealth{{end}}' radar-leilao-backend 2>/dev/null || echo missing)"
    case "$status" in
      healthy) ok "Backend saudável."; break ;;
      unhealthy) err "Backend ficou 'unhealthy'. Veja: docker compose logs backend"; break ;;
      *) sleep 3 ;;
    esac
    if [ "$i" = "60" ]; then warn "Backend ainda não reportou 'healthy'. Verifique: docker compose logs backend"; fi
  done
fi

# 7) Health geral
info "Executando verificação de saúde..."
bash "$ROOT_DIR/scripts/health.sh" || warn "Alguns componentes não responderam; veja os logs."

cat <<EOF

============================================================
 Radar Leilão preparado.

 Frontend: http://localhost:${FRONTEND_PORT:-5173}
 Backend:  http://localhost:${BACKEND_PORT:-8000}
 Swagger:  http://localhost:${BACKEND_PORT:-8000}/docs

 Parar:      ./scripts/stop.sh
 Iniciar:    ./scripts/start.sh
 Saúde:      ./scripts/health.sh
============================================================
EOF
