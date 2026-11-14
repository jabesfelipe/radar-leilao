# Plano de ativação da OpenAI — Radar Leilão v1.0.2

> **Situação: PROPOSTA, NÃO EXECUTADA.** A OpenAI **não** foi ativada em nenhum ambiente. Nenhuma chave foi
> criada, lida ou alterada, o `.env.prod` não foi tocado e nenhuma análise paga foi executada.
> A ativação só acontece com autorização explícita do responsável, depois dos pré-requisitos abaixo.
>
> **Atualizado após a rodada de correções P0/P1** (branch `homologacao-v1.0.2`, sem commit, sem deploy).
> Os itens marcados **CORRIGIDO** têm teste automatizado; o que depende da OpenAI real continua **NÃO VALIDADO**.

Base factual: código da branch de homologação e testes em backend local **sem chave**
(ver [AUDITORIA-LLM.md](AUDITORIA-LLM.md) e [HOMOLOGACAO-PRODUTO.md](HOMOLOGACAO-PRODUTO.md)).

## 1. Estado atual (por evidência)

| Item | Estado | Evidência |
|---|---|---|
| Provider/modelo | `openai` / `gpt-4o-mini`; embeddings `text-embedding-3-small`, 1536 dimensões | `config.py`; `docker-compose.prod.yml` |
| Chave no compose | `OPENAI_API_KEY: ${OPENAI_API_KEY:-}` (vazia por padrão) | `docker-compose.prod.yml` |
| Chave na VPS | **NÃO VALIDADO** (sem acesso à VPS). A documentação operacional afirma que está vazia | `docs/04-operations/infrastructure.md` |
| OCR | Desligado por padrão (`OCR_ENABLED=false`); Tesseract e Poppler estão na imagem. O backend local de teste **não tem** o binário do Tesseract: o OCR real **não foi executado** | `Dockerfile.prod`; `ocr_available()` |
| Sem chave | Agentes retornam `SEM_CHAVE`; a análise é `falha / IA_INDISPONIVEL` (não mais "concluída") | `tests/test_analysis_status.py`, E2E `correcoes.spec.ts` |
| Teste de conexão | **Não existe endpoint.** Usar o script da §4 (passo 3) | `routers/monitoring.py` |

### Verificar a VPS sem expor segredo (somente leitura)

Rodar na VPS, em `/opt/radar-leilao`. Os comandos **não imprimem** a chave:

```bash
DC=scripts/prod/compose.sh
$DC exec -T backend sh -c 'test -n "$OPENAI_API_KEY" && echo CHAVE=PRESENTE || echo CHAVE=AUSENTE'
$DC exec -T worker  sh -c 'test -n "$OPENAI_API_KEY" && echo CHAVE=PRESENTE || echo CHAVE=AUSENTE'
$DC exec -T backend sh -c 'echo OCR_ENABLED=$OCR_ENABLED REQUIRE_HTTPS=$REQUIRE_HTTPS LLM_REDACT_PII=$LLM_REDACT_PII'
```

Resultado esperado hoje: `CHAVE=AUSENTE` em ambos. As três últimas variáveis só existem **depois** que esta
versão corrigida for publicada (o compose atual da v1.0.2 não as repassa).

## 2. Pré-requisitos (bloqueadores de ativação) e situação

| # | Pré-requisito | Situação |
|---|---|---|
| 1 | `/analisar` não pode responder "concluída" quando os agentes falharam | **CORRIGIDO** (status `concluida`/`parcial`/`falha`; UI e histórico mostram) |
| 2 | Filtro RAG por `category` retornava 0 chunks | **CORRIGIDO** (`category` + `domains` gravados; chunks legados continuam elegíveis) |
| 3 | Busca de texto com a consulta padrão retornava 0 chunks | **CORRIGIDO** para consultas genéricas (OR + contingência posicional sinalizada) |
| 4 | Política de dados pessoais | **PARCIAL.** Minimização técnica implementada (CPF, RG, e-mail, telefone, dados bancários, partes de processo). **Nomes escritos dentro de documentos NÃO são removidos** (decisão do responsável, ver §3) |
| 5 | Registro de uso e preço de embeddings | **PARCIAL.** Estimativa de tokens e custo na telemetria/log (`custo_estimado_usd`); continua **sem linha em `llm_runs`/`llm_pricing`** (exigiria migration) |
| 6 | OCR | **PARCIAL.** Estados explícitos e limites (`OCR_MAX_PAGES`, timeout por página); ligar `OCR_ENABLED=true` e medir memória continua sendo decisão do operador |
| 7 | Teto de gasto | **PARCIAL.** `LLM_BUDGET_USD_MONTH` (chat) e `LLM_MAX_OUTPUT_TOKENS` disponíveis; **o limite no painel da OpenAI continua obrigatório** |
| 8 | Análise síncrona sem progresso | **PARCIAL.** A UI mostra "em processamento" mesmo após recarregar a página; a execução continua síncrona (limite do proxy: 300 s) |
| 9 | Criar o ADMIN real e remover a senha de bootstrap | **NÃO VALIDADO** (não executável sem a VPS) |
| 10 | HTTPS | **PARCIAL.** `REQUIRE_HTTPS=true` recusa a API em HTTP (426) e envia HSTS; **colocar HTTPS na frente é ação de infraestrutura, não feita** (§5) |

## 3. Privacidade: o que sai para a OpenAI

Fronteira única: o `LLMGateway` mascara o texto de **todo** chat e de **todo** embedding antes de chamar o provider
(`LLM_REDACT_PII=true` por padrão). Testado com um provider falso que captura o que seria enviado
(`tests/test_privacy_minimization.py`).

| Dado | Tratamento |
|---|---|
| CPF (com ou sem pontuação, rotulado), RG, e-mail, telefone, agência/conta | Substituído por `[CPF]`, `[RG]`, `[EMAIL]`, `[TELEFONE]`, `[DADO BANCÁRIO]` |
| Partes de processo (polo ativo/passivo) pessoa física | Enviadas como `[PARTE ATIVA]`/`[PARTE PASSIVA]`; empresas, bancos, condomínios e entes públicos permanecem |
| Mensagens de erro e logs | Passam por redação de segredos **e** de dados pessoais |
| Nomes de PF **conhecidos** (titular do cadastro, polos de processos, ocupantes) e nomes após rótulos jurídicos ("Proprietário:", "Executado:"…) | **Pseudonimizados** como `[TITULAR]`, `[PARTE PASSIVA 1]`, `[PROPRIETARIO 1]`… (reversível só localmente; a resposta do LLM é restaurada antes de gravar). Em chat, extração **e** embeddings |
| **Nomes soltos sem rótulo/cadastro**, referências parciais ("Sra. Ferreira Lima") | **NÃO removidos.** Exigiria NER; regex não é confiável. **Risco residual** |
| Endereço do imóvel, nº CNJ, CNPJ, nome de arquivo, observações livres | Enviados (necessários à análise ou só mascarados por regex) |
| Judicial API (DataJud) e Geocoding | Recebem CPF/CNPJ/nome/nº do processo e endereço **sem redação** (ação iniciada pelo usuário) |

Pseudonimização e regex **não são anonimização completa**. Antes de usar um documento real, o responsável precisa decidir, por escrito,
se aceita o risco residual (ou se usa cópias com nomes já tratados). Para o primeiro teste, use imóvel fictício
(ver `CHECKLIST-PRIMEIRO-IMOVEL.md`).

## 4. Procedimento de ativação (um passo por vez; pare ao primeiro erro)

Pré-condição: §2 revisado, **versão corrigida publicada por tag** (esta rodada ainda não foi publicada), backup
recente (`scripts/prod/pg-backup.sh`) e janela combinada.

**Passo 0 — Baseline (sem chave).** Registrar `GET /api/monitoring/rag` e `GET /api/monitoring/rag/pending`.

**Passo 1 — Configurar (ação do responsável, fora do repositório).** Em `/opt/radar-leilao/.env.prod` (modo 600):

```bash
# NUNCA cole a chave em chat, issue, commit ou log.
OPENAI_API_KEY=<chave de um projeto OpenAI exclusivo, com limite mensal baixo>
LLM_MAX_OUTPUT_TOKENS=1500          # teto de saída por chamada
LLM_BUDGET_USD_MONTH=5              # teto da aplicação (chat); o painel da OpenAI também deve ter limite
LLM_REDACT_PII=true
REQUIRE_HTTPS=true                  # só depois de o acesso por HTTPS estar funcionando (§5)
OCR_ENABLED=false                   # ligar apenas após testar um PDF escaneado e conferir memória
```

**Passo 2 — Recriar só o necessário.**

```bash
scripts/prod/compose.sh up -d --no-build backend worker
scripts/prod/compose.sh ps          # backend e worker "healthy"
```

**Passo 3 — Teste de conexão (1 embedding, custo desprezível).** Imprime só a dimensão:

```bash
scripts/prod/compose.sh exec -T backend python - <<'PY'
from app.ai.gateway import build_gateway
vec = build_gateway().embed(["teste de conexao"])[0]
print("OK dimensao=", len(vec))   # esperado: 1536
PY
```

Se a dimensão for diferente de 1536, **pare**: a coluna `vector(1536)` não aceitaria o vetor.

**Passo 4 — Embeddings de um documento fictício.** Enviar um documento **fictício** pelo celular. Na tela de
Documentos, a etapa "Embeddings" deve ficar "Concluída" e o selo "Indexado". Conferir também
`GET /api/monitoring/rag` e `GET /api/monitoring/rag/pending` (deve voltar a 0). Documentos já enviados sem chave
são retomados pelo worker (intervalo de 30 s) ou por `POST /api/monitoring/rag/reprocess` (admin).

**Passo 5 — Um agente por vez**, nesta ordem: `documental`, `juridico`, `checklist`, depois `financeiro` e
`mercado` (dependem de dados manuais): `POST /api/imoveis/{id}/analises/{analysis_id}/agents/{agente}`. Após cada
um, conferir `llm_runs` (status, modelo, tokens, latência, custo) e o gasto no painel da OpenAI.

**Passo 6 — Análise completa** com o imóvel fictício. Esperado: `status: "concluida"`, `ia_disponivel: true`,
`agentes_ok: 5`. Qualquer outra coisa (`parcial`, `falha`) deve ser investigada **antes** de seguir.

**Passo 7 — Só então o caso real**, com a decisão do §3 tomada por escrito.

### Automatizar a validação

`e2e/tests/ia-real.spec.ts` cobre os passos 4 a 6 e só roda com `RADAR_E2E_OPENAI=1` e
`RADAR_E2E_ALLOW_COST=SIM`. **Nunca foi executado** (sem chave autorizada). Teste com mock não vale como prova.

## 5. HTTPS: requisitos antes de documento real ou chave

Revisão (somente leitura, nada foi alterado na infraestrutura):

| Achado | Onde | Risco |
|---|---|---|
| Acesso de homologação por IP público em **HTTP**; senha, JWT (em `localStorage`) e documentos trafegam sem criptografia | `docs/04-operations/homologation-guide.md` §3.1 | Alto com dados reais |
| Cookie do portão `radar_gate` sem atributo `Secure` | `docker/nginx/templates/default.conf.template` | Cookie pode vazar em HTTP |
| O template de produção não envia HSTS (o `docker/nginx-proxy.conf` do modo B envia) | idem | Downgrade para HTTP |

Requisitos para considerar a produção apta a documentos reais (**ações do operador**):

1. Terminar TLS no proxy (modo B/Tailscale do guia de homologação, ou domínio com certificado válido).
2. Manter `proxy_set_header X-Forwarded-Proto $scheme` (já existe) — é o que o backend usa para decidir.
3. Ligar `REQUIRE_HTTPS=true`. A partir daí o backend responde **426** a qualquer chamada de API em HTTP (exceto
   `/health` e loopback) e envia `Strict-Transport-Security` em HTTPS. **Testado** (`tests/test_cost_controls_and_https.py`);
   a integração com o nginx real **não foi testada** (sem Docker local).
4. Adicionar `Secure` ao cookie `radar_gate` quando o acesso for só por HTTPS (mudança de template: exige deploy).

## 6. Controle de custos

1. **Projeto exclusivo** no painel da OpenAI, com **chave própria** e limite mensal baixo (hard limit) e alerta.
2. Comece com `gpt-4o-mini` (padrão). Não troque de modelo durante a homologação.
3. Estimativa: `custo ≈ tokens_entrada × preço_entrada + tokens_saída × preço_saída`. Preço semeado para
   `gpt-4o-mini`: US$ 0,15 / US$ 0,60 por 1 milhão de tokens. Embeddings: `EMBEDDING_PRICE_PER_1M_USD` (padrão
   0,02, **confirmar na página oficial de preços**) é usado só para **estimar** em log/telemetria.
4. Na aplicação: `LLM_BUDGET_USD_MONTH` (soma de `llm_runs` do mês; ao atingir, agentes devolvem
   `ORCAMENTO_EXCEDIDO` e não chamam a OpenAI), `LLM_MAX_OUTPUT_TOKENS`, rate limit (10 críticas/min, 2
   simultâneas), upload ≤ 30 MB. **Limitações:** o orçamento não conta embeddings (não ficam em `llm_runs`) e
   chamadas simultâneas podem ultrapassá-lo por uma análise.
5. Conferir o gasto real no painel da OpenAI após cada etapa e comparar com `llm_runs`.

### Controles adicionados na auditoria final

- `LLM_BUDGET_USD_PER_ANALYSIS`: teto de uma análise; agentes restantes ficam `ORCAMENTO_EXCEDIDO`. Defina **junto** com `LLM_BUDGET_USD_MONTH`.
- Orçamento **falha fechado**: modelo de chat sem linha em `llm_pricing` bloqueia (`sem_preco`). Hoje o seed só tem `openai/gpt-4o-mini`.
- Embeddings agora aparecem em `llm_runs` (`agent="embedding"`, tokens estimados, `EMBEDDING_PRICE_PER_1M_USD`).
- Monitoramento: `GET /api/monitoring/rag` → `orcamento_llm`.
- Não contabilizado: retries internos do SDK (`LLM_MAX_RETRIES`), diferença da estimativa de embeddings. Conferir sempre o painel da OpenAI.
- HTTPS, cookie `Secure`, OCR (Tesseract), health checks e logs: `docs/04-operations/https-ocr-monitoramento.md` (ação do operador; nada foi alterado na VPS).

## 7. Critérios de aceite depois da ativação

| Critério | Como medir | Aceite |
|---|---|---|
| Embeddings persistidos | tela Documentos / `/api/monitoring/rag` | todos os trechos com embedding; selo "Indexado" |
| Sem pendências | `/api/monitoring/rag/pending` | `pendentes = 0` em até 2 ciclos do worker |
| Chamadas registradas | `llm_runs` da análise | 1 linha por agente, com tokens e latência |
| Custo coerente | `llm_runs.total_cost` × painel OpenAI | diferença pequena e explicável |
| Falha visível | forçar erro em ambiente de teste (chave inválida) | UI mostra "Análise sem resultado da IA" / "parcial" |
| Sem vazamento | logs do backend/worker e prompt capturado em teste | nenhuma chave, CPF, e-mail ou telefone |
| Latência | tempo do `/analisar` | abaixo de 300 s |

## 8. Rollback (reversível, sem perda de dados)

1. Esvaziar `OPENAI_API_KEY` no `.env.prod` (e `OCR_ENABLED=false`, se mudou).
2. `scripts/prod/compose.sh up -d --no-build backend worker`.
3. Estado resultante: volta a `SEM_CHAVE`; embeddings já gravados permanecem; versões sem vetor voltam a aguardar.
4. **Revogar a chave no painel da OpenAI** se houver suspeita de exposição.
5. Nenhuma migration é necessária para ligar/desligar.

## 9. O que este plano **não** faz

- Não cria nem sugere valor de chave. Não altera `.env.prod`, secrets do GitHub ou regras de acesso.
- Não executa deploy nem cria release. A v1.0.2 permanece como baseline.
- Não importa documentos reais.
