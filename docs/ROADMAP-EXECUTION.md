# ROADMAP EXECUTION — Radar Leilão

> **Roadmap consolidado e priorizado**, em visão única. Reconcilia `ROADMAP-MASTER.md`,
> `ROADMAP-PLATAFORMA-COMPLETA.md`, `IMPLEMENTATION-PLAN-100.md` e o estado real do código
> (`FEATURE-INVENTORY.md`/`PRODUCT-DASHBOARD.md`). **Não descarta decisões anteriores**; onde há
> divergência, o motivo está registrado. Documento de planejamento — **nada é executado aqui.**

## 1. Princípios herdados (preservados)
- Evolução **reuse-first**, **aditiva** e **reversível**; migrations nullable; **sem backfill** sem
  Gate 2; **preservar** 633/V1–V9/`llm_runs`/27 `canonical_key`/Central Jurídica; sem LLM pago/
  integração externa sem autorização; append-only onde exigido; contrato de API sob guard-rail (M0).
- Medir prontidão por **evidência/validação**, não por documentação.

## 2. Reconciliação com o plano anterior (sem apagar decisões)
- `IMPLEMENTATION-PLAN-100.md` previa migrations `0018` (opportunity), `0019` (workflow+transition),
  `0020` (opportunity_id ×9), `0021` (backfill, Gate 2), e `0022` em diante para modalidade/etc.
- **O que mudou na execução real (justificado):** as migrations estruturais da Onda 1 foram
  **consolidadas em `0018`+`0019`** (0018 = tabelas do domínio; 0019 = `opportunity_id` nas 9
  tabelas). O backfill (que seria `0020`/`0021`) **não** foi criado — Gate 2 permanece bloqueado.
  Logo, a próxima migration livre era **`0020`**, não `0022`. A numeração segue a cadeia efetiva; o
  conteúdo lógico das ondas é preservado.
- **Atualização (Etapa A da Central de Débitos):** a migration `0020_central_debitos` foi executada
  para a fundação da Central (ver §4 abaixo).
- **Atualização (Etapa B da Central de Débitos):** a migration `0021_cobertura_municipal` foi executada
  para a cobertura município × tipo.
- **Atualização (Etapas C–F da Central de Débitos):** a migration `0022_consulta_estimativa` foi
  executada (consulta de débito + estimativa condominial). Portanto a **Onda 2 (modalidade)** deverá usar
  a próxima livre, **`0023`**.
- As ondas do Ciclo 2 permanecem as mesmas; a **Onda 0 (M0+CI)** e a **Onda 1 (Opportunity/Workflow)**
  estão concluídas; as **Etapas A–F da Central de Débitos** estão concluídas (coletores automáticos e
  identidade/RBAC permanecem dependências externas); a **Onda 2 (modalidade)** está planejada
  (`PLAN-WAVE-2-MODALIDADES.md`).

## 3. Legenda
- **Prioridade:** P0 (crítico/caminho crítico) · P1 (alto valor) · P2 (evolução).
- **Valor:** impacto no negócio. **Complexidade:** S/M/G/GG.

## 4. Roadmap consolidado por onda

### Onda 0 — M0 modularização + CI ✅ CONCLUÍDA
- **Prioridade:** P0 (fundação). **Valor:** base técnica. **Complexidade:** M.
- **Entrega:** routers + guard-rail de contrato (99 paths) + CI. **Critério de aceite:** contrato
  idêntico; 626/2 testes; migrations up/down. **Status:** VALIDADO (HEAD inclui `1d2d06d`/`7257c43`).

### Onda 1 — Opportunity + Workflow Engine (fundação) ✅ CONCLUÍDA (parcial por desenho)
- **Prioridade:** P0. **Valor:** base do "conduzir por processo". **Complexidade:** G.
- **Entrega:** modelos + migrations 0018/0019 + engine puro F0–F13 + testes de isolamento.
- **Critério de aceite:** migrations reversíveis; 658/2 testes; contrato preservado; 633 intacto.
- **Status:** IMPLEMENTADO (engine **não** exposto — ver Onda 1b). **Refs:** `ff422fd`.

### Etapa A — Central de Débitos/Despesas + Parâmetros administráveis ✅ CONCLUÍDA (fundação)
- **Prioridade:** P1. **Valor:** apuração rica/rastreável de passivos + parametrização sem código.
  **Complexidade:** G.
- **Entrega:** 6 tabelas aditivas (migration `0020_central_debitos`); serviços `parameters.py`
  (resolução por precedência + versionamento/histórico imutável) e `debts_service.py` (seeds, natureza,
  consolidação sem dupla contagem); routers `/api/admin/*` (escrita protegida por `X-Admin-Token`
  provisório) e `/api/imoveis/{id}/debitos`; 1ª UI admin (`/administracao`). `build_finance` inalterado.
- **Critério de aceite:** migrations reversíveis (up/down(0019)/up RC=0); backend 682/2; frontend tsc +
  141; contrato 113 paths (+14 intencionais); `Debt`/`Cost`/633 intactos. **Status:** VALIDADO em banco
  descartável. **Refs:** `docs/CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A.md`.
- **Dependência ABERTA:** auth/RBAC (Onda 11) para expor a admin em produção. **Fora de escopo:**
  coletores/scraping/consulta real/agentes/modalidades (Etapas B–F).

### Etapa B — Cobertura municipal e fontes de consulta ✅ CONCLUÍDA
- **Prioridade:** P1. **Valor:** cobertura operacional por município × tipo, extensível sem código.
  **Complexidade:** M-G.
- **Entrega:** tabela `municipality_coverage` (migration `0021_cobertura_municipal`, aditiva/reversível);
  vocabulários canônicos de nível/situação/método; `coverage_service.py` (seed como dado, matriz com
  combinações não investigadas, validação de referências/vocabulário/duplicidade); APIs
  `/api/admin/cobertura` (escrita protegida por `X-Admin-Token` provisório) + fontes validadas e com UI
  de cadastro/edição; aba Cobertura na admin; inventário documental das 4 fontes oficiais; especificação
  de adaptadores (`SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md`).
- **Critério de aceite:** cobertura independente por município×tipo; nenhuma lista fixa no código;
  migrations reversíveis (up/down(0020)/up RC=0); backend 694/2; frontend tsc + 143; contrato 115 paths;
  Etapa A/633 intactos. **Status:** VALIDADO em banco descartável.
  **Refs:** `docs/COBERTURA-MUNICIPAL-FONTES-ETAPA-B.md`.
- **NÃO implementado (deliberado):** coletores/adaptadores concretos, consulta real, `debt_query`,
  workers. **Dependência ABERTA:** auth/RBAC (Onda 11). **Fora de escopo:** Etapas C–F.

### Etapas C–F — Estimativa, parâmetros consumidos, consulta e integração ✅ CONCLUÍDAS
- **Prioridade:** P1/P2. **Valor:** apuração rica integrada ao dossiê + parametrização efetiva.
  **Complexidade:** G/GG.
- **Entrega:** (C) `estimates_service.py` + `CondominiumEstimate` (3 cenários ESTIMADO; idade ≠
  inadimplência; alertas parametrizáveis); (D) parâmetros **consumidos** em `market.py` via
  `parameters.resolve` + snapshot por execução (`FinancialAnalysis.inputs.parametros`, imutável);
  (E) contrato `MunicipalDebtProvider` + `ManualAssistedProvider` + registry + `debt_query_service`
  (retry/status/histórico `DebtQuery`); (F) seção Débitos no dossiê (`DebtsSection`) + consolidação sem
  dupla contagem; segurança `authz.py` (papéis sobre o token). Migration `0022_consulta_estimativa`.
- **Critério de aceite:** migrations reversíveis (up/down(0021)/up RC=0); backend 715/2; frontend tsc +
  146; contrato 119 paths; Etapas A/B/633 intactos. **Status:** VALIDADO em banco descartável.
  **Refs:** `docs/CENTRAL-DEBITOS-DESPESAS-ETAPAS-C-F-RELATORIO.md`.
- **Dependência ABERTA:** identidade/RBAC real (Onda 11); coletores automáticos de portais (viabilidade
  + termos + autorização por município). **NÃO implementado (deliberado):** scraping/consulta real,
  providers automáticos, workers.

### Onda 1b — Serviço + API + UI de Workflow/Oportunidade ⬅️ **CAMINHO CRÍTICO**
- **Prioridade:** P0. **Valor:** materializa a Onda 1 (hoje o engine é código não-ligado).
- **Complexidade:** G. **Dependências:** Onda 1. **Impacto técnico:** novo `workflow_service.py`,
  router `workflow.py` (rotas aditivas), dossiê por oportunidade, UI de oportunidades.
- **Regras:** `apply_transition` append-only + `DomainEvent`; GET sem LLM; serviços de leitura ganham
  `opportunity_id` opcional.
- **Critério de aceite:** criar oportunidade, avançar/bloquear/reabrir/descartar com trilha imutável;
  dossiê read-only; contrato cresce só por adição; 633 intacto.
- **Risco:** médio-alto (1ª exposição do workflow; acoplamento com leitura por oportunidade).

### Onda 2 — Modalidades (F1)
- **Prioridade:** P0 (destrava regras por modalidade). **Valor:** alto (produto trata judicial ×
  extrajudicial). **Complexidade:** M-G. **Dependências:** Onda 1. **Migrations:** `0020_modality`.
- **Entrega:** vocabulário canônico + classificação com evidência + aplicabilidade por modalidade no
  checklist e nas regras jurídicas (ver `PLAN-WAVE-2-MODALIDADES.md`).
- **Critério de aceite:** modalidade só muda com evidência; 27 `canonical_key` intactos; contrato
  preservado (exceto adição intencional da rota de modalidade).
- **Decisões de negócio pendentes:** incluir `LICITACAO`?; curadoria jurídica da matriz de
  aplicabilidade.

### Onda 3 — Documentos 2.0 + Central Jurídica 2.0
- **Prioridade:** P1. **Valor:** alto (confiabilidade jurídica/documental). **Complexidade:** G.
- **Entrega:** validade/confidencialidade/`supersedes`/`NAO_LOCALIZADO` no cofre; OCR provisionado;
  Central Jurídica com vigência/redação histórica/jurisprudência + aplicabilidade por modalidade.
- **Dependências:** Onda 2 (modalidade). **Aceite:** campos documentais + testes; catálogo jurídico
  expandido com proveniência (sem fabricar normas).

### Onda 4 — Checklist dinâmico
- **Prioridade:** P1. **Valor:** alto. **Complexidade:** G. **Dependências:** Ondas 2 e 3.
- **Entrega:** aplicabilidade por modalidade/UF/fase, criticidade/hard stop, critérios de
  aprovação/reprovação, dependências entre itens — **tudo aditivo sobre os 27 `canonical_key`**.
- **Aceite:** nenhuma chave canônica renomeada/removida; aplicabilidade determinística + testes.

### Onda 5 — Financeiro avançado + parâmetros fiscais
- **Prioridade:** P1. **Valor:** alto. **Complexidade:** G. **Migrations:** parâmetros fiscais.
- **Entrega:** TIR/VPL/fluxo descontado/sensibilidade; tabela de parâmetros por
  `(tributo/ato, jurisdição, base, vigência, fonte)` com memória de cálculo.
- **Regra inegociável:** nada fiscal fixado sem **fonte oficial + vigência**.
- **Aceite:** cálculos reconciliados por casos conhecidos; parâmetros versionados.

### Onda 6 — Comitê/decisão (F8) + hard stops
- **Prioridade:** P0 (fecha a decisão). **Valor:** alto. **Complexidade:** G. **Dependências:**
  Ondas 1b, 4, 5.
- **Entrega:** score por dimensão separado dos **hard stops** (ADR-004: hard stop bloqueia
  aprovação independentemente do score); decisão humana versionada; invalidação por mudança.
- **Aceite:** aprovar com hard stop ativo é impossível (teste explícito); decisão append-only.

### Onda 7 — Aquisição (F9 lance/pagamento)
- **Prioridade:** P1. **Complexidade:** M-G. **Dependências:** Onda 6.
- **Entrega:** resultado do leilão (arrematou/perdeu), pagamentos, obrigações/prazos.

### Onda 8 — Posse/reforma (F10/F11)
- **Prioridade:** P2. **Complexidade:** G. **Dependências:** Onda 7. Evolui pós-arrematação com
  modelagem registral e domínio de reforma/regularização dedicado.

### Onda 9 — Exploração/saída (F12) + encerramento (F13)
- **Prioridade:** P2. **Complexidade:** G. **Entrega:** venda/locação/holding, resultado realizado,
  ROI projetado×realizado, dossiê exportável.

### Onda 10 — Radar/descoberta (F0) + dashboards
- **Prioridade:** P1 (origem do funil). **Complexidade:** GG (integrações). **Dependências:**
  termos/credenciais de portais (BLOQUEADO até autorização). Entrega: ingestão/snapshot/dedupe/
  detecção de mudança/alertas; fallback manual permanece.

### Onda 11 — Segurança/operação (transversal) ⬅️ **BLOQUEANTE PARA PRODUÇÃO**
- **Prioridade:** P0 para expor multiusuário. **Complexidade:** G. **Entrega:** auth/RBAC,
  limites de upload (tamanho/MIME/streaming), observabilidade (métricas/tracing), backup/restore,
  runbooks. **Nota:** auth deve vir **antes** de qualquer exposição multiusuário real.

## 5. Caminho crítico (para produto funcional ponta a ponta)
```
Onda 1b (workflow exposto) ─► Onda 2 (modalidade) ─► Onda 4 (checklist dinâmico)
                                          │
                                          └─► Onda 5 (financeiro) ─► Onda 6 (comitê/hard stops)
                                                                          │
                                                                          ▼
                                                     Onda 7 (lance) ─► Onda 9 (saída/dossiê)
Onda 11 (auth/RBAC) = pré-requisito para PRODUÇÃO multiusuário (paralelizável, mas bloqueante p/ expor)
```
- **Mínimo para "fluxo de decisão ponta a ponta" (sem produção multiusuário):** 1b → 2 → 4 → 5 → 6.
- **Mínimo para "produção":** o acima **+ Onda 11 (auth/RBAC + segurança)**.

## 6. Matriz de priorização (resumo)
| Onda | Prioridade | Valor | Complexidade | Dependências | Caminho crítico |
|---|---|---|---|---|---|
| 1b Workflow exposto | P0 | Alto | G | Onda 1 | ✅ |
| 2 Modalidade | P0 | Alto | M-G | Onda 1 | ✅ |
| 4 Checklist dinâmico | P1 | Alto | G | Ondas 2,3 | ✅ |
| 5 Financeiro+fiscal | P1 | Alto | G | Onda 2 | ✅ |
| 6 Comitê/hard stops | P0 | Alto | G | 1b,4,5 | ✅ |
| 11 Auth/RBAC/segurança | P0 (produção) | Alto | G | — | ✅ (p/ produção) |
| 3 Docs/Jurídico 2.0 | P1 | Alto | G | Onda 2 | parcial |
| 7 Lance (F9) | P1 | Médio | M-G | Onda 6 | ✅ |
| 9 Saída/dossiê (F12/F13) | P2 | Médio | G | Onda 7 | ✅ |
| 8 Posse/reforma | P2 | Médio | G | Onda 7 | — |
| 10 Radar (F0) | P1 | Alto | GG | Credenciais (BLOQUEADO) | — |

## 7. Gates e bloqueios ativos
- **Gate 2 (backfill de oportunidade legada):** NÃO autorizado. Sem ele, 633 permanece
  `opportunity_id IS NULL` (legado). Pré-requisito: `pg_dump` + autorização explícita.
- **Integrações externas (DataJud/Maps/RI/Prefeitura/portais):** BLOQUEADAS até termos/credenciais;
  fallback manual permanece.
- **Parâmetros fiscais:** bloqueados por exigência de fonte oficial + vigência.
