# Radar Leilão — Checklist de implantação na Contabo (homologação TEMPORÁRIA por IP público)

> **Ambiente temporário de testes.** Acesso por `http://IP_DA_VPS` (HTTP, sem TLS). Senha,
> token, cookie do portão e documentos trafegam sem criptografia, e várias rotas da API
> não exigem JWT (ver `SECURITY-EXPOSURE-AUDIT.md`). **Não use dados sensíveis reais** e não
> trate isto como produção. Barreiras mantidas: portão por chave (`GATE_KEY`) + login.
> Alternativa privada (Tailscale + HTTPS): `HOMOLOGATION-GUIDE.md §3`.

Marque na ordem. Explicações: `INFRASTRUCTURE-CONTABO.md`, `DOCKER-DEPLOYMENT.md`,
`BACKUP-RESTORE.md`. Todos os comandos abaixo foram conferidos contra os scripts do repositório.

## 0. Antes de contratar
- [ ] Plano: mínimo 2 vCPU / 4 GB / 60 GB NVMe (OCR desligado); 8 GB se OCR/PDFs grandes.
- [ ] Imagem **Ubuntu 24.04 LTS**. Anote o **IP público** da VPS.

## 1. Preparar a VPS (como root)
```bash
ssh root@IP_DA_VPS
apt-get update && apt-get -y upgrade
timedatectl set-timezone America/Sao_Paulo
adduser radar && usermod -aG sudo radar
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10 && echo 'vm.swappiness=10' > /etc/sysctl.d/99-radar.conf
free -h
```
SSH por chave (do seu computador; depois na VPS):
```bash
ssh-keygen -t ed25519 -C radar-vps && ssh-copy-id radar@IP_DA_VPS && ssh radar@IP_DA_VPS 'echo chave-ok'
# na VPS, só depois do "chave-ok":
printf 'PasswordAuthentication no\nPermitRootLogin no\n' | sudo tee /etc/ssh/sshd_config.d/99-radar.conf
sudo sshd -t && sudo systemctl restart ssh
```
Firewall:
```bash
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw enable && sudo ufw status verbose
```
(O Docker publica a porta 80 por regras próprias de iptables; a regra do UFW documenta a
intenção. 5432 e 8000 nunca são publicadas.)

## 2. Instalar Docker
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker radar
exit                      # entre de novo:  ssh radar@IP_DA_VPS
docker version && docker compose version
```

## 3. Clonar o repositório
```bash
sudo mkdir -p /opt/radar-leilao /opt/radar-backups
sudo chown radar: /opt/radar-leilao /opt/radar-backups && chmod 700 /opt/radar-backups
git clone https://github.com/jabesfelipe/radar-leilao.git /opt/radar-leilao
cd /opt/radar-leilao
chmod +x scripts/prod/*.sh
```

## 4. Configurar `.env.prod`
```bash
cp .env.prod.example .env.prod && chmod 600 .env.prod
openssl rand -base64 24    # -> POSTGRES_PASSWORD
openssl rand -base64 48    # -> JWT_SECRET_KEY
openssl rand -hex 24       # -> GATE_KEY  (guarde: é a "chave de entrada" dos dispositivos)
nano .env.prod
```
Preencha:
- `POSTGRES_PASSWORD=`, `JWT_SECRET_KEY=`, `GATE_KEY=` (valores gerados acima)
- `CORS_ALLOW_ORIGINS=http://IP_DA_VPS`
- `AUTH_BOOTSTRAP_ADMIN_EMAIL=` e `AUTH_BOOTSTRAP_ADMIN_PASSWORD=` (senha forte)

## 5. Acesso temporário pelo IP público
Já vem assim no `.env.prod.example` — só confira:
```
PROXY_BIND=0.0.0.0
PROXY_PORT=80
ALLOW_PUBLIC_HTTP=1
```
Mantenha também: `RUN_MIGRATIONS_ON_START=false`, `STORAGE_BACKEND=local`, `OCR_ENABLED=false`,
`BACKUP_DEST=/opt/radar-backups`. `OPENAI_API_KEY` vazio = sem chamadas pagas (RAG por
busca textual; agentes registram `SEM_CHAVE`).

## 6 + 7. Migrations e serviços (um comando)
```bash
scripts/prod/deploy.sh first
```
Faz, em ordem: valida o `.env.prod` → build das imagens → sobe só o PostgreSQL → confirma
banco **vazio** → `migrate` (0001 → head) → sobe backend, worker, frontend e proxy →
smoke. Saída esperada no final:
```
health=200 sem_cookie=403 interface_externa=200
DEPLOY_OK
AMBIENTE TEMPORÁRIO DE TESTES (HTTP sem TLS; não use dados sensíveis).
1º acesso em cada dispositivo: http://IP_DA_VPS/acesso?k=<GATE_KEY do .env.prod>
Depois: http://IP_DA_VPS
```
- [ ] `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` → backend, postgres, frontend e proxy *healthy*; worker *running*.
- [ ] `scripts/prod/post-deploy-check.sh http://IP_DA_VPS` → `SMOKE_OK`.

## 8. Validar no navegador (celular e computador)
- [ ] Abrir **uma vez por dispositivo** `http://IP_DA_VPS/acesso?k=<GATE_KEY>` → vai para o login
      (cookie de 30 dias). Sem isso, tudo responde 403.
- [ ] Login com o admin de bootstrap.
- [ ] Depois do 1º login: apagar `AUTH_BOOTSTRAP_ADMIN_PASSWORD` do `.env.prod` e rodar
      `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend`.
- [ ] Criar usuários de teste (tela de usuários / `POST /api/auth/usuarios`, só ADMIN).

## 9. Validar upload, download, análises e persistência
- [ ] Cadastrar um imóvel de teste; enviar um PDF e um TXT na aba de documentos.
- [ ] Rodar a análise do imóvel (sem chave LLM: análise determinística + agentes `SEM_CHAVE`).
- [ ] Abrir financeiro, jurídico e due diligence do imóvel.
- [ ] Download (não há botão no frontend; pela API com o token):
```bash
# no seu computador; TOKEN = access_token do login, ID = id da versão (aba documentos/API)
curl -b "radar_gate=<GATE_KEY>" -H "Authorization: Bearer TOKEN" -o arquivo.pdf "http://IP_DA_VPS/api/documentos/versoes/ID/arquivo"
```
- [ ] Persistência: `sudo reboot` → tudo volta sozinho; imóvel, documentos e download continuam.

## 10. Backups (cron do usuário radar)
```bash
crontab -e
0 3 * * * cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
30 4 * * * cd /opt/radar-leilao && APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh >> /opt/radar-backups/cron.log 2>&1
```
- [ ] Rodar `scripts/prod/pg-backup.sh /opt/radar-backups` e `scripts/prod/storage-backup.sh /opt/radar-backups` uma vez à mão.
- [ ] Cópia fora da VPS (`BACKUP-RESTORE.md §5`), ex. do seu computador:
      `rsync -a radar@IP_DA_VPS:/opt/radar-backups/ ./radar-backups/`

## 11. Atualizar a aplicação
```bash
cd /opt/radar-leilao
git pull                   # ou: git fetch --tags && git checkout <tag>
scripts/prod/deploy.sh update
```
Exige instalação existente; faz backup de banco + documentos antes de migrar (aborta se o
backup falhar); migra; sobe; smoke. Rollback: `DOCKER-DEPLOYMENT.md §6`.

## Não fazer
- Não usar `docker compose down -v` (apaga os volumes de dados). Para parar: `docker compose -f docker-compose.prod.yml --env-file .env.prod stop` (ou `down` sem `-v`).
- Não rodar `deploy.sh first` numa instalação existente (ele recusa).
- Não publicar 5432/8000; não compartilhar o link `/acesso?k=...` publicamente.
- Não carregar dados sensíveis reais enquanto o acesso for HTTP público.
