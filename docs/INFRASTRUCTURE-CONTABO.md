# Radar Leilão — Infraestrutura na VPS Contabo (homologação)

Guia passo a passo para quem nunca configurou uma VPS. Tudo roda numa única VPS com
Docker Compose. Não há serviços pagos adicionais.

```
 celular / notebook ──internet──► IP da VPS :80 ──► proxy (nginx, portão de acesso)
                                                     ├─► frontend (nginx, React)
                                                     └─► backend (FastAPI) ─► PostgreSQL + pgvector
                                                                   worker ──┘   (rede interna, sem porta pública)
                                                     documentos: volume radar-prod_backend_storage
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
```

## 3. SSH com chave (desligar senha)

No **seu computador**:
```bash
ssh-keygen -t ed25519 -C "radar-vps"
ssh-copy-id radar@IP_DA_VPS
```
Na VPS, edite `/etc/ssh/sshd_config`:
```
PasswordAuthentication no
PermitRootLogin no
```
```bash
sudo systemctl restart ssh
```
Teste um novo login **antes** de fechar a sessão atual.

## 4. Firewall (UFW)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp        # remova se usar só Tailscale
sudo ufw enable
sudo ufw status
```
A porta 5432 (PostgreSQL) **não** é aberta: o banco não publica porta no host.

> Atenção: o Docker escreve regras de iptables próprias e pode contornar o UFW para
> portas publicadas. Por isso o compose só publica a porta do proxy; nada mais.

## 5. Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker radar   # saia e entre de novo
docker version && docker compose version
```
Rotação de logs já está configurada no compose (10 MB × 5 por container).

## 6. Código e configuração

```bash
sudo mkdir -p /opt/radar-leilao /opt/radar-backups && sudo chown radar: /opt/radar-leilao /opt/radar-backups
git clone https://github.com/jabesfelipe/radar-leilao.git /opt/radar-leilao
cd /opt/radar-leilao
cp .env.prod.example .env.prod && chmod 600 .env.prod
nano .env.prod   # preencha POSTGRES_PASSWORD, JWT_SECRET_KEY, GATE_KEY, CORS_ALLOW_ORIGINS, admin
```
Geração de segredos:
```bash
openssl rand -base64 24   # POSTGRES_PASSWORD
openssl rand -base64 48   # JWT_SECRET_KEY
openssl rand -hex 24      # GATE_KEY
```

## 7. Primeiro deploy

```bash
chmod +x scripts/prod/*.sh
scripts/prod/deploy.sh first
```
O script: build → sobe o PostgreSQL → aplica migrations (serviço `migrate`) → sobe tudo →
smoke test. Detalhes em `docs/DOCKER-DEPLOYMENT.md`.

## 8. Acesso pelo celular/computador

1. Abra **uma vez por dispositivo**: `http://IP_DA_VPS/acesso?k=<GATE_KEY>`
   (grava um cookie de 30 dias; sem ele tudo responde 403).
2. Abra `http://IP_DA_VPS` e faça login com o administrador.

Alternativa mais segura (sem porta pública): Tailscale — ver `docs/HOMOLOGATION-GUIDE.md`.

## 9. Backups automáticos (cron do usuário radar)

```bash
crontab -e
# 03:00 banco ; 03:20 documentos
0 3 * * * cd /opt/radar-leilao && BACKUP_DEST=/opt/radar-backups RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
```
Copie `/opt/radar-backups` para **fora da VPS** (ex.: `rsync`/`scp` para seu computador).
Ver `docs/BACKUP-RESTORE.md`.

## 10. Reinicialização da VPS

Todos os serviços usam `restart: unless-stopped`: após reboot o Docker sobe tudo sozinho.
```bash
sudo reboot
# depois:
cd /opt/radar-leilao && docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

## 11. Checklist

Ver `docs/CONTABO-CHECKLIST.md`.
