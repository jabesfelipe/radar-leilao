# ACCEPTANCE CRITERIA — Fundação do Workflow (M0 + B1)

> **Status:** PROPOSTO (revisão documental; **nada implementado**). Critérios **objetivos e
> verificáveis** por etapa. Base: `SEQUENCING-M0-B1.md`, `PLAN-M0`, `PLAN-B1`,
> `SPEC-OPPORTUNITY-ISOLATION.md`, `SPEC-INVALIDATION-STRATEGY.md`, `SPEC-HARD-STOPS.md`.
> Nenhuma etapa é "pronta" sem evidência de teste (logs anexados ao PR).

## 0. Critérios TRANSVERSAIS (valem para toda etapa)

| ID | Critério | Como verificar |
|---|---|---|
| G-1 | **Preservação do 633**: V1–V9, `financial_analyses` V1–V9, `llm_runs`, 27 `canonical_key` inalterados | teste de não regressão (contagem + hashes/ids) antes/depois |
| G-2 | **Sem LLM / sem rede** na suíte | `OPENAI_API_KEY` vazio; sem chamadas externas; teste falha se houver |
| G-3 | **GET/CRUD não dispara** análise/versão/custo | teste observa que nenhum `Analysis`/`LLMRun` é criado em GET |
| G-4 | **Migrations reversíveis**: `upgrade` **e** `downgrade` em banco descartável | CI roda ambos; estado final == inicial |
| G-5 | **Contrato das rotas atuais** preservado | diff `openapi.json` × baseline = vazio (salvo adições novas intencionais) |
| G-6 | **Append-only** onde exigido (transições, decisões, invalidações, histórico de hard stop) | teste tenta UPDATE/DELETE lógico e falha/é proibido |
| G-7 | **Sem comando destrutivo / sem backfill não aprovado** | revisão do PR; `0021` só com Gate 2 |

## 1. M0 — por PR de domínio (M0.1 … M0.final)

| ID | Critério | Verificação |
|---|---|---|
| M0-A | `openapi.json` **idêntico** ao baseline (paths, métodos, `response_model`, status) | `test_openapi_contract` verde |
| M0-B | Conjunto de `route.path` do `app` inalterado (mesmo set antes/depois) | teste de smoke de montagem |
| M0-C | Testes HTTP existentes do domínio movido continuam verdes (mesmos 200/404/422) | suíte do domínio |
| M0-D | Nenhuma mudança em `models.py`, migrations ou dados | diff do PR |
| M0-E | Reversível: reverter o PR restaura `main.py` sem efeito colateral | revisão |
| M0-FINAL | `main.py` = bootstrap + `include_router` (sem rotas soltas) | inspeção + M0-A/B |

## 2. B1.1 — Modelos Opportunity/Workflow/Transition (migrations 0018/0019)

| ID | Critério | Verificação |
|---|---|---|
| B11-A | Criar `Opportunity` (property_id NOT NULL) persiste e lê corretamente | teste CRUD mínimo |
| B11-B | `OpportunityWorkflow` 1:1 (UNIQUE `opportunity_id`) — violação rejeitada | teste de constraint |
| B11-C | `WorkflowTransition` grava e **não** aceita UPDATE/DELETE pela via de serviço | teste append-only (G-6) |
| B11-D | `0018`/`0019` upgrade+downgrade limpos; sem tocar tabelas existentes | G-4 |
| B11-E | 633 intacto (nenhuma linha nova associada a ele) | G-1 |

## 3. B1.2 — Engine puro (workflow_rules + workflow_engine)

| ID | Critério | Verificação |
|---|---|---|
| B12-A | `evaluate_phase`/`can_transition`/`compute_hard_stops` são **puros** (sem DB, sem I/O) | unit test sem fixtures de DB |
| B12-B | Transições inválidas rejeitadas conforme matriz (SPEC-WORKFLOW §4.4) | unit tests por par origem→destino |
| B12-C | `WORKFLOW_RULESET_VERSION` presente e retornado na avaliação | assert de versão |
| B12-D | Hard stop `CONFIRMADO` ⇒ `can_transition(F8→F9)` = bloqueado mesmo com score alto | **T-HS-1** |
| B12-E | Hard stop `HIPOTESE` ⇒ não bloqueia | **T-HS-2** |

## 4. B1.3 — Serviço: create_opportunity + apply_transition

| ID | Critério | Verificação |
|---|---|---|
| B13-A | `apply_transition` valida via engine antes de gravar; bloqueada não persiste avanço | teste permitida/bloqueada |
| B13-B | Cada transição gera `WorkflowTransition` + `DomainEvent` | teste de efeito |
| B13-C | **Idempotência**: reenviar a mesma transição (mesma intenção/evento) não duplica | teste idempotência |
| B13-D | **Concorrência**: duas transições concorrentes não corrompem estado (append-only; última vence como novo registro) | teste de concorrência simulada |
| B13-E | Descarte exige justificativa; grava motivo | teste de validação |

## 5. B1.4 — Colunas `opportunity_id` NULLABLE (migration 0020)

| ID | Critério | Verificação |
|---|---|---|
| B14-A | Colunas criadas **nullable**, default ausente, nas 9 tabelas da matriz | inspeção de schema |
| B14-B | Registros existentes permanecem `opportunity_id IS NULL` (legado) | G-1 + contagem |
| B14-C | `cascade` de `Property` inalterado (apagar Opportunity não apaga legado) | **T-ISO-8** |
| B14-D | `0020` upgrade+downgrade (drop_column) limpo | G-4 |

## 6. B1.5 — Contexto + gates de leitura (F0–F8)

| ID | Critério | Verificação |
|---|---|---|
| B15-A | Serviços de leitura ganham `opportunity_id` **opcional**; assinatura atual preservada | teste de compat + chamada legada |
| B15-B | Gate lê o estado real dos domínios (checklist/risk/dd/finance) — não recalcula | teste compara com o domínio |
| B15-C | **Isolamento**: contexto de Opp B não traz dados de Opp A | **T-ISO-1/3/5/8** |
| B15-D | `opportunity_id IS NULL` casa com legado via `IS NOT DISTINCT FROM` | **T-ISO-7** |
| B15-E | Numeração de versão por oportunidade | **T-ISO-2** |

## 7. B1.6 — Hard stops + bloqueio F8 + score

| ID | Critério | Verificação |
|---|---|---|
| B16-A | Score alto **não** libera aprovação com hard stop CONFIRMADO | **T-HS-1** |
| B16-B | LLM só cria hard stop `HIPOTESE`; promoção a CONFIRMADO exige evidência+validação | **T-HS-3/T-HS-5** |
| B16-C | Hard stop determinístico (`PRECO_ACIMA_MAXIMO`) nasce CONFIRMADO e bloqueia | **T-HS-6** |
| B16-D | Trilha de estado do hard stop append-only | **T-HS-7** + G-6 |
| B16-E | Hard stop isolado por oportunidade | **T-HS-8** |

## 8. B1.7 — Invalidação

| ID | Critério | Verificação |
|---|---|---|
| B17-A | Evento material invalida fases afetadas sem apagar histórico | **T-INV-1/2** |
| B17-B | Decisão anterior preservada (nova transição `APROVACAO_INVALIDADA`) | **T-INV-1** + G-6 |
| B17-C | Idempotência por `(opportunity_id, cause_event_id, fase)` | **T-INV-3** |
| B17-D | Invalidação ABERTA bloqueia avanço até resolução | **T-INV-4** |
| B17-E | **Nenhum** LLM / nenhuma Analysis criada na invalidação | **T-INV-5** + G-2/G-3 |
| B17-F | Documento irrelevante não invalida avaliação jurídica/financeira | **T-INV-6** |

## 9. C1 + B1.8 — Router workflow + dossiê

| ID | Critério | Verificação |
|---|---|---|
| C1-A | Novas rotas de workflow entram **sem** alterar as existentes | G-5 (adições intencionais) |
| C1-B | `GET /oportunidades/{id}/dossie` é consulta pura (G-3) | teste observa zero LLM/Analysis |
| C1-C | Dossiê consolida imóvel+oferta+documentos+workflow+resultados por oportunidade | teste de agregação + isolamento |

## 10. B1.9 — Frontend

| ID | Critério | Verificação |
|---|---|---|
| FE-A | `tsc --noEmit` limpo; `vitest run` verde (inclui novos testes) | CI frontend |
| FE-B | Dashboard mostra fase, status, bloqueio, **próxima ação** por oportunidade | teste de componente |
| FE-C | Bloqueio exibido com **motivo + evidência** (hard stop) separado do score | teste de componente |

## 11. B1.10 — Backfill legado (OPCIONAL, Gate 2)

| ID | Critério | Verificação |
|---|---|---|
| BF-A | `pg_dump` feito e registrado antes de rodar | evidência no PR |
| BF-B | Idempotente: rodar 2× não duplica oportunidades legadas | teste idempotência |
| BF-C | Reversível: downgrade seta `opportunity_id=NULL` e remove legadas criadas | G-4 |
| BF-D | 633 ganha **1** oportunidade legada apontando V1–V9; **conteúdo** das análises inalterado | G-1 + verificação de associação |

## 12. Definição de pronto (fundação completa)
- Todos os critérios transversais (G-1..G-7) verdes em cada PR.
- Isolamento (T-ISO), invalidação (T-INV) e hard stops (T-HS) implementados e verdes.
- Contrato OpenAPI das rotas atuais idêntico (M0); novas rotas de workflow aditivas.
- 633/V1–V9/`financial_analyses` V1–V9/`llm_runs`/27 `canonical_key`/Central Jurídica intactos.
- Backfill (B1.10) **não** é requisito de "pronto" — é opcional e só com Gate 2.
