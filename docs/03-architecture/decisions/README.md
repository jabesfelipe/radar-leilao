# Decisões de arquitetura (índice de ADRs)

Regra: só entram decisões com **evidência** no repositório. Quando a motivação não está documentada, o campo fica "pendente".
Data e aprovador formais não constam no repositório para nenhuma destas decisões; ficam "pendente de confirmação".

## ADRs do workflow (documento original)

Fonte: [ADR-WORKFLOW-ARCHITECTURE.md](ADR-WORKFLOW-ARCHITECTURE.md). O cabeçalho original diz "PROPOSTO"; o código implementa as decisões (ver banner no documento).

| ADR | Decisão | Evidência no código | Status |
|---|---|---|---|
| ADR-001 | Separar Imóvel, Oportunidade, Processo de Análise, Workflow e Dossiê | `models.py` (Opportunity), migrations 0018 e 0019 | em vigor |
| ADR-002 | "Oportunidade legada" para preservar o histórico | migration 0019 (FK de oportunidade) | em vigor |
| ADR-003 | Workflow como máquina de estados que orquestra, não substitui | `workflow_engine.py` puro; `workflow_service.py` | em vigor |
| ADR-004 | Hard stops independentes do score | `HARD_STOPS` em `workflow_rules.py` | em vigor |
| ADR-005 | Transições imutáveis; reabertura por evento | `INVALIDATION_EVENTS`, tipos de transição | em vigor |
| ADR-006 | Versionamento declarativo das regras | `WORKFLOW_RULESET_VERSION = "workflow-v1"` | em vigor |
| ADR-007 | M0 (modularização) sem mudança de contrato | `routers/` com 11 routers; contrato OpenAPI em `tests/contract/openapi_baseline.json` | em vigor |

## Decisões inferidas da documentação e do código

| ID | Decisão | Evidência | Motivação documentada |
|---|---|---|---|
| D-08 | Deploy automático por tag; a VPS não constrói imagens; imagens no GHCR sem `latest` | `release.yml`, `tests/test_release_workflow_policy.py`, [github-actions.md](../../04-operations/github-actions.md) | parcial: a tag é a autorização e tags são imutáveis; demais motivos pendentes |
| D-09 | Portão por cookie no proxy como proteção de borda | `docker/nginx/templates/default.conf.template`, [homologation-guide](../../04-operations/homologation-guide.md) | sim: rotas legadas sem JWT |
| D-10 | Roteamento manual no frontend (sem react-router) | `frontend/src/App.tsx`, `package.json` | pendente |
| D-11 | Vetores no PostgreSQL (pgvector) com busca híbrida | [RAG-ARCHITECTURE](../specs/RAG-ARCHITECTURE.md) | consultar o documento; resumo pendente |
| D-12 | Storage local em volume com abstração para S3/MinIO | [storage.md](../../04-operations/storage.md) | sim, no documento |
| D-13 | Credenciais de portal cifradas (Fernet) em coluna separada | docstring de `PortalAccess` em `models.py` | sim: nunca devolver ou enviar a LLM |
| D-14 | Projeto Compose fixo `radar-prod` para separar volumes de dev e produção | [docker-deployment.md](../../04-operations/docker-deployment.md) | sim |
| D-16 | Portão de segurança **global default-deny** (dependência do app) em vez de decorar cada rota; permissões por papel reaproveitando o RBAC existente | `backend/app/security.py`, `tests/test_security_gate.py` | sim: ~150 rotas legadas sem autenticação e nenhuma segunda arquitetura de auth |
| D-17 | Advisory locks do PostgreSQL (de transação) e `FOR UPDATE SKIP LOCKED` contra duplicidade, em vez de fila ou lock em memória | `backend/app/locks.py`, `documents/worker.py` | sim: 2 workers uvicorn + worker + reprocesso compartilham o banco |
| D-18 | Rate limit e concorrência em memória por processo (sem Redis) | `backend/app/security.py` | sim: simplicidade do MVP; limitação documentada em security.md §9 |
| D-15 | Uma única VPS com Docker Compose na fase de homologação | [infrastructure.md](../../04-operations/infrastructure.md) | sim: testar remotamente com custo baixo; VPC adiada |

Para registrar uma nova decisão: crie `ADR-NNN-titulo.md` nesta pasta e acrescente uma linha na tabela acima.
