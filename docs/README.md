# Documentação do Radar Leilão

Ponto de entrada da documentação. Estrutura criada na reestruturação documental (79 documentos reclassificados).

## Mapa

| Pasta | Conteúdo |
|---|---|
| [01-business](01-business/README.md) | visão do produto, contexto de mercado, critérios de avaliação, regras de negócio e glossário |
| [02-product](02-product/README.md) | módulos (status verificado no código), roadmap, especificações de produto |
| [03-architecture](03-architecture/README.md) | arquitetura com 11 diagramas, modelo de dados, integrações, segurança, ADRs, especificações técnicas |
| [04-operations](04-operations/README.md) | infraestrutura Contabo, GitHub Actions, deploy, backup, operação |
| [05-development](05-development/README.md) | ambiente local, fluxo, testes, migrations, padrões |
| [06-quality](06-quality/README.md) | estratégia de testes, números atuais, limitações conhecidas |
| [99-archive](99-archive/README.md) | histórico e originais consolidados, com redirecionamento |

## Fontes oficiais por assunto

| Assunto | Documento oficial |
|---|---|
| O que é o produto | [01-business/product-overview.md](01-business/product-overview.md) |
| Critérios de avaliação | [01-business/evaluation-criteria.md](01-business/evaluation-criteria.md) |
| Status de cada módulo | [02-product/README.md](02-product/README.md) |
| Arquitetura e diagramas | [03-architecture/architecture.md](03-architecture/architecture.md) |
| Infraestrutura da VPS | [04-operations/infrastructure.md](04-operations/infrastructure.md) |
| Deploy por tag | [04-operations/github-actions.md](04-operations/github-actions.md) |
| Rollback e migrations em produção | [04-operations/deployment.md](04-operations/deployment.md) |
| Backup e restauração | [04-operations/backup-restore.md](04-operations/backup-restore.md) |
| Como contribuir | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| Limitações | [06-quality/known-limitations.md](06-quality/known-limitations.md) |

Fora de `docs/`: [`judicial_api/README.md`](../judicial_api/README.md) (módulo de consulta judicial) e `backend/migrations/README` permanecem onde estão.
Tudo precisa ficar dentro de `docs/` porque o `.dockerignore` exclui essa pasta das imagens.

## Contagens confirmadas (estado de `main`)

| Item | Valor |
|---|---|
| Paths OpenAPI | 144 (`tests/contract/openapi_baseline.json`) |
| Rotas | 184; em `main`/produção 36 com credencial e 148 sem; na branch de hardening todas protegidas pelo portão global, exceto `/health` e o login |
| Tabelas / migrations | 60 nos modelos (produção: 69) / 23 em `main` (head `0023_usuarios`), 24 na branch de hardening (`0024_analysis_version_unique`) |
| Itens de checklist | 27 |
| Testes | backend 964 passed, 2 skipped; frontend 29 arquivos, 169 testes (branch de hardening, com PostgreSQL real; `main`: 813 passed, 3 skipped) |

## Inventário e classificação (79 documentos)

Classificação: VÁLIDO, ATUALIZAR, CONSOLIDAR, ARQUIVAR, OBSOLETO, INCERTO. Os caminhos de origem eram `docs/<NOME>.md`, salvo indicação.
Ação "mover" usou `git mv`. "Stub" indica que o caminho antigo continua existindo com um aviso, por ser citado por scripts ou workflows.

| Arquivo | Assunto | Situação | Ação proposta | Documento de destino |
|---|---|---|---|---|
| BACKUP-RESTORE | backup e restore | VÁLIDO | mover + stub | 04-operations/backup-restore.md |
| GITHUB-ACTIONS-DEPLOY | deploy por tag | CONSOLIDAR | arquivar original + stub com §8 | 04-operations/github-actions.md |
| DOCKER-DEPLOYMENT | compose na VPS | VÁLIDO | mover + stub | 04-operations/docker-deployment.md |
| INFRASTRUCTURE-CONTABO | infra Contabo | CONSOLIDAR | arquivar | 04-operations/infrastructure.md |
| infra/CONTABO-VPS | contratação e preparação da VPS | CONSOLIDAR | arquivar + stub | 04-operations/infrastructure.md |
| CONTABO-CHECKLIST | roteiro Contabo | CONSOLIDAR | arquivar | 04-operations/infrastructure.md |
| HOMOLOGATION-GUIDE | camadas de acesso restrito | ATUALIZAR | mover com banner | 04-operations/homologation-guide.md |
| STORAGE-LOCAL | storage local | VÁLIDO | mover | 04-operations/storage.md |
| OPERATIONS-RUNBOOK | runbook de operação | CONSOLIDAR | arquivar | 04-operations/operations.md, deployment.md |
| PRODUCTION-CHECKLIST | checklist de produção (VITE_API_URL, HTTPS) | OBSOLETO | arquivar | 04-operations/deployment.md |
| CAPACITY-PLANNING | dimensionamento 2 vCPU/4 GB | OBSOLETO | arquivar | 04-operations/infrastructure.md |
| DEPLOYMENT | deploy manual, TLS futuro | CONSOLIDAR | arquivar | 04-operations/deployment.md §6 |
| DB-MAINTENANCE | manutenção do banco local | ATUALIZAR | mover com banner | 04-operations/database-maintenance.md |
| DATABASE-MIGRATION | procedimento de migrations | VÁLIDO | mover | 05-development/database-migrations.md |
| LOCAL-SETUP | setup local | VÁLIDO | mover + stub | 05-development/getting-started.md |
| OPERATIONS | operação local | VÁLIDO | mover | 05-development/local-operations.md |
| DEVELOPMENT-WORKFLOW | fluxo (específico do Kiro) | ATUALIZAR | arquivar e reescrever neutro | 05-development/development-workflow.md |
| ARCHITECTURE | arquitetura | ATUALIZAR | arquivar e reescrever | 03-architecture/architecture.md |
| RAG-ARCHITECTURE | arquitetura do RAG | VÁLIDO | mover | 03-architecture/specs/ |
| RAG-LIFECYCLE | ciclo de vida do RAG | VÁLIDO | mover | 03-architecture/specs/ |
| SECURITY-EXPOSURE-AUDIT | auditoria de exposição | VÁLIDO | mover | 03-architecture/specs/ |
| JUDICIAL-API-SPEC | spec da Judicial API | VÁLIDO | mover | 03-architecture/specs/ |
| SPEC-ADAPTADORES-CONSULTA-MUNICIPAL | adaptadores municipais | INCERTO | mover (planejado, sem cliente) | 03-architecture/specs/ |
| SPEC-WORKFLOW-ENGINE | máquina de estados | VÁLIDO | mover | 03-architecture/specs/ |
| SPEC-HARD-STOPS | hard stops | VÁLIDO | mover | 03-architecture/specs/ |
| SPEC-INVALIDATION-STRATEGY | invalidação | VÁLIDO | mover | 03-architecture/specs/ |
| SPEC-OPPORTUNITY-DOMAIN | domínio de oportunidade | VÁLIDO | mover | 03-architecture/specs/ |
| SPEC-OPPORTUNITY-ISOLATION | isolamento por oportunidade | VÁLIDO | mover | 03-architecture/specs/ |
| MODEL-DATA-WORKFLOW | modelo de dados do workflow | VÁLIDO | mover | 03-architecture/specs/ |
| MATRIZ-OPPORTUNITY-ID | matriz de opportunity_id | VÁLIDO | mover | 03-architecture/specs/ |
| ADR-WORKFLOW-ARCHITECTURE | ADRs 001 a 007 | ATUALIZAR | mover com banner de status | 03-architecture/decisions/ |
| MATRIZ-CHECKLIST-MODALIDADE | checklist × modalidade | ATUALIZAR | mover com banner | 02-product/specs/ |
| MATRIZ-CURADORIA-JURIDICA | curadoria jurídica | VÁLIDO | mover | 02-product/specs/ |
| MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS | custos e tributos | VÁLIDO | mover | 02-product/specs/ |
| WORKFLOW-LEILAO-END-TO-END | workflow F0-F13 (alvo) | ATUALIZAR | mover com banner | 02-product/specs/ |
| CENTRAL-JURIDICA | Central Jurídica | VÁLIDO | mover | 02-product/specs/ |
| DUE-DILIGENCE | due diligence | VÁLIDO | mover | 02-product/specs/ |
| MODULO-POS-ARREMATACAO | pós-arrematação | VÁLIDO | mover | 02-product/specs/ |
| REVISAO-ANOTACOES-LEILAO | backlog de anotações | VÁLIDO (backlog) | mover | 02-product/specs/ |
| TODO-CENTRAL-JURIDICA | pendências da curadoria | VÁLIDO | mover | 02-product/specs/ |
| E2E-DIAGNOSTICO-TASK-51 | diagnóstico E2E | ARQUIVAR | mover | 99-archive/reports/ |
| AUDITORIA-MOTOR-FINANCEIRO | auditoria do motor financeiro | ARQUIVAR | mover | 99-archive/reports/ |
| ANDAMENTO-VALIDACAO-2026-10-21 | andamento de validação | ARQUIVAR | mover | 99-archive/reports/ |
| VALIDACAO-POS-ARREMATACAO | validação do pós-arrematação | ARQUIVAR | mover | 99-archive/reports/ |
| TASK-75-FECHAMENTO-FUNCIONAL-PRODUTO | fechamento da Task 75 | ARQUIVAR | mover | 99-archive/reports/ |
| TASK-75.2.1-FECHAMENTO-FINAL | fechamento da Task 75.2.1 | ARQUIVAR | mover | 99-archive/reports/ |
| ONDA-2-WORKFLOW-DASHBOARD-RELATORIO | relatório da Onda 2 | ARQUIVAR | mover | 99-archive/reports/ |
| CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A | relatório Etapa A | ARQUIVAR | mover | 99-archive/reports/ |
| COBERTURA-MUNICIPAL-FONTES-ETAPA-B | relatório Etapa B | ARQUIVAR | mover | 99-archive/reports/ |
| CENTRAL-DEBITOS-DESPESAS-ETAPAS-C-F-RELATORIO | relatório Etapas C-F | ARQUIVAR | mover | 99-archive/reports/ |
| MVP-CONSOLIDACAO-FINAL-2026-11 | consolidação do MVP | ARQUIVAR | mover | 99-archive/reports/ |
| PROJECT-AUDIT-2026-11 | auditoria do projeto | ARQUIVAR | mover | 99-archive/reports/ |
| PROJECT-STATUS-2026-10-01 | status antigo | ARQUIVAR | mover | 99-archive/reports/ |
| PROJECT-HISTORY-2026-10-01 | histórico antigo | ARQUIVAR | mover | 99-archive/reports/ |
| PROJECT-STATUS | status (2104 linhas) | ARQUIVAR | mover | 99-archive/reports/ |
| PROJECT-HISTORY | histórico (2746 linhas) | ARQUIVAR | mover | 99-archive/reports/ |
| SPEC-VIBE-CODING-RADAR-LEILAO | especificação mestra original | ARQUIVAR | mover (fonte histórica) | 99-archive/specs-originais/; resumo em 01-business |
| IMPLEMENTATION-REFERENCE | mapa de implementação antigo | ARQUIVAR | mover | 99-archive/specs-originais/ |
| JUDICIAL-IMPLEMENTATION-TASKS | tarefas da Judicial API | ARQUIVAR | mover | 99-archive/specs-originais/ |
| PLAN-M0-API-MODULARIZATION | plano M0 | ARQUIVAR | mover | 99-archive/specs-originais/ |
| PLAN-B1-WORKFLOW-ENGINE | plano B1 | ARQUIVAR | mover | 99-archive/specs-originais/ |
| PLAN-WAVE-2-MODALIDADES | plano da Onda 2 | ARQUIVAR | mover | 99-archive/specs-originais/ |
| PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN | plano da Central de Débitos | ARQUIVAR | mover | 99-archive/specs-originais/ |
| SEQUENCING-M0-B1 | sequenciamento M0/B1 | ARQUIVAR | mover | 99-archive/specs-originais/ |
| ACCEPTANCE-CRITERIA-MASTER | critérios de aceite | ARQUIVAR | mover | 99-archive/specs-originais/ |
| ACCEPTANCE-CRITERIA-WORKFLOW | critérios de aceite do workflow | ARQUIVAR | mover | 99-archive/specs-originais/ |
| IMPLEMENTATION-PLAN-100 | plano de implementação | ARQUIVAR | mover | 99-archive/specs-originais/ |
| TODO-WORKFLOW-FOUNDATION | pendências da fundação | ARQUIVAR | mover | 99-archive/specs-originais/ |
| TODO-PLATAFORMA-COMPLETA | pendências da plataforma | ARQUIVAR | mover | 99-archive/specs-originais/ |
| ROADMAP-MASTER | roadmap | ARQUIVAR | mover | 99-archive/planning/; atual em 02-product/roadmap.md |
| ROADMAP-EXECUTION | roadmap de execução | ARQUIVAR | mover | 99-archive/planning/ |
| ROADMAP-PLATAFORMA-COMPLETA | roadmap da plataforma | ARQUIVAR | mover | 99-archive/planning/ |
| PRODUCT-SCOPE-100 | escopo do produto | ARQUIVAR | mover | 99-archive/planning/ |
| FEATURE-BACKLOG | backlog de funcionalidades | ARQUIVAR | mover | 99-archive/planning/ |
| FEATURE-INVENTORY | inventário (99 paths, 50 tabelas, sem auth) | OBSOLETO | mover | 99-archive/planning/; atual em 02-product/README.md |
| PRODUCT-DASHBOARD | painel de produto | ARQUIVAR | mover | 99-archive/planning/ |
| EVOLUTION-BACKLOG | backlog de evolução | ARQUIVAR | mover | 99-archive/planning/ |
| PROMPT-KIRO-CICLO-1-AUDITORIA | prompt de ferramenta de IA | ARQUIVAR | mover | 99-archive/prompts/ |
| PROMPT-KIRO-PLATAFORMA-COMPLETA | prompt de ferramenta de IA | ARQUIVAR | mover | 99-archive/prompts/ |

Totais: VÁLIDO 24 (inclui 1 backlog), ATUALIZAR 7, CONSOLIDAR 6, OBSOLETO 3, INCERTO 1, ARQUIVAR 38 (soma 79).
Destino físico: 49 em `99-archive` (10 originais consolidados, 16 relatórios, 13 specs originais, 8 de planejamento e 2 prompts), 22 em `02-product/specs` e `03-architecture` (specs e ADR), 8 em `04-operations` e `05-development`.
