# SPEC — Estratégia de Invalidação

> **Status:** PROPOSTO (revisão documental; **nada implementado**). Expande
> `SPEC-WORKFLOW-ENGINE.md §7`. Preserva 633/V1–V9/`financial_analyses` V1–V9/`llm_runs`/27
> `canonical_key`/Central Jurídica. **Nenhuma análise LLM é disparada automaticamente.**

## 1. Princípio

Quando um **fato material** muda — edital, matrícula, preço ou um documento relevante — as
avaliações afetadas deixam de ser confiáveis. A estratégia é **invalidar sem apagar**:
- **preservar** o histórico e as decisões anteriores (append-only);
- **marcar** o que ficou obsoleto, com **motivo, evidência e necessidade de reavaliação**;
- **nunca** reanalisar automaticamente via LLM — a reanálise é **ação humana explícita**.

> Regra inegociável reafirmada: GET/CRUD/evento **não** disparam LLM, nova versão analítica nem
> custo externo. A invalidação **apenas marca estado**.

## 2. O que "invalidar" significa (e o que NÃO significa)

| Invalidar É | Invalidar NÃO é |
|---|---|
| marcar uma fase/decisão como `APROVACAO_INVALIDADA`/`REABERTA` | apagar análise, veredito ou decisão |
| registrar motivo + evidência + evento causador | sobrescrever o veredito histórico |
| exigir **nova** decisão/reavaliação humana | recalcular sozinho (sem pedido) |
| preservar a decisão anterior como registro imutável | gerar V(n+1) automaticamente |

## 3. Eventos invalidadores (gatilhos)

Reusa `DomainEvent` (já existente). Cada evento tem um **conjunto de fases afetadas**:

| Evento (`event_type`) | Origem | Fases invalidadas | Severidade padrão |
|---|---|---|---|
| `EDITAL_ATUALIZADO` / `EDITAL_EXTRAIDO` (nova versão) | novo edital/retificação | F1, F2, F3, F7, F8 | ALTA |
| `MATRICULA_ATUALIZADA` / `MATRICULA_EXTRAIDA` | nova matrícula/averbação | F3, F8 | ALTA |
| `PRECO_ALTERADO` / `LEILAO_ATUALIZADO` | mudança de valor/data | F7, F8 | ALTA |
| `DOCUMENTO_VERSAO_ADICIONADA` (doc relevante: edital/matrícula/contrato) | nova versão de documento | F2, F3, F7, F8 | MEDIA/ALTA |
| `PROCESSO_VINCULADO` / `CONSULTA_JUDICIAL_REALIZADA` (correlação ALTA) | achado judicial | F3, F8 | ALTA |
| `OCUPACAO_ATUALIZADA` | mudança de ocupação | F6, F7, F8 | MEDIA |
| `DIVIDA_ADICIONADA` / `CUSTO_ADICIONADO` | novo débito/custo | F4, F7, F8 | MEDIA |

> "Documento relevante" é definido por tipo (edital, matrícula, contrato/título,
> notificações). Documentos não relevantes (ex.: foto adicional) não invalidam avaliação
> jurídica/financeira — no máximo registram atualização documental.

## 4. Fluxo de invalidação (determinístico, sem LLM)

```
evento material (DomainEvent)                     ← já gerado pelos fluxos atuais
        │
        ▼
ImpactAnalyzer.analyze(evento)                    ← REUSO: mapeia evento → domínios/fases afetados
        │  (puro, sem efeito, sem LLM)
        ▼
workflow_service.invalidate_on_event(opp, evento) ← marca fases afetadas
        │
        ├── para cada fase afetada: phase_state → REABERTA
        ├── se a fase tinha aprovação: registra APROVACAO_INVALIDADA (nova WorkflowTransition)
        ├── grava InvalidationRecord (motivo, evidência, evento causador, fases, ruleset_version)
        └── NÃO recalcula; NÃO chama LLM; NÃO cria Analysis nova
        │
        ▼
UI mostra: "reavaliação necessária em F3/F8 — motivo: edital atualizado (doc v3) — [Reavaliar]"
        │
        ▼
usuário decide reavaliar  → aí sim a reanálise (já existente) roda sob ação explícita
```

## 5. O que é preservado (append-only)

- **Decisão anterior:** a `WorkflowTransition` de `DECISAO`/`APROVADA` original permanece
  imutável. A invalidação é uma **nova** transição (`APROVACAO_INVALIDADA`) que aponta
  `cause_event_id`.
- **Veredito/Análise históricos:** inalterados. A V8/V9 do 633 continuam como estão; invalidação
  nunca reescreve conteúdo de análise.
- **Trilha:** `InvalidationRecord` + `WorkflowTransition` + `DomainEvent` contam a história
  completa ("aprovado em X; invalidado em Y por causa de Z; reavaliado em W").

## 6. Entidade de registro de invalidação (especificação)

> Avaliar no MODEL-DATA se vira tabela própria `invalidation_records` **ou** se é representada
> como um tipo de `WorkflowTransition` (`transition_type=APROVACAO_INVALIDADA`) com
> `cause_event_id` + `justification` + `gate_snapshot`. **Recomendação: reusar
> `WorkflowTransition`** (evita tabela redundante; já tem `cause_event_id`, `justification`,
> `actor`, `ruleset_version`). Campos necessários já previstos no MODEL-DATA.

Campos lógicos da invalidação (onde quer que sejam persistidos):
- `opportunity_id`, `fases_afetadas[]`, `event_type`, `cause_event_id`.
- `motivo` (texto legível: "edital atualizado para v3").
- `evidencia` (referência: `document_version_id`/`evidence_id`/`process_id`).
- `severidade` (MEDIA/ALTA), `exige_reavaliacao` (bool), `status` (ABERTA/RESOLVIDA).
- `actor`, `ruleset_version`, `created_at` (imutável).

## 7. Resolução da invalidação

- Uma invalidação é **resolvida** quando o usuário (a) reavalia a(s) fase(s) afetada(s) e toma
  nova decisão, ou (b) marca explicitamente que a mudança não afeta a avaliação (com
  justificativa). Em ambos os casos, nova `WorkflowTransition` registra o desfecho.
- Enquanto `ABERTA`, a oportunidade **não** pode avançar além da fase afetada (gate bloqueia),
  e o comitê **não** pode reconfirmar aprovação sem nova decisão.

## 8. Idempotência e concorrência

- `invalidate_on_event` é **idempotente por evento**: o mesmo `DomainEvent` não gera duas
  invalidações para a mesma fase (chave lógica `(opportunity_id, cause_event_id, fase)`).
- Concorrência: a marcação roda dentro da transação do evento; transições são append-only, então
  não há *lost update* (a última marca é um novo registro, não uma edição).

## 9. Casos de teste CONCEITUAIS (implementar no B1.7; aqui só especificados)

| Caso | Arrange | Act | Assert |
|---|---|---|---|
| T-INV-1 | Opp aprovada em F8 | `EDITAL_ATUALIZADO` | F8 vira `APROVACAO_INVALIDADA`; decisão original preservada; `InvalidationRecord` com motivo+evidência |
| T-INV-2 | Opp em F3 CONCLUIDA | `MATRICULA_ATUALIZADA` | F3 e F8 → REABERTA; histórico intacto |
| T-INV-3 | mesmo evento chega 2× | 2 chamadas | 1 só invalidação por fase (idempotência) |
| T-INV-4 | invalidação ABERTA | tentar avançar fase | bloqueado até resolver |
| T-INV-5 | — | qualquer invalidação | **nenhuma** chamada LLM / **nenhuma** Analysis criada |
| T-INV-6 | doc irrelevante (foto) | `DOCUMENTO_VERSAO_ADICIONADA` não-relevante | não invalida avaliação jurídica/financeira |
| T-INV-7 | preservação real | fixture espelho do 633 | invalidar não altera V8/V9/`financial_analyses` V1–V9 |

## 10. Conformidade

- ✅ Especificação; nada implementado; nenhum LLM; nenhum dado tocado.
- ✅ Invalidação **preserva** histórico/decisões; apenas marca estado e exige reavaliação.
- ✅ Reusa `DomainEvent`/`ImpactAnalyzer`/`WorkflowTransition` (sem tabela redundante).
