# GitHub Actions: CI e deploy automático por tag

**Regra:** criar e publicar uma tag `vX.Y.Z` testa, publica as imagens no GHCR e atualiza a VPS.
Não há "Run workflow" manual nem aprovação. A tag **é** a autorização do deploy.

```bash
git checkout main && git pull
git tag -a v1.2.3 -m "v1.2.3"
git push origin v1.2.3
```

Fontes de verdade: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `scripts/prod/*.sh`
e o teste `tests/test_release_workflow_policy.py` (exige que existam **somente** `ci.yml` e
`release.yml` e que os `.sh` tenham modo 100755). Este documento substitui o antigo
`GITHUB-ACTIONS-DEPLOY.md` (preservado em [99-archive/originais](../99-archive/originais/GITHUB-ACTIONS-DEPLOY.md)).

## 1. Fluxo do pipeline

```mermaid
flowchart LR
  T[Tag vX.Y.Z] --> V[validate-tag]
  V --> C[ci reutilizado]
  C --> P[publish no GHCR]
  P --> D[deploy por SSH]
  D --> S[smoke e resumo]
```

| Job | O que faz |
|---|---|
| `validate-tag` | exige o formato `vMAJOR.MINOR.PATCH` e que o commit da tag esteja na `main` |
| `ci` | reutiliza `ci.yml`: backend (migrations 0001→head, downgrade/upgrade, pytest), frontend (tsc + vitest), compose, nginx, scripts, actionlint |
| `publish` | build e push de `ghcr.io/jabesfelipe/radar-leilao/backend:vX.Y.Z` e `.../frontend:vX.Y.Z` (sem `latest`) |
| `deploy` | SSH na VPS, checkout da tag, `scripts/prod/release.sh`: pull, backup (se já existe instalação), migrations, `up`, smoke, resumo |

Regras:

- Falhou uma etapa, as seguintes não rodam.
- Um deploy por vez: `concurrency: deploy-production`, sem cancelar o que está em andamento.
- Push em `main` e pull requests rodam só o CI (`ci.yml`); nunca publicam nem implantam.
- A VPS não constrói imagens: só baixa as publicadas.
- Tag inválida (`v1.0`, `1.0.0`, `v1.0.0-rc1`) ou fora da `main` faz `validate-tag` falhar.

## 2. Primeiro deploy × atualização

`release.sh` chama `scripts/prod/deploy.sh auto`, que decide pelo estado do PostgreSQL da VPS:

| Estado do banco | `.release.env` | Resultado |
|---|---|---|
| vazio | não existe | **first**: sem backup, migrations 0001→head, up |
| com `alembic_version` | existe ou não | **update**: backup do banco e dos documentos, migrations, up |
| vazio | existe | **aborta** (possível perda de volume) |
| com tabelas, sem `alembic_version` | qualquer | **aborta** (estado desconhecido) |

- Backup falhou: aborta antes das migrations.
- Após as migrations, grava `.release.env` (versão atual) e guarda o anterior em `.release.env.prev` (usado pelo rollback). Ficam só na VPS.
- O smoke confere `/health` com o cookie do portão, que `/api/imoveis` sem cookie retorna 403, o proxy pela interface externa (se houver `VPS_PUBLIC_URL`) e que backend, worker e frontend em execução são as imagens da tag. Saídas: `DEPLOY_OK` ou `SMOKE_FALHOU`.
- Passos do `deploy.sh`: `[0/6]` a `[6/6]` (a migration é o `[4/6]`).

## 3. Configuração única

### 3.1 Na VPS

Bootstrap descrito em [infrastructure.md](infrastructure.md#6-bootstrap-do-servidor).

### 3.2 Secrets e variável

Lista completa e significado em [infrastructure.md](infrastructure.md#8-github-actions-secrets-variável-e-ruleset):
secrets `VPS_HOST`, `VPS_USER`, `VPS_APP_DIR`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS` (recomendado),
`VPS_PORT`, `GHCR_USER`/`GHCR_TOKEN` (opcionais) e a variável `VPS_PUBLIC_URL`.
`.env.prod` e segredos da aplicação permanecem só na VPS. Não há Environment com aprovação.

### 3.3 Login da VPS no GHCR (sem token guardado)

O job envia ao `release.sh`, pela **stdin do SSH**, o usuário e o `GITHUB_TOKEN` da execução
(expira ao fim do job). O script faz `docker login` em um `DOCKER_CONFIG` temporário, baixa as duas
imagens e apaga a configuração; nada fica em `~/.docker`. O token não aparece em argumentos, ambiente
remoto nem logs. Se o pull falhar com "denied", dê acesso de leitura ao repositório no pacote
(Package settings) ou use o par opcional `GHCR_USER`/`GHCR_TOKEN`.

### 3.4 Ruleset de tags

Ruleset de tag com padrão `v*`, restringindo criação, atualização e exclusão a administradores.
Sem isso, qualquer colaborador com permissão de escrita dispara um deploy. A tag `v1.0.1` foi criada
contornando o ruleset como administrador (registro do histórico da sessão de trabalho).

## 4. Acompanhar uma execução

GitHub → Actions → run **Release** da tag. O resumo (Summary) traz tag, commit, digests, modo
(first/update), última etapa e, em falha, as linhas de erro. Na VPS:

```bash
cd /opt/radar-leilao
scripts/prod/compose.sh ps
scripts/prod/compose.sh logs --tail=100 backend
grep RADAR_RELEASE_TAG .release.env
```

## 5. Rollback

Ver [deployment.md](deployment.md#4-rollback).

## 6. Resultado observado × simulado

- **Observado (informado pelo proprietário):** `v1.0.0`, 12/11/2026, pipeline concluído com sucesso em 5 min 40 s, imagens publicadas no GHCR e deploy concluído na VPS.
- **Validado só por teste local:** actionlint, política do workflow em teste automatizado, simulação de `release.sh`, `deploy.sh` e `rollback.sh` com imagens locais, e `bootstrap-vps.sh` em Ubuntu descartável.

A afirmação antiga "o pipeline ainda não foi executado de verdade" está superada.

## 7. Limites conhecidos

- Migrations destrutivas dependem de revisão humana antes da tag; o pipeline não as detecta.
- Tag recriada sobrescreve as imagens daquele nome: trate tags como imutáveis.
- Se três tags chegam enquanto uma roda, só a última fica pendente (limitação do `concurrency`).

## 8. Recuperar de falha

| Onde falhou | O que fazer |
|---|---|
| validate-tag / ci / publish | nada foi implantado; corrija e crie **nova** tag (ou "Re-run failed jobs" se a falha foi transitória) |
| deploy: secrets, SSH ou host key | ajuste os secrets; Re-run (as imagens já estão publicadas) |
| deploy: pull | permissão do pacote ou token (§3.3); Re-run |
| deploy: backup | nada foi migrado; corrija disco/permissão em `/opt/radar-backups`; Re-run |
| deploy: migration | a versão anterior segue no ar; leia o log do passo `[4/6]`; não force nada no banco; restaure backup se preciso |
| deploy: smoke | migrations aplicadas; veja `compose.sh logs`; `rollback.sh` se o schema permitir, senão corrija à frente com nova tag |

Re-run é seguro: `deploy.sh auto` reavalia o estado e o `update` refaz o backup antes de migrar.
