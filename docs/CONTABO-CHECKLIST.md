# Radar Leilão — Checklist de implantação na Contabo

Marque na ordem. Detalhes: `INFRASTRUCTURE-CONTABO.md`, `DOCKER-DEPLOYMENT.md`,
`HOMOLOGATION-GUIDE.md`, `BACKUP-RESTORE.md`.

## Antes de contratar
- [ ] Plano: 4 vCPU/8 GB recomendado; mínimo 2 vCPU/4 GB (OCR desligado). Disco ≥ 60 GB NVMe.
- [ ] Ubuntu 24.04 LTS.
- [ ] Decidir acesso: **Tailscale** (recomendado) ou IP público + portão.

## VPS
- [ ] Atualizar pacotes, timezone `America/Sao_Paulo`.
- [ ] Usuário `radar` com sudo; login por chave SSH; `PasswordAuthentication no`; `PermitRootLogin no`.
- [ ] Swap 2 GB, `vm.swappiness=10`.
- [ ] UFW: deny incoming; allow OpenSSH; allow 80 (só se IP público).
- [ ] Docker + compose instalados; `radar` no grupo docker.

## Aplicação
- [ ] `git clone` em `/opt/radar-leilao` (tag/commit homologado).
- [ ] `.env.prod` criado de `.env.prod.example`, `chmod 600`.
- [ ] `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `GATE_KEY` gerados com `openssl rand`.
- [ ] `CORS_ALLOW_ORIGINS` = `http://IP_DA_VPS` (ou nome Tailscale).
- [ ] Admin de bootstrap preenchido (remover a senha depois do 1º login).
- [ ] `scripts/prod/deploy.sh first` terminou com `DEPLOY_OK`.

## Verificação
- [ ] `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` → backend/postgres/proxy *healthy*.
- [ ] Sem cookie: `curl -I http://IP_DA_VPS/` → **403**.
- [ ] `http://IP_DA_VPS/acesso?k=<GATE_KEY>` → redireciona e abre o login.
- [ ] Login com o admin; criar 1 imóvel de teste; upload de 1 PDF; baixar o PDF.
- [ ] `ss -tlnp` na VPS: só 22 e 80 escutando externamente (nada em 5432/8000).
- [ ] `sudo reboot` → serviços voltam sozinhos; documento enviado continua baixando.

## Operação
- [ ] Cron de backup (banco 03:00, documentos 03:20) configurado.
- [ ] 1º backup copiado para fora da VPS (`rsync`).
- [ ] Restore ensaiado: `pg-restore-verify.sh` + `storage-restore.sh` em destino isolado.
- [ ] Usuários de homologação criados com papel CONSULTA/ANALISTA.

## Não fazer
- [ ] Não publicar 5432/8000; não desligar o portão; não usar `docker compose down -v`.
