# FEATURE BACKLOG — Radar Leilão

> **Backlog de novas funcionalidades + processo de gestão.** Permite incorporar ideias sem
> desorganizar o roadmap de execução (`ROADMAP-EXECUTION.md`). Documento vivo e atualizável.
> **Regra:** nada aqui é implementação; é fila de avaliação. Uma feature só vira trabalho após
> passar pelos estágios e ser alocada a uma onda.

## 1. Processo de gestão de features (pipeline)

```
[1] BACKLOG DE IDEIAS   → captura bruta (qualquer pessoa registra)
        │  triagem
        ▼
[2] EM ANÁLISE          → problema/benefício/impacto avaliados
        │  cabe no produto?
        ▼
[3] ESPECIFICADA        → spec objetiva + critérios de aceite + impacto arquitetural
        │  decisão de negócio
        ▼
[4] APROVADA            → alocada a uma onda/ciclo do ROADMAP-EXECUTION
        │
        ▼
[5] EM DESENVOLVIMENTO  → implementação (migrations aditivas, testes, preservação)
        │
        ▼
[6] EM VALIDAÇÃO        → testes verdes + E2E + evidência de preservação (633/V1–V9)
        │
        ▼
[7] CONCLUÍDA           → validada e documentada (entra no FEATURE-INVENTORY como VALIDADO)
```

**Regras do processo**
- Toda feature entra em **[1]** com o modelo de cadastro (§3). Sem o modelo preenchido, não avança.
- Passagem **[3]→[4]** exige decisão de negócio explícita (quem aprova, quando) e alocação a uma onda.
- Passagem **[6]→[7]** exige: testes automatizados verdes, contrato OpenAPI preservado (ou adição
  intencional documentada), e evidência de que 633/V1–V9/`llm_runs`/27 `canonical_key`/Central
  Jurídica permanecem intactos. Sem isso, não é "concluída".
- **Preservação e gates** (herdados): migrations aditivas/reversíveis; sem backfill sem Gate 2; sem
  LLM pago/integração externa sem autorização; sem comando destrutivo.
- **Impacto arquitetural** classificado em: **Nenhum** / **Aditivo** (coluna nullable, rota nova) /
  **Estrutural** (nova tabela/fluxo) / **Transversal** (auth, observabilidade, contrato). Estrutural/
  Transversal exige ADR antes de aprovar.

## 2. Critérios de avaliação (toda nova feature responde)
- **Problema de negócio** que resolve.
- **Benefício esperado** (e como medir).
- **Módulos impactados** (A–G do `FEATURE-INVENTORY`).
- **Dependências** (features/ondas/credenciais).
- **Complexidade** (S/M/G/GG).
- **Prioridade** (P0/P1/P2).
- **Riscos** (técnico, jurídico, dados, segurança).
- **Necessidade de alteração arquitetural** (Nenhum/Aditivo/Estrutural/Transversal; ADR?).
- **Encaixe no roadmap:** onda atual, próxima onda, ou ciclo futuro.

## 3. Modelo de cadastro de nova feature (copiar para cada item)

```markdown
### FB-XXX — <título curto>
- **Estágio:** BACKLOG | EM ANÁLISE | ESPECIFICADA | APROVADA | EM DESENVOLVIMENTO | EM VALIDAÇÃO | CONCLUÍDA
- **Problema de negócio:** <qual dor resolve>
- **Benefício esperado:** <resultado + métrica de sucesso>
- **Módulos impactados:** <A/B/C/D/E/F/G + arquivos prováveis>
- **Dependências:** <features/ondas/credenciais>
- **Complexidade:** S | M | G | GG
- **Prioridade:** P0 | P1 | P2
- **Riscos:** <técnico/jurídico/dados/segurança>
- **Impacto arquitetural:** Nenhum | Aditivo | Estrutural | Transversal  (ADR? sim/não)
- **Migrations:** <não / descrição aditiva reversível>
- **Preservação:** <como garante 633/V1–V9/27 keys/Central Jurídica intactos>
- **Critério de aceite:** <condições objetivas e testáveis>
- **Encaixe no roadmap:** <onda/ciclo recomendado>
- **Decisão:** <pendente / aprovado por <quem> em <data> / recusado (motivo)>
```

## 4. Backlog inicial (derivado dos gaps da auditoria)

> Itens extraídos de `FEATURE-INVENTORY.md`/`PRODUCT-DASHBOARD.md`. Estão em estágio inicial e
> **não** foram aprovados — é a fila para o usuário priorizar. Os que já têm onda no
> `ROADMAP-EXECUTION.md` referenciam-na.

### FB-001 — Expor Workflow/Oportunidade (serviço + API + UI)
- **Estágio:** ESPECIFICADA (Onda 1b). **Problema:** o engine de workflow existe mas não é usável.
- **Benefício:** conduzir um imóvel por fases com trilha auditável. **Módulos:** A, F, E.
- **Complexidade:** G. **Prioridade:** P0. **Impacto arquitetural:** Aditivo (rotas novas) + serviço.
- **Encaixe:** Onda 1b (caminho crítico). **Decisão:** pendente.

### FB-002 — Modalidades de aquisição (F1)
- **Estágio:** ESPECIFICADA (Onda 2, `PLAN-WAVE-2-MODALIDADES.md`). **Problema:** regras não variam
  por modalidade. **Benefício:** tratar judicial × extrajudicial corretamente. **Módulos:** A6, B3, F.
- **Complexidade:** M-G. **Prioridade:** P0. **Impacto:** Aditivo (migration `0020` + ruleset).
- **Decisão:** pendente (inclui decidir `LICITACAO`).

### FB-003 — Autenticação + RBAC + multiusuário
- **Estágio:** IMPLEMENTADO E TESTADO (Onda 11). **Problema (resolvido):** não havia login/papéis.
- **Benefício:** uso seguro por múltiplos usuários. **Módulos:** Transversal (todos). **Complexidade:** G.
- **Prioridade:** P0 (era bloqueante para produção). **Impacto:** Transversal.
- **Entrega:** modelo `User` (migration `0023`, bcrypt), JWT HS256 (`auth.py`), papéis
  ADMIN/ANALISTA/OPERADOR/CONSULTA + permissões (`authz.py`), router `/api/auth`
  (login/me/usuarios), proteção no backend + login/gate/logout no frontend, compat
  `X-Admin-Token` em desativação. Testes: `tests/test_auth.py` (14) + `LoginPage.test.tsx`.
  Ver `docs/MVP-CONSOLIDACAO-FINAL-2026-11.md`. **Evolução (não bloqueante):** MFA,
  refresh token, rotação de segredo, bloqueio por tentativas.

### FB-004 — Comitê de decisão (F8) com score + hard stops
- **Estágio:** EM ANÁLISE (Onda 6). **Problema:** Verdict não é decisão de comitê. **Benefício:**
  decisão auditável com hard stops não mascarados por score. **Módulos:** A7, A8, F. **Complexidade:** G.
- **Prioridade:** P0. **Impacto:** Estrutural (decisão versionada). **Decisão:** pendente.

### FB-005 — Financeiro avançado (TIR/VPL/sensibilidade) + parâmetros fiscais
- **Estágio:** EM ANÁLISE (Onda 5). **Problema:** falta valor do dinheiro no tempo e parâmetros por
  jurisdição. **Benefício:** decisão financeira robusta. **Módulos:** A9. **Complexidade:** G.
- **Prioridade:** P1. **Impacto:** Estrutural (tabela de parâmetros). **Risco jurídico:** nada fiscal
  sem fonte oficial + vigência. **Decisão:** pendente.

### FB-006 — Cofre documental 2.0 (validade/confidencialidade/supersedes) + OCR operante
- **Estágio:** EM ANÁLISE (Onda 3). **Módulos:** A2, A3. **Complexidade:** M-G. **Prioridade:** P1.
- **Impacto:** Aditivo (colunas) + provisionar Tesseract/Poppler. **Decisão:** pendente.

### FB-007 — Checklist dinâmico (aplicabilidade/criticidade/dependências)
- **Estágio:** EM ANÁLISE (Onda 4). **Módulos:** A6. **Complexidade:** G. **Prioridade:** P1.
- **Impacto:** Aditivo (preserva os 27 `canonical_key`). **Decisão:** pendente.

### FB-008 — Radar/descoberta (F0): ingestão/snapshot/dedupe/alertas
- **Estágio:** BACKLOG (Onda 10). **Módulos:** A1, novos. **Complexidade:** GG. **Prioridade:** P1.
- **Impacto:** Estrutural + integrações. **Dependência:** termos/credenciais de portais (BLOQUEADO).
- **Decisão:** pendente.

### FB-009 — F9 Lance/pagamento e F12 Saída (venda/locação) + F13 dossiê exportável
- **Estágio:** BACKLOG (Ondas 7 e 9). **Módulos:** C, novos. **Complexidade:** G. **Prioridade:** P1/P2.
- **Impacto:** Estrutural. **Decisão:** pendente.

### FB-010 — Observabilidade + limites de upload (tamanho/MIME/streaming)
- **Estágio:** EM ANÁLISE (Onda 11). **Módulos:** Transversal, A2. **Complexidade:** M. **Prioridade:** P1
  (segurança). **Impacto:** Transversal/Aditivo. **Decisão:** pendente.

### FB-011 — Clientes HTTP de RI Digital e Prefeitura (due diligence automática)
- **Estágio:** BACKLOG. **Módulos:** C2. **Complexidade:** G. **Prioridade:** P2. **Impacto:** Aditivo +
  integração. **Dependência:** credenciais/contrato (BLOQUEADO). **Decisão:** pendente.

### FB-012 — CPF/CNPJ estruturado do proprietário (habilita correlação ALTA)
- **Estágio:** EM ANÁLISE. **Módulos:** B1. **Complexidade:** M. **Prioridade:** P2. **Impacto:** Aditivo
  (coluna) + LGPD. **Risco:** dados pessoais sensíveis (tratar conforme LGPD). **Decisão:** pendente.

---

## 6. Frente Central de Débitos/Despesas + Admin (plano em `docs/PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md`)

> Itens derivados do plano da Central de Débitos (Etapas A–F). Estágio ESPECIFICADA (planejado,
> **não** aprovado). Não apagam itens anteriores. Dependem das decisões de negócio da §21 do plano.

### FB-013 — Central de Débitos: domínio normalizado (Etapa A)
- **Estágio:** IMPLEMENTADA (Etapa A — fundação) e VALIDADA em banco descartável. **Problema:** `Debt`
  é flat (sem município/tipo canônico/original×atualizado/confiabilidade). **Benefício:** apuração rica,
  rastreável e sem dupla contagem. **Módulos:** A9, C2, B.
- **Complexidade:** G. **Prioridade:** P1. **Impacto:** Estrutural (novas tabelas) + Aditivo (preserva
  `Debt`/`Cost`). **Migrations:** `0020_central_debitos` (aditiva/reversível; Onda 2 usa `0021`).
  **Preservação:** `Debt`/`Cost`/`build_finance`/633 intactos (confirmado). **Entrega:** `property_debts`
  normalizado + consolidação por natureza + registro manual; coletores/consulta real fora de escopo.
  Ver `docs/CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A.md`.

### FB-014 — Municípios, cobertura e fontes (Etapa B)
- **Estágio:** IMPLEMENTADA (Etapa B) e VALIDADA em banco descartável. **Problema:** não havia cadastro
  de cobertura por tipo (só flag global) nem cadastro efetivo de fontes. **Benefício:** cobertura
  independente por município×tipo, extensível sem código. **Módulos:** C2, B.
- **Complexidade:** M-G. **Prioridade:** P1. **Impacto:** Estrutural. **Dependência:** FB-013 (atendida).
  **Entrega:** tabela `municipality_coverage` (migration `0021`, reversível) + vocabulários canônicos +
  `coverage_service` (seed como dado; matriz com não investigados) + APIs `/api/admin/cobertura` +
  fontes validadas e com UI de cadastro/edição + inventário documental das 4 fontes oficiais +
  especificação de adaptadores (sem coletor). **Fora de escopo:** consulta real/automação (Etapas E/F).
  Ver `docs/COBERTURA-MUNICIPAL-FONTES-ETAPA-B.md` e `docs/SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md`.

### FB-015 — Estimativa condominial + alertas de idade (Etapa C)
- **Estágio:** IMPLEMENTADA (Etapa C) e VALIDADA. **Problema:** sem condomínio acessível, faltava
  estimativa confiável e distinção idade×condomínio×financiamento. **Benefício:** cenários
  conservador/provável/otimista sem afirmar passivo. **Módulos:** A6 (checklist), A9 (financeiro).
  **Complexidade:** M-G. **Prioridade:** P1. **Impacto:** Aditivo (preserva 27 keys).
  **Entrega:** `estimates_service.py` + `CondominiumEstimate` (migration `0022`); 3 cenários sempre
  ESTIMADO; período de inadimplência é parâmetro (nunca derivado de idade); alertas de idade
  parametrizáveis não conclusivos sem evidência. Ver `CENTRAL-DEBITOS-DESPESAS-ETAPAS-C-F-RELATORIO.md`.

### FB-016 — Módulo administrativo + catálogo de parâmetros (Etapa A/D)
- **Estágio:** IMPLEMENTADA (fundação na Etapa A) e VALIDADA. **Problema:** parâmetros de negócio
  hardcoded (ver §3 do plano). **Benefício:** configurar médias/limites/regras sem código, com histórico
  e versionamento. **Módulos:** Transversal, E (frontend). **Complexidade:** G. **Prioridade:** P1.
  **Impacto:** Transversal (ADR) + Aditivo. **Entrega:** catálogo central `parameters` + resolução por
  precedência + `parameter_history` imutável + 1ª UI admin (`/administracao`). **Etapa D concluída:**
  parâmetros **consumidos de fato** (`market.py` via `parameters.resolve`) + **snapshot por execução**
  (`FinancialAnalysis.inputs.parametros`; análises passadas imutáveis) + autorização por papel
  (`authz.py`: admin/operador, 503/401/403). **Dependência (ABERTA):** identidade/RBAC real
  (FB-003 / Onda 11) — a escrita usa `X-Admin-Token` com papéis **provisórios**; a admin só deve ser
  exposta em produção após a Onda 11 (§17).

### FB-017 — Orquestração/coletores + consolidação financeira (Etapas E/F)
- **Estágio:** PARCIALMENTE IMPLEMENTADA (E/F) e VALIDADA; coletores automáticos BLOQUEADOS.
  **Entregue (E/F):** contrato `MunicipalDebtProvider` + `ManualAssistedProvider` + registry por
  cobertura + `debt_query_service` (status por consulta, retry controlado, histórico `DebtQuery`) +
  consolidação por natureza integrada ao dossiê (`DebtsSection`) sem dupla contagem; `build_finance`
  inalterado. **Benefício:** apuração com status por consulta + exposição consolidada. **Módulos:**
  C2, A9. **Complexidade:** GG. **Prioridade:** P2. **Impacto:** Estrutural + integrações.
  **BLOQUEADO (dependência externa):** providers automáticos de portal reais dependem de
  viabilidade/termos por município + autorização; consulta real/scraping não executados. **Decisão:**
  pendente (§21.2 — autorizar investigação de automação por município).

## 5. Como manter este backlog consistente
- Toda nova ideia → novo `FB-XXX` com o modelo (§3), estágio inicial BACKLOG.
- Ao aprovar, referenciar a **onda** em `ROADMAP-EXECUTION.md` e mover o estágio.
- Ao concluir e validar, registrar a feature em `FEATURE-INVENTORY.md` com status VALIDADO e atualizar
  os indicadores em `PRODUCT-DASHBOARD.md`.
- Manter os quatro documentos (dashboard, inventário, backlog, roadmap) **consistentes entre si**:
  o inventário é a fonte de status atual; o backlog é a fila de futuro; o roadmap é a ordem; o
  dashboard é a leitura executiva.
