# MATRIZ — Tabelas que recebem `opportunity_id`

> **Status:** PROPOSTO (revisão documental; **nada implementado**). Complementa
> `MODEL-DATA-WORKFLOW.md §2`. Preserva 633/V1–V9/`financial_analyses` V1–V9/`llm_runs`/27
> `canonical_key`/Central Jurídica. Nenhuma migration/coluna criada nesta etapa.

## 1. Princípio

A coluna `opportunity_id` é **aditiva, NULLABLE, sem default obrigatório, sem alterar `cascade`**.
`NULL` = **oportunidade legada implícita** do imóvel (comportamento idêntico ao atual). Só recebe
a coluna a tabela cujo registro representa **trabalho específico de uma oferta de aquisição** —
não o que é intrínseco ao **imóvel** (ex.: `documents`, `property_registrations`,
`property_locations`, `property_sources` permanecem do imóvel) nem o que é **catálogo global**
(Central Jurídica, `knowledge_items`, `llm_pricing`).

## 2. Matriz das 9 tabelas (confirmadas no código)

| # | Tabela (`__tablename__`) | Por que recebe `opportunity_id` | Cardinalidade com Opportunity | Hoje (chave do histórico) |
|---|---|---|---|---|
| 1 | `auctions` | A **oferta concreta** (datas, lance, avaliação, comissão, `financial_assumptions`) é de uma oportunidade específica; um imóvel re-ofertado tem outro leilão. | N auctions : 1 opportunity | `property_id` |
| 2 | `auction_notices` | O **edital** (e retificações) pertence à oferta daquela oportunidade; editais de leilões distintos não se misturam. | N : 1 | `property_id` |
| 3 | `analyses` | O **processo de análise** (V1..Vn) avalia uma oportunidade; versões de oportunidades diferentes não compartilham numeração/escopo. | N : 1 | `property_id` + `version` |
| 4 | `verdicts` | O **veredito** é a conclusão de uma análise de uma oportunidade. | N : 1 | `property_id` + `analysis_version` |
| 5 | `financial_analyses` | O **snapshot financeiro** (inputs/outputs) reflete premissas/preço daquela oferta. | N : 1 | `property_id` + `analysis_version` |
| 6 | `checklist_executions` | A **execução do checklist** (27 keys) é da análise daquela oportunidade; estados valem para aquela oferta. | N : 1 | `property_id` + `analysis_version` |
| 7 | `risks` | **Riscos** (inclusive os que viram hard stop) são relativos à oportunidade avaliada. | N : 1 | `property_id` + `analysis_version` |
| 8 | `due_diligence_fronts` | As **4 frentes** (matrícula/judicial/prefeitura/localização) são investigadas por oportunidade; edital/matrícula podem mudar entre ofertas. | N : 1 (até 4 por oportunidade) | `property_id` + `frente` (unique) |
| 9 | `post_auctions` | O fluxo **pós-arrematação** nasce de uma aquisição = uma oportunidade que foi arrematada. | **1 : 1** por oportunidade | `property_id` **UNIQUE** |

> **Observação de domínio (não é do imóvel):** `documents`/`document_versions`/`document_chunks`
> são do **imóvel** (reaproveitáveis entre oportunidades); **não** recebem `opportunity_id` por
> padrão. Se no futuro um documento for claramente de uma oferta (um edital-arquivo específico),
> trata-se em decisão fina posterior, fora de B1.

## 3. Impacto por tabela (dados legados, consultas, APIs, relatórios)

### Regra transversal de compatibilidade
Toda consulta que hoje filtra por `property_id` continua válida. A evolução é **aditiva**: onde
fizer sentido, acrescenta-se um filtro **opcional** `opportunity_id`. Quando ausente ⇒
comportamento atual (todo o histórico do imóvel = oportunidade legada). **Nenhuma assinatura de
serviço/endpoint muda nesta fundação; só ganham parâmetro opcional.**

| Tabela | Dados legados | Consultas/Services | APIs/Endpoints | Relatórios/Hubs |
|---|---|---|---|---|
| `auctions` | `opportunity_id=NULL` nas ofertas atuais (633 incl.) | `current_auction(prop)` permanece; ganha overload opcional por oportunidade | `/imoveis/{id}/leilao*` inalterados | hubs por imóvel inalterados |
| `auction_notices` | editais atuais ⇒ legado | leitura por imóvel preservada | `/imoveis/{id}/edital*` inalterados | — |
| `analyses` | V1–V9 do 633 ⇒ `opportunity_id=NULL` (legado) | `latest_execution`/seleção por versão inalteradas | `/imoveis/{id}/analisar`, `/historico` inalterados | hub `/historico` por imóvel inalterado |
| `verdicts` | vereditos V1–V9 ⇒ legado | seleção determinística por `analysis_version` preservada | `/imoveis/{id}` (veredito) inalterado | hub `/veredito` inalterado |
| `financial_analyses` | **V1–V9 preservados**; `opportunity_id=NULL` | `build_finance(prop)` inalterado; overload opcional | `/imoveis/{id}/financeiro*` inalterados | hub `/financeiro` inalterado |
| `checklist_executions` | execuções atuais ⇒ legado (27 keys intactas) | `latest_execution`/`execution_for_version` inalterados | `/imoveis/{id}/checklist*` inalterados | hub `/checklist-global` inalterado |
| `risks` | riscos atuais ⇒ legado | `recalculate_risks` inalterado; filtro opcional por oportunidade | `/imoveis/{id}/juridico/riscos`, `/riscos` inalterados | hub `/riscos` inalterado |
| `due_diligence_fronts` | frentes atuais ⇒ legado | `due_diligence_overview(db, prop)` inalterado; overload opcional | `/imoveis/{id}/due-diligence*` inalterados | — |
| `post_auctions` | registro atual (se houver) ⇒ legado | `get_post_auction(property_id)` inalterado | `/imoveis/{id}/pos-arrematacao*` inalterados | — |

### Impacto específico — `post_auctions.property_id UNIQUE` (decisão a registrar)
Hoje há **1 pós-arrematação por imóvel** (`unique=True` em `property_id`). Com múltiplas
oportunidades, o correto conceitual é **1 por oportunidade**. Opções (decisão no B1, não agora):
- **(A)** manter `property_id UNIQUE` por ora (um imóvel só tem 1 pós-arrematação "vivo") e
  adicionar `opportunity_id` nullable só para rastreabilidade; **ou**
- **(B)** migrar a unicidade para `opportunity_id UNIQUE` (aditivo) quando o fluxo multi-oferta
  de aquisição for realmente exercido.
> Recomendação: **(A) na fundação** (menor risco; preserva o atual) e **(B)** só quando houver
> necessidade real de duas aquisições do mesmo imóvel — documentado como risco aberto (§5).

## 4. Tabelas que **não** recebem `opportunity_id` (e por quê)

| Tabela | Motivo |
|---|---|
| `documents`/`document_versions`/`document_chunks` | pertencem ao **imóvel**; reaproveitáveis entre oportunidades |
| `property_registrations` | matrícula é do **imóvel** |
| `property_locations` | geolocalização é do **imóvel** |
| `property_sources` | origem/links do **imóvel** |
| `costs`/`debts` | **decisão aberta (§5):** podem ser do imóvel ou da oferta; ver análise abaixo |
| `legal_sources/provisions/rules/...`, `knowledge_items`, `llm_pricing` | **catálogo global** |
| `domain_events`/`entity_history` | trilha transversal; o vínculo à oportunidade vem via `WorkflowTransition.cause_event_id` e pelo agregado afetado |
| `evidences`/`evidence_links` | ancoradas a documento/chunk do imóvel; herdam o contexto pela análise/risk que as referencia |

### Nota sobre `costs`/`debts` (decisão aberta)
`debts` (IPTU/condomínio) tende a ser do **imóvel** (persiste entre ofertas); `costs` (custos de
uma operação) tende a ser da **oportunidade**. Como o motor financeiro atual lê ambos por
`property_id` sem dupla contagem, a fundação B1 **não** adiciona `opportunity_id` a `costs`/`debts`
— fica como **decisão explícita posterior** (épico H), para não ampliar o escopo nem arriscar o
cálculo existente. Registrado como risco aberto (§5).

## 5. Riscos abertos desta matriz (dependem de decisão do usuário)

1. **`post_auctions` unicidade** — manter por imóvel (A) ou migrar para por oportunidade (B)?
   Recomendo (A) na fundação.
2. **`costs`/`debts` por oportunidade** — adicionar `opportunity_id` agora ou adiar para o épico
   financeiro (H)? Recomendo **adiar** (não mexer no motor financeiro na fundação).
3. **`documents` de oferta específica** — permanecer 100% do imóvel ou permitir marcação por
   oportunidade? Recomendo **permanecer do imóvel** na fundação.

## 6. Conformidade

- ✅ Nenhuma coluna/migration criada aqui (só especificação da matriz).
- ✅ Todos os dados atuais (incl. 633, V1–V9, `financial_analyses` V1–V9, `llm_runs`) mapeados
  como **legado (`opportunity_id=NULL`)** — zero reescrita.
- ✅ Nenhuma assinatura de serviço/endpoint alterada; apenas ganho futuro de parâmetro opcional.
- ✅ Central Jurídica e catálogos globais **não** recebem `opportunity_id`.
