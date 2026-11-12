# Deploy, migrations e rollback

Visão geral do deploy do Radar Leilão. O fluxo oficial é **automático por tag** ([github-actions.md](github-actions.md)).
O detalhamento do que roda dentro da VPS (serviços, cadeia de scripts, gate de schema, tetos de memória)
está em [docker-deployment.md](docker-deployment.md). Este documento substitui `DEPLOYMENT.md`,
`OPERATIONS-RUNBOOK.md §5` e `PRODUCTION-CHECKLIST.md`, que descreviam deploy **manual** com build na VPS
(arquivados em [99-archive/originais](../99-archive/originais/)).

## 1. Modelo de deploy

| Aspecto | Hoje |
|---|---|
| Gatilho | push de tag `vMAJOR.MINOR.PATCH` na `main` |
| Build | no GitHub Actions; a VPS **não** constrói |
| Imagens | `ghcr.io/jabesfelipe/radar-leilao/{backend,frontend}:vX.Y.Z` |
| Execução | `docker-compose.prod.yml`, projeto `radar-prod`, sempre via `scripts/prod/compose.sh` |
| Migrations | serviço `migrate` (profile), executado pelo deploy; o backend em produção **não** migra sozinho |
| Gate de schema | backend e worker não iniciam se `alembic_version` ≠ head do código |
| Frontend | compilado com `VITE_API_URL` vazio (chamadas em `/api` no mesmo host) |
| Exposição | proxy nginx na porta 80 (HTTP, sem TLS), com portão por cookie |

## 2. Como publicar uma versão

1. Garanta a `main` verde no CI e a documentação atualizada na mesma entrega.
2. Revise manualmente qualquer migration destrutiva (o pipeline não detecta).
3. `git tag -a vX.Y.Z -m "vX.Y.Z"` e `git push origin vX.Y.Z`.
4. Acompanhe em Actions; confirme `DEPLOY_OK` e a versão em `.release.env`.

## 3. Migrations em produção

Procedimento padrão: nenhum passo manual (o deploy faz backup, migra e sobe). Procedimento manual
excepcional, na VPS (`DC=scripts/prod/compose.sh`):

1. `scripts/prod/pg-backup.sh /opt/radar-backups`
2. Conferir a versão: `$DC run --rm --entrypoint sh migrate -c "cd /app/backend && alembic current && alembic heads"`
3. Aplicar: `$DC --profile migrate run --rm migrate`
4. Subir: `$DC up -d --no-build`

Detalhes: [docker-deployment.md §5](docker-deployment.md), e regras para escrever migrations em
[../05-development/database-migrations.md](../05-development/database-migrations.md). Migrations são
incrementais; nunca edite uma já aplicada.

## 4. Rollback

Rollback de **imagem** e de **dados** são operações diferentes.

- **Imagem, sem migration nova:** `scripts/prod/rollback.sh` volta para a versão registrada em
  `.release.env.prev`, sem build e sem tocar no banco. Só prossegue se as heads do Alembic da versão
  anterior forem iguais à revisão atual do banco; se não forem, recusa com `rc=3` sem mudar nada.
- **Com migration nova:** o gate de schema impede o código antigo de subir. Com a versão nova ainda no
  ar, revise a migration e, se for reversível sem perda, rode `alembic downgrade <revisão-anterior>`
  (a revisão anterior aparece no passo `[3/6]` do log do deploy) e então `rollback.sh`.
- **Downgrade inseguro** (dados novos, colunas removidas): restaure o backup gerado pelo deploy em
  banco isolado, valide e só então troque. Nunca automático.
- **Preferido para bugs:** corrigir à frente com nova tag.
- **Reexecução de emergência sem GitHub:** `RELEASE_OFFLINE=1 scripts/prod/release.sh vX.Y.Z ghcr.io/jabesfelipe/radar-leilao` (usa as imagens já baixadas).

Status de evidência: `rollback.sh` e a recusa por schema divergente foram **validados por teste local**,
não exercitados na VPS real.

## 5. Verificação pós-deploy

- `scripts/prod/post-deploy-check.sh` e o smoke embutido no deploy.
- `scripts/prod/compose.sh ps`: serviços saudáveis.
- Abra o sistema pelo navegador (com o cookie do portão) e confirme login e uma tela de leitura.
- `GET /api/monitoring/readiness` (autenticado) confere banco e Alembic.

## 6. Referência futura: domínio e TLS (não existe hoje)

O guia antigo `DEPLOYMENT.md` descrevia uma fase com domínio e HTTPS (certificados em `infra/certs/`,
Let's Encrypt via certbot, `server_name` no proxy, `CORS_ALLOW_ORIGINS` com o domínio). Isso **não está
implantado**: o ambiente atual é HTTP puro na porta 80. Quando o domínio existir, será necessário:
certificados, ajuste do proxy (`docker/nginx/templates/default.conf.template`), `CORS_ALLOW_ORIGINS`,
`ALLOW_PUBLIC_HTTP` revisto e atualização desta seção. Passos de build e migrate manuais daquele guia
não devem ser usados na VPS gerenciada por tags.

## 7. Contradições corrigidas nesta reestruturação

| Documento antigo | Dizia | Realidade atual |
|---|---|---|
| `PRODUCTION-CHECKLIST` | `VITE_API_URL=/api` | deve ficar **vazio** (o frontend já chama `/api`) |
| `OPERATIONS-RUNBOOK §5` | `git pull`, `build` e `up` na VPS | deploy por tag, sem build na VPS |
| `DEPLOYMENT`, `ARCHITECTURE` | proxy 80/443 com HTTPS | HTTP 80 |
| `CAPACITY-PLANNING`, `DEPLOYMENT §1` | 2 vCPU / 4 GB | 6 vCPU / ~11 GiB |

## 8. Release com a migration 0024 (hardening de segurança)

A versão com o hardening inclui a migration `0024_analysis_version_unique` (índice único de análise por imóvel, oportunidade e versão). O deploy por tag já faz backup antes de migrar. A migration é idempotente, não altera dados e **aborta com mensagem clara** se houver análises duplicadas (o que não ocorre num banco sem análises).

Rollback: como a migration muda o schema, `rollback.sh` recusa voltar a imagem (rc=3). Procedimento: `alembic downgrade 0023_usuarios` (apenas remove o índice) e então `rollback.sh`; ou corrija à frente com nova tag. Plano completo em [security.md §11](../03-architecture/security.md#11-homologação-implantação-e-rollback).
