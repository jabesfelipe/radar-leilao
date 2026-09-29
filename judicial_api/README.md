# Judicial API

Módulo **independente** de pesquisa processual judicial nacional (fonte inicial: DataJud/CNJ).
Não depende do Radar Leilão; será consumido por ele futuramente via uma única API REST.

> Estado atual: **JUR-01 — Fundação**. Ainda **não** há integração real com o DataJud,
> consulta a tribunais, persistência completa, sinais, retry, paginação ou concorrência.
> A SPEC completa está em `docs/JUDICIAL-API-SPEC.md`; a ordem de execução em
> `docs/JUDICIAL-IMPLEMENTATION-TASKS.md`.

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
  `SOURCE_*`, `SEARCH_COMPLETED`, `REANALYSIS_REQUESTED`). A persistência em
  PostgreSQL fica para uma fase posterior.

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

## Configuração

Variáveis de ambiente (prefixo `JUDICIAL_`), todas com padrão seguro:

| Variável | Padrão | Descrição |
|---|---|---|
| `JUDICIAL_LOG_LEVEL` | `INFO` | Nível de log estruturado |
| `JUDICIAL_CORRELATION_ID_HEADER` | `X-Correlation-ID` | Header do correlation id |
| `JUDICIAL_DEFAULT_SOURCE_TIMEOUT_MS` | `8000` | Timeout base por fonte (uso futuro) |
| `JUDICIAL_GLOBAL_TIMEOUT_MS` | `60000` | Timeout global (uso futuro) |
| `JUDICIAL_DATAJUD_API_KEY` | *(vazio)* | Credencial do DataJud — **nunca versionar**; opcional na JUR-01 |

Nenhum segredo é necessário para subir a aplicação ou rodar os testes desta fase.

## Testes

```bash
pytest -q tests/judicial
```

Os testes desta fase não exigem banco de dados nem chamada real ao DataJud.
