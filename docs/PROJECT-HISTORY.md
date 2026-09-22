# Radar Leilão — Histórico de Implementação

Este documento registra a trajetória técnica do projeto e os commits que representam as etapas já executadas.

## Marco inicial

- `5e2872cb790299122697774931696f9b1266eadd` — docs: init
- `3f370691fb3f20d90e950ca18d293ad66afb6bf8` — docs: adiciona spec oficial do vibe coding do MVP
- `1333c2f43277c2c6be3e6aad3ca0247ade19af15` — docs: consolida arquitetura mestre completa para vibe coding
- `baebc3eb1f6ec297cabb2437786aa63d0ccf6d55` — docs: remove documentos antigos consolidados na arquitetura mestre

## Implementação do MVP

Os marcos de implementação anteriores permanecem registrados neste histórico.

## Correções que devem permanecer registradas

### Reanálise incremental
`d416345516fe11c7c27a1684a4071d916433dfaf` — correção para executar Checklist apenas quando efetivamente afetado.

### Risk Engine
`acc515f321a6f827ae32c10be98972940530fe08` — remoção de regras de risco não formalizadas.

### Cadastro de imóvel
`d244a08e375e4b2c23f88e9acbeccd84fe12719b` — remoção de enum artificial de tipo de imóvel.

## TASK 44 — Mercado + Ocupação
- `13b6c9325978908b7960e17edb65700fd94c0aa2` — feat: implementa mercado e ocupacao no hub do imovel
- Auditoria: 🟢 aprovado.

## TASK 45 — Checklist no Hub
- `a8fe36ac643090ff4c74008dfe4bb3c2f9aaf0d2` — feat: implementa checklist no hub do imovel
- `14da0329cb7c03fd59291d6b0fc585943fc83abc4` — fix: corrige contrato e valores ausentes do checklist
- Auditoria: 🟢 aprovado.

## TASK 46 — Riscos + Veredito no Hub
- `3480a5ce388d5ff45250c217dcdb394f7f583c1d` — feat: implementa riscos e veredito no hub do imovel
- Auditoria: 🟢 aprovado.

## TASK 47 — Histórico no Hub
- `bed0c5688497accbd4db8413e40077c3cef9232d` — feat: implementa historico no hub do imovel
- `b08b63002e7365e55be9b99d2abd6057e473332d` — fix: ajusta contrato do historico no hub do imovel
- Auditoria final: 🟢 aprovado.

## TASK 49 — Revisão da integração Frontend ↔ Backend
- `2a549c8e9b90e6fc07e50b1f915f109fdc31ca02` — fix: revisa integracao frontend backend
- Auditoria: 🟢 aprovado.

## TASK 50 — Testes de integração
- `1e50f30e09f314e058eaa396a49b0a769209f6c2` — test: adiciona testes de integracao do radar
- Auditoria: 🟢 aprovado.

## TASK 51 — Primeiro E2E com imóvel real da Caixa
- `ea7db957b6ef6e739bfa19d086b4a508d462acc6` — test: executa primeiro e2e com imovel real da caixa
- Auditoria: 🟡 não aprovado como E2E completo.

## TASK 52 — Cadeia de migrations validada
- `b676a889fdfb79c4609b72107a345f9b5ed3a080` — fix: corrige cadeia de migrations do radar
- Migrations 0001 → 0008 concluídas em banco limpo; 211 passed, 10 failed por problemas de aplicação fora do escopo.

## TASK 53 — Snapshot anterior do Checklist
- `f36cecebb490112945d2f6a91ae96bf2e9492157` — fix: corrige snapshot anterior do checklist
- Auditoria: 🟢 aprovado.

## TASK 54 — Correção da próxima falha
- `ecde86518d4d9d4136184877974f103b9735e80d` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Suíte: 213 passed, 8 failed.

## TASK 55 — Correção da próxima falha
- `27a65e3cd21053d710c68338a4f1a853a4ad8caa` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Suíte: 214 passed, 7 failed.

## TASK 56 — Correção da próxima falha
- `1aa3912445c3e25a6f0b9e2ac4fa93d9e82f1d74` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Suíte: 215 passed, 6 failed.

## TASK 57 — Correção da próxima falha
- `4c26ee67243cc622b89748a607fc01e3e294ca26` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Corrigida fixture de `test_extraction.py` para fornecer `success=True`.
- Suíte: 216 passed, 5 failed.

## TASK 58 — Correção da próxima falha de integração
- `23b47172f1855e7f6facde86142ed7762759615c` — fix: corrige serializacao decimal na integracao
- Auditoria: 🟢 aprovado.
- A falha foi reproduzida e a causa real confirmada: o PATCH do Checklist retornava `{}` porque o ORM era retornado após `db.commit()` sem `db.refresh(result)`.
- Correção mínima: `db.refresh(result)` em `main.py`.
- Contrato preservado; nenhum schema, migration, teste ou regra de negócio alterado.
- Resultado: teste alvo passou; `test_integration_flows.py`: 12 passed, 4 failed; suíte: 217 passed, 4 failed.

## TASK 59 — Correção da primeira falha do fluxo de análise
- `92c3e44aa314fc38c402a895d64b9add17381d85` — fix: corrige primeira falha do fluxo de analise
- Auditoria: 🟢 aprovado.
- Correção: serialização do resultado financeiro antes da criação do veredito.

## TASK 60 — Correção das 3 falhas restantes da integração
- `1262637fa681d056f4191a8e15cbb72aefcc4038` — fix: corrige 3 falhas restantes da integracao
- Auditoria: 🟢 aprovado por inspeção do diff.
- `get_property` passou a ordenar as análises por versão.
- `create_analysis` passou a consultar a maior versão persistida diretamente no banco, evitando duplicidade na reanálise incremental.
- Sem migration/schema, alteração de testes ou nova regra de negócio.
- CI/workflow não publicou execução para este commit; não há contagem independente de testes.


---

## Consolidação de validação — 21/09/2026

### Validação da TASK 60 em runtime

Após as correções da TASK 60, os três testes diretamente relacionados à correção passaram:

```text
3 passed, 13 deselected
```

Em seguida, a suíte completa de integração foi executada:

```text
pytest -q tests/test_integration_flows.py
16 passed, 2110 warnings in 3.29s
```

### Validação da suíte completa

```text
pytest -q
221 passed, 2744 warnings in 9.41s
```

Resultado: **221 testes passaram e nenhuma falha automatizada permanece neste estado do projeto.**

Os warnings foram registrados para acompanhamento futuro, mas não bloquearam a validação.

### Documentação mestre

A especificação principal foi movida da raiz para:

`docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`

Na consolidação, a referência residual a **Java 21 / Spring** na arquitetura foi corrigida para **Python + FastAPI**, alinhando a documentação com a implementação efetiva.

### Estado após a consolidação

O projeto entra na fase de validação operacional com imóveis reais. A suíte automatizada está verde, mas o E2E real com documentos da Caixa, OCR e LLM continua sendo uma etapa distinta e deve ser validado antes de declarar o fluxo real completamente concluído.


## TASK 61 — Setup local automatizado (WSL2 + Docker)

- Objetivo: permitir subir o Radar Leilão em um notebook novo (Windows + WSL2 + Docker) sem configuração manual de banco/migrations/infra.
- Implementação:
  - `docker-compose.yml`: serviços `postgres` (pgvector/pgvector:pg16), `backend` (FastAPI) e `frontend` (React/Vite). Volumes persistentes `postgres_data` e `backend_storage`. Healthchecks em postgres e backend. Portas e credenciais via `.env` (com defaults).
  - `backend/Dockerfile` + `docker/backend-entrypoint.sh`: espera o PostgreSQL, executa `alembic upgrade head` (mecanismo oficial, sem estratégia paralela) e sobe o Uvicorn.
  - `frontend/Dockerfile`: build com `VITE_API_URL` embutido e serve via `vite preview` na porta 5173.
  - `.env.example` revisado com todas as variáveis realmente usadas (PostgreSQL, backend, frontend, LLM). `.env` continua ignorado pelo `.gitignore`.
  - Scripts em `scripts/`: `setup.sh`, `start.sh`, `stop.sh`, `restart.sh`, `health.sh`, `reset.sh` (destrutivo, com confirmação), `backup.sh`, `restore.sh`.
  - `docs/LOCAL-SETUP.md`: passo a passo para usuário leigo (WSL2, Docker, clone, `.env`, setup, URLs, parar/iniciar, health, reset, backup/restore) + troubleshooting.
- Decisões:
  - **MinIO não incluído**: o código atual armazena documentos no filesystem local (`storage/documents`), sem MinIO/S3. Persistência garantida por volume Docker (`backend_storage`). Documentado em `docs/LOCAL-SETUP.md`.
  - **Redis não incluído**: não há dependência real no código.
  - **LLM opcional**: a stack sobe sem `OPENAI_API_KEY`; apenas as etapas de IA ficam indisponíveis, sem quebrar o sistema.
- Validação real (WSL2 → Docker):
  - `docker compose config` válido; `docker compose up -d --build` subiu os 3 serviços.
  - Backend `healthy`; `/health` = `{status: ok}`; Swagger `/docs` = HTTP 200; frontend `:5173` = HTTP 200.
  - Migrations aplicadas automaticamente no boot: `alembic_version = 0008_extracao_documental`.
  - `scripts/health.sh`: PostgreSQL/pgvector/Migrations/Backend/Frontend = OK (5/0).
  - `pytest -q` = **221 passed** (sem regressão; nenhum teste removido; nenhuma regra de negócio alterada).
- Limitações conhecidas:
  - Primeiro `setup.sh`/build é demorado (instala dependências pesadas do backend e faz build do frontend).
  - Backup cobre banco (pg_dump) + storage de documentos; não cobre `.env`, imagens Docker nem código-fonte.
  - `reset.sh` é destrutivo (remove volumes) e exige confirmação; não faz parte do fluxo normal.
