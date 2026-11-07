# TODO — Fundação do Workflow (M0 + B1)

> Backlog acionável desta fundação. **Planejamento; nada implementado.** Cada item só começa
> após aprovação. Preservar 633/V1–V9/`llm_runs`/27 `canonical_key`. Sem LLM/consulta externa
> nesta fundação. Referências: `PLAN-M0-API-MODULARIZATION.md`, `PLAN-B1-WORKFLOW-ENGINE.md`.

## P0 — M0 (modularização, sem mudança de contrato)
- [ ] M0.1 — `routers/` + `deps.py`; baseline `openapi.json`; `test_openapi_contract.py`; mover `health` e `hubs`.
- [ ] M0.2..n — mover um domínio por PR (ordem: market, costs_debts, occupancy, evidence, auctioneers, documents, registration, notices, legal_processes, checklist, financial, analysis, due_diligence, post_auction, legal_central).
- [ ] M0.final — mover `properties`; `main.py` vira bootstrap + `include_router`.
- [ ] Diff de contrato verde a cada PR; suíte existente sem regressão.

## P0 — Integridade e preservação
- [ ] Toda migration `0018`–`0020` aditiva; `upgrade` **e** `downgrade` testados em banco descartável.
- [ ] `opportunity_id` sempre NULLABLE; `NULL` = oportunidade legada; `cascade` de `Property` intacto.
- [ ] `pg_dump` obrigatório antes do backfill `0021` (opcional, só com aprovação).
- [ ] Teste de não regressão: 633 mantém V1–V9, `llm_runs` e 27 `canonical_key`.
- [ ] GET/CRUD/dossiê **não** disparam LLM, nova versão analítica ou custo externo.

## P1 — Domínio de Oportunidade (B1.1, B1.4)
- [ ] `Opportunity` (property_id NOT NULL, modality, status, is_legacy, …).
- [ ] `OpportunityWorkflow` 1:1 (current_phase, phase_states, active_hard_stops, ruleset_version, blocked).
- [ ] `WorkflowTransition` append-only (from/to_phase, type, result, hard_stops, gate/score snapshot, decision, justification, actor, ruleset_version, cause_event_id).
- [ ] Colunas `opportunity_id` NULLABLE nas tabelas da MODEL-DATA §2.
- [ ] Decisão registrada: **não** criar `WorkflowGateResult` (redundante).

## P1 — Engine de workflow (B1.2, B1.5, B1.6, B1.7)
- [ ] `workflow_rules.py` v1 (fases F0–F13, transições válidas, gates obrigatórios/condicionais, hard stops) + `WORKFLOW_RULESET_VERSION`.
- [ ] `workflow_engine.py` puro: `build_opportunity_context`, `evaluate_phase`, `can_transition`, `compute_hard_stops`, `compute_dimension_score`.
- [ ] Gates de leitura reusando: checklist (27 keys), `juridical_overview`, `due_diligence_overview`, `build_finance`, `legal_correlation`, `OccupancyAnalysis`, `PostAuction*`.
- [ ] Hard stops (lista v1) derivados de `Risk`/`ChecklistResult`/DD; **bloqueio de aprovação F8 com hard stop ativo**.
- [ ] Score por dimensão v1 (jurídico/documental/físico/ocupação/fiscal/mercado/financeiro/liquidez/execução) — **separado** do hard stop.
- [ ] `invalidate_on_event` para `EDITAL_ATUALIZADO`/`MATRICULA_*`/`PRECO_*`/`PROCESSO_VINCULADO`/`OCUPACAO_ATUALIZADA`/`DIVIDA_ADICIONADA`.

## P1 — Serviço e API (B1.3, B1.8)
- [ ] `workflow_service.py`: `create_opportunity`, `apply_transition` (valida via engine, grava transição + `DomainEvent`), `invalidate_on_event`, `opportunity_dossier`.
- [ ] Router `workflow.py` (endpoints do PLAN-B1 §6).
- [ ] Serviços de leitura existentes ganham `opportunity_id` **opcional** (assinatura atual preservada).

## P2 — UX / Interface (detalhe fino no épico L)
- [ ] **Dashboard de oportunidades**: lista com imóvel, modalidade, fase atual, status, bloqueio, próxima ação.
- [ ] **Linha do tempo das fases** (F0–F13) com estado por fase e marcos (transições).
- [ ] **Indicador de progresso** (quantas fases concluídas / bloqueios).
- [ ] **Pendências prioritárias** por oportunidade (o que falta para avançar).
- [ ] **Bloqueios explicados**: por que está parado (hard stop + evidência que o originou).
- [ ] **Próxima ação recomendada** (vem de `evaluate_phase`).
- [ ] **Histórico de decisões** (trilha imutável de `WorkflowTransition`).
- [ ] **Dossiê consolidado** read-only por oportunidade.
- [ ] A UI deixa claro **por que o imóvel está parado** e **o que precisa acontecer para avançar**.
- [ ] Reuso do UI kit (`components/ui`) e padrão das `*Section.tsx`; aba "Workflow/Oportunidades" no dossiê.

## P0 — Testes (ver PLAN-B1 §8)
- [ ] Todas as transições permitidas/negadas.
- [ ] Bloqueios e hard stops (incl. **financeiro alto + hard stop jurídico = bloqueado**).
- [ ] Reabertura de fases; mudança de edital/matrícula/preço invalida aprovação.
- [ ] Concorrência e idempotência de `apply_transition`.
- [ ] Imutabilidade de `WorkflowTransition` (sem UPDATE/DELETE).
- [ ] Múltiplas oportunidades para um mesmo imóvel (históricos não se misturam).
- [ ] Compatibilidade das rotas atuais (contrato OpenAPI — herdado do M0).
- [ ] Migrations upgrade/downgrade; preservação do 633/V1–V9/`llm_runs`.

## Gates de aprovação (não pular)
- [ ] Aprovação do usuário destes documentos antes de qualquer código.
- [ ] Aprovação explícita **adicional** antes do backfill de dados `0021`.
