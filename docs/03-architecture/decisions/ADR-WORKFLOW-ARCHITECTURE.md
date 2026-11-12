# ADR — Arquitetura de Workflow do Radar Leilão

> **Situação (reestruturação documental): ATUALIZAR STATUS.** O cabeçalho original abaixo diz "PROPOSTO" e "nada foi implementado".
> O código atual **implementa** o que este ADR descreve (`workflow_rules.py` cita "ADR-006" no versionamento de regras;
> `workflow_engine.py`, `routers/opportunities.py`). Não há registro, no repositório, da data nem do aprovador da decisão:
> o status formal permanece **pendente de confirmação pelo proprietário**. Índice: [README.md](README.md).

> **Status:** PROPOSTO (aguardando aprovação). **Natureza:** decisão arquitetural — documento
> de especificação. **Nada foi implementado.** Nenhuma migration, modelo, endpoint ou dado foi
> alterado. Preserva imóvel 633, análises V1–V9, `llm_runs` e os 27 `canonical_key`.
>
> **Escopo:** fundação dos épicos **M0** (modularização da API) e **B1** (máquina de estados /
> workflow). Base de trabalho: `docs/ROADMAP-PLATAFORMA-COMPLETA.md` (Fase Zero, aprovada).

---

## ADR-001 — Separar os domínios Imóvel, Oportunidade, Processo de Análise, Workflow e Dossiê

### Contexto
Hoje **todo** o histórico do sistema pendura diretamente em `Property` via `property_id`
(`auctions`, `documents`, `analyses`, `verdicts`, `checklist_executions`, `risks`, `events`,
`llm_runs`, …), com `cascade="all, delete-orphan"`. Não existe nenhuma noção de "oportunidade":
uma reanálise do mesmo imóvel em um novo leilão, meses depois, hoje se misturaria no mesmo
fluxo de versões (`Analysis.version` por `property_id`). Isso conflita com o requisito: *"um
mesmo imóvel poderá ter várias oportunidades ao longo do tempo; não devemos misturar os
históricos."*

### Decisão
Adotar um modelo de **5 conceitos distintos**:

| Conceito | Significado | Entidade |
|---|---|---|
| **Imóvel** | O bem imobiliário (identidade física/registral estável). | `Property` (existente) |
| **Oportunidade** | Uma oferta específica de aquisição daquele imóvel (um leilão/edital/data/preço num momento). | **`Opportunity` (nova)** |
| **Processo de Análise** | A avaliação técnica de uma oportunidade (versões, agentes, veredito). | `Analysis`/`Verdict`/… (existentes, re-ancoradas) |
| **Workflow** | O controle de fases F0–F13, transições e gates de uma oportunidade. | **`OpportunityWorkflow` + `WorkflowTransition` (novas)** |
| **Dossiê** | A visão consolidada read-only de documentos, evidências, análises e decisões de uma oportunidade. | **Projeção** (sem tabela própria; agrega o existente) |

**Chave da decisão:** a `Opportunity` é introduzida de forma **ADITIVA e OPCIONAL**. Nenhuma
FK obrigatória nova; nenhum `cascade` alterado; nenhum dado reescrito.

### Alternativas consideradas
1. **Reaproveitar `Property` como "oportunidade" (status quo).** ❌ Rejeitada: mistura
   históricos de leilões diferentes do mesmo imóvel; impossível ter duas oportunidades vivas.
2. **Migrar tudo para FK obrigatória `opportunity_id` (reescrita).** ❌ Rejeitada: viola as
   regras inegociáveis (preservar 633/V1–V9; migrations aditivas; sem reescrita). Alto risco.
3. **`Opportunity` aditiva + "oportunidade legada" para o passado.** ✅ **Escolhida.** Ver ADR-002.

### Consequências
- **Positivas:** históricos separados por oportunidade; um imóvel com N oportunidades; passado
  intacto; evolução incremental.
- **Negativas/custo:** durante a transição coexistem registros "com `opportunity_id`" e
  "legados (sem)". Exige regra de resolução (ADR-002) e cuidado nas consultas.

---

## ADR-002 — "Oportunidade legada" para preservar o histórico atual

### Contexto
Os dados atuais (ex.: imóvel 633 com V1–V9) foram criados sem `opportunity_id`. Precisamos
introduzir a `Opportunity` sem reescrever esse passado e sem bloquear a leitura do dossiê atual.

### Decisão
- Toda tabela de histórico que passar a referenciar oportunidade ganha uma coluna
  **`opportunity_id` NULLABLE** (default `NULL`). `NULL` ⇒ **"oportunidade legada implícita"**
  daquele imóvel.
- Um **backfill opcional e idempotente** (migration de dados **separada**, fora desta etapa de
  especificação) poderá criar **1 `Opportunity` legada por `Property` existente** e vincular os
  registros atuais. O backfill é **não destrutivo** e reversível (seta `opportunity_id` de volta
  a `NULL` no downgrade). **Não roda nesta etapa.**
- Enquanto o backfill não rodar, o sistema trata `opportunity_id IS NULL` como a oportunidade
  default do imóvel — **comportamento idêntico ao atual**.

### Consequências
- Imóvel 633 permanece **exatamente** como está; V1–V9 e `llm_runs` intactos.
- A nova funcionalidade (criar 2ª oportunidade) só afeta imóveis onde o usuário explicitamente
  abrir uma nova oportunidade.

---

## ADR-003 — Workflow como máquina de estados que ORQUESTRA, não substitui

### Contexto
Os domínios de análise (checklist, riscos, veredito, financeiro, due diligence, pós-arrematação,
Central Jurídica) já existem e funcionam. O workflow não pode duplicá-los.

### Decisão
- O workflow é uma **camada fina de orquestração** sobre uma `Opportunity`: mantém a **fase
  corrente** (F0–F13), o **estado de cada fase** e os **gates**. Ele **lê** sinais dos domínios
  existentes (via serviços determinísticos já disponíveis) para decidir se um gate está
  satisfeito; **não recalcula** nem reimplementa regra de negócio dos domínios.
- O engine de transição é **determinístico e puro** (sem LLM, sem I/O externo), no mesmo
  espírito de `risk_engine.py`/`verdict_engine.py`.
- Cada transição gera um **`DomainEvent`** e um registro imutável **`WorkflowTransition`**
  (append-only), reusando a infraestrutura de histórico existente (`DomainEvent`/`EntityHistory`).

### Consequências
- Reuso máximo; o workflow vira o "maestro" e os domínios continuam as "fontes de verdade".
- O gate consulta serviços existentes (ex.: `latest_execution`, `juridical_overview`,
  `due_diligence_overview`, `build_finance`) — nenhuma lógica duplicada.

---

## ADR-004 — Hard stops são independentes do score (risco jurídico crítico nunca é mascarado)

### Contexto
Requisito explícito: *"não permita que um score financeiro alto esconda um risco jurídico
crítico."* O `VerdictEngine` atual produz um rótulo global; não há score por dimensão nem hard
stops formais.

### Decisão
- Os **gates de fase** avaliam **duas trilhas separadas**:
  1. **Hard stops** (condições de bloqueio **binárias**): se presente, a transição é
     **BLOQUEADA** independentemente de qualquer score. Ex.: `RISCO_JURIDICO_CRITICO`,
     `MATRICULA_DIVERGENTE`, `USUFRUTO_NAO_EXTINTO`, `CONSOLIDACAO_NAO_REGISTRADA`.
  2. **Score/avaliação por dimensão** (jurídico, documental, físico, ocupação, fiscal, mercado,
     financeiro, liquidez, execução): informa a decisão, **mas nunca anula um hard stop**.
- O comitê (F8) **exibe hard stops em bloco separado do score** e exige **decisão humana
  versionada** para aprovar; aprovação com hard stop ativo é **proibida** pelo engine.
- Hard stop é sempre **derivado de evidência** (reusa `Risk`/`Evidence`/`ChecklistResult`),
  nunca inferido por LLM.

### Consequências
- Impossível, por construção, aprovar uma oportunidade com hard stop ativo via média/score.
- A regra de hard stop é **versionada** (ADR-006) e auditável.

---

## ADR-005 — Transições imutáveis e reabertura/invalidação por evento

### Contexto
Requisitos: histórico imutável de transições; retornar a fases anteriores com nova evidência;
reabrir quando edital/matrícula/preço/situação jurídica mudar; invalidar aprovação anterior.

### Decisão
- `WorkflowTransition` é **append-only** (nunca se edita/apaga uma transição). "Voltar de fase"
  é uma **nova** transição (`REABERTURA`/`RETROCESSO`), preservando a trilha.
- **Eventos invalidadores** (ex.: `EDITAL_ATUALIZADO`, `MATRICULA_ATUALIZADA`, `PRECO_ALTERADO`,
  `PROCESSO_VINCULADO`, `OCUPACAO_ATUALIZADA`) disparam, via `ImpactAnalyzer` (reuso), uma
  marca de **`APROVACAO_INVALIDADA`** na fase afetada e exigem revisão. Reusa o mecanismo de
  reanálise incremental já existente (`DomainEvent` → `ImpactAnalyzer` → revisão).
- **Nunca** há GET/CRUD que dispare LLM ou nova versão analítica: a invalidação apenas **marca
  pendência/estado**; a reanálise real continua sendo ação explícita.

### Consequências
- Auditoria completa de "por que a oportunidade está onde está".
- Mudança material nunca passa silenciosa: aprovação cai para estado que exige nova decisão.

---

## ADR-006 — Versionamento das regras de workflow (definição declarativa)

### Contexto
As regras (estados, transições, gates, hard stops) vão evoluir por modalidade/UF/fase. Decisões
precisam ser reproduzíveis: *"qual regra valia quando esta transição foi registrada?"*

### Decisão
- As regras do workflow são **declarativas e versionadas** (um `workflow_ruleset_version`,
  análogo ao `prompt_version`/`Checklist.version` já usados). Cada `WorkflowTransition` grava a
  **versão de regra** aplicada.
- A definição inicial do ruleset vive em **código** (um módulo `workflow_rules.py`, análogo a
  `checklist.py`/`legal_catalog.py`), permitindo revisão em PR e testes determinísticos. (A
  implementação do módulo é do épico B1 — aqui apenas se especifica.)

### Consequências
- Decisões reproduzíveis e auditáveis ao longo do tempo.
- Evolução de regra não reescreve o significado de transições passadas.

---

## ADR-007 — M0 (modularização) é pré-requisito organizacional, sem mudança de contrato

### Contexto
`backend/app/main.py` concentra ~130 rotas no `app`, sem `APIRouter`. Introduzir o domínio de
workflow nesse monólito aumenta o acoplamento e o risco.

### Decisão
- **M0 primeiro:** extrair as rotas para **`APIRouter` por domínio**, montados por
  `app.include_router(...)`, **sem alterar nenhum path, método, `response_model`, status code ou
  corpo de resposta**. É refactor de organização, **não** de comportamento.
- O workflow (B1) entra como **um novo router** (`workflow`/`opportunities`), sem tocar os demais.
- Testes de **regressão de rota** (snapshot do OpenAPI + testes HTTP das rotas existentes)
  garantem contrato idêntico antes/depois.

### Consequências
- Trabalho paralelo por domínio fica viável; B1 não precisa editar o monólito inteiro.
- Risco controlado: M0 é verificável por diff de contrato (OpenAPI) e testes.

---

## Resumo das entidades (detalhe em `MODEL-DATA-WORKFLOW.md`)

**Novas (justificadas):** `Opportunity`, `OpportunityWorkflow`, `WorkflowTransition`,
`WorkflowGateResult` (opcional — pode ser JSON no workflow; decidir no MODEL-DATA).
**Reutilizadas sem alteração estrutural destrutiva:** `Property`, `Auction`, `Document*`,
`Analysis`, `Verdict`, `Risk`, `Checklist*`, `DueDiligenceFront`, `PostAuction*`, `Legal*`,
`DomainEvent`, `EntityHistory`, `KnowledgeItem`.
**Aditivo nas existentes:** coluna `opportunity_id` **NULLABLE** onde fizer sentido ancorar
histórico por oportunidade (migração aditiva, sem default obrigatório, sem alterar cascade).

## Riscos arquiteturais e mitigações

| Risco | Mitigação |
|---|---|
| Dupla fonte de verdade (fase no workflow × estado real dos domínios) | Gate **lê** os domínios em tempo de avaliação; workflow guarda decisão, não recalcula |
| Quebra de histórico ao introduzir `opportunity_id` | Coluna **nullable**, `NULL`=legado; backfill separado/reversível; sem alterar cascade |
| Regressão de contrato no M0 | Snapshot OpenAPI + testes HTTP de rota antes/depois; sem mudar paths |
| Hard stop mascarado por score | ADR-004: trilha de hard stop binária e separada; engine proíbe aprovação com hard stop ativo |
| Transição disparar LLM/custo | Engine puro; invalidação só marca estado; reanálise permanece ação explícita |

## Conformidade

- ✅ Sem migration/modelo/endpoint/dado alterado nesta etapa (só especificação).
- ✅ 633, V1–V9, `llm_runs`, 27 `canonical_key` preservados por design (aditivo/opcional).
- ✅ Reuso máximo dos domínios e da infraestrutura de eventos/histórico existentes.
- ⏭️ Implementação só após aprovação (ver `PLAN-M0-API-MODULARIZATION.md` e `PLAN-B1-WORKFLOW-ENGINE.md`).
