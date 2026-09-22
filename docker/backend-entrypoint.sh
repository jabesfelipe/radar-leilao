#!/usr/bin/env bash
# Entrypoint do backend: espera o PostgreSQL, aplica migrations e sobe a API.
# Reutiliza o mecanismo oficial (Alembic) — não cria estratégia paralela.
set -euo pipefail

cd /app/backend

echo "[backend] Aguardando PostgreSQL em ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os, time, sys
import psycopg

host = os.getenv("POSTGRES_HOST", "postgres")
port = os.getenv("POSTGRES_PORT", "5432")
db   = os.getenv("POSTGRES_DB", "radar_leilao")
user = os.getenv("POSTGRES_USER", "radar")
pwd  = os.getenv("POSTGRES_PASSWORD", "radar_local")

dsn = f"host={host} port={port} dbname={db} user={user} password={pwd} connect_timeout=3"
for attempt in range(1, 61):
    try:
        with psycopg.connect(dsn):
            print(f"[backend] PostgreSQL disponível (tentativa {attempt}).")
            break
    except Exception as exc:
        print(f"[backend] PostgreSQL indisponível ainda ({type(exc).__name__}); aguardando...")
        time.sleep(2)
else:
    print("[backend] ERRO: PostgreSQL não ficou disponível a tempo.", file=sys.stderr)
    sys.exit(1)
PY

echo "[backend] Aplicando migrations (alembic upgrade head)..."
alembic upgrade head

echo "[backend] Migrations aplicadas. Iniciando API..."
exec "$@"
