# Radar Leilão — Guia de Homologação (acesso restrito)

Objetivo: permitir que poucas pessoas validem o produto pelo celular e computador **sem**
abrir uma plataforma pública. Nada do RBAC foi removido.

## 1. Camadas de proteção

| Camada | O que faz | Onde |
|---|---|---|
| Firewall (UFW) | só 22 e 80 (ou só 22 com Tailscale) | VPS |
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

## 2. Modo A — IP público com portão (padrão do compose)

`.env.prod`:
```
PROXY_BIND=0.0.0.0
PROXY_PORT=80
GATE_KEY=<openssl rand -hex 24>
```
Em cada dispositivo, **uma vez**: `http://IP_DA_VPS/acesso?k=<GATE_KEY>` → cookie de 30 dias
(HttpOnly). Depois: `http://IP_DA_VPS` e login.

Revogar acesso de todos: troque `GATE_KEY` e `docker compose ... up -d proxy`.

Limitação: sem HTTPS, o tráfego (inclusive senha e cookie) vai em texto claro. Aceitável
apenas para validação curta com dados não sensíveis; para uso contínuo use o Modo B ou
adicione domínio + TLS (§4).

## 3. Modo B — Tailscale (recomendado, sem porta pública)

Tailscale cria uma rede privada criptografada entre seus dispositivos e a VPS (plano
gratuito pessoal). Passos (exigem conta Tailscale — não feito nesta missão):

```bash
# Na VPS
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up            # abre um link para autorizar a máquina
tailscale ip -4              # ex.: 100.x.y.z
```
`.env.prod`:
```
PROXY_BIND=127.0.0.1      # proxy só local
PROXY_PORT=8080
CORS_ALLOW_ORIGINS=http://radar-vps   # nome MagicDNS da VPS
```
Exponha o proxy só na tailnet:
```bash
sudo tailscale serve --bg --http=80 http://127.0.0.1:8080
sudo ufw delete allow 80/tcp     # fecha a porta pública
```
No celular/notebook: instale o app Tailscale, entre na mesma conta e abra
`http://radar-vps` (o portão continua ativo: use `/acesso?k=...` uma vez).
Opcional: `tailscale serve --https=443 ...` fornece HTTPS com certificado da própria tailnet.

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
