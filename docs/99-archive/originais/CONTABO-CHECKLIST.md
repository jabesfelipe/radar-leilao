# Radar Leilão — Checklist Contabo (deploy automático por tag)

> **Ambiente temporário de testes** pelo IP público, por HTTP (sem TLS) e com rotas da API
> sem JWT (`SECURITY-EXPOSURE-AUDIT.md`). **Não use dados sensíveis reais.** Barreiras mantidas:
> portão por chave (`GATE_KEY`) + login.

Ordem única. Detalhes do pipeline: `GITHUB-ACTIONS-DEPLOY.md`. Dados da máquina:
`infra/CONTABO-VPS.md`.

## 0. VPS — já concluído (validado em 11/11/2026)
- [x] Contabo Cloud VPS 6: 6 vCPU AMD EPYC, ~11 GiB RAM, 193 GB, Ubuntu 24.04.5 LTS.
- [x] Kernel `6.8.0-149-generic` ativo após reboot.
- [x] Docker Engine 29.9.3 + Compose 5.7.1, serviço habilitado; `hello-world` OK.
- [x] Swap 4 GB ativa e persistente no `/etc/fstab`.

## 1. Chave do deploy (no SEU computador)
```bash
ssh-keygen -t ed25519 -f radar_deploy -N "" -C "radar-deploy"
cat radar_deploy.pub          # vai para a VPS (pública)
# radar_deploy (privada) vai SÓ para a secret VPS_SSH_KEY do GitHub
```

## 2. Bootstrap único (na VPS, como root)
```bash
git clone https://github.com/jabesfelipe/radar-leilao.git /root/radar-boot && cd /root/radar-boot
bash scripts/prod/bootstrap-vps.sh --deploy-pubkey "ssh-ed25519 AAAA... radar-deploy" --configure-ufw
```
- [ ] Terminou com `BOOTSTRAP_OK`.
- [ ] **Guardei** a `GATE_KEY`, a senha do admin e o link `/acesso?k=...` impressos (aparecem uma vez).
- [ ] Anotei a impressão digital da host key mostrada no final.
- [ ] `rm -rf /root/radar-boot`
- [ ] Do seu computador: `ssh -i radar_deploy radar@IP_DA_VPS 'docker ps'` funciona.

O que foi criado: usuário `radar` (sem senha, grupo docker, chave `restrict`),
`/opt/radar-leilao` (clone), `/opt/radar-backups` (700), `/opt/radar-leilao/.env.prod` (600,
segredos aleatórios, modo IP público na porta 80, OCR desligado, LLM sem chave).

## 3. GitHub (uma vez)
Settings → Secrets and variables → Actions → **Secrets**:
- [ ] `VPS_HOST` = IP público
- [ ] `VPS_USER` = `radar`
- [ ] `VPS_SSH_KEY` = conteúdo de `radar_deploy` (privada)
- [ ] `VPS_APP_DIR` = `/opt/radar-leilao`
- [ ] `VPS_KNOWN_HOSTS` = saída de `ssh-keyscan -t ed25519 IP_DA_VPS` (confira com a impressão digital do passo 2)
- [ ] (`VPS_PORT` só se não for 22)

**Variables**:
- [ ] `VPS_PUBLIC_URL` = `http://IP_DA_VPS` (smoke externo)

Settings → Rules → Rulesets:
- [ ] Tag ruleset `v*`: criação/atualização/exclusão só por administradores.

Settings → Actions → General:
- [ ] Workflow permissions: o padrão (read) basta; o workflow pede `packages: write` só no job de publicação.

## 4. Primeiro deploy = primeira tag
```bash
git checkout main && git pull
git tag v1.0.0
git push origin v1.0.0
```
- [ ] Actions → **Release** `v1.0.0`: validate-tag → CI → publish → deploy verdes.
- [ ] Summary: modo `first`, `health=200 sem_cookie=403 interface_externa=200 versao=v1.0.0(ok)`.
- [ ] Se o pull falhar com *denied*: Packages → `radar-leilao/backend` e `/frontend` →
      Package settings → dar acesso de leitura ao repositório; *Re-run failed jobs*.

## 5. Validar no navegador (celular e computador)
- [ ] `http://IP_DA_VPS/acesso?k=<GATE_KEY>` uma vez por dispositivo → abre o login.
- [ ] Login com o admin do bootstrap; trocar/remover a senha de bootstrap:
      na VPS, apague o valor de `AUTH_BOOTSTRAP_ADMIN_PASSWORD` no `.env.prod`
      e `cd /opt/radar-leilao && scripts/prod/compose.sh up -d --no-build backend`.
- [ ] Cadastrar imóvel de teste, enviar PDF/TXT, rodar análise (sem chave: `SEM_CHAVE`),
      abrir financeiro/jurídico/due diligence.
- [ ] `sudo reboot` → tudo volta (restart: unless-stopped); dados e documentos continuam.

## 6. Backups (cron do usuário `radar`)
```bash
sudo -iu radar
crontab -e
0 3 * * * cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
30 4 * * * cd /opt/radar-leilao && APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh >> /opt/radar-backups/cron.log 2>&1
```
- [ ] Cópia fora da VPS (`BACKUP-RESTORE.md §5`).
Além do cron, **todo deploy de atualização faz backup antes de migrar**.

## 7. Próximas versões
```bash
git tag v1.0.1 && git push origin v1.0.1
```
Automático: CI → GHCR → backup → migrations → up → smoke. Rollback e recuperação:
`GITHUB-ACTIONS-DEPLOY.md §5–§6`.

## Não fazer
- `docker compose down -v`, `docker volume rm`, `DROP`/`TRUNCATE`.
- `docker compose ...` direto na VPS (use `scripts/prod/compose.sh`).
- Reaproveitar/mover uma tag já publicada (tags são imutáveis; crie a próxima).
- Carregar dados sensíveis enquanto o acesso for HTTP público.
