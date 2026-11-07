# IMPLEMENTATION PLAN 100 — Ciclo 2 (construção) + Ciclo 3 (validação)

> **Natureza:** plano único e executável derivado de `PROJECT-AUDIT-2026-11.md`,
> `ROADMAP-MASTER.md`, `PRODUCT-SCOPE-100.md`, `ACCEPTANCE-CRITERIA-MASTER.md` e das specs
> M0/B1. **Planejamento — nenhum código nesta etapa.** Projetado para que **um** prompt
> abrangente autorize a construção (Ciclo 2) e **outro** autorize a validação final (Ciclo 3),
> sem perder gates internos.

## 0. Princípios de execução (herdados dos documentos mestres)
- Entregas pequenas, coerentes, reversíveis; migrations aditivas com upgrade/downgrade testados
  em banco descartável.
- Reuso máximo; workflow orquestra (não recalcula nem dispara LLM em GET/CRUD/transição).
- Preservar 633/V1–V9/`financial_analyses` V1–V9/`llm_runs`/27 `canonical_key`/Central Jurídica.
- Nunca dois PRs no mesmo arquivo quente (`main.py`/`models.py`) simultaneamente (ver `SEQUENCING-M0-B1.md`).
- Dependência externa indisponível ⇒ `BLOQUEADO`, nunca simulada.
- Toda saída de IA registra modelo/versão/prompt/fontes/timestamp/estado de validação.

## 1. Gates de autorização (controle do usuário)
- **Gate A — Autorizar Ciclo 2** (construção). Pré: este plano aprovado.
- **Gate 1 — Antes da onda de dados de oportunidade** (coluna `opportunity_id`): confirmar
  `MATRIZ-OPPORTUNITY-ID` (decisões `post_auctions`=UNIQUE mantido, `costs`/`debts` adiados).
- **Gate 2 — Backfill `0021`** (oportunidade legada): só com autorização explícita + `pg_dump`.
- **Gate B — Autorizar Ciclo 3** (validação final e release 100%).

## 2. Ciclo 2 — ondas de construção

> Cada onda = conjunto de PRs pequenos. "Avança quando" = critério de aceite da onda (resumido;
> detalhe em `ACCEPTANCE-CRITERIA-WORKFLOW.md`/`-MASTER.md`). Migrations indicadas são
> **planejamento** (numeração a confirmar na implementação).

### Onda 0 — Fundação técnica (habilita o resto)
- **M0** modularização gradual da API (`main.py` → `APIRouter` por domínio; baseline+diff OpenAPI).
- Esqueleto de **CI** (lint + testes em banco descartável) — destrava validação contínua.
- Arquivos: `backend/app/routers/*`, `backend/app/main.py` (bootstrap), `.github/workflows/*`.
- Migrations: nenhuma. Risco: contrato de rota — mitigado por diff OpenAPI.
- **Avança quando:** OpenAPI idêntico ao baseline; suíte atual verde em CI; `main.py` = bootstrap.

### Onda 1 — Domínio Opportunity + Workflow (B1)
- Modelos `Opportunity`/`OpportunityWorkflow`/`WorkflowTransition` (migr. `0018`/`0019`);
  `workflow_rules.py` + `workflow_engine.py` (puro); `workflow_service.py`; router workflow.
- Coluna `opportunity_id` nullable nas 9 tabelas (migr. `0020`) — **após Gate 1**.
- Arquivos: `models.py` (append), novos módulos de workflow, `routers/workflow.py`.
- Risco: quebra de histórico — mitigado (nullable/legado). **Avança quando:** T-ISO + transições
  + append-only verdes; 633 intacto.

### Onda 2 — Modalidade + triagem (F0/F1 base)
- `Opportunity.modality` (enum) + evidência; regras de aplicabilidade por modalidade.
- Captura/estruturação de intake (sem conector externo): snapshot + dedupe manual-assistido.
- Migrations: `0022` (campos de modalidade/intake). **Avança quando:** classificação com
  evidência; dedupe rastreável; sem scraping.

### Onda 3 — Documentos/evidências + Jurídico 2.0
- Upload: **limite de tamanho + validação MIME** + streaming; classificação documental.
- Central Jurídica 2.0: vigência estruturada, jurisprudência, aplicabilidade, revisor.
- Migrations: `0023` (metadados documentais + legais 2.0). **Avança quando:** upload malicioso
  rejeitado; curadoria jurídica com fonte/vigência; sem inventar norma.

### Onda 4 — Checklist dinâmico + Due Diligence por modalidade (F5)
- Checklist por modalidade/UF/fase preservando os 27 `canonical_key`; estados 7→10 aditivos;
  snapshot por oportunidade; reabertura por fato.
- Migrations: `0024`. **Avança quando:** 27 keys preservados; variação por modalidade; snapshots.

### Onda 5 — Financeiro completo (F6/F7)
- TIR/VPL/fluxo descontado/payback; sensibilidade paramétrica; **custos por jurisdição/ato/
  vigência/fonte**; valuation/liquidez.
- Migrations: `0025` (tabela de parâmetros fiscais/registrais). **Avança quando:** casos de
  referência reconciliados; estimado×confirmado separados; testes de fórmula.

### Onda 6 — Hard stops + Comitê/decisão (F8)
- Hard stops (estado HIPOTESE→CONFIRMADO, reuso de `Risk` + Central Jurídica); score por
  dimensão; decisão humana versionada; invalidação por evento.
- Migrations: `0026` (colunas de hard stop em `risks` + decisão). **Avança quando:** hard stop
  CONFIRMADO bloqueia mesmo com score alto; invalidação preserva decisão; sem LLM bloqueando.

### Onda 7 — Aquisição/lance/pagamento (F9/F10)
- Domínio de lance/limite aprovado/resultado (inclui não-vencedor/cancelado); pagamentos/
  comissão/comprovantes; registro formal (prenotação/baixa de ônus) sobre Pós-Arrematação.
- Migrations: `0027`. **Avança quando:** resultado sem arremate também fecha fluxo; registro
  não marcado sem evidência.

### Onda 8 — Posse/regularização/reforma (F11/F12)
- Reforma (orçamento/fornecedor/medição/aceite/ART-RRT); regularização (habite-se/averbação).
- Migrations: `0028`. **Avança quando:** posse física ≠ regularidade documental; realizado registrado.

### Onda 9 — Rentabilização/encerramento (F13)
- Venda/locação/holding; receitas/despesas; projetado×realizado; encerramento com resultado.
- Migrations: `0029`. **Avança quando:** reconciliação projeção×realizado; estados finais.

### Onda 10 — Radar/conectores/dashboards (F0 avançado)
- Conectores **somente** de fontes autorizadas (API/termos); dashboards de carteira/oportunidade/
  radar; alertas. Migrations: `0030`. **Avança quando:** fonte não autorizada não é acessada.

### Onda 11 — Segurança/RBAC/observabilidade/operação (J)
- Auth + RBAC + auditoria por usuário; métricas/tracing/alertas; backup **restore testado** +
  runbooks; política de retenção; rate limiting. Migrations: `0031` (users/roles). **Avança
  quando:** RBAC por perfil testado; restore validado em ambiente isolado; logs sem segredo.

## 3. Dependências entre ondas

```
Onda 0 (M0+CI) ─► Onda 1 (Opportunity/Workflow) ─► Onda 2 (modalidade)
                         │                               │
                         ├─► Onda 3 (docs+jurídico 2.0)   │
                         ├─► Onda 4 (checklist dinâmico) ◄┘
                         ├─► Onda 5 (financeiro) ─► Onda 6 (hard stops/comitê)
                         │                               │
                         │                               ▼
                         │                         Onda 7 (aquisição) ─► Onda 8 (posse/reforma) ─► Onda 9 (saída)
                         │
                         └─► Onda 10 (radar/dashboards)
Onda 11 (segurança/operação) = transversal; auth antes de qualquer exposição multiusuário.
```

## 4. Migrations previstas (planejamento; aditivas/reversíveis)
`0018` opportunity · `0019` opportunity_workflow+transition · `0020` opportunity_id (9 tabelas,
Gate 1) · `0021` backfill legado (**Gate 2**, dados) · `0022` modalidade/intake · `0023`
docs+jurídico 2.0 · `0024` checklist dinâmico · `0025` parâmetros financeiros · `0026` hard
stops/decisão · `0027` lance/pagamento/registro · `0028` reforma/regularização · `0029`
saída/encerramento · `0030` radar/conectores · `0031` users/roles. Cada uma: upgrade+downgrade
em banco descartável; sem tocar dados existentes (colunas nullable).

## 5. Estratégia de commits/PRs
- Um domínio/arquivo-quente por PR; migration única por PR; mensagem com escopo + preservação.
- `models.py`: adição de classes e adição de colunas em PRs **distintos e sequenciais**.
- Toda onda abre com testes (vermelho→verde) e fecha com evidência anexada.

## 6. Ciclo 3 — validação e fechamento
- Regressão + compatibilidade (diff OpenAPI); **re-executar suíte em banco descartável**.
- E2E por modalidade/fonte suportada + fluxos alternativos (descartada/suspensa/sem lance/
  reaberta/adquirida).
- Isolamento multi-oportunidade, concorrência, idempotência, integridade histórica.
- Validação financeira por casos conhecidos + revisão de fórmulas.
- Revisão jurídica/proveniência; segurança/RBAC; backup→restore em ambiente isolado; runbooks.
- **Guarda do 633:** teste de não regressão (V1–V9/`financial_analyses`/`llm_runs`/27 keys) em
  toda a validação; **sem** criar V10 nem rodar LLM no 633.
- **Saída:** relatório de aceite 100% (todos itens `PRODUCT-SCOPE-100` CONCLUIDO ou exclusão
  formal), limitações residuais explícitas, versão candidata.

## 7. Definição de pronto por onda (DoD)
1. Diff de código revisado; 2. testes da onda verdes com log; 3. migration upgrade/downgrade
ok; 4. docs/STATUS/HISTORY atualizados (append); 5. limitações listadas; 6. evidência de
preservação do 633; 7. commit rastreável; 8. gates transversais G-01..G-10 satisfeitos.

## 8. Riscos e mitigação (plano)
| Risco | Mitigação |
|---|---|
| Regressão de contrato (M0) | baseline + diff OpenAPI por PR |
| Quebra de histórico (opportunity) | nullable/legado; backfill só Gate 2 + pg_dump |
| Hard stop mascarado por score | trilha binária separada; teste proíbe aprovação com hard stop |
| Upload malicioso/grande | limite de tamanho + MIME + streaming (Onda 3) |
| Dependência externa | marcar BLOQUEADO; nunca simular; fluxo manual como fallback |
| Escopo "100%" inflar | medir por evidência/validação (Ciclo 3), não por documentação |

## 9. Como autorizar em poucos prompts
- **Prompt 1 (Ciclo 2):** "Autorizo o Ciclo 2 a partir da Onda 0, respeitando Gates 1 e 2 e os
  critérios de aceite por onda." → Kiro executa ondas sequenciais, parando nos gates.
- **Prompt 2 (Ciclo 3):** "Autorizo o Ciclo 3 de validação e o relatório de aceite 100%." →
  Kiro roda a bateria de validação em banco descartável e produz o relatório.
