# Segurança

Estado da segurança da aplicação. Auditoria original de exposição (histórica):
[specs/SECURITY-EXPOSURE-AUDIT.md](specs/SECURITY-EXPOSURE-AUDIT.md). Infraestrutura:
[../04-operations/infrastructure.md](../04-operations/infrastructure.md#12-segurança-e-limitações).

> **Hardening pré-OpenAI (branch `feature/security-hardening-openai`).** As seções 1 a 9 descrevem o
> comportamento implementado nesta branch. **Ele só vale em produção depois do próximo deploy por tag**; até lá a
> produção continua com o comportamento anterior (rotas legadas atrás do portão do proxy). Seção 11 traz o plano de
> implantação e rollback.

## 1. Modelo de autenticação

- **Login** por e-mail e senha (`POST /api/auth/login`, bcrypt) emite um **JWT HS256** (expira em 480 min). `JWT_SECRET_KEY` é obrigatório; sem ele nenhum token é aceito (falha-fechada).
- **Portão global** `security_gate` (`backend/app/security.py`), registrado como dependência do `FastAPI(...)`: **todas** as rotas passam por ele. É *default-deny*: uma rota nova nasce protegida sem precisar declarar nada.
- Credencial aceita: `Authorization: Bearer <jwt>` de usuário **ativo** (preferencial) ou, apenas se configurado, o `X-Admin-Token` de compatibilidade (em desativação, ver [operations.md](../04-operations/operations.md#3-desativação-controlada-do-x-admin-token-legado); não configurado na produção atual). Token inválido, expirado, assinado com outro segredo ou de usuário desativado resulta em 401.
- O **cookie do portão do proxy** (`radar_gate`) continua sendo uma barreira adicional de borda, mas **deixou de ser a única autorização**: o backend valida sessão e permissão por conta própria.
- O frontend injeta o `Bearer` em toda chamada `/api` (`services/session.ts`), trata 401 (limpa a sessão e volta ao login), 403 (aviso de falta de permissão, sem deslogar) e 429 (aviso de limite). A autorização real é sempre do backend; o frontend não duplica a regra.

## 2. Perfis e permissões (RBAC)

| Papel | Permissões |
|---|---|
| ADMIN | todas: `admin:write`, `admin:parameters`, `debt:query`, `user:manage`, `analysis:write`, `read` |
| ANALISTA | `analysis:write`, `debt:query`, `read` |
| OPERADOR | `analysis:write`, `admin:parameters`, `debt:query`, `read` |
| CONSULTA | `read` |

Regra do portão (primeira que casar):

| Operação | Permissão exigida |
|---|---|
| Leitura (`GET`/`HEAD`/`OPTIONS`) | `read` (qualquer papel autenticado) |
| Busca da biblioteca jurídica (`GET .../biblioteca/busca`) | `read` + rate limit do bucket `search` |
| Escrita (`POST`/`PUT`/`PATCH`/`DELETE`) | `analysis:write` |
| Operações críticas e uploads (seção 4) | `analysis:write` + limites |
| Regras do Checklist Mestre (criar, editar, ativar, desativar) | `admin:write` |
| Excluir leiloeiro; criar/editar/excluir portal; **recuperar credencial de portal** | `admin:write` (a recuperação ainda exige `X-Portal-Admin-Token`) |
| `/api/admin/*`, `/api/auth/usuarios`, oportunidades | o portão exige autenticação; a permissão específica continua nas dependências da própria rota (`require_permission`, `authorized_writer`) |

As dependências por rota existentes foram **mantidas** como camada adicional (não há segunda arquitetura de autenticação).

## 3. Rotas públicas

Somente duas, definidas em `security.PUBLIC_ROUTES`:

- `GET /health`
- `POST /api/auth/login` (protegido por rate limit no proxy: 10 requisições por minuto)

Um teste (`test_inventario_de_rotas_somente_as_publicas_previstas_sao_abertas`) falha se qualquer outra rota ficar pública, e outro (`test_toda_regra_de_politica_aponta_para_uma_rota_real`) falha se uma regra de política deixar de casar com uma rota real (por exemplo, após renomear uma rota crítica). `/docs`, `/redoc` e `/openapi.json` não são rotas da API e continuam ocultos pelo proxy (404).

## 4. Operações críticas e proteção contra consumo indevido

Classificadas como **críticas** (potencial de chamada LLM, embeddings ou serviço externo):

`POST /api/imoveis/{id}/analisar`, `POST /api/imoveis/{id}/analises/{aid}/agents/*` (5 agentes), `POST /api/imoveis/{id}/documentos/{vid}/extrair`, `POST /api/imoveis/{id}/eventos/{eid}/reanalisar`, `POST /api/monitoring/rag/reprocess`, `POST /api/imoveis/{id}/processos/consultar` (DataJud), `POST /api/imoveis/{id}/debitos/consultar`, `POST /api/imoveis/{id}/localizacao/geocodificar`.

Uploads (`POST /api/imoveis/{id}/documentos`, `POST /api/documentos/{id}/versoes`) têm bucket próprio, pois processam e indexam o arquivo.

A **busca da biblioteca jurídica** (`GET /api/juridico/biblioteca/busca`) gera o embedding da consulta na OpenAI quando há chave. Ela continua exigindo só `read` (o papel CONSULTA pode pesquisar), mas passa pelo mesmo mecanismo de rate limit, em bucket próprio (`search`). O limite é aplicado no portão, **antes** do endpoint e, portanto, antes de qualquer chamada ao provider; acima do limite a resposta é 429 e nenhum embedding é gerado.

Controles (em `security.py`, `locks.py` e `config.py`):

| Controle | Valor padrão | Justificativa |
|---|---|---|
| Rate limit de operações críticas, por usuário | 10 por minuto (`RATE_LIMIT_CRITICAL_PER_MINUTE`) | Uma análise completa é 1 requisição; usar os 5 agentes um a um são 5; 10/min cobre o uso humano normal e barra automação/loop. |
| Rate limit de uploads, por usuário | 30 por minuto (`RATE_LIMIT_UPLOAD_PER_MINUTE`) | Envio de um lote de documentos de um imóvel sem atrito. |
| Rate limit da busca jurídica (embedding), por usuário | 30 por minuto (`RATE_LIMIT_SEARCH_PER_MINUTE`) | Pesquisa interativa sem atrito (digitação e refinamento), mas sem permitir laço automático contra o provider. Bucket separado para não consumir a cota das análises. |
| Operações críticas simultâneas, por usuário | 2 (`MAX_CONCURRENT_CRITICAL_PER_USER`) | Cliques repetidos e abas paralelas não multiplicam chamadas pagas. |
| Lock por imóvel em análise/reanálise | `409` se já há análise em andamento | Evita análises duplicadas e custo duplicado entre processos (ver seção 8). |
| Lock por (imóvel, análise, agente), por documento (extração) e por imóvel (consulta judicial) | `409` | Idem. |
| Domínios de análise validados | só `documental`, `juridico`, `financeiro`, `mercado`, `checklist`; no máximo 5; `query` até 500 caracteres | Impede disparar chamadas por nomes inesperados e limita o tamanho do que vai ao provider. |

Os contadores de rate limit e concorrência são **em memória, por processo**: com 2 workers do uvicorn, o limite efetivo é até 2x. A proteção entre processos contra duplicidade é feita por locks do PostgreSQL. Não existe sistema de saldo, créditos ou cobrança interno; o teto financeiro real é o limite configurado no painel da OpenAI.

Resposta 429 inclui `Retry-After`.

### Contrato de `POST /api/imoveis/{id}/analisar`

Corpo **opcional** (`AnalyzeRequest`). `{}` ou ausente = análise completa, que é o que o frontend envia hoje. Restrições (também descritas no OpenAPI, em `components.schemas.AnalyzeRequest` e nas respostas da operação):

| Campo | Regra | Violação |
|---|---|---|
| `domains` | lista de, no máximo, **5** itens; cada item deve ser um de `documental`, `juridico`, `financeiro`, `mercado`, `checklist`; duplicatas são ignoradas; vazio ou ausente = todos | **422** (mais de 5 itens, tipo errado ou domínio desconhecido) |
| `query` | texto de até **500** caracteres | **422** |

A resposta 422 não repete o valor enviado. Exemplos:

```json
{}
{"domains": ["juridico", "mercado"]}
{"domains": ["checklist"], "query": "riscos de ocupação e dívidas condominiais"}
```

Outras respostas documentadas: 401 (sem login), 403 (sem `analysis:write`), 404 (imóvel inexistente), 409 (análise já em andamento) e 429 (limite de operações críticas). Clientes que enviavam outros nomes de domínio ou textos longos passam a receber 422; o frontend atual não é afetado.

## 5. Uploads e documentos

`backend/app/upload_security.py`, aplicado antes de qualquer gravação:

- leitura em partes com teto de tamanho (`UPLOAD_MAX_MB`, padrão 30 MB, abaixo dos 50 MB do nginx) → **413**;
- arquivo vazio → **400**;
- nome seguro: remove diretórios (inclusive `..\` do Windows), caracteres de controle e símbolos fora de `[\w.-() ]`, limita a 150 caracteres e exige extensão permitida (`.pdf .doc .docx .xls .xlsx .csv .txt .md .png .jpg .jpeg`) → 400;
- MIME declarado coerente com a extensão (ou genérico) → **415**;
- **assinatura real do conteúdo**: PDF começa com `%PDF-`, PNG e JPEG pelos bytes mágicos, DOC/XLS pelo cabeçalho OLE, DOCX/XLSX como ZIP com a estrutura OOXML esperada e teto de descompressão de 300 MB (zip bomb), texto sem bytes nulos → 400;
- mensagens fixas, sem eco do conteúdo; rejeições ocorrem antes de criar versão, chunks ou arquivo (nada persiste).

O armazenamento não mudou: o caminho é composto por `property-{id}/original/v{versão}-{nome seguro}`, com número de versão (sem sobrescrita). O download exige autenticação, serve apenas arquivos **dentro** da raiz do storage e envia `X-Content-Type-Options: nosniff`.

**Isolamento entre usuários:** o produto é de organização única; imóveis e documentos **não têm dono por usuário**. Qualquer usuário autenticado com a permissão adequada acessa os dados da instalação. Isolamento por usuário não existe e não foi simulado; seria uma mudança de modelo de dados.

## 6. Tratamento de erros e segredos

- Erros inesperados devolvem **500** com mensagem genérica e `ref` (código de correlação); o stack trace e os detalhes ficam só no log interno, já sanitizados.
- Falhas de provider, orquestração, upload, consulta judicial e geocodificação devolvem mensagem amigável + `ref` (`public_error` em `request_context.py`); a mensagem bruta da biblioteca **não** vai ao frontend.
- 422 de validação não repete o valor enviado (evita devolver senhas ou trechos de documentos).
- Todo request recebe `X-Request-ID` (aceita o do cliente se válido, senão gera); o id aparece nos logs (`[<id>]`) e nas respostas de erro.
- `backend/app/redaction.py` remove de mensagens e logs: chaves `sk-...`, `Bearer`/`Authorization`, pares `api_key=`/`password=`/`token=`, connection strings (`postgresql://...`), JWTs e valores de `X-Admin-Token`. Um filtro de logging (`SecretRedactingFilter`) aplica isso a **todas** as mensagens e tracebacks, inclusive de bibliotecas de terceiros.
- A chave OpenAI nunca é retornada por endpoint algum (os de monitoramento expõem apenas `provider_disponivel`).

## 7. Integração OpenAI

Configuração em `backend/app/config.py` e repassada ao backend e ao worker em `docker-compose.prod.yml`:

| Variável | Padrão | Observação |
|---|---|---|
| `OPENAI_API_KEY` | vazia | sem chave nenhuma chamada é feita; agentes respondem `SEM_CHAVE`, embeddings ficam pendentes |
| `LLM_PROVIDER` / `LLM_MODEL` | `openai` / `gpt-4o-mini` | antes não eram repassados ao container |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 1536 dimensões |
| `LLM_TIMEOUT_SECONDS` | 90 | por chamada; o padrão da biblioteca seria ~600 s |
| `LLM_MAX_RETRIES` | 1 | pior caso de uma chamada: (1 + retries) x timeout = 180 s, abaixo do `proxy_read_timeout` (300 s) |
| `LLM_MAX_OUTPUT_TOKENS` | sem limite | opcional; não é repassada pelo compose (valor vazio quebraria a leitura) |
| `WORKER_MAX_ATTEMPTS` | 5 | agora repassada ao worker; inclui tentativas interrompidas por crash |
| `WORKER_LEASE_SECONDS` | 600 | só o worker; prazo após o qual uma tentativa sem conclusão é tratada como interrompida. Dimensionamento abaixo |
| `RATE_LIMIT_SEARCH_PER_MINUTE` | 30 | só o backend; limite da busca jurídica (ver seção 4) |

**Dimensionamento do lease.** O lease não é o mutex (quem impede a execução simultânea é o lock de linha); ele só define em quanto tempo uma tentativa sem conclusão passa a contar como interrompida. Regra:

```
WORKER_LEASE_SECONDS >= lotes x ((1 + LLM_MAX_RETRIES) x LLM_TIMEOUT_SECONDS + 10) + 60
lotes = ceil(chunks da versão / 1000)      # o cliente de embeddings envia até 1000 textos por chamada
```

Com os padrões (timeout 90 s, 1 retry) cada lote custa até ~190 s no pior caso: 600 s cobre 2 lotes lentos (~2000 chunks) e 900 s cobre 4. Um erro em qualquer lote aborta a versão, então o pior caso longo só ocorre com a API lenta mas respondendo. Valor acima do necessário só atrasa a recuperação de um crash; valor abaixo apenas faz a versão aparecer como elegível enquanto um worker vivo a processa (o lock de linha impede duplicidade e a recuperação a ignora). O default de 600 s foi mantido; `chunk_size` do cliente de embeddings não foi alterado.

Falhas do provider são classificadas (`AUTENTICACAO`, `RATE_LIMIT`, `TIMEOUT`, `CONEXAO`, `REQUISICAO_INVALIDA`, `PROVEDOR`, `DESCONHECIDO`) em `LLMCall.error_category`, registradas em log e sanitizadas. No worker, erros **transitórios** (credencial, rate limit, timeout, rede, provedor) não consomem as 5 tentativas (`WORKER_MAX_ATTEMPTS`) e aplicam backoff exponencial (60 s até 15 min); o motivo fica em `extraction_metadata.embedding_last_error`. Se o **processo morrer** no meio de uma versão, a tentativa já foi gravada antes do trabalho (ver seção 8): ela conta, recebe o mesmo backoff e, ao atingir o limite, a versão sai da fila com status `ERRO`. Prompts e regras de análise **não** foram alterados. Embeddings continuam fora de `llm_runs` (pendência P2).

## 8. Concorrência e duplicidade

| Risco | Tratamento |
|---|---|
| Duas análises/reanálises do mesmo imóvel ao mesmo tempo | advisory lock de transação `analise:{imóvel}` → 2ª requisição recebe **409** |
| Mesma versão de análise calculada duas vezes | índice único `uq_analysis_property_opp_version` em `(property_id, COALESCE(opportunity_id,0), version)` (migration **0024**); a migration aborta, sem apagar nada, se existirem duplicatas ou se houver, no schema de `analyses`, um índice homônimo diferente do esperado |
| Dois cliques no mesmo agente / extração / consulta judicial | locks `agente-*`, `extrair`, `consulta-judicial` → 409 |
| Worker e reprocesso processando a mesma versão (embeddings e custo duplicados) | `SELECT ... FOR UPDATE SKIP LOCKED` na versão; quem encontra a linha travada a ignora |
| Duas varreduras manuais simultâneas | lock de sessão numa conexão dedicada; a segunda sai sem fazer nada |
| Perda de vetores já gerados se o lote falhar | `run_once` faz commit por versão |
| Seed do checklist concorrente (HTTP 500 por violação de unicidade) | `INSERT ... ON CONFLICT DO NOTHING` |
| Seed da Central Jurídica concorrente (primeira leitura; HTTP 500 por violação de unicidade) | catálogo completo => caminho rápido sem escrita nem lock; incompleto => `pg_advisory_xact_lock` bloqueante serializa os seeders e quem espera reavalia e não cria nada. Só cria o que falta, nunca altera dados existentes, nunca gera embedding (`embed=False`) |
| Worker morre no meio da versão (rollback desfazia o contador; reprocesso infinito) | a tentativa e um lease (`embedding_lease_until`) são gravados com **commit antes** de chamar o provider; lease vencido e linha livre => `INTERROMPIDO` (motivo em `embedding_last_error`, `embedding_interruptions`, backoff 60 s a 15 min); ao atingir `WORKER_MAX_ATTEMPTS` => status `ERRO`, fora da fila. Chunks e vetores permanecem; nada é marcado como indexado |
| Outro executor segura a linha entre a gravação da tentativa e o início do processamento (tentativa gasta sem processar) | o lease guarda o dono (`embedding_lease_owner`); a etapa 2 re-adquire o lock de forma **bloqueante com `lock_timeout` (5 s)** e reavalia o lease. Lock não obtido: a tentativa é devolvida, mas só se o lease ainda for desta execução (se nem a devolução obtiver o lock, o lease vence e a tentativa conta uma única vez como interrompida). Lease de outra execução: nada é alterado. Nada a processar: a tentativa não é consumida |

**Seeds executados por GET.** `GET /api/checklist` e os GETs da Central Jurídica inicializam seus dados na primeira leitura. Avaliada a separação "inicialização x leitura" (migration, comando de seed ou seed no startup): ela mudaria o fluxo de implantação e os testes que dependem da inicialização preguiçosa, sem ganho de segurança depois que o seed passou a ser idempotente e serializado. Decisão: manter a inicialização preguiçosa, agora segura sob concorrência; o caminho comum (catálogo completo) não escreve nada.

Os locks são de transação e liberados no commit/rollback; não há lock "esquecido".

## 9. Lacunas e riscos que permanecem

1. **HTTP sem TLS**: senha, JWT e cookie do portão em texto claro. Não enviar matrícula real (nomes, CPF) até haver domínio e TLS.
2. **JWT em `localStorage`** (exposto a XSS).
3. **Produto de organização única**: sem isolamento de dados entre usuários.
4. **Dados vão à OpenAI**: trechos de documentos (contexto RAG) e embeddings são enviados ao provider quando a chave é configurada; não há anonimização automática.
5. **Rate limit em memória por processo** (limite efetivo = limite x workers) e reiniciado a cada restart.
6. **`X-Admin-Token` legado** ainda aceito se configurado (não está na produção atual).
7. `/docs` e `/openapi.json` existem no app; só o proxy os esconde.
8. Sem criptografia em repouso para arquivos e chunks.
9. Embeddings sem registro de custo (`llm_runs` cobre só chat) e sem preço cadastrado para o modelo de embedding.
10. Verificação de arquivo é por assinatura e estrutura, **não** há varredura antivírus.

## 10. Práticas obrigatórias

- Nunca versionar `.env`, chaves, tokens, `GATE_KEY` nem senhas; este repositório é público.
- Segredos da aplicação vivem só na VPS (`.env.prod`, modo 600) e no GitHub (Secrets).
- Ao documentar, use `<VPS_HOST>` no lugar do IP e não cole saída de comandos com segredos.
- Rotas novas: não é preciso declarar autenticação (default-deny). Se a rota for crítica (LLM, externo), adicione-a às regras de `security.py` e um lock de operação; o teste de inventário apontará omissões de regras.

## 11. Homologação, implantação e rollback

**Antes de ativar a OpenAI em produção**

1. Deploy por tag da versão com este hardening (CI verde). A migration `0024` roda no deploy (o `deploy.sh` faz backup antes); em produção o banco está vazio de análises, então não há duplicatas.
2. Confirmar login e navegação com um usuário real; verificar que uma chamada sem login recebe 401.
3. Só então configurar a chave exclusiva da OpenAI (com teto de gasto no painel) e recriar `backend` e `worker`.
4. Homologar com um imóvel (edital público e matrícula anonimizada), conferindo em `llm_runs` status, tokens, custo e latência, e nos logs o `ref` das respostas de erro.

**Rollback**

- Código: `scripts/prod/rollback.sh` volta à versão anterior **somente se o schema não mudou**; a migration `0024` altera o schema, portanto o rollback de imagem exige antes o downgrade para `0023_usuarios` (remove só o índice único; reversível e sem perda de dados). A ordem completa e o comando exato (downgrade, confirmar `alembic_version`, `rollback.sh`, `post-deploy-check.sh`, esvaziar `OPENAI_API_KEY`) estão em [deployment.md §8](../04-operations/deployment.md#8-release-com-a-migration-0024-hardening-de-segurança). Alternativa preferida: corrigir à frente com nova tag.
- Chave OpenAI: esvaziar `OPENAI_API_KEY` no `.env.prod`, recriar `backend`/`worker` (volta a `SEM_CHAVE`) e revogar a chave no painel.
- **Evidência:** o downgrade da migration foi validado em banco descartável; o procedimento em containers **ainda não foi executado na VPS** (nem em Docker local).
