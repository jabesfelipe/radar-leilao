# Radar Leilão — Infraestrutura na VPS Contabo (homologação)

> **Fase atual: homologação TEMPORÁRIA pelo IP público, por HTTP**, com **deploy automático
> por tag** (GitHub Actions). Sem TLS e com rotas da API sem JWT, este ambiente **não** é
> adequado a dados sensíveis nem a produção.
>
> - Roteiro sequencial: `docs/CONTABO-CHECKLIST.md`
> - Pipeline (tag → CI → GHCR → VPS): `docs/GITHUB-ACTIONS-DEPLOY.md`
> - Registro da máquina contratada: `docs/infra/CONTABO-VPS.md`

```
 git push origin vX.Y.Z ─► GitHub Actions ─► GHCR (imagens vX.Y.Z)
                                   │ SSH (usuário radar, chave restrita)
                                   ▼
 celular / notebook ──internet──► http://IP_DA_VPS:80 ► proxy (nginx, portão de acesso)
                                                         ├─► frontend (React)
                                                         └─► backend (FastAPI) ─► PostgreSQL + pgvector
                                                                   worker ──┘   (rede interna, sem porta)
                                    volumes: radar-prod_postgres_data (banco)
                                             radar-prod_backend_storage (documentos)
 Portas públicas: 22 (SSH por chave) e 80 (proxy). 5432/8000 nunca publicadas.
```

## 1. Máquina (validada)

| Item | Contabo Cloud VPS 6 |
|---|---|
| CPU | 6 vCPU AMD EPYC |
| RAM | ~11 GiB + swap 4 GB (persistente) |
| Disco | 193 GB |
| SO / kernel | Ubuntu 24.04.5 LTS / `6.8.0-149-generic` (após reboot) |
| Docker | Engine 29.9.3, Compose 5.7.1 (repositório oficial), serviço habilitado |

Limites de memória dos containers dimensionados para essa máquina:
`docs/DOCKER-DEPLOYMENT.md §8`. Instalação do Docker e swap como foram feitas:
`docs/infra/CONTABO-VPS.md §4–§5` (não repetir).

## 2. O que falta fazer na VPS (uma vez)

Só o **bootstrap** (`scripts/prod/bootstrap-vps.sh`, como root) — passo 2 do checklist. Ele
cria o usuário de deploy `radar`, autoriza a chave do GitHub Actions, clona o repositório em
`/opt/radar-leilao`, cria `/opt/radar-backups` e gera o `.env.prod` com segredos aleatórios.
Com `--configure-ufw` libera SSH e 80/tcp.

> **Docker ignora o UFW para portas publicadas** (regras próprias no iptables): com
> `PROXY_BIND=0.0.0.0` a porta 80 fica acessível mesmo sem regra no UFW; com
> `PROXY_BIND=127.0.0.1` (modo Tailscale) fica inacessível de fora mesmo com a regra.

Recomendado (manual, com cuidado para não se trancar fora): desligar login por senha no SSH
depois de confirmar que a chave funciona:
```bash
printf 'PasswordAuthentication no\nPermitRootLogin prohibit-password\n' | sudo tee /etc/ssh/sshd_config.d/99-radar.conf
sudo sshd -t && sudo systemctl restart ssh      # teste um novo login ANTES de fechar a sessão
```

## 3. Deploy

Não há deploy manual: cada versão é uma tag (`git push origin vX.Y.Z`). A primeira tag faz o
**primeiro deploy** (banco vazio ⇒ modo `first`); as seguintes, **atualizações** com backup
obrigatório antes das migrations. Ver `docs/GITHUB-ACTIONS-DEPLOY.md`.

## 4. Primeiro acesso

1. Em cada dispositivo, **uma vez**: `http://IP_DA_VPS/acesso?k=<GATE_KEY>` (cookie de 30 dias;
   sem ele tudo responde 403). A `GATE_KEY` foi impressa pelo bootstrap.
2. Abra `http://IP_DA_VPS` e faça login com o administrador do bootstrap.
3. Remova a senha de bootstrap: apague o valor de `AUTH_BOOTSTRAP_ADMIN_PASSWORD` no
   `.env.prod` e rode `scripts/prod/compose.sh up -d --no-build backend`.
4. Crie os usuários de homologação (papel CONSULTA/ANALISTA).

Modo Tailscale (opcional, rede privada + HTTPS): `docs/HOMOLOGATION-GUIDE.md §3`.

## 5. Operação

```bash
cd /opt/radar-leilao
scripts/prod/compose.sh ps
scripts/prod/compose.sh logs -f --tail=100 backend
scripts/prod/post-deploy-check.sh http://IP_DA_VPS
docker stats --no-stream
```

## 6. Backups automáticos (cron do usuário radar)

```bash
crontab -e
# 03:00 banco ; 03:20 documentos ; 04:30 limpeza de temporários (só storage/tmp, > 1 dia)
0 3 * * * cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
30 4 * * * cd /opt/radar-leilao && APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh >> /opt/radar-backups/cron.log 2>&1
```
Cópia **fora da VPS** e restore: `docs/BACKUP-RESTORE.md §4–§5`.

## 7. Reinicialização

Todos os serviços usam `restart: unless-stopped`: após `sudo reboot` tudo volta sozinho, com as
imagens da versão registrada em `.release.env`.
```bash
cd /opt/radar-leilao && scripts/prod/compose.sh ps
```
