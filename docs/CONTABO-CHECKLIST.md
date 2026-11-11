# Radar Leilão — Checklist de implantação na Contabo

Marque **na ordem**. Explicações: `INFRASTRUCTURE-CONTABO.md` (passo a passo),
`HOMOLOGATION-GUIDE.md` (acesso), `BACKUP-RESTORE.md`, `SECURITY-EXPOSURE-AUDIT.md`.
Modo de acesso padrão: **Tailscale + HTTPS da tailnet** (sem porta pública da aplicação).

## 0. Antes de contratar
- [ ] Plano: mínimo 2 vCPU/4 GB/60 GB NVMe (OCR desligado); 8 GB se OCR/PDFs grandes.
- [ ] Imagem Ubuntu 24.04 LTS.
- [ ] Conta Tailscale criada; no painel DNS: **MagicDNS** e **HTTPS Certificates** ligados.
- [ ] App Tailscale instalado no celular e no computador.
- [ ] Destino do backup externo decidido (máquina com pull/rsync **ou** rclone criptografado).

## 1. Sistema (root)
```bash
apt-get update && apt-get -y upgrade
timedatectl set-timezone America/Sao_Paulo
adduser radar && usermod -aG sudo radar
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10 && echo 'vm.swappiness=10' > /etc/sysctl.d/99-radar.conf
```
- [ ] `free -h` mostra 2 GB de swap.

## 2. SSH por chave (do seu computador, depois na VPS)
```bash
ssh-keygen -t ed25519 -C radar-vps && ssh-copy-id radar@IP_DA_VPS && ssh radar@IP_DA_VPS 'echo chave-ok'
# na VPS:
printf 'PasswordAuthentication no\nPermitRootLogin no\n' | sudo tee /etc/ssh/sshd_config.d/99-radar.conf
sudo sshd -t && sudo systemctl restart ssh
```
- [ ] Novo login em outro terminal funciona **antes** de fechar a sessão atual.

## 3. Firewall (antes do Docker)
```bash
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw enable && sudo ufw status verbose
```
- [ ] Só `22/tcp (OpenSSH)` liberado. **Não** abrir 80/443 no modo Tailscale.

## 4. Docker
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker radar
exit   # reentrar como radar
docker version && docker compose version
```

## 5. Tailscale
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --hostname=radar-vps
tailscale status
```
- [ ] Nome anotado: `radar-vps.<tailnet>.ts.net`.

## 6. Código e `.env.prod`
```bash
sudo mkdir -p /opt/radar-leilao /opt/radar-backups
sudo chown radar: /opt/radar-leilao /opt/radar-backups && chmod 700 /opt/radar-backups
git clone https://github.com/jabesfelipe/radar-leilao.git /opt/radar-leilao && cd /opt/radar-leilao
git checkout <tag-ou-commit-homologado>
cp .env.prod.example .env.prod && chmod 600 .env.prod
openssl rand -base64 24; openssl rand -base64 48; openssl rand -hex 24
nano .env.prod
```
- [ ] `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` (≥ 32), `GATE_KEY` (48 hex) preenchidos.
- [ ] `CORS_ALLOW_ORIGINS=https://radar-vps.<tailnet>.ts.net`.
- [ ] `AUTH_BOOTSTRAP_ADMIN_EMAIL` / `AUTH_BOOTSTRAP_ADMIN_PASSWORD` (senha forte).
- [ ] `PROXY_BIND=127.0.0.1`, `PROXY_PORT=8080`, `ALLOW_PUBLIC_HTTP=0`, `RUN_MIGRATIONS_ON_START=false`,
      `OCR_ENABLED=false`, `BACKUP_DEST=/opt/radar-backups`.
- [ ] `ADMIN_API_TOKEN`, `AUTHZ_ROLE_TOKENS`, `PORTAL_ADMIN_TOKEN` **ausentes** (o compose não os repassa).

## 7. Primeiro deploy (valida env → postgres → banco vazio → migrations → serviços → smoke)
```bash
chmod +x scripts/prod/*.sh
scripts/prod/deploy.sh first
```
- [ ] Terminou com `health=200 sem_cookie=403` e `DEPLOY_OK`.
- [ ] `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` → backend/postgres/frontend/proxy *healthy*, worker *running*.

## 8. Publicar só na tailnet
```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve status
sudo ss -tlnp | grep -E ':(80|443|8080|8000|5432)\b'
```
- [ ] `ss` mostra o proxy só em `127.0.0.1:8080` (e o tailscaled no IP 100.x); nada em `0.0.0.0`.
- [ ] De uma rede **fora** da tailnet: `curl -m 5 http://IP_DA_VPS/` e `curl -m 5 http://IP_DA_VPS:8080/` falham.

## 9. Primeiro acesso
- [ ] Dispositivo com Tailscale conectado: `https://radar-vps.<tailnet>.ts.net/acesso?k=<GATE_KEY>` → abre o login.
- [ ] Sem o cookie (aba anônima): `https://radar-vps.<tailnet>.ts.net/` → **403**.
- [ ] Login com o admin; criar imóvel de teste; upload de 1 PDF; baixar o PDF.
- [ ] Apagar `AUTH_BOOTSTRAP_ADMIN_PASSWORD` do `.env.prod` e
      `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend`.
- [ ] Usuários de homologação criados (CONSULTA/ANALISTA) — só pessoas de confiança (ver bloqueador B1).

## 10. Backups
```bash
crontab -e
0 3 * * * cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
30 4 * * * cd /opt/radar-leilao && APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh >> /opt/radar-backups/cron.log 2>&1
```
- [ ] Rodar os dois backups uma vez à mão; arquivos com permissão `-rw-------`.
- [ ] Cópia externa automática configurada (`BACKUP-RESTORE.md §5`) e 1ª cópia conferida.
- [ ] Restore ensaiado em destino isolado (`BACKUP-RESTORE.md §4`).

## 11. Reboot
- [ ] `sudo reboot` → serviços *healthy*, `tailscale serve status` ativo, PDF enviado continua baixando.

## Não fazer
- Não publicar 5432/8000; não usar `PROXY_BIND=0.0.0.0` com dados reais; não usar `tailscale funnel`.
- Não desligar o portão (`GATE_KEY`) enquanto houver rotas sem JWT.
- Não usar `docker compose down -v`; não rodar `deploy.sh first` em instalação existente (ele recusa).
