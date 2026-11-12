# PLAN — Ciclo 2 / Onda 2: Modalidades de Aquisição (F1)

> **Status:** PLANEJAMENTO (análise). **Nada implementado.** Nenhuma migration, alteração de
> banco, commit ou chamada externa foi executada ao produzir este documento. Base:
> `ROADMAP-PLATAFORMA-COMPLETA.md` (F1), `IMPLEMENTATION-PLAN-100.md`, `SPEC-OPPORTUNITY-DOMAIN.md`,
> `SPEC-WORKFLOW-ENGINE.md`, `MATRIZ-CHECKLIST-MODALIDADE.md`, `MATRIZ-CURADORIA-JURIDICA.md`,
> `MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md`, `REVISAO-ANOTACOES-LEILAO.md`, e o **código efetivo**
> (verificado, não apenas a documentação).
>
> **Diagnóstico ancorado no código, não em docs:** nada abaixo é tratado como "pronto" por existir
> um campo no banco ou um parágrafo em spec. Cada afirmação cita arquivo/linha real.
>
> **Objetivo da Onda 2:** dar ao sistema a capacidade de **classificar a modalidade de aquisição
> de uma oportunidade (com evidência)** e de **fazer regras variarem por modalidade** de forma
> configurável, determinística e auditável — começando pela aplicabilidade do checklist e pela
> seleção de regras jurídicas por modalidade. Sem antecipar as ondas de checklist dinâmico (Onda 4),
> financeiro parametrizado (Onda 5) nem comitê/hard stops (Onda 6).

---

## 1. Diagnóstico do que existe de fato

### 1.1 Modalidade no modelo de dados
| Onde | Código | Situação real |
|---|---|---|
| `Property.modality` | `models.py:34` — `String(80)`, nullable, **sem default, sem enum, sem validação** (migration `0009`) | String livre; apenas armazenada/exibida |
| `Opportunity.modality` | `models.py:997` — `String(40)`, `default/server_default "INDEFINIDO"`, indexada (migration `0018`, Onda 1) | String livre com default; **sem enum/validação** |
| `Opportunity.modality_evidence_id` | `models.py:998` — FK `evidences.id`, nullable | Existe; **nenhuma lógica consome** |
| `Auction` / `AuctionNotice` | — | **Não possuem** campo de modalidade |

Não existe **nenhuma lista/enum canônico** de modalidades em código (busca por
`MODALITIES/JUDICIAL=/EXTRAJUDICIAL=/VENDA_DIRETA/LICITACAO` = nada). A única string "mágica" é
`"INDEFINIDO"`.

### 1.2 Uso efetivo da modalidade na lógica
- **Único ponto:** `workflow_engine.py:121-124` emite o hard stop `MODALIDADE_INDEFINIDA` quando
  `modality == "INDEFINIDO"` (catálogo em `workflow_rules.py`). **Não há nenhuma ramificação que
  trate `JUDICIAL` diferente de `EXTRAJUDICIAL`** nem de qualquer valor concreto.
- **Gotcha crítico:** `workflow_engine` **não é importado por nenhum router/serviço** (fundação
  pura da Onda 1). Logo, mesmo essa única regra **não roda em produção hoje** — é código correto,
  testado e não-ligado. A modalidade, na prática, é 100% "armazenar e exibir".

### 1.3 Checklist (`checklist.py`)
- `CHECKLIST_MASTER`: 27 `canonical_key`; `master_items()` marca **`applicable: True` fixo para
  todos** (`checklist.py:31-50`). **Não há campo de aplicabilidade por modalidade.** O conteúdo das
  perguntas 1–9 é do rito **extrajudicial da Lei 9.514/97**, mas isso é só texto — nenhum metadado
  condiciona o item a uma modalidade.

### 1.4 Central Jurídica (`legal_service.py`, `legal_catalog.py`, `models.py`)
- Regras/dispositivos são classificados por `contexts` ⊂ `LEGAL_CONTEXTS`
  (`models.py:877-886`): `LEILAO, ARREMATACAO, MATRICULA, CONSOLIDACAO, DESOCUPACAO, POSSE,
  TRIBUTARIO, LOCACAO, GERAL`. **Não há modalidades** (judicial/extrajudicial/alienação fiduciária/
  venda direta) no vocabulário de contexto.
- Seleção de regra hoje = **match de string de contexto** (`legal_service.py:330-333`), nunca por
  imóvel/oportunidade/modalidade.

### 1.5 Motor financeiro (`services.py` `build_finance`, `finance.py`)
- **Uniforme / modality-agnostic.** `COST_KEYS` fixas; comissão por precedência Auction→custo;
  nenhuma ramificação por modalidade (comissão, tributos ou responsabilidade por débitos não
  variam por judicial/extrajudicial em código).

### 1.6 Agentes LLM (`ai/`)
- **Zero** referência a modalidade/judicial/extrajudicial nos prompts/comportamento.

### 1.7 Frontend (`frontend/src`)
- `PropertyWizard.tsx` — **input de texto livre** ("Ex.: Extrajudicial"); não é select, sem opções
  fixas. `PropertyDetailPage.tsx` só exibe. `services/properties.ts` — `modality?: string`.

### 1.8 Síntese (fato vs campo vazio vs inexistente)
- **Existe e funciona:** persistência de `modality`/`modality_evidence_id`; CRUD/exibição; a regra
  `MODALIDADE_INDEFINIDA` em código puro (não-ligado).
- **Existe só como campo, sem lógica:** `Property.modality`, `Opportunity.modality` (nenhum
  consumo real), `modality_evidence_id`.
- **Não existe em lugar nenhum:** enum/validação de modalidade; classificação com evidência;
  qualquer `if modalidade == X` concreto; aplicabilidade de checklist por modalidade; vínculo
  regra↔modalidade; diferença financeira por modalidade; modalidade em agentes; `modality` em
  `Auction`/`AuctionNotice`.

**Conclusão:** F1 está **🔴 ausente** como funcionalidade. O que há é um *campo* — não uma
*capacidade*. A Onda 2 precisa transformar o campo em uma camada transversal canônica, validada,
com evidência e com efeito determinístico sobre checklist e regras jurídicas.

---

## 2. Modalidades-alvo (F1)

Vocabulário canônico (do `ROADMAP-PLATAFORMA-COMPLETA.md` §4.1 F1 e `MATRIZ-CHECKLIST-MODALIDADE`):

| Código | Descrição | Trilha | Prioridade |
|---|---|---|---|
| `EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA` | Execução extrajudicial da Lei 9.514/97 (foco do produto) | Principal | Alta |
| `EXTRAJUDICIAL_OUTRA_GARANTIA` | Outras garantias extrajudiciais | Principal | Média |
| `JUDICIAL` | Arrematação judicial (CPC) | Separada | Alta |
| `VENDA_DIRETA` | Venda direta (sem leilão) | Principal | Média |
| `INDEFINIDO` | Modalidade ainda não evidenciada (estado inicial) | Triagem | — |

> **`LICITACAO`** é citada pelo usuário como modalidade a considerar, mas **não** consta das
> specs atuais como modalidade-alvo da F1. Tratada como **decisão de negócio em aberto** (§8): ou
> entra como 6º código, ou fica para onda futura. Enquanto não decidido, **não** será cadastrada.

**Princípio de evidência (SPEC-OPPORTUNITY §3 / ROADMAP F1):** a modalidade só sai de `INDEFINIDO`
**com evidência** (trecho do edital/matrícula vinculado via `Evidence`). Classificar sem evidência
= permanece `INDEFINIDO` (e o hard stop `MODALIDADE_INDEFINIDA` continua ativo).

---

## 3. Arquitetura proposta

Princípios: **reuse-first**, **aditivo**, **determinístico**, **auditável**, **configurável** (sem
`if` espalhado por modalidade) e **compatível com o legado** (`opportunity_id IS NULL` /
`modality = INDEFINIDO`). Zero duplicação de lógica entre modalidades.

### 3.1 Representação canônica da modalidade
- Nova constante **`MODALITIES`** em código (ex.: em `backend/app/modality_rules.py`), no mesmo
  espírito declarativo de `LEGAL_CONTEXTS`/`CHECKLIST_STATES`/`workflow_rules.py`. Fonte única da
  verdade do vocabulário; validada no schema Pydantic e (opcionalmente) por `CHECK` no banco.
- A modalidade **canônica** vive na **`Opportunity.modality`** (já existe). `Property.modality`
  permanece como **texto livre de origem** (o que o portal/Caixa informou) — **não** é promovido a
  canônico; serve de *dica* para a classificação. Isso evita quebrar o cadastro atual e separa
  "rótulo da origem" de "classificação validada".

### 3.2 Classificação com evidência (o coração da F1)
- Serviço determinístico `classify_modality(opportunity_ctx) -> ModalityDecision` (puro, sem LLM),
  que propõe a modalidade a partir de sinais objetivos (texto do edital, tipo de origem, campos do
  `AuctionNotice`) **mas só confirma com evidência vinculada** (`modality_evidence_id`).
- Sem evidência suficiente ⇒ `INDEFINIDO` + pendência (nunca "adivinha"). LLM, se um dia usado,
  entra apenas como **hipótese** a validar (coerente com `SPEC-HARD-STOPS`), nunca confirma sozinho.
- Reaproveita `Evidence`/`extraction.py` existentes; **não** cria pipeline novo.

### 3.3 Regras que variam por modalidade — camada configurável
Em vez de ramificar lógica, declara-se um **ruleset de modalidade** (tabela declarativa em
`modality_rules.py`, versionada com `MODALITY_RULESET_VERSION`) que mapeia:
- **Aplicabilidade de checklist por modalidade:** `canonical_key -> {modalidade -> APLICAVEL |
  CONDICIONAL | NAO_APLICAVEL}`, partindo da proposta do `MATRIZ-CHECKLIST-MODALIDADE`. Os **27
  `canonical_key` permanecem imutáveis**; a aplicabilidade é um **campo aditivo** (metadado),
  nunca renomeia/remove chave.
- **Contexto jurídico por modalidade:** vínculo regra↔modalidade (ver §3.5).
- **Hard stops específicos de modalidade:** ex.: `CONSOLIDACAO_NAO_REGISTRADA`/`INTIMACAO_MORA_
  AUSENTE` só fazem sentido em `EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA`; `preço vil 50%` é sinal do
  `JUDICIAL` e **não** vira piso no extrajudicial (`REVISAO-ANOTACOES-LEILAO §5`).

### 3.4 Separação de fluxos judicial × extrajudicial
- **Não** se cria um fluxo paralelo de código. A separação é **de dados/regras**: a mesma máquina
  de estados (workflow F0–F13 da Onda 1) consulta o ruleset de modalidade para decidir **quais
  gates/itens/regras se aplicam**. Trilha judicial e extrajudicial divergem na **configuração**,
  não em ramos de `if` duplicados.

### 3.5 Vínculo modalidade ↔ Central Jurídica
Duas opções (decisão de negócio/arquitetura — §8):
- **(A) Ampliar `LEGAL_CONTEXTS`** com contextos de modalidade (ex.: `ALIENACAO_FIDUCIARIA`,
  `JUDICIAL`) — aditivo, reaproveita todo o mecanismo de seleção por contexto já existente.
- **(B) Campo `modalities` (JSON) em `LegalRule`** — explícito, mas novo campo + nova lógica de
  seleção.
> **Recomendação:** **(A)** na Onda 2 (menor risco, reuso máximo do `legal_service`), deixando (B)
> para quando houver necessidade real de granularidade por modalidade além de contexto.

### 3.6 Documentos, prazos, riscos, custos e critérios por modalidade
- **Documentos/prazos:** nesta onda, apenas **marcação** de quais documentos/prazos são exigidos
  por modalidade (metadado no ruleset), **sem** alterar o cofre documental (Onda 3) nem criar
  modelos de prazo. É leitura/declaração, não automação.
- **Riscos:** a aplicabilidade por modalidade alimenta quais checklist-items/hard stops entram —
  o Risk Engine **não** é alterado nesta onda (consome o que já existe).
- **Custos/tributos:** **fora da Onda 2.** A parametrização por jurisdição/ato/vigência é o épico H
  (Onda 5). Aqui no máximo se **declara** que a modalidade influencia custos (ex.: comissão/ITBI),
  sem fixar valores — `REVISAO-ANOTACOES-LEILAO §5` proíbe fixar IR/FUNREJUS/taxa de ocupação sem
  fonte oficial e vigência.
- **Critérios de decisão:** comitê/score por dimensão é a Onda 6; aqui só se prepara a entrada
  (modalidade + aplicabilidade), sem implementar o comitê.

### 3.7 Integração com o Workflow Engine (Onda 1)
- `OpportunityContext.modality` já existe. A Onda 2 adiciona ao contexto a **modalidade canônica
  validada** e a **tabela de aplicabilidade**, e expõe funções puras (`applicable_checklist_keys
  (modality)`, `modality_hard_stops(modality)`) que o futuro serviço de leitura (onda do serviço de
  workflow) consumirá. O engine continua **puro**; a modalidade entra como dado do contexto.

### 3.8 Compatibilidade com o legado
- `opportunity_id IS NULL` (633 e todo o histórico) ⇒ modalidade **implícita `INDEFINIDO`**;
  comportamento idêntico ao atual (nenhuma regra nova de modalidade altera registros legados).
- A aplicabilidade por modalidade só afeta **novas execuções** no contexto de uma oportunidade com
  modalidade definida; execuções legadas continuam com os 27 itens como hoje.
- **Sem backfill** (Gate 2 bloqueado). O 633 não ganha modalidade nem oportunidade nesta onda.

---

## 4. Matriz de impacto técnico

| Componente | Situação atual | Alteração necessária (Onda 2) | Risco |
|---|---|---|---|
| **Vocabulário** | Nenhum enum de modalidade | Nova constante `MODALITIES` + `MODALITY_RULESET_VERSION` em `modality_rules.py` | Baixo |
| **`models.py` — Opportunity** | `modality` String(40) livre + `modality_evidence_id` | Validar contra `MODALITIES` (schema/CHECK); sem mudança estrutural obrigatória | Baixo |
| **`models.py` — classificação** | — | (Opcional) campos de rastreabilidade da classificação (`modality_source`, `modality_classified_at`) — aditivos, nullable | Baixo |
| **`models.py` — AuctionNotice** | Sem modalidade | (Decisão §8) talvez `modality_signal` para guardar o indício extraído do edital | Médio |
| **Migrations** | head `0019_opportunity_fk` | `0020_modality`: `CHECK`/validação + colunas aditivas nullable; **sem backfill**; upgrade+downgrade | Médio |
| **`checklist.py`** | 27 itens, `applicable:True` fixo | **Não tocar os 27 keys.** Adicionar mapa de aplicabilidade por modalidade (metadado aditivo, em `modality_rules.py` ou campo novo) | Médio |
| **`legal_service.py` + `LEGAL_CONTEXTS`** | Seleção por contexto; sem modalidade | Ampliar `LEGAL_CONTEXTS` (opção A) + função `rules_for_modality()` | Médio |
| **`legal_catalog.py` (seed)** | Regras com `contexts` temáticos | Adicionar contextos de modalidade às regras pertinentes (aditivo, idempotente) | Médio |
| **`workflow_rules.py` / `workflow_engine.py`** | `MODALIDADE_INDEFINIDA` puro, não-ligado | Expor helpers puros de aplicabilidade/hard stops por modalidade; manter engine puro | Baixo |
| **Backend APIs** | Sem endpoint de modalidade | (Decisão §8) endpoint de classificação/confirmação de modalidade; contrato OpenAPI muda **só por adição** | Médio |
| **`services.py`/`finance.py`** | Modality-agnostic | **Nenhuma** nesta onda (custos = Onda 5) | — |
| **Agentes LLM (`ai/`)** | Sem modalidade | **Nenhuma** nesta onda (classificação determinística; LLM só hipótese futura) | — |
| **Frontend** | Input texto livre | `select` com `MODALITIES`; exibição da modalidade + evidência; (se houver endpoint) UI de classificação | Médio |
| **Testes** | Sem testes de modalidade | Unit puros (classificação/aplicabilidade/ruleset) + DB (isolamento por oportunidade) + contrato OpenAPI + guarda do 633 | Médio |
| **Central Jurídica (catálogo)** | Preservada | Enriquecimento aditivo por contexto de modalidade; **sem** remover/renomear | Baixo |

---

## 5. Plano de implementação por etapas

> Cada etapa é pequena, independente e fecha verde (migrations up/down em banco descartável;
> contrato OpenAPI preservado salvo adições intencionais; guarda do 633). Numeração W2.x.

### W2.1 — Vocabulário canônico + validação (sem migration de dados)
- **Objetivo:** fonte única de modalidades + validação; eliminar o "texto livre" como canônico.
- **Arquivos:** `backend/app/modality_rules.py` (novo: `MODALITIES`, `MODALITY_RULESET_VERSION`,
  helpers puros); `backend/app/schemas.py` (validar `Opportunity.modality` contra `MODALITIES`).
- **Migration:** nenhuma (ou `0020_modality` apenas com `CHECK` opcional — ver W2.2).
- **Regras:** `INDEFINIDO` é o default; valor fora do conjunto é rejeitado no schema.
- **Testes:** unit puros (conjunto canônico, rejeição de valor inválido, versão do ruleset).
- **Aceite:** `MODALITIES` definido; schema rejeita modalidade inválida; nenhum efeito no 633.
- **Deps/risco:** nenhuma; risco baixo.

### W2.2 — Migration `0020_modality` (estrutural, aditiva, reversível)
- **Objetivo:** persistir rastreabilidade da classificação e (se decidido) sinal no edital.
- **Arquivos:** `backend/migrations/versions/0020_modality.py`; `models.py` (colunas aditivas
  nullable); `0001_fundacao_radar.py` (atualizar `COLUMNS_ADDED_LATER` para o upgrade do zero).
- **Migration:** `add_column` nullable (ex.: `opportunities.modality_source`,
  `opportunities.modality_classified_at`; opcional `auction_notices.modality_signal`); opcional
  `CHECK` de domínio em `opportunities.modality`. **Sem backfill.**
- **Regras:** colunas nullable; `NULL` = legado; `post_auctions.property_id UNIQUE` intocado.
- **Testes:** `alembic upgrade head` + `downgrade 0019` + re-upgrade RC=0 em banco descartável.
- **Aceite:** migration reversível; 633 inalterado; `upgrade head` do zero funciona (CI).
- **Deps/risco:** depende de W2.1 (vocabulário); risco médio (schema/CHECK).

### W2.3 — Classificação determinística com evidência
- **Objetivo:** `classify_modality()` puro que propõe modalidade a partir de sinais e **confirma só
  com evidência**; sem evidência ⇒ `INDEFINIDO`.
- **Arquivos:** `backend/app/modality_rules.py` (regras de classificação declarativas);
  serviço de leitura/escrita que grava `Opportunity.modality` + `modality_evidence_id`.
- **Migration:** nenhuma.
- **Regras:** LLM **não** confirma (só hipótese); classificação é determinística e auditável;
  `DomainEvent` registra a classificação (reuso).
- **Testes:** unit puros (com evidência ⇒ confirma; sem evidência ⇒ `INDEFINIDO`); DB (persistência
  + isolamento por oportunidade).
- **Aceite:** modalidade só muda com evidência; legado permanece `INDEFINIDO`.
- **Deps/risco:** W2.1; risco médio.

### W2.4 — Aplicabilidade de checklist por modalidade (aditiva, 27 keys intactos)
- **Objetivo:** mapa `canonical_key × modalidade -> aplicabilidade`, partindo do
  `MATRIZ-CHECKLIST-MODALIDADE` (proposta de curadoria — exige validação jurídica, §8).
- **Arquivos:** `modality_rules.py` (mapa declarativo); função pura
  `applicable_checklist_keys(modality)`; **não** alterar `CHECKLIST_MASTER`.
- **Migration:** nenhuma (mapa em código) — ou aditiva se a aplicabilidade for persistida.
- **Regras:** os 27 `canonical_key` permanecem; itens não-aplicáveis a uma modalidade ficam
  `NAO_APLICAVEL` (com justificativa), nunca removidos; legado (`INDEFINIDO`) mantém os 27.
- **Testes:** unit (aplicabilidade por modalidade conforme matriz); guarda de que os 27 keys e a
  numeração seguem intactos.
- **Aceite:** aplicabilidade determinística por modalidade; checklist mestre imutável.
- **Deps/risco:** W2.1/W2.3; risco médio (curadoria jurídica).

### W2.5 — Vínculo modalidade ↔ Central Jurídica (opção A: contextos)
- **Objetivo:** selecionar regras jurídicas conforme a modalidade.
- **Arquivos:** `models.py` (`LEGAL_CONTEXTS` += contextos de modalidade); `legal_service.py`
  (`rules_for_modality()`); `legal_catalog.py` (seed idempotente adiciona os contextos às regras).
- **Migration:** nenhuma estrutural (contexts é JSON); seed idempotente.
- **Regras:** aditivo; Central Jurídica preservada; nenhum texto legal alterado.
- **Testes:** unit/DB (regra correta por modalidade; legado inalterado).
- **Aceite:** regra jurídica selecionável por modalidade; catálogo preservado.
- **Deps/risco:** W2.1; risco médio.

### W2.6 — Integração com o Workflow Engine + hard stops por modalidade
- **Objetivo:** engine puro consome modalidade canônica + aplicabilidade/hard stops por modalidade.
- **Arquivos:** `workflow_rules.py`/`workflow_engine.py` (helpers puros; manter pureza);
  `modality_rules.py`.
- **Migration:** nenhuma.
- **Regras:** `preço vil 50%` só `JUDICIAL`; hard stops de alienação fiduciária só na modalidade
  correspondente; `MODALIDADE_INDEFINIDA` mantido.
- **Testes:** unit puros por modalidade (hard stops aplicáveis variam corretamente).
- **Aceite:** engine determinístico varia por modalidade sem ramos duplicados.
- **Deps/risco:** W2.4; risco baixo-médio.

### W2.7 — API (aditiva) + Frontend
- **Objetivo:** expor classificação/confirmação de modalidade e refletir na UI.
- **Arquivos:** `backend/app/routers/` (endpoint novo, aditivo — ex.: `POST
  /api/oportunidades/{oid}/modalidade`); `frontend/src` (select com `MODALITIES`, exibição +
  evidência). **Atualizar o baseline OpenAPI** conscientemente (adição intencional).
- **Migration:** nenhuma.
- **Regras:** GET não dispara LLM/custo; classificação exige evidência.
- **Testes:** contrato OpenAPI (adições intencionais documentadas); `tsc` + `vitest`; backend HTTP.
- **Aceite:** modalidade selecionável/visível; contrato só cresce por adição; sem regressão.
- **Deps/risco:** W2.3; risco médio (primeira mudança intencional de contrato desde o M0).

### W2.8 — Docs + histórico + fechamento da onda
- **Objetivo:** PROJECT-HISTORY (seção Onda 2), PROJECT-STATUS, TODOs; relatório da onda.
- **Aceite:** documentação atualizada; evidências de validação anexadas; commits rastreáveis.

> **Observação de sequência:** W2.1→W2.6 **não** alteram o contrato OpenAPI (99 paths). Só a W2.7
> introduz rota(s) nova(s) — a primeira adição intencional ao baseline desde o M0.

---

## 6. Estimativa de complexidade e riscos

| Etapa | Complexidade | Risco | Observação |
|---|---|---|---|
| W2.1 vocabulário | Baixa | Baixo | fundação declarativa |
| W2.2 migration 0020 | Média | Médio | reversibilidade + upgrade do zero (CI) |
| W2.3 classificação | Média | Médio | determinismo + evidência; não usar LLM |
| W2.4 aplicabilidade checklist | Média | Médio-alto | **depende de curadoria jurídica** (§8) |
| W2.5 vínculo jurídico | Média | Médio | aditivo em contexts; seed idempotente |
| W2.6 integração engine | Baixa-Média | Baixo-Médio | engine já é puro |
| W2.7 API + frontend | Média | Médio | 1ª mudança intencional de contrato |
| W2.8 docs | Baixa | Baixo | — |

**Riscos transversais e mitigação**
- **Curadoria jurídica da matriz de aplicabilidade** (quais itens valem por modalidade) é a maior
  incerteza: a matriz do `MATRIZ-CHECKLIST-MODALIDADE` é **proposta**, não verdade validada.
  Mitigação: tratar como configuração versionada; marcar itens `CONDICIONAL` como pendência de
  validação; **não** transformar proposta em regra sem aprovação (§8).
- **Mudança de contrato (W2.7):** mitigar com baseline OpenAPI atualizado conscientemente + diff
  documentado (padrão M0).
- **Regressão do legado:** tudo aditivo/nullable; `INDEFINIDO`/`NULL` preserva comportamento atual;
  teste de guarda do 633.
- **Escopo inflar:** custos/tributos, comitê e checklist dinâmico completo **ficam fora** (ondas
  4/5/6). A Onda 2 entrega a *camada de modalidade*, não a totalidade das regras que dela dependem.

---

## 7. Dependências externas

- **Nenhuma integração externa é necessária** para a Onda 2. A classificação é determinística sobre
  dados já cadastrados (edital/matrícula/origem) + evidência manual.
- Portais de leilão, RI Digital, Prefeitura, RTD etc. (`REVISAO-ANOTACOES-LEILAO`) **não** entram:
  permanecem manuais/bloqueados até autorização, termos e credenciais (épico M).
- Sem LLM pago: a classificação não depende de modelo; se LLM for usado no futuro, é **hipótese** a
  validar, nunca confirmação automática.

---

## 8. Pontos que exigem decisão de negócio

1. **`LICITACAO` é 6ª modalidade?** As specs F1 definem 5 códigos; o usuário cita licitação.
   Decidir: incluir agora (ampliar `MODALITIES`) ou adiar. **Sem decisão, não será cadastrada.**
2. **Curadoria da aplicabilidade checklist × modalidade:** a matriz do `MATRIZ-CHECKLIST-MODALIDADE`
   é proposta. Precisa de **validação jurídica** antes de virar regra executável — especialmente os
   itens `CONDICIONAL (⚠️)` e o `preço vil 50%` (judicial, não extrajudicial).
3. **Vínculo jurídico — opção (A) contextos vs (B) campo `modalities`:** recomendo (A); confirmar.
4. **`Property.modality` (texto livre) vs `Opportunity.modality` (canônico):** confirmar que a
   origem livre permanece informativa e a canônica vive na oportunidade (proposta deste plano).
5. **Classificação: manual, assistida ou automática?** Proposta: determinística + evidência manual
   nesta onda; automação/LLM só como hipótese em onda futura.
6. **`AuctionNotice.modality_signal`:** criar coluna para guardar o indício extraído do edital, ou
   manter o sinal apenas em `Evidence`? (impacta a migration 0020).
7. **Numeração de migration:** confirmar `0020_modality` (as estruturais da Onda 1 ficaram em
   0018/0019; não houve 0020/0021 porque o backfill — Gate 2 — não foi autorizado). O
   `IMPLEMENTATION-PLAN-100` citava `0022` nominalmente; a numeração real segue a cadeia efetiva.

---

## 9. Critérios de aceite da Onda 2

Além dos transversais (G-1..G-7 de `ACCEPTANCE-CRITERIA-WORKFLOW`), para a Onda 2:

- **CA-1:** existe vocabulário canônico `MODALITIES` + versão do ruleset; modalidade inválida é
  rejeitada no schema.
- **CA-2:** `Opportunity.modality` só muda para um valor ≠ `INDEFINIDO` **com evidência** vinculada;
  sem evidência permanece `INDEFINIDO` (determinístico, sem LLM).
- **CA-3:** aplicabilidade de checklist varia por modalidade **sem alterar os 27 `canonical_key`**
  nem a numeração; itens não-aplicáveis ficam `NAO_APLICAVEL` justificado.
- **CA-4:** seleção de regra jurídica por modalidade funciona e a Central Jurídica permanece
  preservada (nenhuma regra/fonte removida ou renomeada).
- **CA-5:** o engine de workflow continua **puro** e varia por modalidade via configuração (sem
  ramos duplicados); `preço vil 50%` não é piso no extrajudicial.
- **CA-6:** migration `0020` aditiva e reversível (upgrade/downgrade/re-upgrade RC=0 em banco
  descartável); `upgrade head` do zero funciona.
- **CA-7:** contrato OpenAPI preservado nas etapas W2.1–W2.6; adições em W2.7 são intencionais e
  refletidas no baseline + diff documentado.
- **CA-8:** suíte backend e frontend sem regressão; novos testes (classificação/aplicabilidade/
  ruleset/isolamento) verdes.
- **CA-9 (preservação):** imóvel 633, análises V1–V9, financeiras V1–V9, `llm_runs`, 27
  `canonical_key` e Central Jurídica intactos; nenhum backfill; nenhuma V10; `.env`/segredos
  intocados; nenhuma chamada externa/LLM paga.
- **CA-10:** custos/tributos e comitê/score **não** foram implementados nesta onda (fora de escopo),
  evitando antecipar as ondas 5/6.

---

## 10. Resumo executivo

- **Diagnóstico:** F1 é hoje um **campo**, não uma **capacidade**. Modalidade é string livre,
  armazenada/exibida, com uma única regra (`MODALIDADE_INDEFINIDA`) que sequer está ligada à
  produção. Checklist, Central Jurídica, financeiro e agentes são **modality-agnostic**.
- **Arquitetura:** camada transversal de modalidade — vocabulário canônico + classificação com
  evidência + ruleset declarativo que parametriza checklist e regras jurídicas por modalidade —
  reaproveitando `Opportunity.modality`/`modality_evidence_id`, `Evidence`, `legal_service` e o
  engine puro da Onda 1. Judicial × extrajudicial divergem na **configuração**, não em código
  duplicado.
- **Entrega mínima da onda:** classificar modalidade com evidência e fazer **checklist** e **regras
  jurídicas** variarem por modalidade. Custos/comitê ficam para ondas 5/6.
- **Preservação:** tudo aditivo/nullable; legado (`NULL`/`INDEFINIDO`) inalterado; Gate 2 bloqueado;
  633 intocado.
- **Bloqueadores de negócio:** curadoria jurídica da matriz de aplicabilidade e a decisão sobre
  `LICITACAO` (§8) precisam ser resolvidos antes de transformar a proposta em regra executável.

> **Aguardando aprovação explícita deste planejamento antes de qualquer implementação.** Nenhuma
> alteração de código, migration ou commit será feita sem o "ok" do usuário.
