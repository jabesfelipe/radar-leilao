# Onda 2 — Modalidades + Workflow operacional + Dashboard (Relatório de entrega)

**Data:** 2026-11 • **Base:** HEAD `c5e4bfb` (Onda 11 Auth/RBAC) • **Ruleset:** `workflow-v1`, `modality-v1`

Este ciclo entregou as três frentes de forma funcional, integrada (backend ↔ frontend),
testada e validada em banco descartável, **sem nenhuma migration nova** (o domínio
Opportunity/Workflow já existia desde a migration `0018`, e `Opportunity.modality` já é
`String` com default `INDEFINIDO`). A modalidade canônica vive em **código declarativo**
(`modality_rules.py`), não em tabela — mesma filosofia de `checklist.py`/`workflow_rules.py`.

---

## 1. O que foi entregue

### Frente A — Modalidades canônicas (`modality_rules.py`)
Catálogo declarativo e versionado (`modality-v1`) com **5 modalidades canônicas**:
`EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA`, `EXTRAJUDICIAL_OUTRA_GARANTIA`, `JUDICIAL`,
`VENDA_DIRETA`, `INDEFINIDO`. `LICITACAO` ficou **fora** (decisão de escopo documentada no
plano; não cadastrada).

- **Classificação evidence-gated:** sem `evidence_id` a oportunidade **permanece
  `INDEFINIDO`** e `needs_manual_review`. A classificação é **determinística** (palavras-chave);
  o LLM nunca confirma modalidade. Confirmação exige evidência + `confirm=true`.
- **Aplicabilidade de checklist por modalidade** como metadado **aditivo**: os **27
  `canonical_key` são preservados** — a modalidade apenas marca itens como
  `APLICAVEL`/`NAO_APLICAVEL`, nunca remove uma chave. `INDEFINIDO` ⇒ 27 aplicáveis (legado).
- **Hard stops suprimidos por modalidade:** `CONSOLIDACAO_NAO_REGISTRADA` e
  `INTIMACAO_MORA_AUSENTE` só se aplicam a alienação fiduciária (suprimidos nas demais).

### Frente B — Workflow operacional (`workflow_service.py` + router)
Exposição do motor **puro** F0–F13 (`workflow_engine.py`/`workflow_rules.py`, **não
alterados**) ligando-o aos domínios reais:

- `workflow_service.py` monta o `OpportunityContext` agregando checklist/risco/financeiro/
  modalidade e **persiste transições append-only** (`WorkflowTransition`), atualizando o
  cache `OpportunityWorkflow`. **O engine continua sem I/O.**
- **Regras validadas exclusivamente no backend.** Hard stop ativo **nunca** é contornável
  pelo cliente. `WorkflowTransition` é gravada **sempre** (inclusive `BLOQUEADA`) para auditoria.
- `set_phase_state` (novo) permite concluir o **gate de saída** de uma fase (`CONCLUIDA`)
  como operação auditada — pré-requisito do `AVANCO`. Não pula hard stops: o `AVANCO`
  continua avaliado pelo engine.
- Router `/api/oportunidades`: catálogo de modalidades, CRUD/listagem com filtros
  (município/modalidade/status/fase) + paginação, estado/transições/hard-stops/pendências/
  histórico/checklist-aplicável, `POST` transição, reavaliar, `fase/estado`, classificar/
  corrigir modalidade.
- **Autorização:** leitura exige `get_current_user` (401 sem token); escrita exige usuário
  autenticado real **E** `analysis:write` (dependência `authorized_writer`). O ator real
  (`user:<id>:<email>`) alimenta a trilha de auditoria.

### Frente C — Dashboard (`routers/dashboard.py`)
`GET /api/dashboard/oportunidades` com **agregação real** no backend (por fase, modalidade,
município, status + bloqueadas + riscos críticos ativos). Cada contagem tem **fonte
identificável** (`fontes`); ausência de dado = **zero explícito** (sem números fictícios).
Leitura exige autenticação.

### Frente integração — Frontend
`services/opportunities.ts` (cliente tipado), `pages/OpportunitiesPage.tsx` (master-detail:
lista com filtros, criar, detalhe com fase/hard stops/transições/histórico, concluir fase,
corrigir modalidade), item **Oportunidades** na Sidebar + rota no `App.tsx`, e
`OpportunitiesDashboardPanel` no Dashboard Hub. Nenhuma regra de workflow é recalculada no
frontend — ele apenas consome a decisão do backend.

---

## 2. Classificação por item

| Item | Classificação | Evidência |
|---|---|---|
| Catálogo de 5 modalidades canônicas | **IMPLEMENTADO E TESTADO** | `test_modalidades.py`; `GET /api/oportunidades/modalidades` |
| Classificação evidence-gated (INDEFINIDO sem evidência) | **IMPLEMENTADO E TESTADO** | `test_modalidades.py`; `test_classificar_modalidade_remove_hard_stop` |
| Aplicabilidade de checklist por modalidade (27 keys preservadas) | **IMPLEMENTADO E TESTADO** | `test_checklist_aplicavel_por_modalidade` (27 itens; JUDICIAL ⇒ CONSOLIDACAO_REGISTRADA=NAO_APLICAVEL) |
| Motor F0–F13 exposto via serviço (engine puro intacto) | **IMPLEMENTADO E TESTADO** | `test_workflow_api.py`; `test_workflow_engine.py` (sem regressão) |
| Transição append-only + auditoria (inclusive BLOQUEADA) | **IMPLEMENTADO E TESTADO** | `test_historico_append_only` |
| Hard stop não contornável (MODALIDADE_INDEFINIDA bloqueia F1→F2) | **IMPLEMENTADO E TESTADO** | `test_hard_stop_modalidade_indefinida_bloqueia_f1_para_f2` |
| Gate de saída (`set_phase_state`) | **IMPLEMENTADO E TESTADO** | `test_avanco_valido_f0_para_f1` |
| Isolamento por oportunidade | **IMPLEMENTADO E TESTADO** | `test_isolamento_por_oportunidade` |
| Autorização backend (401/403; escrita exige analysis:write) | **IMPLEMENTADO E TESTADO** | `test_criar_oportunidade_sem_token_401`, `test_consulta_403_para_consulta_sem_escrita` |
| Dashboard agregado por fase/modalidade/município/status | **IMPLEMENTADO E TESTADO** | `test_dashboard.py` |
| Riscos críticos ativos no dashboard | **IMPLEMENTADO E TESTADO** | `test_dashboard_conta_riscos_criticos_ativos` |
| Filtros + paginação da listagem | **IMPLEMENTADO E TESTADO** | `test_listagem_filtra_por_modalidade_e_municipio`, `test_listagem_pagina_resultados` |
| Frontend Oportunidades (lista/criar/detalhe/transição/concluir fase) | **IMPLEMENTADO** (teste de UI em `OpportunitiesPage.test.tsx`) | vitest mock por URL |
| `LICITACAO` como modalidade | **NÃO IMPLEMENTADO (fora de escopo)** | decisão documentada |
| Coletor automático de modalidade a partir de portais | **NÃO IMPLEMENTADO (dependência externa)** | — |

---

## 3. Fluxos ponta-a-ponta testados

1. **Criação → triagem → bloqueio por modalidade:** criar oportunidade (INDEFINIDO) →
   concluir F0 → avançar F0→F1 (permitido) → concluir F1 → tentar F1→F2 ⇒ **BLOQUEADA** por
   `MODALIDADE_INDEFINIDA` (registrada no histórico).
2. **Classificação com evidência remove o hard stop:** classificar modalidade com
   `evidence_id` + `confirm` ⇒ `EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA`; o hard stop
   `MODALIDADE_INDEFINIDA` desaparece.
3. **Auditoria append-only:** transição permitida + transição bloqueada ⇒ **2 registros**
   imutáveis em `/historico`.
4. **Isolamento:** avanço de uma oportunidade não afeta a fase de outra.
5. **Dashboard real:** contagens por fase/modalidade/município conferem com as oportunidades
   criadas; dashboard vazio zera explicitamente.

---

## 4. Validação executada (banco descartável)

Validação em **banco descartável** (`radar_onda2_val`, criado e **dropado**) dentro do
PostgreSQL estável — o banco de desenvolvimento `radar_leilao` **nunca foi alterado**.

- **Migrations:** `upgrade head` → `downgrade 0022` → `upgrade head` ⇒ **RC=0** (reversível).
  **Nenhuma migration nova** foi necessária; a próxima livre permanece **0024**.
- **Contrato OpenAPI:** **138 paths** (+15 em relação aos 123 da Onda 11); baseline
  regenerado (`tests/contract/openapi_baseline.json`) e teste de contrato **verde**.
- **Backend:** suíte completa **745 passed / 2 skipped** (antes dos novos testes); com os
  novos testes da Onda 2, verificação dirigida **67 passed / 0 failed**
  (`test_workflow_api` + `test_dashboard` + `test_modalidades` + `test_workflow_engine` +
  `test_auth` + `contract`).
- **Bug de produção corrigido:** o router usava o retorno de `require_permission`
  (string de papel) como se fosse `User` em `_actor(user)` → `AttributeError`. Corrigido com
  a dependência `authorized_writer` (resolve o usuário real **e** valida a permissão).

### Preservação (evidência direta no `radar_leilao`)
Consultas ao banco de desenvolvimento **após** a validação:

```
llm_runs        = 45
canonical_keys  = 27
prop_633_exists = 1
```

As análises V1–V9 e históricos permanecem intactos: as rotas abertas continuam abertas, os
endpoints novos são **aditivos**, **não houve migration** nem backfill, e a validação rodou
em banco separado. Testes verdes isoladamente não comprovam integridade histórica — a
evidência acima (contagens diretas no banco dev) comprova.

---

## 5. Política do `X-Admin-Token` (compat em desativação)

Os endpoints **novos** de escrita da Onda 2 **não** aceitam `X-Admin-Token` — exigem usuário
autenticado real (JWT), porque a trilha de auditoria precisa de um ator identificável. O
`X-Admin-Token` permanece válido apenas nos endpoints administrativos legados (compat
temporária da Onda 11), em **desativação controlada**. Recomenda-se, em ciclo futuro,
migrar os consumidores restantes para JWT por papel e então remover o token de compat.

---

## 6. Fora de escopo / próximos passos

- `LICITACAO` como modalidade (decisão aberta; não cadastrada).
- Coletor automático de sinais de modalidade a partir de portais (dependência externa).
- Dashboards adicionais (SLA por fase, funil de conversão) — a fundação de agregação já está pronta.
