# Radar Leilão — Guia de Implantação (VPS Linux)

Este guia permite subir o Radar Leilão numa VPS Linux limpa (Ubuntu 22.04+/Debian 12+)
usando Docker Compose de produção. **Não** cobre deploy automatizado em nuvem gerenciada;
é o caminho VPS + proxy reverso + HTTPS, adequado ao MVP.

> Regra de ouro: o PostgreSQL **não** é exposto à internet; o único ponto público é o
> proxy (80/443). Segredos vêm do `.env.prod` (nunca versionado).

## 1. Pré-requisitos na VPS

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker "$USER"   # reabra a sessão após isso
```

Recomendado (MVP): 2 vCPU, 4 GB RAM, 40 GB SSD. Ver `docs/CAPACITY-PLANNING.md` para
dimensionamento por volume de chunks.

## 2. Obter o código

```bash
git clone https://github.com/jabesfelipe/radar-leilao.git
cd radar-leilao
```

## 3. Configurar variáveis de ambiente

```bash
cp .env.prod.example .env.prod
# Edite .env.prod e preencha (NUNCA versione este arquivo):
#  - POSTGRES_PASSWORD        (openssl rand -base64 24)
#  - JWT_SECRET_KEY           (python -c "import secrets; print(secrets.token_urlsafe(48))")
#  - CORS_ALLOW_ORIGINS       (ex.: https://app.seudominio.com)
#  - VITE_API_URL=/api        (frontend chama a API pelo mesmo domínio atrás do proxy)
#  - (opcional) OPENAI_API_KEY, STORAGE_BACKEND=s3 + STORAGE_S3_*
#  - (opcional) AUTH_BOOTSTRAP_ADMIN_EMAIL/_PASSWORD para criar o 1º admin
```

## 4. Certificados HTTPS

Coloque os certificados em `infra/certs/fullchain.pem` e `infra/certs/privkey.pem`.
Para Let's Encrypt (certbot) via webroot:

```bash
sudo apt-get install -y certbot
# 1) suba só o proxy respondendo HTTP para o desafio ACME (porta 80)
# 2) emita o certificado:
sudo certbot certonly --webroot -w ./infra/certs/acme -d app.seudominio.com
# 3) copie/symlink fullchain.pem e privkey.pem para infra/certs/ e ajuste server_name
#    em docker/nginx-proxy.conf. Configure renovação (cron/systemd timer).
```

Ajuste `server_name` em `docker/nginx-proxy.conf` para o domínio real.

## 5. Subir a infraestrutura

```bash
# Build das imagens de produção + sobe postgres, backend, worker, frontend, proxy.
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

O PostgreSQL inicia com o volume persistente `postgres_data`. Na primeira subida o banco
está vazio — aplique as migrations de forma CONTROLADA (passo 6).

## 6. Migrations (procedimento controlado)

**Nunca** confie no start do backend para migrar (ele não migra por padrão). Use o
serviço dedicado `migrate` e o procedimento de `docs/DATABASE-MIGRATION.md`:

```bash
# Backup ANTES (em banco já populado). Na 1ª subida o banco está vazio, pode pular.
scripts/prod/pg-backup.sh backups

# Aplica a cadeia completa de migrations (0001 -> head) de forma controlada.
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile migrate run --rm migrate
```

## 7. Criar o administrador

Duas opções:
- **Bootstrap por ambiente:** defina `AUTH_BOOTSTRAP_ADMIN_EMAIL`/`_PASSWORD` no
  `.env.prod` ANTES de subir o backend (idempotente: cria só se não houver usuários).
- **Manual:** via endpoint `/api/auth/usuarios` autenticado como um admin já existente.

## 8. Validação pós-deploy

```bash
# Saúde dos serviços
curl -fsS https://app.seudominio.com/health         # backend via proxy
docker compose -f docker-compose.prod.yml ps         # todos "healthy"/"running"
# Readiness (autenticado) e métricas RAG: ver docs/OPERATIONS-RUNBOOK.md
```

Checklist completo em `docs/PRODUCTION-CHECKLIST.md`.

## 9. Operação contínua

- Backups: agende `scripts/prod/pg-backup.sh` (cron diário) em disco **separado**.
- Logs: já limitados (json-file, 10m x5) no compose.
- Atualização de versão: `git pull` → rebuild → `migrate` controlado → `up -d`.
- Storage de PDFs: `STORAGE_BACKEND=local` (volume) no MVP; `s3`/`minio` para desacoplar.

## 10. Serviços do compose de produção

| Serviço | Imagem | Exposto | Papel |
|---|---|---|---|
| postgres | pgvector/pgvector:pg16 | não (rede interna) | banco + pgvector |
| migrate | backend-prod (profile) | não | aplica Alembic sob demanda |
| backend | backend-prod (não-root) | não (via proxy) | API FastAPI (uvicorn workers) |
| worker | backend-prod | não | processa embeddings pendentes (polling DB) |
| frontend | frontend-prod (nginx) | não (via proxy) | SPA estático |
| proxy | nginx:1.27-alpine | 80/443 | HTTPS + roteamento /api e / |

## 11. Limitações conhecidas (produção)

- Embeddings exigem `OPENAI_API_KEY`; sem ela, o RAG opera por busca textual (sem vetor).
- HTTPS depende de certificados válidos em `infra/certs/` (certbot recomendado).
- Índice vetorial IVFFlat deve ser recriado após a primeira carga (ver `docs/RAG-ARCHITECTURE.md`).
- Backup é local por padrão; para produção séria, replicar para storage externo.
