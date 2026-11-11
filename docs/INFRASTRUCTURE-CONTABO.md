# Radar Leilão — Infraestrutura na VPS Contabo (homologação)

Guia passo a passo para quem nunca configurou uma VPS. Tudo roda numa única VPS com
Docker Compose. Não há serviços pagos adicionais. **Siga a ordem**: cada passo depende do
anterior (ex.: o firewall vem antes do Docker; o nome Tailscale vem antes do `.env.prod`;
as migrations rodam antes de backend/worker, que recusam subir com schema incompatível).

```
 celular / notebook ──(app Tailscale, WireGuard + HTTPS *.ts.net)──► tailscale serve :443
                                                                        │ (só na tailnet)
                                                                        ▼
                                              127.0.0.1:8080 ► proxy (nginx, portão de acesso)
                                                                ├─► frontend (nginx, React)
                                                                └─► backend (FastAPI) ─► PostgreSQL + pgvector
                                                                          worker ──┘   (rede interna, sem porta)
                                              documentos: volume radar-prod_backend_storage
 Internet ──► IP público: só a porta 22 (SSH por chave). Nada da aplicação.
```

## 1. Plano recomendado

| Item | Mínimo (validação) | Recomendado |
|---|---|---|
| vCPU | 2 | 4 |
| RAM | 4 GB (sem OCR em lote) | **8 GB** se usar OCR/PDFs grandes |
| Disco | 60 GB NVMe | 80 GB NVMe |
| SO | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |

Detalhes de memória em `docs/DOCKER-DEPLOYMENT.md §Memória`.

## 2. Preparar o Ubuntu (como root, no primeiro acesso)

```bash
ssh root@IP_DA_VPS
apt-get update && apt-get -y upgrade
timedatectl set-timezone America/Sao_Paulo

# Usuário de operação (não use root no dia a dia)
adduser radar
usermod -aG sudo radar

# Swap de 2 GB (protege contra pico de memória em 4 GB)
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10 && echo 'vm.swappiness=10' > /etc/sysctl.d/99-radar.conf
free -h   # deve mostrar Swap: 2.0Gi
```

## 3. SSH com chave (desligar senha)

No **seu computador**:
```bash
ssh-keygen -t ed25519 -C "radar-vps"
ssh-copy-id radar@IP_DA_VPS
ssh radar@IP_DA_VPS 'echo chave-ok'     # TEM que funcionar antes do próximo passo
```
Na VPS (`sudo nano /etc/ssh/sshd_config` ou um arquivo em `/etc/ssh/sshd_config.d/`):
```
PasswordAuthentication no
PermitRootLogin no
```
```bash
sudo sshd -t && sudo systemctl restart ssh
```
Teste um novo login em **outro terminal** antes de fechar a sessão atual.

## 4. Firewall (UFW) — antes do Docker

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```
Modo B (Tailscale, padrão): **não** abra 80/443. Modo A (IP público, só teste curto):
`sudo ufw allow 80/tcp`.

> **Docker ignora o UFW para portas publicadas** (insere regras próprias no iptables). Por
> isso a proteção real é o compose publicar o proxy **só em `127.0.0.1`** (`PROXY_BIND`).
> PostgreSQL (5432) e backend (8000) não publicam porta nenhuma.

## 5. Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker radar
exit                                   # saia e entre de novo como radar
docker version && docker compose version
```
Rotação de logs já está configurada no compose (10 MB × 5 por container).

## 6. Tailscale (rede privada)

Pré-requisito no painel Tailscale: **MagicDNS** e **HTTPS Certificates** habilitados.
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --hostname=radar-vps
tailscale status        # anote radar-vps.<tailnet>.ts.net
```
Detalhes e o modo alternativo por IP público: `docs/HOMOLOGATION-GUIDE.md`.

## 7. Código e configuração

```bash
sudo mkdir -p /opt/radar-leilao /opt/radar-backups
sudo chown radar: /opt/radar-leilao /opt/radar-backups && chmod 700 /opt/radar-backups
git clone https://github.com/jabesfelipe/radar-leilao.git /opt/radar-leilao
cd /opt/radar-leilao
git checkout <tag-ou-commit-homologado>
cp .env.prod.example .env.prod && chmod 600 .env.prod
openssl rand -base64 24   # -> POSTGRES_PASSWORD
openssl rand -base64 48   # -> JWT_SECRET_KEY
openssl rand -hex 24      # -> GATE_KEY (48 hex)
nano .env.prod
```
Preencha: `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `GATE_KEY`,
`CORS_ALLOW_ORIGINS=https://radar-vps.<tailnet>.ts.net`, `AUTH_BOOTSTRAP_ADMIN_EMAIL`,
`AUTH_BOOTSTRAP_ADMIN_PASSWORD` (senha forte). Mantenha `PROXY_BIND=127.0.0.1`,
`PROXY_PORT=8080`, `RUN_MIGRATIONS_ON_START=false`, `OCR_ENABLED=false`,
`BACKUP_DEST=/opt/radar-backups`.

## 8. Primeiro deploy (migrations antes dos serviços)

```bash
chmod +x scripts/prod/*.sh
scripts/prod/deploy.sh first
```
O script, em ordem: valida o `.env.prod` (segredos preenchidos, `GATE_KEY` hex ≥ 48,
recusa `PROXY_BIND=0.0.0.0` sem `ALLOW_PUBLIC_HTTP=1`) → build → sobe só o PostgreSQL →
**confirma banco vazio** (se já houver schema, aborta e manda usar `update`) → aplica
migrations (serviço `migrate`) → sobe backend/worker/frontend/proxy → smoke (health 200 com
o cookie e 403 sem). Deve terminar com `DEPLOY_OK`.

Atualizações futuras: `git pull` (ou checkout da nova tag) e `scripts/prod/deploy.sh update`
(exige instalação existente e faz backup de banco + documentos antes de migrar; aborta se o
backup falhar). Detalhes: `docs/DOCKER-DEPLOYMENT.md`.

## 9. Publicar na tailnet e primeiro acesso

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve status
```
1. No celular/computador com o app Tailscale conectado, abra **uma vez por dispositivo**:
   `https://radar-vps.<tailnet>.ts.net/acesso?k=<GATE_KEY>` (cookie de 30 dias).
2. Abra `https://radar-vps.<tailnet>.ts.net` e faça login com o administrador.
3. Remova a senha de bootstrap: apague `AUTH_BOOTSTRAP_ADMIN_PASSWORD` do `.env.prod` e
   rode `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend`.
4. Crie os usuários de homologação (papel CONSULTA/ANALISTA).

## 10. Backups automáticos (cron do usuário radar)

```bash
crontab -e
# 03:00 banco ; 03:20 documentos ; 04:30 limpeza de temporários (só storage/tmp, > 1 dia)
0 3 * * * cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
30 4 * * * cd /opt/radar-leilao && APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh >> /opt/radar-backups/cron.log 2>&1
```
Cópia **fora da VPS** (automática, por pull ou rclone criptografado) e restore:
`docs/BACKUP-RESTORE.md §4–§5`.

## 11. Reinicialização da VPS

Todos os serviços usam `restart: unless-stopped` e o `tailscale serve --bg` é persistente:
após reboot tudo volta sozinho.
```bash
sudo reboot
# depois:
cd /opt/radar-leilao && docker compose -f docker-compose.prod.yml --env-file .env.prod ps
tailscale serve status
```

## 12. Checklist

Ver `docs/CONTABO-CHECKLIST.md`.
