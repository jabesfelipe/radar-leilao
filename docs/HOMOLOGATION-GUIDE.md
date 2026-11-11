# Radar Leilão — Guia de Homologação (acesso restrito)

Objetivo: permitir que poucas pessoas validem o produto pelo celular e computador **sem**
abrir uma plataforma pública. Nada do RBAC foi removido.

> Como a versão chega à VPS: **deploy automático por tag** (`git push origin vX.Y.Z`),
> `docs/GITHUB-ACTIONS-DEPLOY.md`. Cada tag homologada fica identificável na VPS
> (`grep RADAR_RELEASE_TAG /opt/radar-leilao/.release.env`) e no resumo do run no GitHub.

## 1. Camadas de proteção

| Camada | O que faz | Onde |
|---|---|---|
| Rede privada (Tailscale, opcional) | proxy publicado só em `127.0.0.1`; acesso remoto só pela tailnet (WireGuard) com HTTPS | VPS + `tailscale serve` |
| Firewall (UFW) | só 22 (modo B) ou 22 e 80 (modo A). **Não protege portas publicadas pelo Docker** | VPS |
| Banco não exposto | PostgreSQL sem porta no host | `docker-compose.prod.yml` |
| **Portão do proxy** | sem cookie `radar_gate` válido ⇒ **403 em tudo** (frontend, API, downloads) | `docker/nginx/templates/default.conf.template` |
| Login JWT + RBAC | ADMIN / ANALISTA / OPERADOR / CONSULTA | backend (Onda 11) |
| Rate limit de login | 10 req/min por IP (burst 5) | proxy |
| Docs da API ocultas | `/docs`, `/redoc`, `/openapi.json` ⇒ 404 | proxy |
| Download autenticado | `GET /api/documentos/versoes/{id}/arquivo` exige JWT; só serve arquivos dentro do storage | backend |

### Por que o portão é necessário
Várias rotas legadas de leitura do backend (`/api/imoveis/...`) ainda **não exigem JWT**
(compatibilidade histórica; o RBAC cobre as rotas novas e as de escrita administrativa).
Expor o backend por IP sem barreira deixaria esses dados acessíveis. O portão fecha isso
na entrada, sem alterar regras de negócio. Fechar as rotas legadas com JWT é pendência
**IMPORTANTE** antes de qualquer acesso público (ver relatório).

## 2. O que trafega e como proteger (sem domínio)

| Dado | Como trafega | Sem HTTPS (modo A) |
|---|---|---|
| Senha do login | corpo do `POST /api/auth/login` | texto claro |
| JWT | header `Authorization: Bearer` em toda chamada `/api` (guardado em `localStorage`) | texto claro |
| Cookie do portão `radar_gate` | todo request | texto claro (sem `Secure`) |
| Documentos (upload/download) | corpo das requisições | texto claro |

Quem capturar o cookie do portão ganha acesso às rotas legadas **sem JWT** (ver
`docs/SECURITY-EXPOSURE-AUDIT.md`). Por isso o **modo seguro de homologação sem domínio é o
modo B**: o tráfego vai cifrado pelo WireGuard da tailnet e, com `tailscale serve --https`,
também por TLS com certificado válido `*.ts.net` — sem comprar domínio e sem porta pública.

> **Decisão da fase atual (business first):** homologação pelo **modo A (IP público, HTTP)**,
> temporária, para testar intensivamente o produto. O `.env.prod.example` já vem nesse modo.
> O modo B fica como opção para quando houver dados reais/sensíveis. Endurecimento global
> (JWT em todas as rotas, RBAC) é uma fase posterior.

## 3. Modo B — Tailscale (opcional, sem porta pública)

Pré-requisitos (conta Tailscale gratuita; não executado nesta missão): no painel
<https://login.tailscale.com/admin/dns> habilite **MagicDNS** e **HTTPS Certificates**.

```bash
# Na VPS
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --hostname=radar-vps        # abre um link para autorizar a máquina
tailscale status                               # confirma o nome radar-vps.<tailnet>.ts.net
```
`.env.prod` (é o padrão do compose quando `PROXY_BIND` não é definido):
```
PROXY_BIND=127.0.0.1      # Docker publica o proxy SÓ no loopback
ALLOW_PUBLIC_HTTP=0
PROXY_PORT=8080
CORS_ALLOW_ORIGINS=https://radar-vps.<tailnet>.ts.net
```
Depois do primeiro deploy (primeira tag), exponha o proxy **só na tailnet**, com HTTPS:
```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve status
```
Restrição da porta (como garantir que nada público aceita conexão):
- O proxy escuta em `127.0.0.1:8080`: inalcançável de fora, independentemente do UFW.
- `tailscale serve` escuta só no IP da tailnet (100.x), nunca no IP público.
- **Nunca** use `tailscale funnel` (publicaria na internet).
- UFW sem regra para 80/443. Confira de fora: `curl -m 5 http://IP_PUBLICO/` deve falhar
  (timeout/recusado) e na VPS `sudo ss -tlnp` não pode mostrar `0.0.0.0:80`/`0.0.0.0:8080`.
- Atenção: se alguém mudar `PROXY_BIND` para `0.0.0.0`, o Docker publica a porta por
  iptables próprias e o UFW **não bloqueia**. O `deploy.sh` recusa `0.0.0.0` sem
  `ALLOW_PUBLIC_HTTP=1`.

Dispositivos: instale o app Tailscale (Android/iOS/Windows/macOS), entre na mesma conta e
abra **uma vez** `https://radar-vps.<tailnet>.ts.net/acesso?k=<GATE_KEY>`; depois use
`https://radar-vps.<tailnet>.ts.net`. O portão continua ativo como 2ª barreira.

Observações: o nome `radar-vps.<tailnet>.ts.net` aparece em logs públicos de Certificate
Transparency (só o nome; o serviço continua inalcançável fora da tailnet). Opcionalmente
restrinja quem da tailnet acessa a VPS com ACLs do Tailscale.

## 3.1 Modo A — IP público com portão (FASE ATUAL: homologação temporária, dados não sensíveis)

`.env.prod`:
```
PROXY_BIND=0.0.0.0
PROXY_PORT=80
ALLOW_PUBLIC_HTTP=1
CORS_ALLOW_ORIGINS=http://IP_DA_VPS
```
+ `sudo ufw allow 80/tcp`. Em cada dispositivo, **uma vez**:
`http://IP_DA_VPS/acesso?k=<GATE_KEY>` → cookie de 30 dias (HttpOnly). Senha, JWT, cookie e
documentos trafegam **em texto claro**; qualquer rede no caminho (Wi-Fi público, operadora)
pode capturá-los. Não use com dados reais.

## 3.2 Revogar acesso / higiene da chave

- Trocar `GATE_KEY` no `.env.prod` e `scripts/prod/compose.sh up -d --no-build proxy`
  invalida todos os cookies.
- O proxy **não registra** `/acesso` em log (a URL contém a chave). O histórico do navegador
  guarda a URL: após o 1º acesso, apague-a do histórico em dispositivos compartilhados.
- Envie o link `/acesso?k=...` só por canal privado.

## 4. Domínio + HTTPS (pós-homologação)

Quando houver domínio: use `docker/nginx-proxy.conf` (TLS) como base, emita certificado com
certbot e mude `CORS_ALLOW_ORIGINS` para `https://seu-dominio`. Ver `docs/DEPLOYMENT.md §4`.

## 5. Usuários

- Primeiro admin: `AUTH_BOOTSTRAP_ADMIN_EMAIL/PASSWORD` no `.env.prod` (cria só se não
  houver usuários). Após o primeiro login, **remova a senha** do `.env.prod`.
- Demais usuários: tela/endpoint de gestão (`/api/auth/usuarios`, só ADMIN). Não existe
  cadastro público.
- Para homologadores use papel **CONSULTA** (leitura) ou **ANALISTA**.

## 6. O que NÃO fazer

- Não publicar a porta 5432 nem 8000.
- Não desativar o portão (`GATE_KEY`) enquanto houver rotas legadas sem JWT.
- Não compartilhar o link `/acesso?k=...` em canais públicos.
- Não usar `X-Admin-Token` em produção (deixe `ADMIN_API_TOKEN` vazio).
