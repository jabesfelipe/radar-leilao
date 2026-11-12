# 99 — Arquivo

Documentos preservados por valor histórico ou porque foram **consolidados** em documentos novos. Nenhum arquivo foi apagado: todos
foram movidos com `git mv` (o histórico do Git continua acessível) e o conteúdo permanece íntegro. O texto dos arquivos arquivados
**não foi atualizado**: pode conter números, caminhos e afirmações superados.

Regra: não use estes documentos como fonte de verdade. A fonte oficial está em `01-business` a `06-quality`.

## 1. Originais consolidados (`originais/`)

| Caminho antigo | Arquivo arquivado | Conteúdo | Destino atual |
|---|---|---|---|
| `docs/ARCHITECTURE.md` | [originais/ARCHITECTURE.md](originais/ARCHITECTURE.md) | arquitetura (mostrava proxy 80/443 com HTTPS e 143 paths) | [03-architecture/architecture.md](../03-architecture/architecture.md) |
| `docs/DEVELOPMENT-WORKFLOW.md` | [originais/DEVELOPMENT-WORKFLOW.md](originais/DEVELOPMENT-WORKFLOW.md) | fluxo específico do Kiro | [05-development/development-workflow.md](../05-development/development-workflow.md) |
| `docs/DEPLOYMENT.md` | [originais/DEPLOYMENT.md](originais/DEPLOYMENT.md) | deploy manual e referência de HTTPS | [04-operations/deployment.md](../04-operations/deployment.md) |
| `docs/GITHUB-ACTIONS-DEPLOY.md` | [originais/GITHUB-ACTIONS-DEPLOY.md](originais/GITHUB-ACTIONS-DEPLOY.md) | deploy por tag (dizia que o pipeline ainda não rodou) | [04-operations/github-actions.md](../04-operations/github-actions.md); stub mantido no caminho antigo |
| `docs/INFRASTRUCTURE-CONTABO.md` | [originais/INFRASTRUCTURE-CONTABO.md](originais/INFRASTRUCTURE-CONTABO.md) | infraestrutura Contabo | [04-operations/infrastructure.md](../04-operations/infrastructure.md) |
| `docs/infra/CONTABO-VPS.md` | [originais/CONTABO-VPS.md](originais/CONTABO-VPS.md) | contratação, Docker, swap, estado (bootstrap "pendente") | [04-operations/infrastructure.md](../04-operations/infrastructure.md); stub mantido no caminho antigo |
| `docs/CONTABO-CHECKLIST.md` | [originais/CONTABO-CHECKLIST.md](originais/CONTABO-CHECKLIST.md) | roteiro de preparação | [04-operations/infrastructure.md](../04-operations/infrastructure.md) §3 |
| `docs/OPERATIONS-RUNBOOK.md` | [originais/OPERATIONS-RUNBOOK.md](originais/OPERATIONS-RUNBOOK.md) | runbook (§5 mandava fazer build na VPS) | [04-operations/operations.md](../04-operations/operations.md) e [deployment.md](../04-operations/deployment.md) |
| `docs/PRODUCTION-CHECKLIST.md` | [originais/PRODUCTION-CHECKLIST.md](originais/PRODUCTION-CHECKLIST.md) | checklist (`VITE_API_URL=/api`, 143 paths, HTTPS) | [04-operations/deployment.md](../04-operations/deployment.md) §5 e §7 |
| `docs/CAPACITY-PLANNING.md` | [originais/CAPACITY-PLANNING.md](originais/CAPACITY-PLANNING.md) | dimensionamento para 2 vCPU e 4 GB | [04-operations/infrastructure.md](../04-operations/infrastructure.md) §10 |

## 2. Relatórios e histórico de execução (`reports/`)

Status, auditorias, fechamentos e relatórios de tarefas. Substituídos por [02-product/README.md](../02-product/README.md) (estado atual) e
[06-quality](../06-quality/README.md).

`E2E-DIAGNOSTICO-TASK-51`, `AUDITORIA-MOTOR-FINANCEIRO`, `ANDAMENTO-VALIDACAO-2026-10-21` (contém URLs absolutas do GitHub para documentos antigos),
`VALIDACAO-POS-ARREMATACAO`, `TASK-75-FECHAMENTO-FUNCIONAL-PRODUTO`, `TASK-75.2.1-FECHAMENTO-FINAL`, `ONDA-2-WORKFLOW-DASHBOARD-RELATORIO`,
`CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A`, `COBERTURA-MUNICIPAL-FONTES-ETAPA-B`, `CENTRAL-DEBITOS-DESPESAS-ETAPAS-C-F-RELATORIO`,
`MVP-CONSOLIDACAO-FINAL-2026-11`, `PROJECT-AUDIT-2026-11`, `PROJECT-STATUS-2026-10-01`, `PROJECT-HISTORY-2026-10-01`,
`PROJECT-STATUS` (2104 linhas), `PROJECT-HISTORY` (2746 linhas). Caminho: `docs/99-archive/reports/<NOME>.md`.

## 3. Especificações e planos originais (`specs-originais/`)

`SPEC-VIBE-CODING-RADAR-LEILAO` (3272 linhas; fonte histórica do método; a seção 2 "Business canônico" foi refletida em
[01-business](../01-business/README.md)), `IMPLEMENTATION-REFERENCE`, `JUDICIAL-IMPLEMENTATION-TASKS`, `PLAN-M0-API-MODULARIZATION`,
`PLAN-B1-WORKFLOW-ENGINE`, `PLAN-WAVE-2-MODALIDADES`, `PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN`, `SEQUENCING-M0-B1`,
`ACCEPTANCE-CRITERIA-MASTER`, `ACCEPTANCE-CRITERIA-WORKFLOW`, `IMPLEMENTATION-PLAN-100`, `TODO-WORKFLOW-FOUNDATION`, `TODO-PLATAFORMA-COMPLETA`.
Caminho: `docs/99-archive/specs-originais/<NOME>.md`.

## 4. Planejamento antigo (`planning/`)

`ROADMAP-MASTER`, `ROADMAP-EXECUTION`, `ROADMAP-PLATAFORMA-COMPLETA`, `PRODUCT-SCOPE-100`, `FEATURE-BACKLOG`, `FEATURE-INVENTORY` (obsoleto: 99 paths,
50 tabelas, "autenticação não iniciada"), `PRODUCT-DASHBOARD`, `EVOLUTION-BACKLOG`. Substituídos por [02-product/roadmap.md](../02-product/roadmap.md).
Caminho: `docs/99-archive/planning/<NOME>.md`.

## 5. Prompts de ferramenta de IA (`prompts/`)

`PROMPT-KIRO-CICLO-1-AUDITORIA`, `PROMPT-KIRO-PLATAFORMA-COMPLETA`. Dependentes da ferramenta; não fazem parte do processo do projeto
([development-workflow.md](../05-development/development-workflow.md#assistentes-de-ia-opcional)).

## 6. Caminhos antigos mantidos como stubs em `docs/`

Citados por mensagens de scripts e workflows, por isso continuam existindo (arquivo curto que aponta para o novo local):

| Stub | Citado por | Novo local |
|---|---|---|
| `docs/GITHUB-ACTIONS-DEPLOY.md` (inclui "§8 Recuperação de falha") | `.github/workflows/release.yml` | [github-actions.md](../04-operations/github-actions.md) |
| `docs/BACKUP-RESTORE.md` | scripts de `scripts/prod/` | [backup-restore.md](../04-operations/backup-restore.md) |
| `docs/DOCKER-DEPLOYMENT.md` (§6 e §8) | `rollback.sh`, `docker-compose.prod.yml`, `.env.prod.example` | [docker-deployment.md](../04-operations/docker-deployment.md) |
| `docs/infra/CONTABO-VPS.md` (§4) | `bootstrap-vps.sh` | [infrastructure.md](../04-operations/infrastructure.md) |
| `docs/LOCAL-SETUP.md` ("Instalar Docker Desktop") | `scripts/setup.sh` | [getting-started.md](../05-development/getting-started.md) |

## 7. Referências em comentários de código (não alteradas)

O código não foi modificado nesta missão. Estes comentários citam caminhos antigos e devem ser atualizados **quando o código for alterado por outro motivo**:

| Arquivo (linha aproximada) | Cita | Novo local |
|---|---|---|
| `docker/nginx/templates/default.conf.template:7` | `INFRASTRUCTURE-CONTABO` | [infrastructure.md](../04-operations/infrastructure.md) |
| `docker/nginx-proxy.conf:5` | `DEPLOYMENT` | [deployment.md](../04-operations/deployment.md) (§6, TLS futuro) |
| `docker-compose.prod.yml:169`, `.env.prod.example:40` | `HOMOLOGATION-GUIDE` | [homologation-guide.md](../04-operations/homologation-guide.md) |
| `backend/app/legal_catalog.py:22` | `TODO-CENTRAL-JURIDICA` | [02-product/specs/TODO-CENTRAL-JURIDICA.md](../02-product/specs/TODO-CENTRAL-JURIDICA.md) |
| `backend/app/models.py:1066` | `PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN` | [specs-originais/PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md](specs-originais/PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md) |
| `backend/app/workflow_rules.py:8` | `SPEC-WORKFLOW-ENGINE` (sem caminho) | [03-architecture/specs/SPEC-WORKFLOW-ENGINE.md](../03-architecture/specs/SPEC-WORKFLOW-ENGINE.md) |
| `tests/test_e2e_financeiro.py:20` | `PROJECT-STATUS` | [reports/PROJECT-STATUS.md](reports/PROJECT-STATUS.md) |
| `tests/test_opportunity_isolation.py` | `SPEC-OPPORTUNITY-ISOLATION`, `MATRIZ-OPPORTUNITY-ID` | [03-architecture/specs](../03-architecture/specs/) |
