# Radar Leilão — Infraestrutura na VPS Contabo (homologação)

> **Fase atual: homologação TEMPORÁRIA pelo IP público, por HTTP** (prioridade: validar o
> produto). Sem TLS e com rotas da API sem JWT, este ambiente **não** é adequado a dados
> sensíveis nem a produção. O roteiro curto e validado está em `docs/CONTABO-CHECKLIST.md`;
> este guia detalha cada passo. O modo privado (Tailscale + HTTPS) continua disponível como
> opção (§6 e `HOMOLOGATION-GUIDE.md §3`).

Tudo roda numa única VPS com Docker Compose. **Siga a ordem**: cada passo depende do
anterior (o firewall vem antes do Docker; as migrations rodam antes de backend/worker, que
recusam subir com schema incompatível).

```
 celular / notebook ──internet──► http://IP_DA_VPS:80 ► proxy (nginx, portão de acesso)
                                                         ├─► frontend (nginx, React)
                                                         └─► backend (FastAPI) ─► PostgreSQL + pgvector
                                                                   worker ──┘   (rede interna, sem porta)
                                    volumes: radar-prod_postgres_data (banco)
                                             radar-prod_backend_storage (documentos)
 Portas públicas: 22 (SSH por chave) e 80 (proxy). 5432/8000 nunca publicadas.
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
Modo IP público (fase atual): `sudo ufw allow 80/tcp`. Modo Tailscale: não abra 80/443.

> **Docker ignora o UFW para portas publicadas** (insere regras próprias no iptables): com
> `PROXY_BIND=0.0.0.0` a porta 80 fica acessível mesmo sem a regra do UFW; com
> `PROXY_BIND=127.0.0.1` fica inacessível de fora mesmo com a regra. PostgreSQL (5432) e
> backend (8000) não publicam porta nenhuma.

## 5. Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker radar
exit                                   # saia e entre de novo como radar
docker version && docker compose version
```
Rotação de logs já está configurada no compose (10 MB × 5 por container).

## 6. (Opcional) Tailscale — rede privada

**Pule esta seção no modo IP público.** Pré-requisito no painel Tailscale: **MagicDNS** e
**HTTPS Certificates** habilitados.
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
`CORS_ALLOW_ORIGINS=http://IP_DA_VPS`, `AUTH_BOOTSTRAP_ADMIN_EMAIL`,
`AUTH_BOOTSTRAP_ADMIN_PASSWORD` (senha forte). O exemplo já vem no modo IP público
(`PROXY_BIND=0.0.0.0`, `PROXY_PORT=80`, `ALLOW_PUBLIC_HTTP=1`). Mantenha
`RUN_MIGRATIONS_ON_START=false`, `OCR_ENABLED=false`, `BACKUP_DEST=/opt/radar-backups`.
(Modo Tailscale: `PROXY_BIND=127.0.0.1`, `PROXY_PORT=8080`, `ALLOW_PUBLIC_HTTP=0`,
`CORS_ALLOW_ORIGINS=https://radar-vps.<tailnet>.ts.net`.)

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

## 9. Primeiro acesso

Modo IP público (fase atual):
1. Em cada dispositivo, **uma vez**: `http://IP_DA_VPS/acesso?k=<GATE_KEY>` (cookie de 30 dias;
   sem ele tudo responde 403).
2. Abra `http://IP_DA_VPS` e faça login com o administrador.

Modo Tailscale (opcional): `sudo tailscale serve --bg --https=443 http://127.0.0.1:8080` e use
`https://radar-vps.<tailnet>.ts.net/acesso?k=<GATE_KEY>` / `https://radar-vps.<tailnet>.ts.net`.
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
