# MODEL-DATA — Workflow & Oportunidade (modelagem de dados)

> **Status:** PROPOSTO (especificação; **nenhuma migration/modelo criado**). Preserva
> 633/V1–V9/`llm_runs`. Base: `ADR-WORKFLOW-ARCHITECTURE.md`, `SPEC-OPPORTUNITY-DOMAIN.md`,
> `SPEC-WORKFLOW-ENGINE.md`. Head atual de migration: `0017_central_juridica`.
>
> Princípio (prompt §5/§7): **não criar tabela redundante; justificar cada entidade; migrations
> aditivas e reversíveis; auditoria e versionamento.**

## 1. Entidades novas (todas justificadas)

### 1.1 `Opportunity` → `opportunities`
**Por que existe:** não há no modelo atual nenhuma entidade que represente "uma oferta de
aquisição específica" — tudo pendura em `Property`. Sem ela, é impossível ter duas oportunidades
do mesmo imóvel sem misturar histórico (requisito explícito). Nenhuma tabela existente cumpre
esse papel (`Auction` é a *oferta concreta/edital*, não o *caso de investimento* que agrega
análise+workflow+decisão).

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | PK int | |
| `property_id` | FK `properties.id`, **NOT NULL**, index | toda oportunidade é de um imóvel |
| `codigo` | String(120) | rótulo legível |
| `modality` | String(40), default `INDEFINIDO`, index | F1 |
| `modality_evidence_id` | FK `evidences.id`, NULL | evidência da modalidade |
| `origin` / `portal` / `external_id` | String | origem da oferta |
| `status` | String(30), default `EM_PROSPECCAO`, index | §4 da SPEC-OPPORTUNITY |
| `is_legacy` | bool, default `false`, index | oportunidade de backfill (passado) |
| `opened_at` / `closed_at` | DateTime, NULL | |
| `close_reason` | String(240), NULL | motivo de descarte/encerramento |
| `actor` | String(120), default `sistema` | autoria (pré-RBAC) |
| `created_at`/`updated_at` | DateTime | TimestampMixin |

Índices: `(property_id)`, `(property_id, status)`, `(modality)`, `(is_legacy)`.

### 1.2 `OpportunityWorkflow` → `opportunity_workflows`
**Por que existe:** guarda o **estado vivo** do workflow de uma oportunidade (fase corrente e
estado por fase). Separada de `Opportunity` porque tem ciclo de atualização próprio e porque
mantém o snapshot de fases como estrutura evolutiva. 1:1 com `Opportunity`.

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | PK int | |
| `opportunity_id` | FK `opportunities.id`, **NOT NULL**, **UNIQUE** | 1:1 |
| `current_phase` | String(40), default `F0_INTAKE`, index | |
| `phase_states` | JSON, default `{}` | mapa `fase -> phase_state` (+ pendências/ressalvas) |
| `active_hard_stops` | JSON, default `[]` | códigos de hard stop ativos (derivados; cache de leitura) |
| `ruleset_version` | String(40) | versão de regra corrente |
| `blocked` | bool, default `false`, index | atalho para "há hard stop ativo" |
| `updated_by` | String(120), default `sistema` | |
| `created_at`/`updated_at` | DateTime | |

> `active_hard_stops`/`phase_states` são **projeção/cache** recalculável a partir dos domínios;
> a **verdade** permanece nos domínios (checklist/risk/dd). Guardar aqui evita recomputar a cada
> render e dá um ponto único para a UI. Nunca é a fonte autoritativa de risco.

### 1.3 `WorkflowTransition` → `workflow_transitions`
**Por que existe:** trilha **imutável append-only** de cada mudança de fase/estado/decisão.
Embora exista `EntityHistory`, ele é genérico (before/after de qualquer entidade); a transição
de workflow tem semântica própria (fase origem/destino, gates, hard stops avaliados, decisão) e
merece entidade dedicada para consulta/auditoria eficiente. Complementa, não duplica,
`EntityHistory`.

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | PK int | |
| `opportunity_id` | FK `opportunities.id`, NOT NULL, index | |
| `from_phase` | String(40), NULL | NULL na criação |
| `to_phase` | String(40) | |
| `transition_type` | String(30), index | AVANCO/RETROCESSO/REABERTURA/DESCARTE/ENCERRAMENTO/PERDA/DECISAO |
| `result` | String(30) | PERMITIDA/BLOQUEADA |
| `phase_state` | String(30) | estado resultante |
| `hard_stops` | JSON, default `[]` | hard stops avaliados no momento |
| `gate_snapshot` | JSON, default `{}` | gates obrigatórios/condicionais e status |
| `score_snapshot` | JSON, default `{}` | score por dimensão (quando aplicável, F8) |
| `decision` | String(30), NULL | APROVADA/REPROVADA/ADIADA (F8) |
| `justification` | Text, NULL | obrigatória em DESCARTE/RETROCESSO/DECISAO |
| `actor` | String(120), default `sistema` | |
| `ruleset_version` | String(40) | regra aplicada |
| `cause_event_id` | FK `domain_events.id`, NULL | evento que causou (reabertura/invalidação) |
| `created_at` | DateTime | imutável |

Índices: `(opportunity_id, id)`, `(opportunity_id, to_phase)`, `(transition_type)`.
**Sem UPDATE/DELETE** por política (append-only) — garantido no serviço + teste.

### 1.4 (Decisão aberta) `WorkflowGateResult` — **provavelmente desnecessária**
Avaliamos uma tabela separada para resultado de gate. **Recomendação: NÃO criar** — o
`gate_snapshot`/`score_snapshot` em `WorkflowTransition` e o `phase_states` em
`OpportunityWorkflow` já cobrem. Criar outra tabela seria **redundante** (viola o princípio).
Registrar como decisão explícita no MODEL-DATA para evitar reintroduzi-la.

## 2. Tabelas existentes reutilizadas

| Tabela | Como é usada pelo workflow | Alteração necessária |
|---|---|---|
| `properties` | imóvel-pai da oportunidade | **nenhuma** |
| `auctions` / `auction_notices` | oferta concreta/edital da oportunidade | `opportunity_id` NULL (aditivo) |
| `documents` / `document_versions` / `document_chunks` | dossiê documental | **nenhuma** (doc é do imóvel) |
| `analyses` / `verdicts` / `financial_analyses` | processo de análise | `opportunity_id` NULL (aditivo) |
| `checklist_executions` / `checklist_results` | gates de várias fases | `opportunity_id` NULL (aditivo em execution) |
| `risks` | hard stops e score | `opportunity_id` NULL (aditivo) |
| `due_diligence_fronts` / `property_locations` | gates F3/F4/F5 | `opportunity_id` NULL (aditivo em fronts) |
| `post_auctions` + filhas | fases F10–F12 | `opportunity_id` NULL (aditivo em post_auctions) |
| `legal_sources/provisions/rules/...` | Central Jurídica (hard stops, orientações) | **nenhuma** (catálogo global) |
| `domain_events` / `entity_history` | eventos/trilha | **nenhuma** (reuso direto) |
| `llm_runs` / `llm_pricing` | custo/observabilidade | **nenhuma** |
| `knowledge_items` | RAG / biblioteca legal | **nenhuma** |

### Coluna aditiva `opportunity_id` (NULLABLE) — onde e por quê
Adicionada **somente** nas tabelas que representam trabalho **específico de uma oportunidade**
(não do imóvel): `auctions`, `auction_notices`, `analyses`, `verdicts`, `financial_analyses`,
`checklist_executions`, `risks`, `due_diligence_fronts`, `post_auctions`. **Sempre NULLABLE,
sem default obrigatório, sem alterar `cascade`.** `NULL` = oportunidade legada implícita.

> `documents` **não** recebe `opportunity_id` por padrão (documento é do imóvel, compartilhável).
> Se no futuro um documento for claramente de uma oferta específica, isso é decisão fina
> posterior — não entra em B1.

## 3. Diagrama de relacionamentos (cardinalidades)

```
properties (1) ──< (N) opportunities (1) ──1:1── opportunity_workflows
                          │                              │
                          │                              └──< (N) workflow_transitions
                          │
      (aditivo opportunity_id NULLABLE em:)
                          ├──< auctions / auction_notices
                          ├──< analyses / verdicts / financial_analyses
                          ├──< checklist_executions
                          ├──< risks
                          ├──< due_diligence_fronts
                          └──< post_auctions

domain_events / entity_history  ← reuso (workflow_transitions.cause_event_id → domain_events.id)
```

## 4. Estratégia de migrations (aditivas, reversíveis)

Cadeia a partir do head `0017_central_juridica`. **Uma responsabilidade por migration:**

| Migration | Conteúdo | upgrade | downgrade |
|---|---|---|---|
| `0018_opportunity` | cria `opportunities` | `create_table` | `drop_table` |
| `0019_opportunity_workflow` | cria `opportunity_workflows` + `workflow_transitions` | `create_table` ×2 | `drop_table` ×2 (reverso) |
| `0020_opportunity_fk_backfill_cols` | adiciona `opportunity_id` **NULLABLE** nas tabelas da §2 | `add_column` (nullable) | `drop_column` |
| `0021_opportunity_legacy_backfill` | **migration de DADOS** opcional: cria 1 `Opportunity(is_legacy=true)` por `Property` e seta `opportunity_id` dos registros atuais | `INSERT` + `UPDATE ... WHERE opportunity_id IS NULL` idempotente | `UPDATE opportunity_id=NULL` + `DELETE` das legadas criadas |

Regras:
- `0018`–`0020` são **puramente estruturais e aditivas** (nenhum dado tocado; colunas nullable).
- `0021` é a **única** que toca dados; é **idempotente** (só preenche onde `NULL`), reversível e
  **não** altera V1–V9 em conteúdo — apenas associa `opportunity_id`. Mesmo assim, **roda só com
  aprovação + `pg_dump` prévio** (ver §6). Pode ser adiada: o sistema funciona com `NULL`=legado.
- **Proibido** (prompt §11): `down -v`, `reset`, `truncate`, `drop` de tabela com dados, seed
  destrutivo. Cada migration testada em `upgrade` **e** `downgrade` em banco descartável.

## 5. Chaves, índices e integridade

- FKs com `ON DELETE` **sem cascade destrutivo** para o passado: `opportunity_id` nullable não
  participa do `cascade all, delete-orphan` de `Property` (é coluna aditiva, não relationship
  com cascade). Apagar uma `Opportunity` **não** apaga análises legadas (elas têm
  `opportunity_id` próprio ou `NULL`).
- Índices de leitura para a UI: `opportunities(property_id, status)`,
  `workflow_transitions(opportunity_id, id)`, `opportunity_workflows(current_phase)`,
  `opportunity_workflows(blocked)`.
- `opportunity_workflows.opportunity_id` **UNIQUE** (1:1).
- `workflow_transitions` sem índice único de "última" — a ordem é por `id` crescente
  (append-only), última = maior `id` por `opportunity_id`.

## 6. Auditoria, versionamento e rollback

- **Auditoria:** cada transição é imutável e guarda `actor`, `ruleset_version`, `gate_snapshot`,
  `hard_stops`, `cause_event_id`. Decisões de comitê guardam snapshot dos dados avaliados.
- **Versionamento de regra:** `ruleset_version` em workflow e transições (ADR-006).
- **Rollback de schema:** cada migration tem `downgrade` testado; `0018`–`0020` revertem sem
  perda (tabelas/colunas novas). `0021` reverte setando `opportunity_id=NULL` e removendo as
  legadas criadas.
- **Rollback de dados:** `pg_dump` obrigatório antes de `0021`. Nenhuma operação destrutiva.
- **Preservação do 633:** sem `0021`, 633 permanece idêntico. Com `0021`, ganha **1 oportunidade
  legada** apontando V1–V9 — conteúdo das análises inalterado, apenas associação.

## 7. Impacto em `models.py` (quando implementar — não agora)

- Novas classes `Opportunity`, `OpportunityWorkflow`, `WorkflowTransition` ao final do arquivo
  (padrão dos módulos recentes: consultadas por FK, sem alterar os relationships com cascade de
  `Property`).
- Colunas `opportunity_id` adicionadas como `Mapped[int | None]` (nullable) nas classes da §2,
  **sem** novo `relationship` com cascade (evita mexer no grafo de deleção existente).

## 8. Checklist de "não-redundância" (autojustificativa)

- `Opportunity` ≠ `Auction`: `Auction` é a oferta/edital; `Opportunity` é o caso de investimento
  que agrega análise+workflow+decisão. **Não redundante.**
- `OpportunityWorkflow` ≠ `Opportunity`: estado vivo de fases vs identidade da oportunidade.
- `WorkflowTransition` ≠ `EntityHistory`: semântica de workflow (fase/gate/decisão) vs
  before/after genérico. Complementar.
- `WorkflowGateResult`: **descartada** por redundância (coberta por snapshots em JSON).
