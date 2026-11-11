# Radar Leilão — Deploy com Docker Compose (VPS única)

Arquivo: `docker-compose.prod.yml` (projeto `radar-prod`). Variáveis: `.env.prod`
(modelo em `.env.prod.example`). Atalho: `DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"`.

## 1. Serviços

| Serviço | Imagem | Porta pública | Limite RAM | Papel |
|---|---|---|---|---|
| proxy | nginx:1.27-alpine | **80** (único) | 64 MB | portão de acesso + roteamento `/api` e `/` |
| frontend | radar-leilao-frontend-prod | — | 64 MB | React compilado servido por nginx |
| backend | radar-leilao-backend-prod | — | 1000 MB | FastAPI (uvicorn, 1 worker), usuário não-root |
| worker | radar-leilao-backend-prod | — | 700 MB | embeddings pendentes (polling do banco) |
| postgres | pgvector/pgvector:pg16 | — | 1200 MB | banco + pgvector (tunado p/ 4 GB) |
| migrate | radar-leilao-backend-prod | — | — | one-shot (`--profile migrate`) |

Volumes persistentes: `radar-prod_postgres_data` (banco) e `radar-prod_backend_storage`
(documentos em `documents/`, temporários em `tmp/`). O nome de projeto fixo `radar-prod`
garante que **nunca** colidam com os volumes de desenvolvimento (`radar-leilao_*`).

O frontend é compilado com `VITE_API_URL` **vazio**: todas as chamadas vão para
`/api/...` no mesmo host do proxy. Não há dependência de `localhost`.

## 2. Primeiro deploy (banco vazio)

```bash
scripts/prod/deploy.sh first
```
Equivalente manual:
```bash
$DC build
$DC up -d postgres
$DC --profile migrate run --rm migrate      # 0001 -> head
$DC up -d
```

## 3. Atualização de instalação existente

```bash
git fetch && git checkout <tag ou commit>
scripts/prod/deploy.sh update     # backup banco+docs -> build -> migrate -> up -> smoke
```

## 4. Gate de schema (proteção)

O entrypoint de produção (`docker/backend-entrypoint.prod.sh`) **não** migra e compara
`alembic_version` do banco com a head do código. Se forem diferentes, o backend e o
worker **não iniciam** e registram:
```
[backend] ERRO: schema incompatível. banco=[...] código=[...]
```
Solução: rode a migração controlada (§3). Não edite `alembic_version` à mão.

## 5. Migrations — procedimento seguro

1. Backup: `scripts/prod/pg-backup.sh /opt/radar-backups`
2. Conferir versão: `$DC --profile migrate run --rm migrate sh -c "cd /app/backend && alembic current"`
   (o serviço `migrate` usa entrypoint `sh -c`; para só consultar, use
   `$DC run --rm --entrypoint sh migrate -c "cd /app/backend && alembic current && alembic heads"`)
3. Ensaio opcional em banco isolado: `scripts/prod/pg-restore-verify.sh <dump> radar_migr_rehearsal`
4. Aplicar: `$DC --profile migrate run --rm migrate`
5. Subir: `$DC up -d` (o gate confirma o schema)

Sobre a divergência histórica "banco em 0017 x código em 0023": no ambiente de
desenvolvimento a verificação direta (`SELECT version_num FROM alembic_version`) mostrou
o banco já em `0023_usuarios`; a divergência relatada antes não existe mais. Numa VPS nova
o banco nasce vazio e passa por `0001 -> head` pelo serviço `migrate`.

## 6. Rollback

- **Código:** `git checkout <tag anterior> && scripts/prod/deploy.sh update`.
- **Schema:** as migrations são reversíveis; um passo:
  `$DC run --rm --entrypoint sh migrate -c "cd /app/backend && alembic downgrade -1"`
  (faça backup antes e confira o código compatível).
- **Dados:** restaure o dump em banco isolado, valide e só então troque (`docs/BACKUP-RESTORE.md`).

## 7. Operação

```bash
$DC ps                          # estado e health
$DC logs -f --tail=100 backend  # logs (também: worker, proxy, postgres)
$DC restart worker              # reiniciar um serviço (estado do worker fica no banco)
docker stats --no-stream        # consumo de CPU/RAM
```
Proibido como rotina: `down -v`, remover volumes, `DROP`/`TRUNCATE`.

## 8. Memória (4 GB × 8 GB)

Tetos definidos no compose: postgres 1,2 GB + backend 1,0 GB + worker 0,7 GB + nginx 0,13 GB
≈ **3,0 GB** + SO/Docker (~0,5 GB).

Consumo **medido** na simulação local do compose de produção (`docker stats`, após login,
upload de PDF, consultas e restart; sem carga concorrente):

| Container | RAM medida | Teto |
|---|---:|---:|
| proxy | 11 MB | 64 MB |
| frontend | 11 MB | 64 MB |
| worker | 61 MB | 700 MB |
| backend | 86 MB | 1000 MB |
| postgres | 61 MB | 1200 MB |
| **total** | **~230 MB** | ~3,0 GB |

Em repouso o sistema usa menos de 10% de 4 GB. O que consome memória é o **pico**:
extração de PDFs grandes (MarkItDown/pdfminer) e principalmente OCR. Os tetos garantem que
um pico mate o backend (que reinicia sozinho) e não o banco.

- **4 GB atende** a homologação com 1–3 usuários, PDFs comuns e **OCR desligado**, com swap
  de 2 GB como reserva. O processamento roda no request de upload; um PDF grande consome
  memória no backend, que tem teto próprio (o kernel mata o backend, não o banco).
- **OCR** (Tesseract + pdf2image) rasteriza página a página e pode passar de 1 GB em PDFs
  escaneados longos. Se a homologação depender de OCR frequente, **comece com 8 GB**
  (e suba `mem_limit` do backend para 2 GB).
- Recomendação objetiva: **4 GB para validar o fluxo; 8 GB se OCR/PDFs grandes forem rotina.**

## 9. Limpeza de temporários

`scripts/prod/cleanup-temp.sh` (dry-run por padrão) lista arquivos de `tmp/` com mais de
1 dia; `APPLY=true` remove. Nunca toca `documents/`.
