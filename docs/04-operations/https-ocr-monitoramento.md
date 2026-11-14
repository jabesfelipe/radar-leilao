# HTTPS, cookie, OCR, health checks e monitoramento — configuração necessária

> **Situação: PROCEDIMENTO DOCUMENTADO, NÃO APLICADO.** Nada aqui foi executado na VPS nem alterou arquivos de
> infraestrutura. Cada item é uma ação do operador, com verificação. Origem: auditoria final de segurança
> (`docs/06-quality/homologacao-v1.0.2/`). Os comandos assumem `cd /opt/radar-leilao` e `DC=scripts/prod/compose.sh`.

## 1. HTTPS no proxy reverso

**Por que é pré-requisito:** hoje o acesso de homologação é por IP público em **HTTP** (`PROXY_BIND=0.0.0.0` +
`ALLOW_PUBLIC_HTTP=1`). Senha, token JWT (guardado em `localStorage`) e documentos trafegam sem criptografia.
Matrícula e edital contêm CPF, nomes e endereços. **Não envie documento real nesse modo.**

Escolha **uma** das opções (a opção A já está descrita no guia de homologação, modo B):

| Opção | Resumo | Observação |
|---|---|---|
| A. Tailscale (`tailscale serve`) | O proxy fica em `127.0.0.1` (`PROXY_BIND=127.0.0.1`, padrão) e o Tailscale termina o TLS com certificado do tailnet | Sem domínio público; só dispositivos do tailnet. Recomendada para o primeiro imóvel |
| B. Domínio + Caddy ou nginx com Let's Encrypt | TLS termina num proxy na frente do contêiner `radar-prod-proxy`, que continua em HTTP interno | Exige DNS, portas 80/443 e renovação do certificado |

Requisitos comuns a qualquer opção:

1. O proxy que termina o TLS **deve** enviar `X-Forwarded-Proto: https` ao `radar-prod-proxy` e este deve repassá-lo ao backend
   (o template já faz `proxy_set_header X-Forwarded-Proto $scheme`; com TLS terminado **antes** do nginx do projeto, é preciso
   repassar o valor recebido em vez de `$scheme`, por exemplo `map $http_x_forwarded_proto $fwd_proto { default $scheme; https https; }`).
   O backend usa esse cabeçalho para decidir se a conexão é segura.
2. Redirecionar HTTP→HTTPS na borda e enviar `Strict-Transport-Security: max-age=31536000; includeSubDomains` (o backend já o envia em
   respostas HTTPS; configurar também na borda protege as respostas servidas só pelo nginx).
3. `client_max_body_size 50m;` e `proxy_read_timeout 300s;` mantidos (upload de 30 MB e análise síncrona).
4. Fechar o acesso HTTP direto: voltar `PROXY_BIND=127.0.0.1` e remover `ALLOW_PUBLIC_HTTP`.

Exemplo de bloco de borda (referência; ajuste domínio e certificados — **não aplicado**):

```nginx
server { listen 80; server_name radar.exemplo.com.br; return 301 https://$host$request_uri; }
server {
  listen 443 ssl http2; server_name radar.exemplo.com.br;
  ssl_certificate     /etc/letsencrypt/live/radar.exemplo.com.br/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/radar.exemplo.com.br/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  client_max_body_size 50m;
  location / {
    proxy_pass http://127.0.0.1:8080;                 # radar-prod-proxy publicado só em loopback
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
  }
}
```

### `REQUIRE_HTTPS=true`

Ligar **somente depois** de o acesso por HTTPS funcionar (senão ninguém acessa a API). Efeito (testado em
`tests/test_cost_controls_and_https.py`): qualquer rota de API chamada sem `X-Forwarded-Proto: https` responde **426**;
`/health` e loopback são isentos; respostas HTTPS recebem HSTS. **Limite:** o backend confia no cabeçalho do proxy — o nginx do
projeto o **sobrescreve** (`$scheme`), mas um proxy externo mal configurado que repasse o cabeçalho do cliente anularia a proteção.
Verificação (de fora): `curl -si http://HOST/api/imoveis` → `426` ou `403` (portão); `curl -si https://HOST/health` → `200` com
`strict-transport-security`.

## 2. Cookie do portão (`radar_gate`) e sessão

Situação atual (`docker/nginx/templates/default.conf.template`):

| Atributo | Hoje | Necessário com HTTPS |
|---|---|---|
| `HttpOnly` | **sim** | manter |
| `SameSite` | `Lax` | manter `Lax` (o link `/acesso?k=` é navegação de topo; `Strict` quebraria o primeiro acesso por link externo) |
| `Secure` | **não** | **adicionar** (`...; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000`). Exige alterar o template e recriar o proxy (**deploy**) |

Outros pontos: o JWT fica em `localStorage` (exposto a XSS; mitigação: sem conteúdo de terceiros na página, CSP — **não configurada**);
a chave do portão não deve aparecer em logs (o template já desliga `access_log` em `/acesso`); a sessão do JWT expira em 8 h
(`ACCESS_TOKEN_EXPIRE_MINUTES`). Após trocar de modo, **troque** `GATE_KEY` (invalida cookies antigos) e remova a senha de bootstrap do `.env.prod`.

## 3. OCR com Tesseract

A imagem de produção já instala `tesseract-ocr`, `tesseract-ocr-por` e `poppler-utils` (`backend/Dockerfile.prod`). O OCR vem **desligado**
(`OCR_ENABLED=false`) e é **100% local** (nenhum serviço pago ou nuvem). O backend de teste local **não tem** o binário, então o OCR real
**nunca foi executado** nesta homologação — este passo é obrigatório antes do primeiro documento escaneado.

Verificação (somente leitura):

```bash
$DC exec -T backend tesseract --version
$DC exec -T backend tesseract --list-langs | grep -x por       # idioma português presente
$DC exec -T backend pdftoppm -v                                # poppler presente
$DC exec -T backend python -c "from app.documents.ocr import ocr_available; print('ocr_available=', ocr_available())"
```

Ativação controlada: (1) `OCR_ENABLED=true` e `OCR_MAX_PAGES=20` no `.env.prod`; (2) recriar `backend` e `worker`; (3) enviar um PDF
**fictício** escaneado de 1–3 páginas pela tela de Documentos; (4) conferir "OCR: Concluída" e o texto extraído; (5) medir a memória
(`docker stats --no-stream radar-prod-backend`) durante o envio; o teto do contêiner é 2 GB. O OCR é feito **uma página por vez**
(memória limitada) e roda dentro da requisição de upload (limite do proxy: 300 s) — PDFs longos devem ficar em poucas páginas na
primeira rodada. Falhas viram `OCR_FALHOU` e o documento **não** entra no RAG.

## 4. Health checks

| Serviço | Verificação existente | Observação |
|---|---|---|
| `postgres` | `pg_isready` (10 s) | OK |
| `backend` | `curl -fsS http://localhost:8000/health` (15 s) | `/health` é estático: **não** prova banco nem migrations. Para isso: `GET /api/monitoring/readiness` (autenticado) → `db` e `alembic_version` |
| `frontend` | `wget http://127.0.0.1:8080/healthz` | OK |
| `proxy` | `wget http://127.0.0.1/_proxy_health` | OK |
| `worker` | **nenhum** | Lacuna: um worker travado não é detectado. Verificar `$DC ps` e `$DC logs --tail=50 worker` (ciclos a cada 30 s); `GET /api/monitoring/rag/pending` deve tender a 0 |

Smoke pós-deploy: `scripts/prod/post-deploy-check.sh` (deve terminar em `SMOKE_OK`).

## 5. Logs e monitoramento

- **Onde:** `json-file`, 10 MB × 5 arquivos por contêiner. `$DC logs -f --tail=100 backend worker`.
- **O que NÃO aparece:** chaves e tokens (filtro de redação), CPF/RG/e-mail/telefone/dados bancários (mesmo filtro), conteúdo de
  documentos e prompts (nenhum log os imprime). Cada requisição tem `X-Request-ID` (correlação).
- **Atenção:** nomes de pessoas escritos livremente em mensagens de exceção de bibliotecas **não** são removidos dos logs.
- **O que acompanhar na primeira semana:**
  - `GET /api/monitoring/rag` → `orcamento_llm` (gasto do mês × teto, `excedido`, `sem_preco`) e cobertura de embeddings;
  - `GET /api/monitoring/rag/pending` → fila de embeddings;
  - tabela `llm_runs` (status, tokens, custo, agente `embedding` = estimado) — consultas no `CHECKLIST-PRIMEIRO-IMOVEL.md`;
  - painel de uso e limite de gasto da **OpenAI** (a fonte de verdade do custo real);
  - respostas **426** (HTTP indevido), **429** (rate limit), **409** (análise já em andamento) e status `ORCAMENTO_EXCEDIDO`.
- **Alertas sugeridos** (manuais, não há ferramenta instalada): erro 5xx recorrente; `versoes_em_erro > 0`; `pendentes` crescendo;
  gasto do mês acima de 50% do teto; contêiner reiniciando (`$DC ps`).
- **Backups:** `scripts/prod/pg-backup.sh` antes de qualquer ativação (ver `backup-restore.md`).
