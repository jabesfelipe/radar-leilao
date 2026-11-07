# SPEC — Isolamento entre Oportunidades

> **Status:** PROPOSTO (revisão documental; **nada implementado**; testes abaixo são
> **conceituais**, não executados). Complementa `SPEC-OPPORTUNITY-DOMAIN.md`. Preserva
> 633/V1–V9/`financial_analyses` V1–V9/`llm_runs`/27 `canonical_key`/Central Jurídica.

## 1. Objetivo

Garantir que **um mesmo imóvel possa ter várias oportunidades** sem que seus históricos se
misturem. Cada oportunidade mantém, **isolado**: edital/oferta, documentos referenciados,
processo de análise (versões), custos, decisões de comitê e workflow.

## 2. Invariantes de isolamento (I1–I8)

| # | Invariante | Como é garantido |
|---|---|---|
| **I1** | Toda `Opportunity` pertence a exatamente 1 `Property`. | FK `property_id` NOT NULL. |
| **I2** | Todo registro de trabalho (análise, veredito, checklist, risco, edital, due diligence, pós-arrematação) referencia no máximo 1 oportunidade. | `opportunity_id` (NULL=legado) nas 9 tabelas; nunca compartilhado entre 2 oportunidades. |
| **I3** | Numeração/escopo de análise (`version`) é **por oportunidade** (não global do imóvel). | Seleção de versão passa a considerar `(opportunity_id, version)`; legado = `(NULL, version)`. |
| **I4** | O veredito e o checklist lidos para uma oportunidade vêm **apenas** das execuções daquela oportunidade. | Serviços de leitura ganham filtro opcional por `opportunity_id`; legado mantém comportamento atual. |
| **I5** | O workflow (`OpportunityWorkflow`) e suas transições são **1:1/N com a oportunidade**, nunca com o imóvel. | `opportunity_id` NOT NULL em `opportunity_workflows`/`workflow_transitions`. |
| **I6** | Documentos do **imóvel** são compartilháveis (referenciados), mas uma oportunidade nunca "vê" análises de outra como se fossem suas. | documentos ficam no imóvel; o isolamento é no nível de análise/decisão, não do arquivo. |
| **I7** | A oportunidade **legada** (`is_legacy`/`opportunity_id IS NULL`) é imutável quanto à associação com o passado (633/V1–V9). | Backfill (opcional) só preenche onde `NULL`; nunca reatribui. |
| **I8** | Apagar/descartar uma oportunidade **não** afeta outra do mesmo imóvel nem o imóvel. | `opportunity_id` é coluna aditiva, **fora** do `cascade all, delete-orphan` de `Property`. |

## 3. Modelo mental (exemplo)

```
Imóvel 633 (COND PARQUE ARVOREDO)
 ├── Opportunity #L (legada, is_legacy=true, opportunity_id dos registros = NULL)
 │     └── Analyses V1..V9, Verdict V8/V9, FinancialAnalysis V1..V9, Checklist execs, Risks  ← INTOCADO
 │
 └── Opportunity #N (nova, ex.: "2º leilão 03/2027")   [só existe se o usuário criar]
       ├── Auction/AuctionNotice próprios (novo edital/preço/data)
       ├── Analyses V1.. (numeração própria da oportunidade #N)
       ├── Checklist execs / Risks / Verdict próprios
       ├── DueDiligenceFronts próprias
       └── OpportunityWorkflow + WorkflowTransitions próprios
```

Os dois conjuntos **nunca** se cruzam: uma consulta da oportunidade #N jamais retorna a V9 da
legada, e vice-versa.

## 4. Como o isolamento é implementado (especificação, não código)

- **Leitura:** serviços como `latest_execution`, `juridical_overview`, `due_diligence_overview`,
  `build_finance` passam a aceitar `opportunity_id` **opcional**. Internamente:
  `WHERE property_id = :pid AND opportunity_id IS NOT DISTINCT FROM :oid`
  (quando `oid` é `NULL`, casa com o legado; quando informado, isola a oportunidade).
- **Escrita:** ao criar análise/edital/checklist/risco no contexto de uma oportunidade, grava-se
  o `opportunity_id` correspondente. Sem contexto de oportunidade ⇒ `NULL` (legado) — idêntico
  ao fluxo atual.
- **Numeração de versão (I3):** `next_version(opportunity)` = max(version) **dentro da
  oportunidade** + 1. Para o legado, continua max por imóvel (preserva V1–V9→V10 se um dia for
  explicitamente pedido — fora de escopo).

## 5. Testes CONCEITUAIS de isolamento (a implementar no B1; aqui só especificados)

> Cada caso roda em PostgreSQL com fixtures sintéticas (savepoint/rollback), **sem LLM e sem
> tocar o 633**. "Conceitual" = especificado agora, implementado como `test_opportunity_isolation.py`
> na entrega correspondente (B1.5/B1.8).

| Caso | Arrange | Act | Assert |
|---|---|---|---|
| **T-ISO-1** histórico não vaza | imóvel sintético com Opp A (análise V1) e Opp B (análise V1) | listar análises de A | retorna só V1 de A; nunca V1 de B |
| **T-ISO-2** numeração por oportunidade | Opp A com V1,V2; Opp B recém-criada | criar análise em B | B recebe `version=1` (não 3) |
| **T-ISO-3** veredito isolado | A tem Verdict FAVORAVEL; B tem Verdict INCONCLUSIVO | ler veredito de B | INCONCLUSIVO (não o de A) |
| **T-ISO-4** edital isolado | A com edital X; B com edital Y (preço diferente) | ler oferta de B | preço/edital de Y |
| **T-ISO-5** due diligence isolada | frente JUDICIAL CONSULTADO em A; NAO_INICIADO em B | overview de B | JUDICIAL NAO_INICIADO |
| **T-ISO-6** descarte não propaga | A e B vivas | descartar A | B intacta; imóvel intacto |
| **T-ISO-7** legado intocado | imóvel 633 (fixture espelho, **não** o real) com registros `opportunity_id=NULL` | criar Opp nova | registros legados permanecem `NULL`; nova não os "adota" |
| **T-ISO-8** workflow isolado | A em F7; B em F1 | transição em B | só B muda; A permanece F7; trilhas separadas |
| **T-ISO-9** custo/decisão por oportunidade | decisão de comitê em A | ler decisões de B | vazio (nenhuma decisão de A aparece) |
| **T-ISO-10** preservação real (guarda) | — | rodar suíte | 633 real: V1–V9, `financial_analyses` V1–V9, `llm_runs`, 27 keys inalterados (teste de não regressão) |

## 6. Consultas de risco (armadilhas a evitar) e como o teste pega

- **Esquecer o filtro de oportunidade** numa query nova ⇒ vazamento. Mitigação: T-ISO-1/3/5/8 +
  revisão de que todo novo acesso use o helper de contexto de oportunidade.
- **`opportunity_id = NULL` com `=`** (em SQL, `NULL = NULL` é desconhecido) ⇒ usar
  `IS NOT DISTINCT FROM` ou ramo explícito para legado. Caso T-ISO-7 cobre.
- **Numeração global vazando para a nova oportunidade** ⇒ T-ISO-2.

## 7. Conformidade

- ✅ Especificação; nenhum teste executado; nenhum dado tocado.
- ✅ 633 real preservado; testes usam **fixtures sintéticas** (T-ISO-10 é guarda de não regressão).
- ✅ Isolamento é aditivo sobre o modelo atual (legado = `NULL`).
