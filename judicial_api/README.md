# Judicial API

Módulo **independente** de pesquisa processual judicial nacional (fonte inicial: DataJud/CNJ).
Não depende do Radar Leilão; será consumido por ele futuramente via uma única API REST.

> Estado atual: **módulo consumível em produção-local**. Contrato REST unificado,
> OpenAPI/Swagger, autenticação por API key, autorização por escopo, rate limiting,
> métricas, auditoria e hardening (JUR-01..05); **persistência PostgreSQL durável**,
> **transporte real do DataJud** e **integração HTTP com o Radar Leilão** (Task Final).
> A SPEC completa está em `docs/JUDICIAL-API-SPEC.md`; a ordem de execução em
> `docs/JUDICIAL-IMPLEMENTATION-TASKS.md`.

## Persistência PostgreSQL (Task Final)

O store padrão é **PostgreSQL durável** (`PostgresSearchStore`), reutilizando o MESMO
banco do Radar (schema `public`, tabelas prefixadas `judicial_`). Não é uma segunda
infraestrutura: a URL vem de `DATABASE_URL`/`JUDICIAL_DATABASE_URL`.

- Tabelas: `judicial_searches`, `judicial_search_sources`, `judicial_processes`,
  `judicial_process_parties`, `judicial_process_subjects`, `judicial_process_movements`,
  `judicial_signals`, `judicial_search_events` (migration Alembic `0011`, reversível,
  na mesma cadeia do Radar).
- **Durabilidade**: os resultados sobrevivem ao reinício e são compartilhados por
  múltiplas instâncias (mesmo banco).
- **Idempotência no retry**: `save` faz UPSERT do agregado por `search_id` e substitui
  os filhos pelo estado atual; constraints únicas (`search_id`; `search+tribunal`;
  `search+tribunal+numeroProcesso`) impedem duplicação mesmo sob concorrência.
- O armazenamento em memória (`InMemorySearchStore`) permanece **apenas** para
  testes/execução efêmera explícita (`JUDICIAL_PERSISTENCE_BACKEND=memory`) — nunca é
  fallback silencioso.

## Consulta real ao DataJud (Task Final)

- Transporte HTTP real (`HttpxTransport`) é injetado no `DataJudProvider` quando há
  credencial (`JUDICIAL_DATAJUD_API_KEY`) e `JUDICIAL_DATAJUD_REAL_TRANSPORT=true`
  (padrão). Sem credencial, a consulta real falha de forma controlada
  (`CONFIGURATION_ERROR`) — a API sobe normalmente e a suíte roda sem rede.
- Autenticação via header oficial `Authorization: APIKey <chave>`. A chave é pública e
  pode mudar pelo CNJ: fica em configuração, nunca em código.
- **Produção falha fechada**: fora de `local`/`test`, `create_app` exige
  `JUDICIAL_API_KEYS` (auth do consumidor) e, se o transporte real estiver habilitado,
  `JUDICIAL_DATAJUD_API_KEY`. Faltando, a aplicação não sobe.
- Capabilities reais são preservadas: o DataJud é pesquisável por `numeroProcesso`,
  `classe.codigo`, `assuntos.codigo`, `orgaoJulgador.codigo` e `grau`. Nome/CPF/CNPJ
  **não** são pesquisáveis diretamente na API pública — critérios não suportados
  resultam em `UNSUPPORTED_SEARCH_CRITERIA` (nunca simulados).

## Contrato REST (JUR-05)

Todos os endpoints de negócio ficam sob `/api/v1/judicial`. O consumidor nunca
conhece URLs do DataJud nem endpoints de tribunais individuais.

| Método | Rota | Escopo | Descrição |
|---|---|---|---|
| `GET` | `/health` | — (público) | Saúde do serviço |
| `GET` | `/metrics` | — (público) | Métricas agregadas (SPEC §72) |
| `POST` | `/api/v1/judicial/search` | `search` | Cria e executa uma pesquisa multi-fonte |
| `GET` | `/api/v1/judicial/search/{search_id}` | `read` | Recupera o resultado de uma pesquisa |
| `GET` | `/api/v1/judicial/search/{search_id}/sources` | `read` | Resultado individual por fonte |
| `POST` | `/api/v1/judicial/search/{search_id}/retry` | `search` | Reprocessa fontes com falha recuperável |
| `GET` | `/api/v1/judicial/tribunals` | `read` | Catálogo de tribunais habilitados |
| `GET` | `/api/v1/judicial/capabilities` | `read` | Capacidades de pesquisa por tribunal |
| `GET` | `/api/v1/judicial/providers/status` | `read` | Saúde dos providers |

OpenAPI/Swagger em `/docs` e `/openapi.json` (esquema de segurança `ApiKeyAuth`).

## Segurança (JUR-05, SPEC §73)

- **Autenticação por API key** do consumidor no header `X-API-Key` (configurável).
  As chaves vêm de `JUDICIAL_API_KEYS` (ambiente/secret), **nunca versionadas**.
  Sem chaves configuradas, a auth fica desligada (modo local/dev); com chaves, é
  obrigatória. A credencial do DataJud é assunto separado.
- **Autorização por escopo**: `search` (disparar/reprocessar) e `read` (consultar).
  Chave sem escopo declarado tem acesso total.
- **Rate limiting** por consumidor (janela deslizante em memória), com resposta
  `429 RATE_LIMITED` e header `Retry-After`.
- **Hardening**: limite de tamanho de payload (`413`), headers de segurança
  (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control`),
  CORS opcional.
- **Mascaramento**: CPF/CNPJ nunca são registrados por inteiro em log/auditoria.

## Observabilidade (JUR-05, SPEC §69, §71-72)

- **Auditoria HTTP**: cada requisição gera uma linha estruturada (método, rota,
  status, duração, principal, correlation id) — sem dados sensíveis. Complementa a
  auditoria de domínio por pesquisa (`SearchEvent`).
- **Métricas** (`GET /metrics`): `searches_total/completed/empty/partial/failed`,
  `provider_errors/timeouts`, `processes_found`, `signals_found`, `retries_total`,
  `unsupported_queries` e latência média por provider.

## O que já existe (JUR-01)

- Estrutura do módulo (`judicial_api/`), isolada do Radar.
- Configuração externa via ambiente (prefixo `JUDICIAL_`), sem segredo hardcoded.
- Aplicação REST (FastAPI) com `GET /health`.
- Contrato de erro unificado e handlers globais (sem vazar stack trace/segredos).
- Correlation ID por requisição (header `X-Correlation-ID`), propagado nos logs e na resposta.
- Logging estruturado (JSON de uma linha) com correlation id.
- Interfaces base de `JudicialProvider` e de `TribunalRegistry` / `ProviderRegistry`.
- DTOs/enums do contrato (request, resultado, processo, fonte, status, ramos, erros).

## Orquestração (JUR-03)

- `SearchOrchestrator`: pesquisa multi-fonte com execução `PARALLEL` ou `SEQUENTIAL`.
- **Timeout efetivo**: cada fonte tem orçamento (timeout por fonte ∧ prazo global
  restante). Uma fonte bloqueada não trava a orquestração — o pool é desligado sem
  esperar a thread travada (`shutdown(wait=False, cancel_futures=True)`); do lado da
  fonte, o timeout do transporte HTTP do provider encerra a chamada. Alinhe
  `JUDICIAL_DEFAULT_SOURCE_TIMEOUT_MS` (provider) ao `source_timeout_ms` do
  orchestrator.
- **Retry seletivo**: reexecuta apenas erros transitórios; respeita
  `retryable=False` explícito (um erro marcado como não recuperável nunca é
  reexecutado nem entra na reanálise). Retry é resiliência a erro — distinto do
  controle de taxa abaixo.
- **Rate limiting / concorrência** (SPEC §13): `max_global_concurrency`,
  `max_provider_concurrency` e `max_tribunal_concurrency` (padrões 20/20/1) limitam
  o paralelismo real de consultas às fontes. É controle de taxa, não retry de 429.
- **execution_mode**: `PARALLEL` e `SEQUENTIAL` implementados; qualquer outro valor
  é **rejeitado explicitamente** com `BAD_REQUEST` (não é ignorado em silêncio).
- **Idempotência operacional**: pesquisas idênticas (mesmo `request_hash`) que
  chegam **concorrentemente** são coalescidas — a segunda aguarda e recebe o mesmo
  `search_id`/resultado, evitando execução duplicada. Pesquisas idênticas em
  **momentos diferentes NÃO** são deduplicadas (os dados das fontes podem ter
  mudado): reexecutam e geram novo `search_id`.
- **Status agregado**: `COMPLETED` / `EMPTY` / `PARTIAL` / `FAILED` (EMPTY ≠ PARTIAL).
- **Reanálise**: `retry_failed` reprocessa somente fontes com falha recuperável.
- **Persistência/auditoria**: store em memória com eventos (`SEARCH_CREATED`,
  `SOURCE_*`, `SIGNAL_ANALYSIS_COMPLETED`, `SEARCH_COMPLETED`, `REANALYSIS_REQUESTED`).
  A persistência em PostgreSQL fica para uma fase posterior.

## Sinais jurídicos (JUR-04)

- `SignalEngine` detecta **evidências** processuais (não parecer nem decisão) a
  partir de movimentos, assuntos e classe dos processos normalizados.
- Regras **versionadas** em dados (`judicial_api/signals/signal_rules.json`):
  penhora, arresto, indisponibilidade, hipoteca, execução, execução fiscal,
  cobrança, falência, recuperação judicial, insolvência, embargos, usucapião,
  desapropriação, alienação fiduciária, inventário, partilha, ação trabalhista.
  Cada sinal tem `signal_code`, `category`, `severity`, `confidence`,
  `evidence_text`, `evidence_type` e `rule_version`.
- **Distinção processo × imóvel** (SPEC §35, §39): uma evidência patrimonial (ex.:
  penhora) gera também um sinal `PROPERTY_<X>_EVIDENCE` que deixa explícito que a
  confirmação de que a medida recai sobre determinado imóvel exige validação
  registral/documental — **nunca** afirma "imóvel penhorado".
- **Homônimos**: quando a pesquisa é por nome sem CPF/CNPJ e as partes não trazem
  documento que confirme identidade, emite `HOMONYM_POSSIBLE`.
- Os sinais são anexados ao `SearchResult.signals` pelo orquestrador e persistidos
  no store. A correlação com o imóvel e o risco jurídico são responsabilidade do
  módulo Jurídico do Radar (fora do escopo deste módulo).

## Requisitos

- Python 3.12
- Dependências já presentes no `backend/requirements.txt` (FastAPI, pydantic-settings, uvicorn, pytest).

## Executar localmente

Na raiz do repositório:

```bash
uvicorn judicial_api.app:app --reload --port 8010
```

Verificar o health check:

```bash
curl -s http://localhost:8010/health
# {"status":"UP","service":"judicial-api","version":"0.1.0"}
```

O correlation id é devolvido no header `X-Correlation-ID`. Se o cliente enviar esse
header, ele é reutilizado; caso contrário, um UUID novo é gerado por requisição.

Verificar o health check:

```bash
curl -s http://localhost:8010/health
# {"status":"UP","service":"judicial-api","version":"0.1.0"}
```

Exemplo de pesquisa (com auth ligada, envie o header da API key):

```bash
curl -s -X POST http://localhost:8010/api/v1/judicial/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: minha-chave" \
  -d '{"cpf": "12345678900", "uf": "PR"}'
```

## Configuração

Variáveis de ambiente (prefixo `JUDICIAL_`), todas com padrão seguro:

| Variável | Padrão | Descrição |
|---|---|---|
| `JUDICIAL_LOG_LEVEL` | `INFO` | Nível de log estruturado |
| `JUDICIAL_CORRELATION_ID_HEADER` | `X-Correlation-ID` | Header do correlation id |
| `JUDICIAL_DEFAULT_SOURCE_TIMEOUT_MS` | `8000` | Timeout base por fonte |
| `JUDICIAL_GLOBAL_TIMEOUT_MS` | `60000` | Timeout global |
| `JUDICIAL_DATAJUD_API_KEY` | *(vazio)* | Credencial do DataJud — **nunca versionar** |
| `JUDICIAL_API_KEYS` | *(vazio)* | Chaves do consumidor: `chave` ou `chave:search\|read`, separadas por vírgula. **Nunca versionar** |
| `JUDICIAL_API_KEY_HEADER` | `X-API-Key` | Header de autenticação do consumidor |
| `JUDICIAL_REQUIRE_AUTH` | `false` | Exige auth mesmo sem chaves configuradas (falha fechada) |
| `JUDICIAL_RATE_LIMIT_ENABLED` | `true` | Liga/desliga o rate limiting HTTP |
| `JUDICIAL_RATE_LIMIT_REQUESTS` | `120` | Máx. de requisições por janela, por consumidor |
| `JUDICIAL_RATE_LIMIT_WINDOW_SECONDS` | `60` | Tamanho da janela do rate limit |
| `JUDICIAL_MAX_REQUEST_BYTES` | `1048576` | Tamanho máximo do corpo (0 desabilita) |
| `JUDICIAL_CORS_ALLOW_ORIGINS` | *(vazio)* | Origens CORS permitidas (separadas por vírgula) |
| `JUDICIAL_ENVIRONMENT` | `local` | `local`/`test` = auth opcional; qualquer outro = produção (auth obrigatória, falha fechada) |
| `JUDICIAL_PERSISTENCE_BACKEND` | `postgres` | `postgres` (padrão durável) ou `memory` (só testes/efêmero explícito) |
| `DATABASE_URL` / `JUDICIAL_DATABASE_URL` | *(banco local)* | URL do PostgreSQL compartilhado com o Radar. **Nunca versionar credencial real** |
| `JUDICIAL_DATAJUD_REAL_TRANSPORT` | `true` | Injeta o transporte HTTP real no DataJudProvider quando há credencial |

Nenhum segredo é necessário para subir a aplicação em modo local ou rodar a suíte
padrão de testes. **Em produção**, `JUDICIAL_API_KEYS` é obrigatório e, com transporte
real habilitado, `JUDICIAL_DATAJUD_API_KEY` também.

## Deploy (Docker Compose)

O serviço `judicial_api` roda a mesma imagem do backend (uvicorn `judicial_api.app:app`
na porta 8010) e usa o MESMO PostgreSQL. As migrations (incluindo as tabelas
`judicial_*`) são aplicadas pelo serviço `backend` (dono da cadeia Alembic); o serviço
judicial não aplica migrations.

```bash
docker compose up -d            # sobe postgres, backend (migrations), judicial_api, frontend
curl -s http://localhost:8010/health
```

## Integração com o Radar Leilão (Task Final)

O Radar consome a Judicial API por HTTP — **não** duplica provider/orchestrator/sinais.

- Cliente: `backend/app/judicial_client.py` (`JudicialApiClient`).
- Integração/persistência: `backend/app/judicial_integration.py` mapeia o resultado da
  Judicial API em `LegalProcess`/`ProcessMovement` e os sinais em `Evidence` (categoria
  `JURIDICO`), preservando a distinção **processo × imóvel** (um sinal processual nunca
  vira gravame confirmado na matrícula), e emite um `DomainEvent`
  `CONSULTA_JUDICIAL_REALIZADA` (alimenta a reanálise incremental).
- Endpoint: `POST /api/imoveis/{id}/processos/consultar`. Indisponibilidade/timeout da
  Judicial API **não** interrompem as demais análises — o endpoint responde
  `200 { "disponivel": false }` (degradação graciosa).
- Configuração no backend (env): `JUDICIAL_API_BASE_URL`, `JUDICIAL_API_KEY` (chave de
  consumidor), `JUDICIAL_API_TIMEOUT_SECONDS`.

### Testes reais (opcionais) e limitações

O teste real contra o DataJud (`tests/judicial/test_real_datajud.py`) permanece **fora
da suíte padrão** e só executa com `RUN_REAL_DATAJUD_TESTS=true` e credencial válida.
Nunca simula sucesso quando não executado. Os testes de persistência PostgreSQL exigem
`RAG_TEST_DATABASE_URL` (pulam quando ausente).

## Testes

```bash
pytest -q tests/judicial
```

A suíte padrão **não** exige banco de dados nem chamada real ao DataJud (usa fakes/mocks).

### Testes reais (opcionais)

Os testes contra o DataJud real ficam fora da suíte padrão e exigem configuração
explícita (SPEC §84):

```bash
RUN_REAL_DATAJUD_TESTS=true JUDICIAL_DATAJUD_API_KEY=<chave> pytest -q tests/judicial/test_real_datajud.py
```
