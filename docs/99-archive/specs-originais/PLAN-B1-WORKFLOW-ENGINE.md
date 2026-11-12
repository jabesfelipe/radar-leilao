# PLAN B1 — Workflow Engine (plano incremental de implementação)

> **Status:** PROPOSTO (plano; nada implementado). Base: `ADR-WORKFLOW-ARCHITECTURE.md`,
> `SPEC-WORKFLOW-ENGINE.md`, `SPEC-OPPORTUNITY-DOMAIN.md`, `MODEL-DATA-WORKFLOW.md`.
> Pré-requisito recomendado: **M0** concluído (router `workflow` entra limpo). Preserva
> 633/V1–V9/`llm_runs`. Engine **determinístico, sem LLM, sem I/O externo**.

## 1. Objetivo do B1
Entregar a **fundação** do workflow: domínio de Oportunidade + máquina de estados F0–F13 com
gates/hard stops de leitura, transições imutáveis, reabertura por evento e um dossiê consolidado
read-only. **Sem** implementar as regras finas por modalidade (épico D) nem score calibrado do
comitê (épico I) — apenas o **arcabouço** e o ruleset v1 mínimo.

## 2. Princípios de implementação
- **Aditivo e reversível**: migrations `0018`–`0020` estruturais; `0021` (dados) só com aprovação.
- **Reuso máximo**: o engine **lê** os domínios existentes; não recalcula regra de negócio.
- **Puro**: avaliação sem efeito colateral; única função com efeito é `apply_transition`.
- **GET nunca dispara LLM/custo**: dossiê e avaliação são consultas puras.
- **Append-only**: transições e decisões nunca são editadas.

## 3. Mapa de integração com módulos existentes (reuso)

| Fase/decisão | Módulo reutilizado | Como o engine usa |
|---|---|---|
| F1 modalidade | `extraction.py`, `AuctionNotice`, `Evidence` | lê modalidade + evidência (sem reclassificar via LLM aqui) |
| F2 documentos | `Document*`, `rag/` | verifica presença/versão de edital/matrícula |
| F3 jurídico/registral | `juridical_overview`, `legal_correlation`, `DueDiligenceFront`, `Legal*` | lê pendências/correlação/hard stops jurídicos |
| F4 fiscal/condominial | `Debt`, `DueDiligenceFront(PREFEITURA)`, `build_finance` | lê débitos/responsabilidade |
| F5 localização | `PropertyLocation`, `geocoding_client` | lê coords confirmadas/pendência |
| F6 ocupação | `OccupancyAnalysis`, `PostAuction*`, `Legal*` | lê classificação/estratégia |
| F7 financeiro | `build_finance`/`FinancialAnalysis` | lê preço máximo definitivo vs provisório |
| F8 comitê | `Risk`, `Verdict`, checklist | monta hard stops + score por dimensão; exige decisão humana |
| F9 lance | `Auction`, `PostAuctionCost` | registra resultado (novo endpoint mínimo) |
| F10–F12 | `PostAuction*`, `PropertyRegistration`, `MarketComparable` | lê etapas/registro/saída |
| transições/eventos | `DomainEvent`, `EntityHistory`, `ImpactAnalyzer` | registra transição + reabre por evento |
| checklist (gates) | `checklist.py` (27 keys), `ChecklistExecution/Result` | lê estados para decidir `phase_state` |
| Central Jurídica | `legal_service.py` | fornece base legal de hard stops/orientações |

**Nenhum** desses módulos é alterado em comportamento; o engine os consome via serviços de leitura.

## 4. Componentes a criar (nomes propostos)
- `backend/app/workflow_rules.py` — ruleset declarativo v1 (fases, gates, hard stops,
  transições válidas) + `WORKFLOW_RULESET_VERSION`. Análogo a `checklist.py`/`legal_catalog.py`.
- `backend/app/workflow_engine.py` — funções puras: `evaluate_phase`, `can_transition`,
  `build_opportunity_context` (agrega domínios), `compute_hard_stops`, `compute_dimension_score`.
- `backend/app/workflow_service.py` — efeitos: `create_opportunity`, `apply_transition`
  (valida via engine + grava `WorkflowTransition` + `DomainEvent`), `invalidate_on_event`,
  `opportunity_dossier` (projeção read-only).
- `backend/app/routers/workflow.py` — endpoints (ver §6).
- `models.py` — `Opportunity`, `OpportunityWorkflow`, `WorkflowTransition` (ao final) + colunas
  `opportunity_id` nullable (MODEL-DATA §2).
- Migrations `0018`–`0020` (e `0021` de dados, separada).
- Frontend: `services/workflow.ts`, `pages/WorkflowSection.tsx`/dashboard (épico L detalha UX).

## 5. Entregas pequenas (PRs incrementais)

| PR | Entrega | Migration | Risco | Teste-chave |
|---|---|---|---|---|
| **B1.1** | Modelos `Opportunity` + `OpportunityWorkflow` + `WorkflowTransition` (sem colunas aditivas ainda) | `0018`+`0019` | baixo | upgrade/downgrade; criar oportunidade |
| **B1.2** | `workflow_rules.py` v1 + `workflow_engine.py` (puro): `evaluate_phase`/`can_transition`/`compute_hard_stops` | — | baixo | unitário determinístico (sem DB) |
| **B1.3** | `workflow_service.py`: `create_opportunity` + `apply_transition` (append-only) + `DomainEvent` | — | médio | transição válida/ bloqueada; imutabilidade |
| **B1.4** | Colunas `opportunity_id` NULLABLE nas tabelas da MODEL-DATA §2 | `0020` | médio | nullable; legado=NULL; 633 intacto |
| **B1.5** | `build_opportunity_context` + gates de leitura F0–F8 (reuso dos domínios) | — | médio | gate lê checklist/risk/dd/finance corretamente |
| **B1.6** | Hard stops + bloqueio de aprovação F8 (ADR-004) + score por dimensão (v1) | — | alto | aprovar com hard stop = proibido |
| **B1.7** | `invalidate_on_event` (reabertura por `EDITAL_ATUALIZADO`/`MATRICULA_*`/`PRECO_*`/…) | — | médio | evento invalida aprovação; reabre fase |
| **B1.8** | Router `workflow.py` + `opportunity_dossier` (GET puro, sem LLM) | — | médio | GET não dispara LLM; dossiê consolida |
| **B1.9** | Frontend: dashboard de oportunidades + linha do tempo + próxima ação | — | médio | Vitest dos componentes |
| **B1.10** | (Opcional, aprovação explícita) Backfill legado | `0021` | alto | idempotência; 633 ganha 1 oportunidade legada; V1–V9 inalteradas |

> B1.1–B1.8 entregam a fundação **sem** mexer no 633 (tudo nullable/legado). B1.10 (backfill) é
> **opcional** e só roda com `pg_dump` + aprovação.

## 6. Endpoints propostos (novos; não alteram os existentes)
- `POST /api/imoveis/{id}/oportunidades` — cria oportunidade (F0).
- `GET /api/imoveis/{id}/oportunidades` — lista oportunidades do imóvel.
- `GET /api/oportunidades/{oid}` — detalhe + estado do workflow.
- `GET /api/oportunidades/{oid}/dossie` — dossiê consolidado (read-only, sem LLM).
- `POST /api/oportunidades/{oid}/transicao` — aplica transição (valida gates/hard stops).
- `POST /api/oportunidades/{oid}/decisao` — decisão de comitê (F8) humana versionada.
- `POST /api/oportunidades/{oid}/descartar` — descarte com justificativa.
- `GET /api/oportunidades/{oid}/transicoes` — trilha imutável.
- `GET /api/workflow/dashboard` — oportunidades em andamento + bloqueios + próximas ações.

## 7. Compatibilidade / preservação
- Rotas atuais por `property_id` continuam funcionando (operam na oportunidade legada quando
  `opportunity_id IS NULL`).
- Serviços de leitura ganham parâmetro `opportunity_id` **opcional** (assinatura atual preservada).
- Sem backfill, 633 tem 1 oportunidade legada implícita com V1–V9; nada muda.

## 8. Testes (resumo; detalhe no TODO-WORKFLOW-FOUNDATION)
Transições (todas), bloqueio por hard stop, reabertura, invalidação por edital/matrícula/preço,
idempotência/concorrência de `apply_transition`, imutabilidade de transição, múltiplas
oportunidades por imóvel, GET não dispara LLM, preservação do 633/V1–V9, contrato das rotas
atuais (herdado do M0).

## 9. Riscos e mitigações
| Risco | Mitigação |
|---|---|
| Engine recalcular regra de domínio (divergir da verdade) | engine só **lê** serviços existentes; testes comparam com os domínios |
| Hard stop escondido por score | ADR-004: trilha binária separada; teste proíbe aprovação com hard stop |
| Concorrência em `apply_transition` | validar `can_transition` dentro da transação; transição é append-only; teste de idempotência |
| Backfill corromper histórico | `0021` idempotente + reversível + `pg_dump`; opcional; não altera conteúdo de V1–V9 |
| Acoplar workflow ao monólito | entra como router isolado (depende de M0) |

## 10. Definição de pronto (B1 fundação)
- Criar oportunidade, avançar/bloquear/reabrir/descartar com trilha imutável.
- Hard stop jurídico crítico impede aprovação mesmo com financeiro alto (teste explícito).
- Dossiê consolidado read-only sem disparar LLM.
- 633/V1–V9/`llm_runs`/27 `canonical_key` intactos; migrations reversíveis testadas.
