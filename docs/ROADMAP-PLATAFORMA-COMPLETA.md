# ROADMAP — Radar Leilão | Plataforma Completa (Fase Zero: diagnóstico)

> **Natureza deste documento:** entregável da **Fase Zero** do `docs/PROMPT-KIRO-PLATAFORMA-COMPLETA.md`.
> É **diagnóstico e plano** — nenhuma funcionalidade foi implementada nesta etapa. Nenhum
> dado, migration, modelo, endpoint ou teste de aplicação foi alterado. O imóvel **633**,
> o histórico **V1–V9**, os **27 `canonical_key`** e a baseline de **llm_runs** permanecem
> intactos.
>
> **Método do diagnóstico:** leitura direta do código (`backend/app/`, `frontend/src/`,
> `backend/migrations/`, `tests/`), do `.env.example` (o `.env` real **não** foi lido) e dos
> documentos `PROJECT-STATUS.md`, `SPEC-VIBE-CODING-RADAR-LEILAO.md`,
> `PROMPT-KIRO-PLATAFORMA-COMPLETA.md` e `TODO-PLATAFORMA-COMPLETA.md`. Os testes **não**
> foram executados nesta etapa; a cobertura abaixo reflete a **existência** de arquivos de
> teste, não um resultado de execução.

---

## 1. Sumário executivo

O Radar Leilão hoje é um **analisador de dossiê por imóvel** maduro: cadastro, documentos
versionados + OCR/RAG, extração estruturada de matrícula/edital, 5 agentes LLM com
separação explícita entre interpretação (LLM) e cálculo/veredito (determinístico),
Checklist Mestre de 27 itens, motores de Risco e Veredito, histórico append-only com
reanálise incremental por evento, due diligence integrada (4 frentes), pós-arrematação e
Central Jurídica 1.0. Arquitetura: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL/pgvector
+ React/TypeScript. **47 modelos, 17 migrations (head `0017_central_juridica`), ~130 rotas.**

O alvo do prompt é maior: uma **plataforma orientada a workflow** com estado por fase
(F0→F13), **triagem de modalidade**, **gates/comitê com hard stops**, **custos
parametrizados por jurisdição/ato/vigência**, **Central Jurídica 2.0** (vigência, redação
histórica, jurisprudência estruturada, aplicabilidade), **lance/pagamento**, **reforma/
venda/locação** e **segurança/LGPD/observabilidade**.

Em uma frase: **a base de "analisar um imóvel" está sólida e reutilizável; falta a camada de
"conduzir um imóvel por um processo" (máquina de estados por fase + gates) e vários
domínios de fase tardia (F9, F11 reforma, F12 saída) e transversais (modalidade, auth/RBAC,
custos parametrizados).**

### Veredito de prontidão por fase (resumo da matriz da §4)

| Fase | Tema | Estado hoje |
|---|---|---|
| F0 | Intake/descoberta/snapshot/dedupe | 🟡 Parcial (cadastro existe; falta snapshot/dedupe/detecção de mudança) |
| F1 | Triagem/classificação de modalidade | 🔴 Ausente (nada classifica modalidade) |
| F2 | Cofre documental + OCR | 🟢 Forte (versões, chunks, RAG, extração) — falta supersedes/validade/confidencialidade |
| F3 | Jurídico pré-leilão | 🟡 Parcial (matrícula/edital/processos/correlação existem; falta cadeia registral e conferência estruturada edital×matrícula) |
| F4 | Fiscal/condomínio/operacional | 🟡 Parcial (Debt + frente PREFEITURA; falta dívida ativa, sub-rogação modelada, zoneamento/habite-se) |
| F5 | Localização/inspeção | 🟡 Parcial (geocode + checklist de localização; falta vistoria estruturada) |
| F6 | Ocupação/posse | 🟡 Parcial (OccupancyAnalysis + pós-arrematação contatos/minutas; falta classificação formal e simulador art. 37-A validado) |
| F7 | Viabilidade financeira | 🟡 Forte-parcial (motor robusto; falta TIR/VPL/fluxo descontado, sensibilidade paramétrica e custos por jurisdição/ato/vigência) |
| F8 | Comitê/decisão | 🔴 Parcial-fraco (Verdict existe, mas não é comitê multidimensional com hard stops e decisão humana versionada) |
| F9 | Lance/pagamento | 🔴 Ausente |
| F10 | Transferência/registro | 🟡 Parcial (Pós-Arrematação cobre etapas/custos; falta modelagem registral formal) |
| F11 | Posse/regularização/reforma | 🟡 Parcial (posse/notificação existem; reforma/regularização sem modelo dedicado) |
| F12 | Exploração/saída (venda/locação/holding) | 🔴 Ausente (sem modelo de venda/locação/resultado realizado) |
| F13 | Encerramento/dossiê | 🟡 Parcial (status e histórico existem; falta dossiê exportável e retrospectiva projetado×realizado) |

Legenda: 🟢 existe e cobre bem · 🟡 existe parcialmente / precisa de evolução · 🔴 ausente.

---

## 2. Arquitetura atual (como o código realmente é)

- **Backend:** FastAPI monolítico em `backend/app/main.py` — **~130 rotas declaradas direto no
  `app`, sem `APIRouter`/`include_router`**. Domínio em módulos determinísticos
  (`finance.py`, `market.py`, `risk_engine.py`, `verdict_engine.py`, `impact.py`,
  `incremental.py`, `consolidation.py`, `legal_correlation.py`, `legal_service.py`,
  `extraction.py`, `evidence.py`, `knowledge_memory.py`, `judicial_*`, `geocoding_client.py`).
- **IA:** `backend/app/ai/` — 5 agentes (`DocumentAgent`, `LegalAgent`, `FinancialAgent`,
  `MarketAgent`, `ChecklistAgent`), `Supervisor`, `orchestrator`, LangGraph
  (`LOAD_CONTEXT → RETRIEVE_RAG → RUN_AGENTS → CONSOLIDATE`), `gateway` (degrada sem chave),
  `contracts` Pydantic. **LLM só interpreta/extrai; cálculo e veredito são determinísticos.**
- **RAG:** `backend/app/rag/` — `HybridRetriever` (pgvector cosine + full-text PT, pesos
  0.7/0.3), fallback textual sem chave, RAG direcionado por item de checklist.
- **Persistência:** PostgreSQL/pgvector; SQLAlchemy 2.0 (`Mapped`); Alembic cadeia linear
  `0001 → 0017` (head `0017_central_juridica`).
- **Frontend:** React/Vite/TS. Dossiê em `PropertyDetailPage.tsx` com **17 abas**
  (`detailSections`), seções `*Section.tsx` + testes, serviços `services/*.ts`, UI kit em
  `components/ui/`.
- **Event-sourcing leve:** `DomainEvent` + `EntityHistory` (before/after) alimentam
  `ImpactAnalyzer` → `IncrementalAnalysisService` (reanálise por evento). Base perfeita para
  a futura máquina de estados de workflow.
- **Rastreabilidade:** `Evidence`/`EvidenceLink`, `LLMRun`/`LLMPricing`, extração com
  referência obrigatória por campo. Alinhado às regras inegociáveis do prompt.

### O que já está alinhado às regras inegociáveis do prompt
- Separação fato/interpretação/hipótese/ausência nos `Finding` (contracts).
- Histórico append-only + before/after (`EntityHistory`, `ChecklistResult.previous_result_id`,
  versões imutáveis de documento/minuta).
- LLM não calcula nem decide (engines determinísticos); GET/CRUD não dispara análise.
- Integrações externas "falham fechado" (sem chave → `NAO_CONFIGURADO`, nunca simulam sucesso).
- Correlação processo×imóvel distingue homônimo de identidade (CPF/CNPJ exato = ALTA).
- Central Jurídica separa texto oficial de orientação prática; nunca inventa norma.

---

## 3. Arquitetura-alvo (incremento, não reescrita)

O prompt pede evolução **reuse-first**. A arquitetura-alvo é a atual **mais** três camadas:

1. **Camada de Workflow (máquina de estados por fase F0–F13).** Um agregado
   `PropertyWorkflow`/`WorkflowStageState` (nomes a definir em ADR) que registra, por imóvel,
   em que fase está, o estado de cada fase, gates satisfeitos/pendentes e transições — tudo
   sobre o `DomainEvent`/`EntityHistory` já existente. **Não substitui** nenhum domínio atual;
   orquestra-os.
2. **Camada de Classificação/Modalidade (F1).** `modality` + evidência exigida, que
   parametriza quais checklists/custos/regras jurídicas se aplicam. Transversal.
3. **Camada de Decisão/Gates (F8).** Score por dimensão (jurídico, documental, físico,
   ocupação, fiscal, mercado, financeiro, liquidez, execução) + **hard stops que o score não
   mascara** + decisão humana versionada. Reaproveita `Risk`/`Verdict` como insumos.

Modularização recomendada (ADR): migrar `main.py` monolítico para `APIRouter` por domínio,
**sem alterar contratos de rota** (só organização). Isso é pré-requisito saudável para os
épicos, mas deve ser um épico próprio, pequeno e com testes de não regressão de rota.

> **Princípio de decisão para novas tabelas (regra do prompt §7):** antes de criar tabela,
> demonstrar que uma entidade existente não atende e registrar um **ADR**. A §4 abaixo já
> indica, por capacidade, o candidato a reuso antes de propor novo modelo.

---

## 4. Matriz: capacidade atual × gap × reuso × implementação × teste

> Esforço: **P** (pequeno, dias) · **M** (médio, 1–2 semanas) · **G** (grande, 2+ semanas /
> requer ADR + migration estrutural). Cobertura de teste = **arquivos de teste existentes**
> (não execução).

### 4.1 Por fase do workflow (F0–F13)

| Fase | Capacidade-alvo | Existe hoje? | Gap | Reuso principal | Esforço | Teste atual |
|---|---|---|---|---|---|---|
| **F0** | Intake, origem/URL, snapshot versionado, detecção de mudança (edital/preço/data/status), dedupe sem fundir | Parcial | Falta snapshot de intake, diff de mudança e dedupe; `PropertySource` guarda fontes mas não versiona snapshot nem detecta mudança | `Property`, `PropertySource`, `DomainEvent`, `EntityHistory` | M | `test_cadastro_completo`, `test_integration_flows` |
| **F1** | Classificar modalidade (JUDICIAL / EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA / EXTRAJUDICIAL_OUTRA_GARANTIA / VENDA_DIRETA / INDEFINIDO) exigindo evidência no edital | **Ausente** | Nada classifica modalidade; `Auction`/`AuctionNotice` não têm `modality` com evidência; regras não variam por modalidade | `AuctionNotice`, `extraction.py`, `Evidence` | M | — |
| **F2** | Cofre documental versionado + OCR com página/trecho; `supersedes`; `NAO_LOCALIZADO`; validade/confidencialidade/período coberto | Forte (parcial) | Versões/chunks/extração OK; faltam campos `supersedes`, `valid_until`, `confidentiality`, `period_covered`, `protocol` e estado `NAO_LOCALIZADO` por campo | `Document`, `DocumentVersion`, `DocumentChunk`, `extraction.py`, RAG | M | `test_documents`, `test_document_intelligence`, `test_extraction` |
| **F3** | Jurídico pré-leilão: edital integral, matrícula/ônus, cadeia registral, correspondência edital×matrícula×endereço×unidade×fração, intimação mora, art. 26/27, processos, homônimo×correlação, resultado com escopo | Parcial | Matrícula/edital/processos/correlação existem; **faltam**: cadeia registral estruturada, conferência cruzada edital×matrícula, estados de resultado (`RISCO_CRITICO`/`INCONCLUSIVO`/…), vínculo a dispositivos da Central Jurídica | `PropertyRegistration`, `AuctionNotice`, `LegalProcess`, `legal_correlation.py`, `DueDiligenceFront(MATRICULA/JUDICIAL)`, `Legal*` | G | `test_processes`, `test_legal_correlation`, `test_matricula_edital`, `test_judicial_integration_pg`, `test_central_juridica` |
| **F4** | Fiscal/condomínio/operacional: IPTU, dívida ativa, exercícios, sub-rogação, condomínio detalhado, água/luz/gás, certidões contextuais, zoneamento/tombamento/habite-se/área | Parcial | `Debt` genérico + frente PREFEITURA; **faltam**: modelo de certidão contextual, sub-rogação explícita, urbanismo/zoneamento/habite-se, decomposição do débito condominial (principal/multa/juros/honorários) | `Debt`, `DueDiligenceFront(PREFEITURA)`, `finance.py` | G | `test_costs_debts`, `test_due_diligence` |
| **F5** | Localização + inspeção/vistoria: geocode com fonte/precisão, entorno, riscos ambientais, vistoria datada | Parcial | Geocode + checklist de localização OK; **falta** vistoria estruturada (fachada/áreas comuns/conservação/fotos datadas) e limitação explícita "sem vistoria interna" | `PropertyLocation`, `geocoding_client.py`, `DueDiligenceFront(LOCALIZACAO)` | M | `test_due_diligence` |
| **F6** | Ocupação/posse: classificar (desocupado/proprietário/locatário/terceiro/incerto), locação averbada, negociação voluntária documentada, simulador art. 37-A validado, proibir autotutela | Parcial | `OccupancyAnalysis` + pós-arrematação (contatos/tentativas/consultorias/minutas) existem; **faltam**: taxonomia formal de ocupante/fundamento, simulador de taxa de ocupação com validação de incidência, vínculo à Central Jurídica | `OccupancyAnalysis`, `OccupantContact`, `ContactAttempt`, `NotificationDraft*`, `Consultancy*`, `Legal*` | M | `test_occupancy`, `test_pos_arrematacao` |
| **F7** | Viabilidade financeira: cenários, custos por jurisdição/ato/base/vigência, break-even, preço máximo, margem, **ROI/TIR/fluxo de caixa/sensibilidade**, IR condicional | Forte (parcial) | Motor robusto (breakdown, resultado líquido, margem, ROI, break-even, preço máximo, cenários); **faltam**: TIR/VPL/fluxo descontado, grid de sensibilidade paramétrica, **parametrização de custos por jurisdição/ato/vigência** (hoje categorias fixas), memória de cálculo por fonte/data-base | `finance.py`, `FinancialAnalysis`, `Auction.financial_assumptions`, `Cost`, `Debt` | G | `test_finance`, `test_finance_assumptions`, `test_e2e_financeiro`, `test_finance_agent` |
| **F8** | Comitê/decisão: score por dimensão, **hard stops não mascarados por média**, pendências/preço máximo/validade temporal, decisão humana versionada, invalidação por mudança | Parcial-fraco | `VerdictEngine` dá veredito global (FAVORAVEL/ATENCAO/DESFAVORAVEL/INCONCLUSIVO) a partir de riscos/pendências; **não** há score por dimensão, hard stops explícitos, registro de decisão humana (responsável/data/justificativa) nem invalidação automática por mudança de premissa | `Risk`, `Verdict`, `verdict_engine.py`, `Analysis`, `DomainEvent` | G | `test_verdict_engine`, `test_verdict_execution_divergence` |
| **F9** | Lance/pagamento: calendário, lance máximo aprovado, incrementos, comprovantes, resultado, pagamento/comissão/guias | **Ausente** | Nenhum modelo/endpoint de lance, pagamento ou resultado de leilão (distinto do cadastro do leilão) | `Auction`, `Auctioneer`, `PortalAccess`, `PostAuctionCost` | M | — |
| **F10** | Transferência/registro: auto/carta, ITBI, registro, prenotação, matrícula atualizada, baixa de ônus, titularidade | Parcial | Pós-arrematação cobre etapas/custos (incl. `REGISTRO`); **falta** modelagem registral formal (prenotação, baixa de ônus, matrícula pós-registro, conferência adquirente/fração) | `PostAuction`, `PostAuctionStage`, `PropertyRegistration` | M | `test_pos_arrematacao` |
| **F11** | Posse/regularização/reforma: entrega/chaves/termo/vistoria, regularização municipal/registral, reforma (escopo/orçamento/contratos/medições/ART-RRT) | Parcial | Posse/minutas existem em pós-arrematação; **faltam** domínio de reforma (orçamento/fornecedor/contrato/medição/aceite) e regularização (habite-se/averbação/licenças) | `PostAuctionStage`, `PostAuctionCost`, `Consultancy*` | G | `test_pos_arrematacao` |
| **F12** | Exploração/saída: venda, reforma-e-venda, locação, holding; comparar projetado×realizado (lucro/ROI/TIR/prazo/desvio) | **Ausente** | Sem modelo de estratégia de saída, contrato de venda/locação, nem resultado realizado vs projetado | `finance.py` (projeção), `MarketComparable`, `PostAuction` | G | — |
| **F13** | Encerramento: dossiê exportável, status final, retrospectiva/indicadores, histórico não sobrescrito | Parcial | `Property.status` + histórico existem; **faltam** estados finais (VENDIDO/LOCADO/…), export de dossiê e retrospectiva | `Property`, `Verdict`, `Analysis`, `EntityHistory` | M | `test_integration_flows` |

### 4.2 Capacidades transversais

| Tema | Existe hoje? | Gap | Reuso | Esforço | Teste atual |
|---|---|---|---|---|---|
| **Checklist dinâmico** | Parcial | 27 `canonical_key` preservados; 7 estados (vs 10 do prompt); **sem** variação por modalidade/UF/fase/tipo nem campos criticidade/hard stop/validade/responsável | `ChecklistItem`, `ChecklistExecution`, `ChecklistResult`, `checklist.py`, `Legal*` | G | `test_checklist`, `test_checklist_execution_selection`, `test_checklist_retrieval` |
| **Central Jurídica 2.0** | Parcial (1.0) | Texto oficial vs paráfrase e vínculo ao checklist existem; **faltam** redação histórica/vigência estruturada, jurisprudência (número/órgão/tese/data/fonte), aplicabilidade por modalidade/jurisdição (APLICAVEL/CONDICIONAL/REFERENCIA/NAO_APLICAVEL/INDETERMINADO), revisor/próxima revisão | `LegalSource`, `LegalProvision`, `LegalRule`, `LegalRuleChecklistLink`, `legal_service.py` | G | `test_central_juridica` |
| **Custos/tributos parametrizados** | Ausente | Categorias de custo fixas; **sem** tabela por jurisdição/ato/base/vigência/fonte (ITBI, emolumentos, FUNREJUS, ISSQN, FUNDEP, selo, IR) | `finance.py`, `Cost`, `Debt` | G | `test_finance*` |
| **Autenticação/usuários/RBAC** | **Ausente** | Nenhuma tabela de usuário/papel; endpoints abertos (exceto `X-Portal-Admin-Token` pontual) | — (novo domínio) | G | — |
| **LGPD (minimização/retenção/mascaramento/trilha)** | Parcial | Trilha (`EntityHistory`) e segredo de portal cifrado existem; **faltam** políticas de retenção/mascaramento/acesso e classificação de dado pessoal | `EntityHistory`, `secrets_crypto.py`, `PortalAccess` | G | `test_task75_backend` |
| **Observabilidade / custo IA** | Parcial | `LLMRun`/`LLMPricing` e `ai/costs.py` existem; **faltam** limites de custo por imóvel/fase e dashboards de execução | `LLMRun`, `LLMPricing` | M | `test_llm_tracking` |
| **Integrações oficiais** | Parcial | Judicial API/DataJud e Google Maps com degradação graciosa; RI Digital e Prefeitura em fluxo manual; **portais de leilão não integrados** | `judicial_*`, `geocoding_client.py`, config DD | G | `test_judicial_*`, `test_due_diligence` |
| **Modularização de API (APIRouter)** | Ausente | `main.py` monolítico (~130 rotas) | FastAPI `APIRouter` | M | cobertura indireta das rotas |
| **Dedupe/qualidade de dados** | Ausente | Sem `DUPLICADO_POTENCIAL`/`DADOS_INSUFICIENTES`/`EM_TRIAGEM` | `Property.status`, `DomainEvent` | M | — |

### 4.3 Mapa capacidade → épico (A–M do prompt §10)

| Épico | Tema | Capacidades da matriz |
|---|---|---|
| **A** | Diagnóstico | **Esta Fase Zero** (este documento + matrizes de apoio) |
| **B** | Workflow/gates | F0 intake, F1 modalidade, máquina de estados, F8 gates/comitê, F13 encerramento |
| **C** | Evidências/documentos | F2 cofre (supersedes/validade/NAO_LOCALIZADO), rastreabilidade |
| **D** | Checklists dinâmicos | Checklist por modalidade/UF/fase + 10 estados + criticidade/hard stop |
| **E** | Central Jurídica 2.0 | Vigência/redação histórica/jurisprudência/aplicabilidade/curadoria |
| **F** | Due Diligence | F3 jurídico, F4 fiscal/condomínio/urbanismo, F5 localização/vistoria |
| **G** | Ocupação/posse | F6 taxonomia, simulador art. 37-A, negociação documentada |
| **H** | Financeiro | F7 TIR/VPL/sensibilidade + custos parametrizados por jurisdição/ato/vigência |
| **I** | Comitê/lance | F8 score/hard stops/decisão humana + F9 lance/pagamento |
| **J** | Pós-arrematação/registro | F10 transferência/registro formal (sobre Pós-Arrematação) |
| **K** | Reforma/locação/venda | F11 reforma/regularização + F12 saída/realizado×projetado |
| **L** | Relatórios/auditoria | F13 dossiê exportável + retrospectiva + observabilidade |
| **M** | Integrações/segurança/observabilidade | Auth/RBAC, LGPD, integrações oficiais, custo IA, modularização API |

---

## 5. Dependências entre épicos (ordem sugerida)

```
A (diagnóstico) ──► B (workflow/gates) ──► D (checklists dinâmicos) ──► F (due diligence)
                      │                        │                          │
                      │                        └──► E (Central Jurídica 2.0)
                      │                                                    │
                      ├──► C (evidências/documentos) ─────────────────────┘
                      │
                      └──► H (financeiro) ──► I (comitê/lance) ──► J (registro) ──► K (reforma/saída) ──► L (relatórios)

M (auth/RBAC, LGPD, integrações, observabilidade, APIRouter) = transversal, começa cedo e acompanha todos.
```

Racional: **B** (máquina de estados + modalidade) destrava quase tudo, porque quase todo
domínio passa a ser parametrizado por fase/modalidade. **D** e **E** andam juntas (checklist
dinâmico consome a Central Jurídica). **H** antes de **I** (comitê depende do financeiro
completo). **M** é contínuo — especialmente **auth/RBAC antes de qualquer exposição além do
uso local**.

---

## 6. Impacto em dados, migrations e rollback (princípios)

- **Preservação absoluta:** nenhuma migration pode alterar/apagar o imóvel 633, V1–V9,
  os 27 `canonical_key` ou `llm_runs`. Toda migration é **aditiva e reversível** (padrão já
  seguido em `0015`/`0016`/`0017`: `create_table` no upgrade, `drop_table` no downgrade, sem
  tocar dados existentes).
- **Checklist:** expandir **sem** renomear/remover `canonical_key`. Novos estados e campos
  entram como colunas/novas tabelas aditivas; os 7 estados atuais continuam válidos e os 3
  novos (ex.: `DIVERGENTE`, `VENCIDO`, `BLOQUEADO`) mapeiam para os existentes quando preciso.
- **Backup/rollback obrigatórios** antes de qualquer migration (prompt §11): `pg_dump`
  previamente; cada migration testada em `upgrade` **e** `downgrade` num banco descartável.
- **Proibido** (prompt §11): `down -v`, `reset`, `truncate`, `drop` de tabela com dados,
  seed destrutivo, sobrescrever `.env`/segredos, rodar LLM no 633 / criar V10, DataJud real /
  consulta paga / scraping / lance automatizado, alterar `canonical_key`.
- **Migrations previstas (todas aditivas, uma por épico, head futura a partir de `0017`):**
  `0018` workflow/estados; `0019` modalidade; `0020` checklist dinâmico (campos+estados);
  `0021` Central Jurídica 2.0 (vigência/jurisprudência/aplicabilidade); `0022` custos
  parametrizados; `0023` comitê/decisão; `0024` lance/pagamento; `0025` reforma/saída;
  `0026` auth/RBAC. (Numeração indicativa; cada uma exige ADR próprio.)

---

## 7. Estratégia de testes (prompt §9)

Reaproveitar o padrão atual: `pytest` com `postgres_engine`/`db` (PostgreSQL real, **sem LLM
e sem rede**), fixtures de savepoint/rollback (nunca tocar dados reais), e Vitest/`tsc` no
frontend. Para a plataforma, acrescentar por épico:
- migrations testadas em **upgrade e downgrade**;
- fixtures de **modalidade** (judicial/extrajudicial/outra garantia/venda direta) e de casos
  **incompletos/divergentes/homônimos/fonte indisponível**;
- testes de **não regressão** dos 27 `canonical_key` e do histórico (imutabilidade);
- teste de que **GET/CRUD não dispara LLM** (guardas explícitas);
- teste de **hard stop** (risco crítico não mascarado por score);
- cálculos financeiros determinísticos + **sensibilidade**;
- **"nunca declarar E2E sem evidência"** — logs anexados ao fechar cada épico.

> Pendência herdada (de `PROJECT-STATUS.md`): **validação E2E real pela UI** após pull/rebuild
> ainda não foi fechada com evidências. Deve ser critério de aceite do primeiro épico de
> workflow, não pressuposto.

---

## 8. Plano incremental (antes de qualquer mudança estrutural)

O prompt exige **apresentar plano incremental antes de implementar o workflow inteiro**.
Proposta de sequência de PRs pequenos, cada um com ADR + migration reversível + testes:

1. **A1 — Documentação da Fase Zero** (este PR): ROADMAP + 5 matrizes de apoio + atualização
   de STATUS/HISTORY. **Sem código.** ← *entrega atual.*
2. **M0 — Modularização de API** (sem mudança de contrato): `main.py` → `APIRouter` por
   domínio, com testes de não regressão de rota. Habilita trabalho paralelo nos épicos.
3. **B1 — Máquina de estados de workflow (esqueleto):** agregado de fase + transições sobre
   `DomainEvent`, **somente leitura/registro**, sem alterar domínios. Migration `0018` aditiva.
4. **B2 — Modalidade (F1):** `modality` + evidência + parametrização mínima. Migration `0019`.
5. **D1 — Checklist dinâmico:** novos estados/campos aditivos, variação por modalidade.
   Migration `0020`. Preserva os 27 `canonical_key`.
6. **E1 — Central Jurídica 2.0:** vigência/jurisprudência/aplicabilidade. Migration `0021`.
7. Demais épicos (F/G/H/I/J/K/L/M) conforme §5, cada um com seu ADR e PR pequeno.

**Gate de aprovação entre A1 e M0:** o usuário revisa esta matriz e aprova o escopo/ordem
antes de qualquer alteração de código. (Este documento existe para habilitar essa decisão.)

---

## 9. Riscos e divergências identificados no diagnóstico

- **Divergência de head de migration na documentação:** seções antigas do `PROJECT-STATUS.md`
  citam head `0011_judicial_persistence`; o head **real** é `0017_central_juridica`. O STATUS
  carrega camadas históricas — a seção autoritativa precisa ser destacada (tratado na
  atualização de STATUS desta Fase Zero).
- **`main.py` monolítico** (~130 rotas) aumenta o custo de cada épico; modularizar cedo (M0).
- **Ausência de auth/RBAC** é aceitável em MVP local, mas é **bloqueador** para qualquer uso
  multiusuário/produção — deve ser decidido explicitamente antes de expor a plataforma.
- **Custos como categorias fixas** conflitam com a exigência de parâmetros por jurisdição/ato/
  vigência; é o maior item de refactor do motor financeiro (sem quebrar o atual).
- **Estados de checklist divergentes** (7 atuais vs 10 pedidos): resolver por expansão
  aditiva + mapeamento, nunca por renomeação.
- **Pendência E2E real pela UI** (herdada) continua aberta e deve ser endereçada no 1º épico.

---

## 10. Confirmação de conformidade da Fase Zero

- ✅ Diagnóstico feito por leitura de código/documentos; **nada implementado**.
- ✅ Imóvel 633, V1–V9, 27 `canonical_key`, `llm_runs` **intactos** (nenhuma escrita).
- ✅ Nenhum LLM/DataJud real executado; `.env` real **não** lido.
- ✅ Entregável principal (`ROADMAP-PLATAFORMA-COMPLETA.md`) + matrizes de apoio (ver §12 do
  prompt) produzidos como documentação.
- ⏭️ Próximo passo é **decisão do usuário** sobre escopo/ordem (gate da §8) antes de código.

---

*Documentos complementares desta Fase Zero:* `WORKFLOW-LEILAO-END-TO-END.md`,
`MATRIZ-CHECKLIST-MODALIDADE.md`, `MATRIZ-CURADORIA-JURIDICA.md`,
`MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md`, `REVISAO-ANOTACOES-LEILAO.md`,
`TODO-PLATAFORMA-COMPLETA.md` (já existente).
