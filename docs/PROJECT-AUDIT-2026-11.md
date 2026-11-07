# PROJECT AUDIT — Radar Leilão (Ciclo 1) — 2026-11

> **Natureza:** auditoria factual do repositório real (código, migrations, testes, config), não
> da documentação. **Ciclo 1 = auditoria e preparação.** Nenhum código/modelo/migration/dado/
> endpoint/UI foi alterado ou executado. Nenhuma análise LLM, chamada externa paga ou scraping.
> Alterações nesta etapa são **apenas documentais**.

## 0. Baseline (evidência de preservação)

| Item | Valor |
|---|---|
| Branch | `main` |
| HEAD auditado | `4c2319f` |
| Working tree | **limpo** (sem alterações pendentes) |
| Sincronização | `origin/main` == `HEAD` (`0 0`) |
| Migration head (real) | `0017_central_juridica` (cadeia linear `0001 → 0017`) |
| Docker | 4 serviços: `postgres` (pgvector/pg16), `backend`, `judicial_api`, `frontend`; volumes `postgres_data`, `backend_storage`; **sem** worker/redis/minio/s3 |
| Testes | 50 `tests/test_*.py` + `tests/judicial/`; `conftest.py` exige `RAG_TEST_DATABASE_URL` (senão `skip`), usa savepoint/rollback |

**Execução de testes nesta auditoria:** **NÃO executada por precaução.** A suíte exige um
PostgreSQL de teste (`RAG_TEST_DATABASE_URL`); o prompt proíbe tocar banco persistente/produtivo
sem ambiente descartável garantido. Resultados **registrados** (não re-executados nesta data):
backend **613 passed / 2 skipped**, frontend **137 passed** (commits anteriores). O Ciclo 3
deve re-executar tudo em banco descartável dedicado e anexar logs.

**Preservação confirmada por não-ação:** nenhuma escrita foi feita; property 633, análises
V1–V9, `financial_analyses` V1–V9, `llm_runs`, 27 `canonical_key` e Central Jurídica permanecem
exatamente como estavam no HEAD `4c2319f`.

## 1. Metodologia da matriz de status

- Estados (ROADMAP §9 / ACCEPTANCE §1): `NAO_INICIADO`, `ESPECIFICADO`, `EM_DESENVOLVIMENTO`,
  `IMPLEMENTADO`, `VALIDADO`, `CONCLUIDO`, `BLOQUEADO`. Acrescento `NAO_AUDITADO` quando não
  houve como confirmar por evidência.
- **Regra:** nenhum item é `VALIDADO`/`CONCLUIDO` só por documentação. Separo três progressos:
  **Especificação**, **Implementação** e **Validação**. "Implementado" = código integrado, ainda
  sem validação completa nesta auditoria (a suíte não foi re-executada aqui).
- Evidência = arquivo/classe/endpoint/migration/teste real.

## 2. Matriz por domínio do PRODUCT-SCOPE-100

> Legenda de progresso: Esp. (especificação) · Impl. (implementação) · Val. (validação nesta auditoria).

### A. Descoberta e radar — **NAO_INICIADO** (Esp. parcial / Impl. 0 / Val. 0)
| Evidência | O que existe | O que falta |
|---|---|---|
| `PropertySource` + CRUD `/api/imoveis/{id}/fontes` | cadastro **manual** de fontes/links | conectores/ingestão automatizada, dedupe de oportunidade, atualização incremental, fila de triagem, proveniência/retries |
Dependências: domínio Opportunity (B). Risco: scraping proibido — exclusão explícita do escopo. Aceite pendente: ingestão autorizada + dedupe rastreável.

### B. Property e Opportunity — **ESPECIFICADO** (Esp. alta / Impl. 0 / Val. 0)
| Evidência | O que existe | O que falta |
|---|---|---|
| specs `SPEC-OPPORTUNITY-DOMAIN/ISOLATION`, `MATRIZ-OPPORTUNITY-ID`; grep `opportunity` em `backend/app` = **0** | `Property` existente; decisões de modelagem fixadas | modelos `Opportunity`/`OpportunityWorkflow`/`WorkflowTransition`, coluna `opportunity_id` (9 tabelas), isolamento, testes de não vazamento |
Dependências: M0 (modularização) recomendável antes. Risco: quebra de histórico — mitigado por `opportunity_id` nullable/legado. Aceite pendente: testes T-ISO.

### C. Documentos e inteligência — **IMPLEMENTADO** (Esp. alta / Impl. alta / Val. parcial-registrada)
| Evidência | O que existe | O que falta |
|---|---|---|
| `documents/pipeline.py` (hash sha256, versão, markdown, chunks, OCR opcional, embedding), RAG `rag/` híbrido, `extraction.py` (matrícula/edital com referência) | upload/versão/OCR/evidência/busca lexical+semântica com fallback | **validação de tamanho/MIME no upload** (hoje só extensão; `await file.read()` carrega tudo em memória), classificação documental ampla, detecção de documento desatualizado |
Risco: upload sem teto de tamanho (DoS/memória). Aceite pendente: teste de upload malicioso/limite.

### D. Jurídico — **IMPLEMENTADO (1.0)** (Esp. alta / Impl. média-alta / Val. parcial)
| Evidência | O que existe | O que falta |
|---|---|---|
| `Legal*` (migration 0017), `legal_service.py`, `legal_catalog.py`, `legal_correlation.py`, `judicial_integration.py`; `CENTRAL-JURIDICA.md` | fonte/dispositivo/regra com texto oficial separado da paráfrase; vínculo ao checklist; correlação processo×imóvel (CPF/CNPJ); separação fato/hipótese nos agentes | metadados 2.0 (vigência estruturada, redação histórica, jurisprudência estruturada, aplicabilidade por modalidade/jurisdição, revisor/próxima revisão); embeddings da biblioteca em produção |
Aceite pendente: `MATRIZ-CURADORIA-JURIDICA` P0/P1.

### E. Due diligence — **IMPLEMENTADO** (Esp. alta / Impl. alta / Val. parcial)
| Evidência | O que existe | O que falta |
|---|---|---|
| `checklist.py` (27 `canonical_key`), `ChecklistExecution/Result`, `DueDiligenceFront` (0016), `due_diligence_overview` | checklist mestre versionado + 4 frentes de DD; estados + evidência | checklist **dinâmico por modalidade/UF/fase** (hoje fixo), estados ampliados (7→10), snapshot por oportunidade, reabertura por fato |
Risco: expansão sem renomear os 27. Aceite pendente: `MATRIZ-CHECKLIST-MODALIDADE`.

### F. Financeiro e mercado — **IMPLEMENTADO (parcial)** (Esp. alta / Impl. média-alta / Val. parcial)
| Evidência | O que existe | O que falta |
|---|---|---|
| `finance.py` (breakdown, resultado líquido, margem, ROI_operacao, break-even, yield, preço máximo por meta, cenários), `market.py` (comparáveis, CV, amostra mín. 7), `FinancialAnalysis` | cálculo determinístico anti-dupla-contagem; cenários BASE/OTIMISTA/PESSIMISTA; separação informado/estimado/desconhecido | **TIR/VPL/fluxo de caixa descontado/payback**, **sensibilidade paramétrica**, **parâmetros por jurisdição/ato/vigência** (hoje categorias fixas), estimativa de valorização/liquidez formal |
Aceite pendente: `MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS` + casos de referência reconciliados.

### G. Decisão e workflow — **ESPECIFICADO** (Esp. alta / Impl. parcial-legado / Val. 0)
| Evidência | O que existe | O que falta |
|---|---|---|
| `risk_engine.py`, `verdict_engine.py` (veredito global); specs `SPEC-WORKFLOW-ENGINE/HARD-STOPS/INVALIDATION`; grep `workflow` em `backend/app` = **0** | riscos + veredito global por análise; event-sourcing (`DomainEvent`/`EntityHistory`); reanálise incremental | **máquina de estados F0–F13**, gates, **hard stops CONFIRMADO** separados de score, decisão humana versionada, invalidação por evento, idempotência/concorrência de transição |
Aceite pendente: T-HS/T-INV + G-02/G-03/G-08.

### H. Aquisição e pós-arrematação — **IMPLEMENTADO (parcial)** (Esp. alta / Impl. média / Val. parcial)
| Evidência | O que existe | O que falta |
|---|---|---|
| `PostAuction*` (0015): etapas, custos previsto/realizado/pago, contatos, consultorias, minutas; `MODULO-POS-ARREMATACAO.md` | fluxo pós-arrematação com custos e posse/notificação | **F9 lance/pagamento/resultado** (inexistente como domínio), modelagem registral formal (prenotação, baixa de ônus), eventos excepcionais (desistência/anulação/reversão) |
Risco: `post_auctions.property_id UNIQUE` (1 por imóvel) vs 1 por oportunidade — decisão: manter nesta etapa. Aceite pendente: F9/F10.

### I. Rentabilização e encerramento — **NAO_INICIADO** (Esp. média / Impl. 0 / Val. 0)
| Evidência | O que existe | O que falta |
|---|---|---|
| projeção em `finance.py`, `MarketComparable` | base de projeção | domínio de venda/locação/holding, contratos, receitas/despesas realizadas, projetado×realizado, encerramento (F12/F13) |
Aceite pendente: fluxo de encerramento + reconciliação.

### J. Plataforma, UX e operação — **PARCIAL** (Esp. média / Impl. média / Val. parcial)
| Evidência | O que existe | O que falta |
|---|---|---|
| frontend 17 abas (`PropertyDetailPage`), hubs globais, UI kit; `logging_config`; `/health`; `scripts/backup.sh`; `OPERATIONS.md`/`DB-MAINTENANCE.md` | dossiê por imóvel, hubs, logs, backup básico | **dashboard de oportunidade/carteira/radar**, **RBAC/auth**, auditoria de ações por usuário, **métricas/tracing/alertas**, **CI/CD**, restore testado/documentado, política de retenção |
Risco: sem auth = bloqueador para uso multiusuário/produção. Aceite pendente: G-06/G-07.

## 3. Matriz por fase F0–F13

| Fase | Estado | Evidência | Gap principal |
|---|---|---|---|
| F0 Radar/descoberta | **NAO_INICIADO** | só `PropertySource` manual | ingestão/dedupe/snapshot |
| F1 Classificação/modalidade | **NAO_INICIADO** (campo texto livre) | `Property.modality` string | enum + triagem com evidência |
| F2 Cadastro/estruturação (Property×Opportunity) | **ESPECIFICADO** | specs; 0 código opportunity | modelos + isolamento |
| F3 Análise documental | **IMPLEMENTADO** | pipeline+RAG+extração | validação upload; classificação |
| F4 Análise jurídica | **IMPLEMENTADO (1.0)** | Central Jurídica 0017 | metadados 2.0 |
| F5 Due diligence | **IMPLEMENTADO** | checklist 27 + DD 0016 | checklist dinâmico/estados |
| F6 Financeiro | **IMPLEMENTADO (parcial)** | `finance.py` | TIR/VPL/sensibilidade/parametrização |
| F7 Mercado/valuation | **IMPLEMENTADO (parcial)** | `market.py` | valuation/liquidez/valorização formal |
| F8 Comitê/decisão | **ESPECIFICADO** | verdict global; specs hard stop | score por dimensão + hard stops + decisão versionada |
| F9 Aquisição/lance | **NAO_INICIADO** | — | domínio lance/pagamento/resultado |
| F10 Arrematação/pagamento/registro | **IMPLEMENTADO (parcial)** | Pós-Arrematação 0015 | registro formal, pagamentos de certame |
| F11 Transferência/posse | **IMPLEMENTADO (parcial)** | Pós-Arrematação (posse/notificação) | regularização/averbação formal |
| F12 Regularização/preparação | **NAO_INICIADO** | — | reforma/regularização dedicada |
| F13 Rentabilização/encerramento | **NAO_INICIADO** | — | venda/locação/holding + realizado |

## 4. Progresso global (metodologia explícita, sem “chute”)

Ponderação por fase com peso igual (14 fases) e crédito: `NAO_INICIADO=0`, `ESPECIFICADO=0,15`,
`IMPLEMENTADO parcial=0,5`, `IMPLEMENTADO=0,65`, `VALIDADO=0,85`, `CONCLUIDO=1`. **Nenhuma fase
está VALIDADO/CONCLUIDO** nesta auditoria (a suíte não foi re-executada aqui).

| Dimensão | Cálculo | Resultado aproximado |
|---|---|---|
| **Especificação** | specs mestres + M0/B1 + matrizes cobrem todo o F0–F13 | ~80% |
| **Implementação** | F3/F4/F5 (0,65) + F6/F7/F10/F11 (0,5) + F2/F8 (0,15) + F0/F1/F9/F12/F13 (0) | **≈ 35%** |
| **Validação (nesta auditoria)** | suíte não re-executada; sem evidência nova | **0% nesta data** (histórico registrava verde) |
| **Global ponderado (impl.)** | média das 14 fases pelos créditos acima | **≈ 33–36%** |

> O número é **indicativo de implementação**, não de produto aceito. O "100%" do
> `PRODUCT-SCOPE-100` depende de validação (Ciclo 3) com evidência, que não foi feita aqui.

## 5. Confronto documental (divergências, sem apagar histórico)

| Documento | Afirmação | Estado real auditado | Ação |
|---|---|---|---|
| `PROJECT-STATUS` (seções antigas) | head de migration `0011` | head real **`0017_central_juridica`** | já sinalizado na §30; mantido histórico |
| `PROJECT-STATUS` (2025) | "MVP ENCERRADO" | núcleo MVP existe, mas escopo 100% está ~1/3 implementado | registrar como marco histórico, não estado atual |
| `ROADMAP-MASTER` §7 | decisões de arquitetura "aprovadas" | coerentes com o código (opportunity ainda não implementado) | OK, é visão-alvo |
| `TODO-WORKFLOW-FOUNDATION` | fundação planejada | 0 código de workflow (só specs) | manter como backlog |
| `PRODUCT-SCOPE-100` | checklist A–J | A/I/F12/F13 `NAO_INICIADO`; B/G `ESPECIFICADO` | refletido nesta matriz |
| `DB-MAINTENANCE.md` | `pg_dump -U postgres` | compose usa usuário **`radar`** | **inconsistência** a corrigir no Ciclo 2 (doc) |
| `ROADMAP-MASTER` baseline `52a3eb9` | — | HEAD avançou para `4c2319f` (add docs-mestre + prompt ciclo) | normal; registrar |

Nenhuma informação antiga foi apagada; as divergências ficam registradas aqui e nas notas
append das seções novas de STATUS/HISTORY.

## 6. Principais gaps (priorizados)

1. **Fundação ausente em código:** Opportunity/Workflow (B/G/F8) — tudo só em spec.
2. **Sem auth/RBAC/auditoria por usuário** (J) — bloqueador de produção/multiusuário.
3. **F0/F1 radar+modalidade** — sem ingestão nem triagem estruturada.
4. **Financeiro** sem TIR/VPL/sensibilidade e sem parametrização por jurisdição/vigência.
5. **F9 lance/pagamento** e **F12/F13 reforma/saída/encerramento** inexistentes.
6. **Qualidade/operação:** sem CI/CD, sem métricas/tracing, upload sem limite de tamanho/MIME,
   restore não documentado; testes faltando (contrato OpenAPI, isolamento multi-oportunidade,
   concorrência no core, auth, E2E por modalidade).
7. **Jobs/assíncrono:** ingestão/processamento pesado roda inline no request.

## 7. Dependências externas (não resolvíveis só por código)
- Portais de leilão (Biasi/Globo/…): termos/API/autorização — **exclusão** do 100% quando proibido.
- RI Digital / Prefeitura / DataJud: credenciais/contratação — `BLOQUEADO/DEPENDÊNCIA EXTERNA`.
- Google Maps: API key + billing.
- OpenAI: chave para embeddings/LLM (sistema sobe sem; validações sem LLM).

## 8. Conformidade do Ciclo 1
- ✅ Só documentação criada/alterada; nenhum código/modelo/migration/dado/endpoint/UI tocado.
- ✅ Nenhum LLM real, chamada externa paga ou scraping executado.
- ✅ Nenhum comando destrutivo; suíte de testes **não** executada (precaução de ambiente).
- ✅ 633/V1–V9/`financial_analyses` V1–V9/`llm_runs`/27 `canonical_key`/Central Jurídica intactos.
