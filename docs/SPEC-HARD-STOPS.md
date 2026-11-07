# SPEC — Modelo de Hard Stops

> **Status:** PROPOSTO (revisão documental; **nada implementado**). Expande
> `SPEC-WORKFLOW-ENGINE.md §6` e `ADR-WORKFLOW-ARCHITECTURE.md (ADR-004)`. Preserva
> 633/V1–V9/Central Jurídica. **O LLM pode sinalizar risco, mas nunca transforma hipótese em
> impedimento jurídico definitivo sem validação.**

## 1. Princípio central

Um **hard stop** é um bloqueio **binário** que impede o avanço (especialmente a aprovação no
comitê F8) **independentemente de qualquer score**. Um score financeiro alto **nunca** mascara
um hard stop. Mas — e isto é essencial — **só bloqueia o que estiver CONFIRMADO**: uma hipótese
levantada por LLM/IA é um **sinal**, não um impedimento, até ser validada por evidência/humano.

## 2. Ciclo de vida de um hard stop (estado)

```
HIPOTESE ──(curadoria/evidência)──► EM_VALIDACAO ──(validação humana)──► CONFIRMADO ──► (bloqueia)
   │                                     │                                   │
   └──(descartado)──► DESCARTADO         └──(descartado)──► DESCARTADO        └──(resolvido)──► RESOLVIDO
```

| Estado | Origem típica | Bloqueia avanço? |
|---|---|---|
| `HIPOTESE` | sinal de LLM / heurística / achado preliminar | **NÃO** (apenas alerta) |
| `EM_VALIDACAO` | em análise de evidência/curadoria | **NÃO** (alerta forte; pendência) |
| `CONFIRMADO` | evidência + validação (humana ou regra determinística) | **SIM** |
| `RESOLVIDO` | condição de resolução atendida (ex.: consolidação registrada) | NÃO (histórico) |
| `DESCARTADO` | hipótese afastada com justificativa | NÃO (histórico) |

**Invariante:** o engine só considera para **bloqueio** hard stops em estado `CONFIRMADO`.
`HIPOTESE`/`EM_VALIDACAO` aparecem como **pendência/risco a validar**, nunca como impedimento.

## 3. Anatomia de um hard stop (campos)

| Campo | Descrição |
|---|---|
| `code` | identificador estável (ex.: `RISCO_JURIDICO_CRITICO`, `USUFRUTO_NAO_EXTINTO`). |
| `regra` | enunciado da regra que o define (de `workflow_rules.py`/Central Jurídica). |
| `evidence_id` / `evidence_refs` | evidência que o sustenta (`Evidence`/`document_version`/`process`). **Obrigatória para `CONFIRMADO`.** |
| `legal_basis` | fundamentação jurídica: `LegalProvision`/`LegalRule` da Central Jurídica (quando jurídico). |
| `gravidade` | `CRITICA` / `ALTA` (hard stops são sempre bloqueantes quando CONFIRMADO; gravidade informa priorização/UX). |
| `condicao_resolucao` | o que precisa acontecer para resolver (ex.: "averbar consolidação na matrícula"). |
| `estado` | ciclo de vida da §2. |
| `origem` | `LLM` / `DETERMINISTICO` / `HUMANO` / `CENTRAL_JURIDICA`. |
| `validado_por` / `validado_em` | quem confirmou e quando (obrigatório para sair de `HIPOTESE`). |
| `responsavel` | a quem cabe resolver. |
| `historico[]` | trilha append-only de mudanças de estado (sinalizado → validando → confirmado → resolvido). |
| `fase_bloqueada` | fase onde o bloqueio incide (default F8; alguns incidem antes, ex.: F1/F3). |
| `opportunity_id` | hard stop é **da oportunidade** (isolamento). |

## 4. Papel do LLM (limite rígido)

- O LLM (agentes `LegalAgent` etc.) pode **criar um hard stop em estado `HIPOTESE`** a partir de
  um `Finding` do tipo `hipotese`/`interpretacao` — **nunca** em `CONFIRMADO`.
- A promoção `HIPOTESE → EM_VALIDACAO → CONFIRMADO` exige:
  - **evidência ancorada** (documento/página/trecho ou processo correlacionado ALTA), **e**
  - **validação determinística** (regra em `workflow_rules.py`/checklist CONFIRMADO) **ou**
    **validação humana** registrada (`validado_por`).
- Hard stops de **origem determinística** (ex.: `PRECO_ACIMA_MAXIMO` calculado por `finance.py`;
  `MODALIDADE_INDEFINIDA`) podem nascer já `CONFIRMADO` porque derivam de regra pura, não de IA.

> Isto operacionaliza a regra do usuário: *"o LLM pode sinalizar riscos, mas não deve transformar
> hipóteses em impedimentos jurídicos definitivos sem validação adequada."*

## 5. Catálogo inicial de hard stops (ruleset v1)

| Code | Fase | Origem possível | Promoção a CONFIRMADO exige | Condição de resolução |
|---|---|---|---|---|
| `RISCO_JURIDICO_CRITICO` | F3→F8 | LLM(HIPOTESE)/HUMANO | `Risk(juridico, CRITICA)` validado + evidência | risco afastado/mitigado com evidência |
| `CONSOLIDACAO_NAO_REGISTRADA` | F3 | DETERMINISTICO | checklist `CONSOLIDACAO_REGISTRADA` ≠ CONFIRMADO (AF) | averbação da consolidação comprovada |
| `INTIMACAO_MORA_AUSENTE` | F3 | DETERMINISTICO/HUMANO | checklist `INTIMACAO_PESSOAL`/`INTIMACAO_EDITAL` | prova da intimação (pessoal ou edital) |
| `MATRICULA_DIVERGENTE` | F3 | DETERMINISTICO/HUMANO | DD(MATRICULA) divergência edital×matrícula | divergência esclarecida/corrigida |
| `USUFRUTO_NAO_EXTINTO` | F3 | CENTRAL_JURIDICA/HUMANO | matrícula + certidão + ausência de cancelamento | cancelamento do usufruto na matrícula |
| `ACAO_ANULATORIA_ATIVA` | F3 | LLM(HIPOTESE)→HUMANO | `LegalProcess` correlação ALTA + natureza anulatória validada | decisão/baixa que afaste o risco |
| `PRECO_ACIMA_MAXIMO` | F8/F9 | DETERMINISTICO | `finance.py`: lance > preço máximo aprovado | lance ≤ preço máximo ou nova aprovação |
| `MODALIDADE_INDEFINIDA` | F1 | DETERMINISTICO | `Opportunity.modality = INDEFINIDO` | modalidade definida com evidência |

> A curadoria fina (por modalidade/UF) é do épico D/E. A `legal_basis` de cada hard stop
> jurídico aponta a `LegalProvision`/`LegalRule` já cadastrada na Central Jurídica (reuso).

## 6. Interação com o score por dimensão (F8)

- O comitê vê **dois blocos separados**: (1) **Hard stops** (CONFIRMADOS = bloqueio;
  HIPOTESE/EM_VALIDACAO = pendência destacada); (2) **Score por dimensão** (informativo).
- O engine **recusa** `decisao=APROVADA` enquanto houver **qualquer hard stop CONFIRMADO ABERTO**
  — por mais alto que seja o score financeiro. (ADR-004.)
- Hard stops em `HIPOTESE`/`EM_VALIDACAO` **não** bloqueiam tecnicamente, mas a UI os exibe como
  "risco a validar" e o comitê pode optar por aguardar validação (decisão humana).

## 7. Persistência (especificação; decidir no MODEL-DATA)

Duas opções, sem redundância:
- **(A) Reusar `Risk`** + colunas aditivas (`is_hard_stop`, `hard_stop_state`, `condicao_resolucao`,
  `legal_provision_id`, `validado_por`) e usar `EntityHistory`/`WorkflowTransition` para a trilha.
  **Recomendada** — `Risk` já tem categoria/severidade/evidência/`analysis_version` e é por
  oportunidade (após `opportunity_id`). Evita tabela nova.
- **(B)** Tabela dedicada `hard_stops`. Só se (A) se mostrar insuficiente; registrar como decisão.

> Recomendação: **(A)** na fundação (reuso de `Risk` + Central Jurídica + trilha existente).
> Uma tabela nova só se a modelagem de estado/validação não couber confortavelmente em `Risk`.

## 8. Casos de teste CONCEITUAIS (implementar no B1.6; aqui só especificados)

| Caso | Arrange | Act | Assert |
|---|---|---|---|
| T-HS-1 | hard stop `CONFIRMADO` + financeiro ROI alto | tentar aprovar F8 | **bloqueado** (ADR-004) |
| T-HS-2 | hard stop em `HIPOTESE` (sinal LLM) | avaliar F8 | **não** bloqueia; aparece como pendência a validar |
| T-HS-3 | promover HIPOTESE→CONFIRMADO sem evidência | validar | **recusado** (evidência obrigatória) |
| T-HS-4 | hard stop CONFIRMADO → resolver (condição atendida) | marcar RESOLVIDO | avanço liberado; trilha preservada |
| T-HS-5 | LLM tenta criar hard stop CONFIRMADO | ingestão de `Finding` | engine cria apenas `HIPOTESE` |
| T-HS-6 | `PRECO_ACIMA_MAXIMO` (determinístico) | lance > máximo | nasce CONFIRMADO; bloqueia F9 |
| T-HS-7 | trilha | sequência sinalizado→validando→confirmado→resolvido | `historico[]` append-only completo |
| T-HS-8 | isolamento | hard stop em Opp A | não afeta Opp B do mesmo imóvel |

## 9. Conformidade

- ✅ Especificação; nada implementado; nenhum LLM executado.
- ✅ LLM só gera `HIPOTESE`; bloqueio exige `CONFIRMADO` com evidência/validação.
- ✅ Reuso de `Risk` + Central Jurídica + trilha; sem tabela redundante (recomendação).
- ✅ Hard stop é por oportunidade (isolamento); nunca mascarado por score.
