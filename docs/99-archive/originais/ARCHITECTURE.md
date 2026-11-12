# Radar Leilão — Arquitetura (visão geral)

Documento de referência da arquitetura real do sistema após as ondas de consolidação
(Onda 2 + RAG production-ready + infraestrutura). Reflete o código em `main`.

## 1. Componentes

```
                         ┌──────────────────────────────┐
  navegador  ──HTTPS──►  │  proxy (nginx 80/443)         │
                         │  /api -> backend   / -> front │
                         └───────┬───────────────┬───────┘
                                 │               │
                      ┌──────────▼───┐     ┌─────▼───────────┐
                      │ backend      │     │ frontend (nginx)│
                      │ FastAPI ASGI │     │ SPA React/Vite  │
                      └──┬────────┬──┘     └─────────────────┘
                         │        │
             ┌───────────▼─┐   ┌──▼───────────────┐
             │ PostgreSQL  │   │ worker (polling) │
             │ + pgvector  │◄──┤ embeddings       │
             └─────────────┘   └──────────────────┘
                   ▲
                   │  (opcional) Object Storage S3/MinIO p/ PDFs
```

- **Backend** (`backend/app`): FastAPI modularizado em routers por domínio
  (`routers/*`), serviços de negócio (`services.py`, `workflow_service.py`,
  `modality_rules.py`, `rag/`, `documents/`), motor de workflow puro
  (`workflow_engine.py`/`workflow_rules.py`), autenticação/RBAC (`auth.py`/`authz.py`).
- **Frontend** (`frontend/src`): React + TypeScript, páginas/hubs, serviços tipados por
  domínio, store de sessão + injeção de `Authorization`.
- **PostgreSQL 16 + pgvector 0.8.6**: dados, relações, chunks e embeddings (`vector(1536)`).
- **Worker**: processamento assíncrono DB-backed (sem Redis) de embeddings pendentes.
- **Judicial API** (`judicial_api/`): módulo independente (DataJud) consumido por HTTP.
- **Storage**: abstração `backend/app/storage` (local default; S3/MinIO preparado).

## 2. Domínios principais

| Domínio | Código | Observação |
|---|---|---|
| Oportunidade + Workflow F0–F13 | `workflow_service.py`, `workflow_engine.py`, `routers/opportunities.py` | motor puro; transições append-only |
| Modalidades | `modality_rules.py` | catálogo canônico declarativo (modality-v1) |
| Dashboard | `routers/dashboard.py` | agregação real por fase/modalidade/município |
| Documentos/RAG | `documents/`, `rag/` | ingestão, dedup, chunks, embeddings, busca híbrida |
| Central Jurídica | `legal_service.py`, `routers/legal_central.py` | biblioteca legal + correlação |
| Central de Débitos | `routers/debts.py`, `debt_query_service.py` | débitos/estimativas |
| Due Diligence | `services.py` (frentes) | integrações externas opcionais (falha-fechada) |
| Auth/RBAC | `auth.py`, `authz.py`, `routers/auth.py` | JWT HS256 + papéis |
| Monitoramento | `routers/monitoring.py` | readiness, RAG, storage, fila do worker |

## 3. Fluxo ponta-a-ponta (produto)

CAPTURA → OPORTUNIDADE → CLASSIFICAÇÃO (modalidade) → DOCUMENTOS (ingestão/RAG) →
ANÁLISE JURÍDICA → DUE DILIGENCE → DÉBITOS → FINANCEIRO → RISCOS → CHECKLIST →
DECISÃO (comitê/hard stops) → AQUISIÇÃO → PÓS-LEILÃO → REGULARIZAÇÃO → SAÍDA.

O workflow (F0–F13) é a espinha operacional: cada fase tem gate de saída; hard stops
determinísticos bloqueiam o avanço e **não** são contornáveis por recomendação de IA.

## 4. Decisões arquiteturais-chave

- **Motor de workflow puro** (sem I/O): decisões determinísticas e testáveis; o serviço
  monta o contexto dos domínios e persiste transições (append-only, auditável).
- **RAG híbrido** (vetor + texto PostgreSQL) com isolamento por imóvel/oportunidade e
  dedup por SHA-256 (ver `docs/RAG-ARCHITECTURE.md` e `docs/RAG-LIFECYCLE.md`).
- **Worker DB-backed** (sem Redis/Celery): menor complexidade; a tabela
  `document_versions` é a fila durável.
- **Storage abstrato**: troca local↔S3/MinIO por configuração, sem reescrever a app.
- **Migrations controladas** em produção (ver `docs/DATABASE-MIGRATION.md`).
- **Contrato OpenAPI versionado** (`tests/contract/openapi_baseline.json`, 143 paths):
  guard-rail de regressão de API no CI.

## 5. Segurança (resumo)

- JWT HS256 (`JWT_SECRET_KEY` obrigatório; falha-fechada 503 sem segredo).
- RBAC: ADMIN/ANALISTA/OPERADOR/CONSULTA; permissões validadas no backend.
- CORS configurável (`CORS_ALLOW_ORIGINS`); nunca `*` com credenciais.
- PostgreSQL não exposto publicamente; proxy é o único ponto de entrada.
- `X-Admin-Token`: compat legado em **desativação controlada** (ver OPERATIONS-RUNBOOK).
- Containers de produção rodam como usuário não-root.

## 6. Variáveis de ambiente

Dev: `.env.example`. Produção: `.env.prod.example`. Nenhum segredo é versionado.
Principais: `POSTGRES_*`, `JWT_SECRET_KEY`, `CORS_ALLOW_ORIGINS`, `STORAGE_BACKEND`
(+`STORAGE_S3_*`), `OPENAI_API_KEY` (opcional), `UVICORN_WORKERS`, `WORKER_*`.

## 7. Documentos relacionados

`RAG-ARCHITECTURE.md`, `RAG-LIFECYCLE.md`, `DEPLOYMENT.md`, `DATABASE-MIGRATION.md`,
`BACKUP-RESTORE.md`, `PRODUCTION-CHECKLIST.md`, `OPERATIONS-RUNBOOK.md`,
`CAPACITY-PLANNING.md`, `ONDA-2-WORKFLOW-DASHBOARD-RELATORIO.md`.
