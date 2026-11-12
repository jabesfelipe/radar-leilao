# SPEC — Workflow Engine (máquina de estados F0–F13)

> **Status:** PROPOSTO (especificação; nada implementado). Preserva 633/V1–V9/`llm_runs`.
> Base: `ADR-WORKFLOW-ARCHITECTURE.md`, `SPEC-OPPORTUNITY-DOMAIN.md`. Engine **determinístico e
> puro** (sem LLM, sem I/O externo), no espírito de `risk_engine.py`/`verdict_engine.py`.

## 1. Conceitos

- **Fase** (`phase`): uma das F0–F13. Posição macro da oportunidade no ciclo de vida.
- **Estado da fase** (`phase_state`): situação da fase corrente (ver §3).
- **Gate**: conjunto de condições avaliadas para permitir **sair** de uma fase. Pode ser
  **obrigatório** (bloqueia) ou **condicional** (adverte/registra pendência, mas não bloqueia).
- **Hard stop**: condição binária de **bloqueio absoluto**, independente de qualquer score.
- **Transição**: mudança de fase/estado registrada de forma **imutável** (`WorkflowTransition`).
- **Ruleset**: definição declarativa e **versionada** das regras (ADR-006).

## 2. As 14 fases

`F0 INTAKE` · `F1 TRIAGEM` · `F2 DOCUMENTOS` · `F3 JURIDICO_REGISTRAL` · `F4 FISCAL_OPERACIONAL`
· `F5 LOCALIZACAO_INSPECAO` · `F6 OCUPACAO_POSSE` · `F7 VIABILIDADE_FINANCEIRA` ·
`F8 COMITE_DECISAO` · `F9 LANCE_PAGAMENTO` · `F10 TRANSFERENCIA_REGISTRO` ·
`F11 POSSE_REGULARIZACAO` · `F12 EXPLORACAO_SAIDA` · `F13 ENCERRAMENTO`.

As fases F2–F7 são majoritariamente **paralelizáveis** (due diligence multifrente); o **gate do
comitê (F8)** é o ponto de convergência. F0→F1 e F8→F9→…→F13 são majoritariamente sequenciais.

## 3. Estados possíveis por fase (`phase_state`)

Vocabulário único aplicável a cada fase (superset dos estados de checklist, alinhado ao prompt):

| Estado | Significado |
|---|---|
| `NAO_INICIADA` | Fase ainda não começou. |
| `EM_ANDAMENTO` | Trabalho em curso. |
| `PENDENTE_EVIDENCIA` | Aguarda documento/dado para concluir. |
| `EM_REVISAO` | Aguardando revisão/validação humana. |
| `CONCLUIDA` | Requisitos atendidos; gate de saída satisfeito. |
| `CONCLUIDA_COM_RESSALVA` | Concluída com pendência condicional registrada (não hard stop). |
| `BLOQUEADA` | Hard stop ativo; não avança até resolução. |
| `NAO_APLICAVEL` | Fase não se aplica a esta modalidade/caso (exige justificativa). |
| `REABERTA` | Retornada por nova evidência/evento invalidador. |

> Estes estados são do **workflow**, não substituem os `CHECKLIST_STATES` (que continuam sendo
> a verdade do item de checklist). O workflow **lê** o checklist para decidir o `phase_state`.

## 4. Transições permitidas

### 4.1 Avanço (forward)
- Só de `Fn` para `Fn+1` (ou para uma fase paralela habilitada em F2–F7) **quando o gate de
  saída de `Fn` estiver satisfeito** e **nenhum hard stop** estiver ativo.
- F8 (comitê) só avança para F9 com **decisão humana APROVADA versionada** e **zero hard stops**.

### 4.2 Retrocesso / reabertura (backward)
- `REABERTURA`: qualquer fase pode voltar a `REABERTA`/`EM_ANDAMENTO` quando surge nova
  evidência ou um **evento invalidador** (§7). É sempre uma **nova** transição (append-only).
- `RETROCESSO` manual: exige justificativa + ator; registrado como transição.

### 4.3 Encerramento / descarte
- `DESCARTE`: a qualquer momento → status `DESCARTADA` com **motivo obrigatório**.
- `ENCERRAMENTO`: de F13 → status `ENCERRADA`.
- `PERDA`: de F9 (não arrematou) → status `PERDIDA`.

### 4.4 Matriz-resumo (origem → destinos válidos)
```
F0 → F1 | DESCARTE
F1 → F2 | DESCARTE                      (exige modality != INDEFINIDO)
F2 → F3,F4,F5,F6,F7 (paralelas) | DESCARTE
F3..F7 → (entre si) → F8 | DESCARTE | REABERTURA(Fx)
F8 → F9 (APROVADA) | DESCARTE | REABERTURA(Fx)   [BLOQUEADA se hard stop]
F9 → F10 (arrematou) | PERDA | DESCARTE
F10 → F11 | REABERTURA(F10)
F11 → F12 | REABERTURA(F11)
F12 → F13
F13 → (terminal: ENCERRADA)
Qualquer fase → REABERTA (por evento invalidador §7)
```

## 5. Gates por fase (obrigatórios e condicionais)

> Cada gate **lê** serviços/domínios existentes (reuso). "Obrigatório" bloqueia a saída;
> "condicional" gera `CONCLUIDA_COM_RESSALVA`. A lista é a **proposta inicial do ruleset v1**;
> a curadoria fina (por modalidade) é do épico D/E.

| Fase | Gate obrigatório (sai quando…) | Condicional (ressalva) | Fonte de dados (reuso) |
|---|---|---|---|
| F0 | Dados mínimos de intake presentes; não `DADOS_INSUFICIENTES` | dedupe `DUPLICADO_POTENCIAL` a revisar | `Property`/`Auction`/`PropertySource` |
| F1 | `modality` definida **com evidência** (≠ `INDEFINIDO`) | modalidade `EXTRAJUDICIAL_OUTRA_GARANTIA` exige revisão | `AuctionNotice`/`extraction` |
| F2 | Edital e matrícula presentes e versionados | OCR de baixa confiança a revisar | `Document*`/`extraction` |
| F3 | Due diligence jurídica/registral revisada; **sem hard stop jurídico** | correlação processual `MEDIA` a validar | `DueDiligenceFront(MATRICULA/JUDICIAL)`, `legal_correlation`, `juridical_overview`, `Legal*` |
| F4 | Débitos fiscais/condominiais levantados; responsabilidade por débitos definida no edital | dívida não confirmada na fonte | `Debt`, `DueDiligenceFront(PREFEITURA)`, `build_finance` |
| F5 | Localização confirmada (coords confirmadas ou registro manual) | sem vistoria interna → ressalva | `PropertyLocation`, `geocoding_client` |
| F6 | Ocupação classificada; estratégia de posse definida | locação averbada a confirmar | `OccupancyAnalysis`, `PostAuction*`, `Legal*` (art. 37-A/8.245) |
| F7 | Financeiro calculado com preço máximo **definitivo** (sem custos desconhecidos) | `preco_maximo` provisório → ressalva | `build_finance`/`FinancialAnalysis` |
| F8 | **Decisão humana versionada** + **zero hard stops** | score baixo em dimensão não crítica | `Risk`/`Verdict` + score por dimensão (novo) |
| F9 | Resultado do leilão registrado (arrematou/perdeu) | — | (novo F9; reusa `Auction`/`PostAuctionCost`) |
| F10 | Registro/averbação evidenciados; titularidade conferida | prenotação pendente | `PostAuction*`, `PropertyRegistration` |
| F11 | Posse + regularização/obras com aceite | ART/RRT pendente | `PostAuction*` |
| F12 | Estratégia de saída executada (venda/locação/holding) | — | `finance`, `MarketComparable` |
| F13 | Status final definido; dossiê exportado | — | projeção dossiê |

## 6. Hard stops (bloqueio absoluto — independentes de score)

Proposta inicial (derivados **de evidência**; nunca de LLM). Cada hard stop referencia um
`Risk`/`ChecklistResult`/frente de due diligence:

| Código | Fase onde bloqueia | Origem (reuso) |
|---|---|---|
| `RISCO_JURIDICO_CRITICO` | F3 → F8 | `Risk(category=juridico, severity=CRITICA)` |
| `CONSOLIDACAO_NAO_REGISTRADA` | F3 | checklist `CONSOLIDACAO_REGISTRADA` ≠ CONFIRMADO (AF) |
| `INTIMACAO_MORA_AUSENTE` | F3 | checklist `INTIMACAO_PESSOAL`/`INTIMACAO_EDITAL` (AF) |
| `MATRICULA_DIVERGENTE` | F3 | DueDiligenceFront(MATRICULA) divergência edital×matrícula |
| `USUFRUTO_NAO_EXTINTO` | F3 | Central Jurídica (alerta crítico; exige cancelamento) |
| `ACAO_ANULATORIA_ATIVA` | F3 | `LegalProcess` correlação ALTA + anulatória |
| `PRECO_ACIMA_MAXIMO` | F8/F9 | `build_finance` (lance > preço máximo aprovado) |
| `MODALIDADE_INDEFINIDA` | F1 | `Opportunity.modality = INDEFINIDO` |

**Invariante (ADR-004):** o engine **recusa** `APROVADA` em F8 se existir qualquer hard stop
ativo, qualquer que seja o score financeiro. Hard stops são exibidos em bloco separado do score.

## 7. Eventos que invalidam uma aprovação anterior

Reusa `DomainEvent` + `ImpactAnalyzer`. Ao ocorrer um destes, a fase afetada vai a `REABERTA` e,
se havia aprovação, ela cai para `APROVACAO_INVALIDADA` (nova transição; exige nova decisão):

| Evento | Fases invalidadas |
|---|---|
| `EDITAL_ATUALIZADO` / `EDITAL_EXTRAIDO` (nova versão) | F1, F2, F3, F7, F8 |
| `MATRICULA_ATUALIZADA` / `MATRICULA_EXTRAIDA` | F3, F8 |
| `PRECO_ALTERADO` / `LEILAO_ATUALIZADO` | F7, F8 |
| `PROCESSO_VINCULADO` / `CONSULTA_JUDICIAL_REALIZADA` (ALTA) | F3, F8 |
| `OCUPACAO_ATUALIZADA` | F6, F7, F8 |
| `DIVIDA_ADICIONADA` / `CUSTO_ADICIONADO` | F4, F7, F8 |

> A invalidação apenas **marca estado/pendência** — **não** dispara LLM nem nova versão
> analítica automaticamente (regra inegociável). A reanálise permanece ação explícita do usuário.

## 8. Aprovação humana (F8) versionada

- A decisão de comitê registra: `decisao` (APROVADA/REPROVADA/ADIADA), `responsavel`, `data`,
  `justificativa`, `workflow_ruleset_version`, **snapshot dos dados** (versão da Analysis,
  hash/ids das evidências consideradas, hard stops avaliados, score por dimensão).
- Aprovar com hard stop ativo é **impossível** (engine bloqueia).
- Decisão é **imutável**; mudança ⇒ nova decisão (append-only), preservando a anterior.

## 9. Tratamento de dados incompletos / inconclusivos

- Fase sem dado suficiente ⇒ `PENDENTE_EVIDENCIA` (nunca "aprovado por omissão").
- Ausência de resultado **não** é ausência de risco: gates não concluem por default otimista.
- "Não encontrado" exige **escopo da consulta** (fonte, data, limitações) registrado — reusa o
  padrão de due diligence (`SEM_OCORRENCIA` ≠ certidão negativa).
- `NAO_APLICAVEL` de fase exige **justificativa** (ex.: F6 quando imóvel desocupado confirmado).

## 10. Versionamento das regras (ruleset)

- Ruleset declarativo em `workflow_rules.py` (futuro), com `WORKFLOW_RULESET_VERSION`.
- Cada `WorkflowTransition` e cada decisão de comitê gravam a versão aplicada.
- Mudança de ruleset é um PR revisável + testes; **não** reescreve transições passadas.
- Variação por **modalidade/UF/fase** entra como parametrização do ruleset (épico D), aditiva.

## 11. Contrato do engine (determinístico) — especificação de interface

Funções puras propostas (implementação em B1):
- `evaluate_phase(opportunity_ctx) -> PhaseEvaluation` — calcula `phase_state`, gates
  satisfeitos/pendentes, hard stops ativos, score por dimensão e **próxima ação recomendada**.
- `can_transition(opportunity_ctx, target_phase) -> TransitionDecision` — permite/bloqueia +
  motivo estruturado.
- `apply_transition(db, opportunity, target_phase, actor, justification) -> WorkflowTransition`
  — registra transição imutável + `DomainEvent` (única função com efeito; validada por
  `can_transition`).
- `invalidate_on_event(db, opportunity, event) -> list[WorkflowTransition]` — marca reabertura.

`opportunity_ctx` é montado por um serviço de leitura que **agrega** os domínios existentes (sem
recalcular). Todas as funções de avaliação são **sem efeito colateral** e **sem LLM**.

## 12. Fora de escopo
- Implementação (B1). UI (TODO-WORKFLOW-FOUNDATION + épico L). Score por dimensão detalhado
  (F8) tem desenho inicial aqui; a calibração fina é do épico I.
