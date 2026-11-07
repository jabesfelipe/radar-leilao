# PLAN M0 — Modularização da API (sem reescrita, sem mudança de contrato)

> **Status:** EM EXECUÇÃO CONTÍNUA — infraestrutura + padrão PROVADOS na Onda 0 (20/09/2026,
> HEAD `1d2d06d`). Implementado: baseline OpenAPI (`tests/contract/openapi_baseline.json`, 99 paths)
> + guard-rail `tests/contract/test_openapi_contract.py`; `routers/deps.py` (`property_or_404`,
> fonte única); routers `health.py`, `hubs.py` (11 hubs), `legal_central.py`, `market.py` montados
> via `app.include_router`. **Nota operacional importante:** vários testes importam os handlers
> diretamente de `backend.app.main` — ao mover uma rota para um router é OBRIGATÓRIO reexportar o
> handler em `main.py` (ex.: `from .routers.market import get_market`), senão a suíte quebra com
> `ImportError`; o guard-rail de contrato OpenAPI não detecta isso. Por esse acoplamento, os ~83
> paths restantes serão modularizados de forma **contínua/incremental**, nunca em massa. Base:
> `ADR-WORKFLOW-ARCHITECTURE.md` (ADR-007).
> **Objetivo:** transformar o `main.py` monolítico (~130 rotas em `@app`) em **`APIRouter` por
> domínio**, montados por `app.include_router`, **preservando exatamente** paths, métodos,
> `response_model`, status codes e corpos de resposta. **Não é reescrita de lógica.**

## 1. Estado atual
- `backend/app/main.py`: `app = FastAPI(...)`, imports diretos de `services`/engines, ~130 rotas
  declaradas em `@app.get/post/patch/delete`. **Sem `APIRouter`/`include_router`.**
- As funções de rota já delegam a `services`/engines (a lógica **não** vive na rota) — isso
  torna o M0 um movimento mecânico e de baixo risco.

## 2. Estrutura-alvo de routers (`backend/app/routers/`)

Um módulo por domínio, cada um expondo um `router = APIRouter()`:

| Router (`routers/…`) | Prefixo lógico | Rotas (amostra, inalteradas) |
|---|---|---|
| `properties.py` | `/api/imoveis` | list/create/patch/get, `/completo`, `/leilao`, `/fontes*` |
| `documents.py` | `/api/imoveis/{id}/documentos`, `/api/documentos` | upload, versões, extrair, extracao |
| `registration.py` | `/api/imoveis/{id}/matricula` | CRUD matrícula |
| `notices.py` | `/api/imoveis/{id}/edital` | CRUD edital |
| `legal_processes.py` | `/api/imoveis/{id}/processos`, `/juridico/*` | processos, consultar, vincular, riscos, evidencias |
| `financial.py` | `/api/imoveis/{id}/financeiro*` | financeiro, premissas, analisar |
| `market.py` | `/api/imoveis/{id}/mercado`, `/comparaveis` | mercado, comparáveis |
| `occupancy.py` | `/api/imoveis/{id}/ocupacao` | ocupação |
| `checklist.py` | `/api/checklist*`, `/api/imoveis/{id}/checklist*` | mestre global + por imóvel |
| `analysis.py` | `/api/imoveis/{id}/analisar`, `/analises/*`, `/eventos/*`, `/historico` | agentes, análise, reanalisar |
| `evidence.py` | `/api/imoveis/{id}/evidencias` | evidências + links |
| `costs_debts.py` | `/api/imoveis/{id}/custos`, `/dividas` | custos, dívidas |
| `auctioneers.py` | `/api/leiloeiros` | leiloeiros, portais, credencial, documentos |
| `due_diligence.py` | `/api/imoveis/{id}/due-diligence`, `/localizacao*` | DD + localização |
| `post_auction.py` | `/api/imoveis/{id}/pos-arrematacao` | etapas/custos/contatos/consultorias/notificacoes |
| `legal_central.py` | `/api/juridico/biblioteca*`, `/referencias/*` | Central Jurídica |
| `hubs.py` | `/api/dashboard`, `/api/riscos`, `/api/veredito`, … | visões globais |
| `health.py` | `/health` | health |
| **`workflow.py`** (novo, entra no B1) | `/api/imoveis/{id}/oportunidades`, `/api/oportunidades/*` | workflow/oportunidade |

> Os **prefixos acima são lógicos** (agrupamento). Para **garantir contrato idêntico**, cada
> rota mantém seu **path completo atual** (ex.: a rota continua `"/api/imoveis/{id}/documentos"`).
> Decisão de implementação: ou usar `APIRouter(prefix=...)` **apenas** quando o prefixo bate 100%
> com o path atual, ou declarar o path completo em cada rota do router (mais seguro para não
> escorregar no contrato). **Preferência: path completo por rota** → zero ambiguidade.

## 3. Camadas e dependências (sem inversão de arquitetura)

```
router (HTTP: validação de entrada, response_model)   ← fino, sem regra de negócio
   │ chama
services.py / *_service.py (orquestração de caso de uso, transação, eventos)
   │ chama
engines puros (finance, risk, verdict, legal_correlation, impact) + models (SQLAlchemy)
   │ usa
database.get_db (Session)
```

- M0 **não** cria uma camada "repository" nova agora (a persistência hoje é via `services` +
  `Session`). Introduzir repositories é refactor opcional **posterior** (não M0) e só se provar
  necessário. **Evitar over-engineering nesta etapa.**
- Dependências compartilhadas (ex.: `property_or_404`, `get_db`, `serialize`) movem para
  `routers/deps.py` ou permanecem em `services`, importadas pelos routers.

## 4. Estratégia de preservação de contrato

1. **Baseline antes:** gerar snapshot do OpenAPI atual (`GET /openapi.json`) e salvar como
   fixture de teste (`tests/contract/openapi_baseline.json`).
2. **Mover em lotes pequenos:** um domínio por PR (ex.: começar por `health` + `hubs`, de baixo
   risco). Cada PR move as rotas daquele domínio para o router e registra `include_router`.
3. **Diff de contrato:** após cada lote, regenerar o OpenAPI e **comparar com o baseline** —
   paths, métodos, `operationId`/nomes, schemas e status codes devem ser **idênticos** (exceto
   reordenação). Qualquer divergência falha o teste.
4. **Nada de renomear** path/param/response. Se algo "feio" aparecer, documenta-se como dívida —
   **não** se corrige no M0 (seria mudança de contrato).

## 5. Migração gradual (coexistência)

- Enquanto um domínio não migrou, suas rotas continuam no `main.py`. `include_router` convive
  com rotas `@app` remanescentes — FastAPI resolve ambos no mesmo `app`.
- Ordem sugerida (menor risco → maior): `health`, `hubs`, `market`, `costs_debts`, `occupancy`,
  `evidence`, `auctioneers`, `documents`, `registration`, `notices`, `legal_processes`,
  `checklist`, `financial`, `analysis`, `due_diligence`, `post_auction`, `legal_central`,
  `properties` (o maior, por último).
- `main.py` termina como: criação do `app`, middleware/CORS, `configure_logging`, e uma lista de
  `app.include_router(...)`. **Comportamento idêntico.**

## 6. Testes de regressão (M0)

- **Contrato OpenAPI:** `test_openapi_contract.py` compara `openapi.json` atual × baseline
  (paths/métodos/schemas/status). Falha a qualquer divergência.
- **Rotas HTTP existentes:** reaproveitar/estender os testes HTTP já existentes
  (`test_juridico_e2e_http.py`, `test_task752_crud.py`, etc.) garantindo 200/404/422 iguais.
- **Smoke de montagem:** teste que importa `app` e verifica que o número de rotas e os paths não
  mudaram (set de `route.path` igual antes/depois).
- **Sem novos dados/sem LLM:** os testes rodam no padrão atual (`postgres_engine`, sem rede).

## 7. Critérios de aceite do M0
- `openapi.json` idêntico ao baseline (paths/métodos/schemas/status).
- Suíte de testes existente verde (mesmos resultados de antes).
- `main.py` reduzido a bootstrap + `include_router`.
- Nenhuma mudança em `models.py`, migrations ou dados. 633/V1–V9 intactos.

## 8. Entregas pequenas (PRs)
- **M0.1** — infra de routers (`routers/__init__.py`, `routers/deps.py`) + baseline OpenAPI +
  `test_openapi_contract.py`. Move `health` e `hubs`. (Prova o mecanismo.)
- **M0.2..M0.n** — um domínio por PR, na ordem da §5, cada um com diff de contrato verde.
- **M0.final** — `properties` migrado; `main.py` vira bootstrap. Revisão de que a lista de rotas
  é idêntica.

## 9. Riscos e mitigações
| Risco | Mitigação |
|---|---|
| Escorregar no path/contrato ao mover | path completo por rota + diff OpenAPI obrigatório |
| Import circular entre routers e services | `deps.py` central; routers só importam services/schemas |
| Ordena­ção/precedência de rotas dinâmicas | preservar ordem relativa dentro do domínio; teste de set de paths |
| PR gigante difícil de revisar | um domínio por PR; `properties` por último |
