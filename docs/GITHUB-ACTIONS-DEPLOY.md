# Radar Leilão — CI/CD com GitHub Actions

## 1. Workflows

| Arquivo | Dispara em | Faz | Publica algo? |
|---|---|---|---|
| `.github/workflows/ci.yml` | push/PR em `main` | backend (migrations 0001→head, downgrade -1/upgrade, pytest), frontend (tsc, vitest), docker (valida compose prod + build das imagens) | **não** |
| `.github/workflows/publish-images.yml` | manual ou tag `vX.Y.Z` | build + push das imagens no GHCR (`ghcr.io/<repo>/backend|frontend:<tag>`) | GHCR (usa `GITHUB_TOKEN`) |
| `.github/workflows/deploy.yml` | **somente manual** (`workflow_dispatch`) | SSH na VPS → `git checkout <ref>` → `scripts/prod/deploy.sh update` (backup + migração + up + smoke) | VPS |

Nenhum push em branch publica na VPS. O deploy usa o Environment `production`.

## 2. Configurar o deploy (uma vez)

1. Na VPS, crie uma chave **dedicada** ao deploy (não reutilize a sua):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/radar_deploy -N ""
   cat ~/.ssh/radar_deploy.pub >> ~/.ssh/authorized_keys
   cat ~/.ssh/radar_deploy        # conteúdo vai para a secret VPS_SSH_KEY
   ```
2. GitHub → Settings → Environments → **New environment** `production`:
   - **Required reviewers**: você (exige aprovação manual a cada deploy).
   - **Deployment branches**: somente `main` e tags.
3. Secrets do environment `production`:

| Secret | Exemplo | Observação |
|---|---|---|
| `VPS_HOST` | `203.0.113.10` | IP da VPS (ou nome Tailscale com runner na tailnet) |
| `VPS_USER` | `radar` | usuário de operação |
| `VPS_SSH_KEY` | conteúdo de `radar_deploy` | chave privada dedicada |
| `VPS_PORT` | `22` | opcional |
| `VPS_APP_DIR` | `/opt/radar-leilao` | onde está o clone |

O `.env.prod` **permanece só na VPS**; nenhuma secret da aplicação vai para o GitHub.

## 3. Executar um deploy

Actions → **Deploy (manual)** → Run workflow → `ref` (tag recomendada, ex.: `v0.1.0`) →
aprovar no environment. O job:
1. valida as secrets e o formato do `ref` (só `A-Z a-z 0-9 . _ / -`: o valor vai para um
   comando remoto, então qualquer outro caractere é recusado); 2. conecta por SSH; 3. faz checkout do `ref`;
4. roda `scripts/prod/deploy.sh update` (backup banco+docs → build → migrate → up → smoke).

## 4. Rollback

Run workflow com `ref` = tag/commit anterior. O mesmo fluxo faz backup antes. Se a versão
que está saindo aplicou migration nova, o rollback **falha** (o código antigo não conhece a
revisão do banco e o gate de schema não deixa o backend subir): faça antes, na VPS e com o
código ainda novo, o `alembic downgrade` de `docs/DOCKER-DEPLOYMENT.md §6`.
A chave do host é obtida por `ssh-keyscan` (confiança no primeiro uso); para fixá-la,
troque por um secret `VPS_KNOWN_HOSTS` com a saída de `ssh-keyscan` conferida.

## 5. Boas práticas

- Crie tags para cada versão homologada: `git tag v0.1.0 && git push origin v0.1.0`.
- Logs de Actions não imprimem secrets (GitHub mascara e os scripts não ecoam variáveis).
- Se usar Tailscale sem porta 22 pública, o runner do GitHub não alcança a VPS: use um
  runner self-hosted na tailnet ou a action oficial `tailscale/github-action` (exige authkey).

## 6. Status

- CI: configurado; executa a cada push em `main`.
- Publish/Deploy: preparados, **não executados** (sem secrets reais nesta fase).
