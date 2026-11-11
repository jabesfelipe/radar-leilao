# Radar Leilão — Deploy com Docker Compose (VPS única)

> **Fluxo oficial: deploy automático por tag** (`git push origin vX.Y.Z`) —
> `docs/GITHUB-ACTIONS-DEPLOY.md`. Este documento descreve o que roda **dentro da VPS** e os
> procedimentos manuais (operação, migrations, rollback). Não há deploy manual "paralelo".

Arquivo: `docker-compose.prod.yml` (projeto `radar-prod`). Variáveis: `.env.prod` (só na VPS,
gerado pelo `scripts/prod/bootstrap-vps.sh`) + `.release.env` (imagens da versão implantada,
gerado pelo deploy). **Na VPS use sempre** `DC=scripts/prod/compose.sh` (carrega os dois
arquivos), nunca `docker compose` direto — senão o compose tentaria as imagens locais `:latest`.

## 1. Serviços (Contabo Cloud VPS 6: 6 vCPU / ~11 GiB)

| Serviço | Imagem (na VPS) | Porta pública | Limite RAM | Papel |
|---|---|---|---|---|
| proxy | nginx:1.27-alpine | **80** (modo IP público) ou 127.0.0.1:8080 (Tailscale) | 64 MB | portão de acesso + roteamento `/api` e `/` |
| frontend | `ghcr.io/jabesfelipe/radar-leilao/frontend:vX.Y.Z` | — | 64 MB | React compilado servido por nginx |
| backend | `ghcr.io/jabesfelipe/radar-leilao/backend:vX.Y.Z` | — | 2 GB | FastAPI (uvicorn, 2 workers), usuário não-root |
| worker | mesma imagem do backend | — | 1 GB | embeddings pendentes (polling do banco) |
| postgres | pgvector/pgvector:pg16 | — | 2 GB | banco + pgvector (`shared_buffers` 768 MB) |
| migrate | mesma imagem do backend | — | — | one-shot (`--profile migrate`) |

Sem `BACKEND_IMAGE`/`FRONTEND_IMAGE` (simulação local) o compose constrói do código
(`radar-leilao-*-prod:latest`). Na VPS isso é **recusado** quando já existe `.release.env`.

Volumes persistentes: `radar-prod_postgres_data` (banco) e `radar-prod_backend_storage`
(documentos em `documents/`, temporários em `tmp/`). O nome de projeto fixo `radar-prod`
garante que **nunca** colidam com os volumes de desenvolvimento (`radar-leilao_*`).

O frontend é compilado com `VITE_API_URL` **vazio**: todas as chamadas vão para
`/api/...` no mesmo host do proxy. Não há dependência de `localhost`.

## 2. Cadeia de scripts executada pelo deploy por tag

```
GitHub Actions (release.yml, job deploy)
  └─ ssh radar@VPS: git checkout refs/tags/vX.Y.Z (confere o SHA)
       └─ scripts/prod/release.sh vX.Y.Z ghcr.io/jabesfelipe/radar-leilao
            ├─ valida a tag; login GHCR em DOCKER_CONFIG temporário (token pela stdin); pull
            └─ scripts/prod/deploy.sh auto   (RADAR_IMAGE_TAG/RADAR_IMAGE_REPO definidos)
                 [0/6] valida .env.prod + imagens
                 [1/6] confere as imagens da tag no Docker local (sem build)
                 [2/6] sobe só o PostgreSQL e lê o estado do banco
                 [3/6] first: banco vazio confirmado | update: backup banco + documentos (falha => aborta)
                 [4/6] migrate (alembic upgrade head)
                 [5/6] grava .release.env (+ .release.env.prev) e sobe os serviços (--no-build)
                 [6/6] smoke: /health 200 c/ cookie, 403 sem cookie, interface externa, versão em execução
```

Regras de `auto`, `first` e `update`: tabela em `docs/GITHUB-ACTIONS-DEPLOY.md §2`.
`first` e `update` explícitos continuam disponíveis e se recusam mutuamente (rc=2).

Validação do `.env.prod`: `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` (≥ 32) e `GATE_KEY`
(≥ 48 hex) preenchidos; `PROXY_BIND=0.0.0.0` só com `ALLOW_PUBLIC_HTTP=1`. O smoke não grava a
chave em disco nem a passa na linha de comando.

## 3. Reexecutar um deploy na própria VPS (emergência, sem GitHub)

As imagens da tag já estão no Docker local depois de um deploy. Para refazer a mesma versão:
```bash
cd /opt/radar-leilao
RELEASE_OFFLINE=1 scripts/prod/release.sh vX.Y.Z ghcr.io/jabesfelipe/radar-leilao
```
`RELEASE_OFFLINE=1` pula o login/pull (sem credencial). O caminho normal é sempre a tag.

## 4. Gate de schema (proteção)

O entrypoint de produção (`docker/backend-entrypoint.prod.sh`) **não** migra e compara
`alembic_version` do banco com a head do código. Se forem diferentes, o backend e o
worker **não iniciam** e registram:
```
[backend] ERRO: schema incompatível. banco=[...] código=[...]
```
Solução: publique a versão por tag (o deploy roda o `migrate`) ou siga §5. Não edite
`alembic_version` à mão.

## 5. Migrations — procedimento seguro

1. Backup: `scripts/prod/pg-backup.sh /opt/radar-backups`
2. Conferir versão: `$DC --profile migrate run --rm migrate sh -c "cd /app/backend && alembic current"`
   (o serviço `migrate` usa entrypoint `sh -c`; para só consultar, use
   `$DC run --rm --entrypoint sh migrate -c "cd /app/backend && alembic current && alembic heads"`)
3. Ensaio opcional em banco isolado: `scripts/prod/pg-restore-verify.sh <dump> radar_migr_rehearsal`
4. Aplicar: `$DC --profile migrate run --rm migrate`
5. Subir: `$DC up -d --no-build` (o gate confirma o schema)

Rotina normal: nada disso é manual — o deploy por tag faz backup → migrate → up.

Sobre a divergência histórica "banco em 0017 x código em 0023": no ambiente de
desenvolvimento a verificação direta (`SELECT version_num FROM alembic_version`) mostrou
o banco já em `0023_usuarios`; a divergência relatada antes não existe mais. Numa VPS nova
o banco nasce vazio e passa por `0001 -> head` pelo serviço `migrate`.

## 6. Rollback

Rollback de **código/imagem** e de **dados** são operações diferentes.

- **Imagem (sem migration nova):** `scripts/prod/rollback.sh` — volta para `.release.env.prev`
  sem build e sem tocar no banco. Confere antes que as heads do Alembic da versão anterior são
  iguais à revisão do banco; se não forem, recusa (rc=3) sem mudar nada.
- **Com migration nova:** o código antigo não conhece a revisão nova (o gate de schema impede
  o backend de subir). Ordem correta, manual e conferida:
  1. Ainda com a versão **nova** em execução, revise a migration e, se for reversível sem perda,
     `$DC run --rm --entrypoint sh migrate -c "cd /app/backend && alembic downgrade <revisão-anterior>"`
     (a revisão anterior aparece no passo `[3/6]` do log do deploy: `schema atual=...`);
  2. `scripts/prod/rollback.sh`.
  Se o downgrade não for seguro (dados novos, colunas removidas), restaure o backup gerado pelo
  deploy (§Dados) — nunca automático.
- **Alternativa preferida para bugs:** corrigir à frente com nova tag (`vX.Y.Z+1`).
- **Dados:** restaure o dump em banco isolado, valide e só então troque (`docs/BACKUP-RESTORE.md`).

## 7. Operação

```bash
$DC ps                          # estado e health
$DC logs -f --tail=100 backend  # logs (também: worker, proxy, postgres)
$DC restart worker              # reiniciar um serviço (estado do worker fica no banco)
docker stats --no-stream        # consumo de CPU/RAM
```
Proibido como rotina: `down -v`, remover volumes, `DROP`/`TRUNCATE`.

## 8. Memória (Contabo Cloud VPS 6: ~11 GiB RAM + 4 GB swap)

Tetos no compose: postgres 2 GB + backend 2 GB + worker 1 GB + nginx 0,13 GB ≈ **5,1 GB**,
deixando ~5,5 GB para SO, Docker, cache de disco do kernel (que o PostgreSQL usa via
`effective_cache_size=3GB`) e o `migrate`/backup que rodam ao lado no deploy.

Por que não "aumentar tudo": os dados do MVP são pequenos (~150 MB) e o consumo **medido** em
repouso é baixo; tetos existem para conter **picos** (extração de PDF grande; OCR) sem derrubar
o banco. Em repouso, medido na simulação local (`docker stats`):

| Container | RAM medida (repouso) | Teto anterior (4 GB) | Teto atual (11 GiB) |
|---|---:|---:|---:|
| proxy | 11 MB | 64 MB | 64 MB |
| frontend | 11 MB | 64 MB | 64 MB |
| worker | 61 MB | 700 MB | 1 GB |
| backend | 86 MB | 1000 MB (1 worker) | 2 GB (2 workers uvicorn) |
| postgres | 61 MB | 1200 MB (`shared_buffers` 384 MB) | 2 GB (`shared_buffers` 768 MB) |

- **2 workers uvicorn**: 6 vCPU permitem atender requisições enquanto um upload pesado é
  processado. Cada worker carrega a aplicação (~80–150 MB); o teto de 2 GB cobre os dois + pico
  de um PDF grande.
- **OCR continua desligado** (`OCR_ENABLED=false`). Se for ligado, observe `docker stats` num PDF
  escaneado longo antes de subir o teto do backend (3 GB é seguro nesta máquina).
- **LLM sem chave** (`OPENAI_API_KEY` vazio): nenhuma chamada paga; agentes registram `SEM_CHAVE`.
- Em VPS menor (4 GB) volte para `UVICORN_WORKERS=1` e os tetos da coluna "anterior".

## 9. Limpeza de temporários

`scripts/prod/cleanup-temp.sh` (dry-run por padrão) lista arquivos de `tmp/` com mais de
1 dia; `APPLY=true` remove. Nunca toca `documents/`.
