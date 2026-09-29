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
