# Plano de HTTPS e implantação da v1.0.4 na VPS de homologação

**Situação: preparado, não executado.** Inspeção somente leitura em 14/11/2026: v1.0.3 em HTTP na porta 80, sem
certificado, sem Tailscale, sem chave da OpenAI e sem limites de IA (ver
[HOMOLOGACAO-QUALIDADE-IA.md §6](HOMOLOGACAO-QUALIDADE-IA.md)). Execução depende de **uma** entrada do responsável:

| Opção | Entrada necessária | Observação |
|---|---|---|
| A. Tailscale (`tailscale serve`) — recomendada sem domínio | autorizar a VPS na conta Tailscale (`sudo tailscale up` abre um link) ou uma auth key de uso único | só dispositivos da tailnet acessam; certificado `*.ts.net` válido e renovado pelo Tailscale |
| B. Domínio + Let's Encrypt | registro DNS `A` do domínio para o IP da VPS; e-mail para o certbot | acesso público por HTTPS; renovação por timer do certbot |

Procedimentos detalhados já existentes: [homologation-guide.md §3](../../04-operations/homologation-guide.md) (A) e
[https-ocr-monitoramento.md §1–2](../../04-operations/https-ocr-monitoramento.md) (B, cookie `Secure`, `REQUIRE_HTTPS`).
Comandos assumem `cd /opt/radar-leilao` e `DC=scripts/prod/compose.sh`.

## 1. Antes (backup e confirmação do ambiente)

```bash
hostname; git describe --tags; docker ps --format '{{.Names}} {{.Status}}'   # confirmar VPS e versão
cp .env.prod ".env.prod.bak.$(date +%Y%m%d%H%M)"                              # cópia do .env.prod (fica na VPS)
scripts/prod/pg-backup.sh && scripts/prod/storage-backup.sh                   # banco + documentos (ver backup-restore.md)
```

## 2. HTTPS

- **A:** `sudo tailscale up --hostname=radar-vps`; `sudo tailscale serve --bg --https=443 http://127.0.0.1:8080`;
  no `.env.prod`: `PROXY_BIND=127.0.0.1`, `PROXY_PORT=8080`, `ALLOW_PUBLIC_HTTP=0`,
  `CORS_ALLOW_ORIGINS=https://radar-vps.<tailnet>.ts.net`.
- **B:** bloco de borda do doc de HTTPS (TLS 1.2/1.3, HSTS, `X-Forwarded-Proto https`, `client_max_body_size 50m`),
  `certbot --nginx -d <dominio>`, `systemctl list-timers | grep certbot` (renovação), `PROXY_BIND=127.0.0.1`,
  `CORS_ALLOW_ORIGINS=https://<dominio>`; cookie do portão com `Secure` (alteração do template, item 2 do doc de HTTPS).

## 3. Versão e variáveis (somente após aprovação e merge da PR e tag v1.0.4)

```bash
# .env.prod (sem imprimir valores): limites validados na homologação e falha segura
LLM_BUDGET_USD_MONTH=0.50
LLM_BUDGET_USD_PER_ANALYSIS=0.10
LLM_MAX_OUTPUT_TOKENS=1500
LLM_REQUIRE_BUDGET=true
LLM_REDACT_PII=true
REQUIRE_HTTPS=true          # SOMENTE depois de o acesso por HTTPS funcionar
```

Implantação pela tag (fluxo existente `release.yml` / `docker-deployment.md`); a migration 0025 só adiciona colunas
opcionais. A chave da OpenAI é configurada pelo responsável no `.env.prod`, nunca no repositório.

## 4. Validação externa (antes de liberar upload real)

```bash
curl -si http://<host>/api/imoveis | head -1        # A: sem resposta pública; B: 301 para https
curl -si https://<host>/health | grep -i strict-transport-security
curl -si -H 'X-Forwarded-Proto: http' https://<host>/api/imoveis | head -1   # 426 com REQUIRE_HTTPS=true (ou 403 do portão)
$DC ps                                                # todos healthy
scripts/prod/post-deploy-check.sh                     # verificação existente pós-implantação
```

E, com a chave e os limites configurados, uma execução do `caso-01` sintético contra o ambiente (`--allow-remote`), nunca
com documento real antes de todos os itens acima.

## 5. Rollback

1. `cp .env.prod.bak.<data> .env.prod` e `$DC up -d` (volta ao modo anterior).
2. A: `sudo tailscale serve reset`; B: remover o bloco de borda e `systemctl reload nginx`.
3. Versão: `scripts/prod/rollback.sh` para a tag anterior (`v1.0.3`); a migration 0025 tem `downgrade` (remove só as colunas novas), mas não é
   necessária para a v1.0.3 funcionar (colunas opcionais são ignoradas).
4. Dados: restaurar do backup do passo 1 apenas se houver corrupção (ver backup-restore.md).
