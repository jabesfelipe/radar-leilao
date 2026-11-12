# Radar Leilão — Deploy automático por tag (GitHub Actions → Contabo)

**Regra:** criou e publicou uma tag `vX.Y.Z` → o pipeline testa, publica as imagens no GHCR e
atualiza a VPS. Sem clicar em "Run workflow" e sem aprovação manual.

```bash
git checkout main && git pull
git tag v1.0.0
git push origin v1.0.0
```

> A tag **é** a autorização do deploy. Restrinja quem pode criar tags `v*` (ver §3.4).

## 1. O que acontece (arquivo `.github/workflows/release.yml`)

```
TAG vX.Y.Z
  └─ validate-tag   formato vMAJOR.MINOR.PATCH; commit da tag precisa estar na main
       └─ ci        backend (migrations 0001→head, downgrade/upgrade, pytest), frontend
       │            (tsc + vitest), compose, nginx, scripts, actionlint   [ci.yml reutilizado]
            └─ publish   build + push no GHCR: backend:vX.Y.Z e frontend:vX.Y.Z
                 └─ deploy   SSH na VPS → checkout da tag → scripts/prod/release.sh
                               pull das imagens → backup (se já existe instalação)
                               → migrations → up → smoke (+ versão em execução) → resumo
```

- **Falhou uma etapa, as seguintes não rodam.** Teste ou publicação falhou ⇒ nada é implantado.
- **Um deploy por vez** (`concurrency: deploy-production`, sem cancelar o que está em andamento).
  Se duas tags forem enviadas juntas, a segunda espera. Só uma execução fica "pendente": se
  três tags chegarem enquanto uma roda, a do meio é descartada (a última contém tudo).
- **Push em `main`/PR** roda **só** o CI (`ci.yml`). Nunca publica nem implanta.
- A VPS **não constrói nada**: usa as imagens publicadas (`ghcr.io/jabesfelipe/radar-leilao/{backend,frontend}:vX.Y.Z`).
  `latest` não é usado.
- Tag inválida (`v1.0`, `1.0.0`, `v1.0.0-rc1`) ⇒ o job `validate-tag` falha e nada acontece.
- Tag em commit fora da `main` ⇒ falha ("faça merge antes de criar a tag").

## 2. Primeiro deploy × atualização (decidido pelo estado do banco)

`release.sh` chama `scripts/prod/deploy.sh auto`, que olha o PostgreSQL da VPS:

| Estado do banco | `.release.env` (deploy anterior) | Resultado |
|---|---|---|
| vazio (sem tabelas) | não existe | **first**: sem backup (nada a salvar) → migrations 0001→head → up |
| tem `alembic_version` | existe ou não | **update**: **backup do banco e dos documentos** → migrations → up |
| vazio | **existe** | **ABORTA** (possível perda do volume; não recria do zero) |
| tem tabelas, sem `alembic_version` | — | **ABORTA** (estado desconhecido) |

- **Backup falhou ⇒ aborta antes das migrations** (testado: nenhuma migration roda, a versão em
  execução permanece).
- Depois das migrations o deploy grava `.release.env` (imagens da versão) e guarda o anterior em
  `.release.env.prev` (usado pelo rollback). Esses arquivos ficam só na VPS e não são versionados.
- O smoke confere: `/health` 200 com o cookie do portão, `/api/imoveis` 403 sem cookie, proxy
  pela interface externa (modo IP público) e **que backend/worker/frontend em execução são as
  imagens da tag**.

## 3. Configuração (uma vez)

### 3.1 Na VPS — bootstrap único (como root)

Pré-requisitos já atendidos na Contabo: Docker + Compose, swap. Depois:

```bash
# No SEU computador: chave dedicada ao deploy (a privada nunca vai para a VPS)
ssh-keygen -t ed25519 -f radar_deploy -N "" -C "radar-deploy"
cat radar_deploy.pub        # uma linha: "ssh-ed25519 AAAA... radar-deploy"

# Na VPS, como root (cole a linha da chave PÚBLICA entre aspas):
git clone https://github.com/jabesfelipe/radar-leilao.git /root/radar-boot && cd /root/radar-boot
bash scripts/prod/bootstrap-vps.sh --deploy-pubkey "ssh-ed25519 AAAA... radar-deploy" --configure-ufw
```
O script, de forma idempotente: cria o
usuário `radar` (sem senha, grupo `docker`), autoriza a chave pública com `restrict`, cria
`/opt/radar-leilao` (clone) e `/opt/radar-backups` (700) e gera `/opt/radar-leilao/.env.prod`
com **segredos aleatórios** (chmod 600). Ele imprime **uma única vez** a `GATE_KEY` e a senha do
admin — guarde-as num gerenciador de senhas. `--configure-ufw` libera SSH e 80/tcp.
Depois apague o clone temporário: `rm -rf /root/radar-boot`.

> O usuário `radar` está no grupo `docker` (equivale a root na máquina). É um usuário **só de
> deploy**: sem senha, com chave restrita. Não o use para tarefas do dia a dia.

### 3.2 No GitHub — Secrets (Settings → Secrets and variables → Actions)

| Secret | Valor | Obrigatória |
|---|---|---|
| `VPS_HOST` | IP público da VPS | sim |
| `VPS_USER` | `radar` | sim |
| `VPS_SSH_KEY` | conteúdo do arquivo **privado** `radar_deploy` | sim |
| `VPS_APP_DIR` | `/opt/radar-leilao` | sim |
| `VPS_PORT` | porta SSH (padrão 22) | não |
| `VPS_KNOWN_HOSTS` | saída de `ssh-keyscan -t ed25519 IP` (confira a impressão digital que o bootstrap mostrou) | recomendada (sem ela o pipeline confia na host key do momento) |
| `GHCR_USER` + `GHCR_TOKEN` | usuário + PAT com `read:packages` | não (só se o `GITHUB_TOKEN` não conseguir ler o pacote) |

Variável (não secreta) opcional: `VPS_PUBLIC_URL` = `http://IP_DA_VPS` — habilita o **smoke
externo** (o runner testa o proxy pela internet).

O `.env.prod` e qualquer segredo da aplicação **permanecem só na VPS**. Nenhum Environment
com aprovação é usado.

### 3.3 Login da VPS no GHCR (sem token guardado)

O job de deploy envia ao `release.sh`, pela **stdin do SSH**, o usuário e o `GITHUB_TOKEN` da
execução (expira ao fim do job). O script faz `docker login` num `DOCKER_CONFIG` temporário,
baixa as duas imagens e apaga a configuração: nada fica em `~/.docker`. O token não aparece em
argumentos, ambiente remoto nem logs.

Se o pull falhar com "denied": em *Packages → radar-leilao/backend → Package settings* dê acesso
de leitura ao repositório, ou use o par opcional `GHCR_USER`/`GHCR_TOKEN`.

### 3.4 Proteja as tags
Settings → Rules → Rulesets → *New tag ruleset*: padrão `v*`, restringir criação/atualização/
exclusão a administradores. Sem isso, qualquer colaborador com escrita dispara um deploy.

## 4. Acompanhar

- GitHub → **Actions** → run **Release** da tag. O resumo (aba *Summary*) traz tag, commit,
  digests das imagens, modo (first/update), última etapa e, em falha, as linhas de erro.
- Na VPS:
  ```bash
  cd /opt/radar-leilao
  scripts/prod/compose.sh ps
  scripts/prod/compose.sh logs --tail=100 backend      # também: worker, proxy, postgres
  grep RADAR_RELEASE_TAG .release.env                  # versão em execução
  ```

## 5. Rollback

**Código/imagem** (dados intactos), na VPS:
```bash
cd /opt/radar-leilao && scripts/prod/rollback.sh
```
Volta para a versão em `.release.env.prev`. **Só prossegue se o schema do banco for o da versão
anterior** (mesmas heads do Alembic). Se a versão que saiu aplicou migration nova, **recusa**
(rc=3): voltar a imagem não desfaz o schema.

**Banco** é outra coisa — nunca é automático:
1. migration reversível e sem dados novos: `alembic downgrade` conferido manualmente
   (`docs/DOCKER-DEPLOYMENT.md §6`), depois `rollback.sh`;
2. caso contrário: restaurar o backup que o próprio deploy gerou antes de migrar
   (`docs/BACKUP-RESTORE.md`), em banco isolado, validando antes de trocar.

**Alternativa sem tocar na VPS:** corrigir na `main` e publicar uma nova tag (`v1.0.1`).

## 6. Recuperar de falha

| Onde falhou | O que fazer |
|---|---|
| validate-tag / ci / publish | nada foi implantado. Corrija, e crie **nova** tag (ou *Re-run failed jobs* se foi falha transitória) |
| deploy: secrets/SSH/host key | ajuste as secrets; *Re-run failed jobs* (as imagens já estão publicadas) |
| deploy: pull | permissão do pacote/token (§3.3); *Re-run* |
| deploy: backup | nada foi migrado; corrija disco/permissão em `/opt/radar-backups`; *Re-run* |
| deploy: migration | a versão anterior segue no ar; leia o log da etapa `[4/6]`; **não** force nada no banco; restaure backup se preciso |
| deploy: smoke | migrations aplicadas; veja `compose.sh logs`; `rollback.sh` se o schema permitir, senão corrija à frente com nova tag |

*Re-run* é seguro: `deploy.sh auto` reavalia o estado e o `update` refaz o backup antes de migrar.

## 7. Limites conhecidos (honestidade)

- O pipeline **ainda não foi executado de verdade** no GitHub nem na Contabo: a validação foi
  local (actionlint, política em teste automatizado, simulação do `release.sh`/`deploy.sh`/
  `rollback.sh` com imagens locais e o `bootstrap-vps.sh` num Ubuntu descartável).
  O pull do GHCR e o SSH real só serão exercitados na primeira tag.
- Migrations destrutivas dependem de revisão humana antes da tag; o pipeline não as detecta.
- Uma tag recriada sobrescreve as imagens daquele nome: trate tags como imutáveis.
