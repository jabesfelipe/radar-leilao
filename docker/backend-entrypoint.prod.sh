#!/usr/bin/env bash
# Entrypoint de PRODUÇÃO do backend.
#
# Diferença-chave vs. o entrypoint de desenvolvimento: NÃO aplica migrations
# automaticamente. Em produção, a migração do banco é um procedimento CONTROLADO
# (backup -> validação -> upgrade), executado por um passo dedicado (serviço
# `migrate` do compose de produção ou manualmente). Isso evita que um restart do
# container altere o schema do banco vivo sem backup/validação.
#
# Opcional: definir RUN_MIGRATIONS_ON_START=true habilita o upgrade no start (NÃO
# recomendado em produção). Default: apenas espera o banco e sobe a API.
set -euo pipefail

cd /app/backend

echo "[backend] Aguardando PostgreSQL em ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os, time, sys
import psycopg
host = os.getenv("POSTGRES_HOST", "postgres"); port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB", "radar_leilao"); user = os.getenv("POSTGRES_USER", "radar")
pwd = os.getenv("POSTGRES_PASSWORD", "radar_local")
dsn = f"host={host} port={port} dbname={db} user={user} password={pwd} connect_timeout=3"
for attempt in range(1, 61):
    try:
        with psycopg.connect(dsn):
            print(f"[backend] PostgreSQL disponível (tentativa {attempt})."); break
    except Exception as exc:
        print(f"[backend] PostgreSQL indisponível ainda ({type(exc).__name__}); aguardando...")
        time.sleep(2)
else:
    print("[backend] ERRO: PostgreSQL não ficou disponível a tempo.", file=sys.stderr); sys.exit(1)
PY

if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
  echo "[backend] RUN_MIGRATIONS_ON_START=true -> aplicando migrations..."
  alembic upgrade head
else
  echo "[backend] Migrations NÃO aplicadas no start (procedimento controlado). Verificando versão atual..."
  alembic current || true
fi

echo "[backend] Iniciando API (produção)..."
exec "$@"
