# FEATURE INVENTORY — Radar Leilão

> **Auditoria de produto (somente leitura).** Inventário detalhado das funcionalidades, com
> **status real verificado no código** (não na documentação). Fonte: varredura do repositório em
> `20/09/2026` (HEAD `7f61667`). Nenhum código/migration/dado foi alterado para produzir este
> inventário.
>
> **Regra honesta:** uma funcionalidade só é `VALIDADO` quando tem teste automatizado verde e/ou
> E2E real comprovando o comportamento. `IMPLEMENTADO` = existe e funciona no código, mas a
> validação formal (teste/E2E) é parcial ou indireta. Documentação **não** conta como implementação.

## Legenda de status
- **NÃO INICIADO** — não existe no código.
- **ESPECIFICADO** — há spec/plano, sem código.
- **EM DESENVOLVIMENTO** — código parcial, não operacional ponta a ponta.
- **IMPLEMENTADO** — operacional no código.
- **IMPLEMENTADO PARCIALMENTE** — parte operacional, parte ausente.
- **VALIDADO** — implementado + teste automatizado verde e/ou E2E real.
- **BLOQUEADO** — depende de autorização/credencial/decisão externa.

## Métricas-base (contagens reais do repositório)
| Métrica | Valor |
|---|---|
| Endpoints (paths OpenAPI distintos) | 99 (131 decorators de rota) |
| Modelos ORM (`__tablename__`) | 50 |
| Migrations (cadeia Alembic) | 19 (`0001`→`0019`, head `0019_opportunity_fk`) |
| Arquivos de teste backend / funções `test_` | 54 / 658 |
| Arquivos de teste frontend / casos | 22 / 137 |
| Páginas/seções frontend | 21 |
| Commits no histórico | 287 |

---

## MÓDULO A — Núcleo de Análise do Imóvel (fluxo "analisar um imóvel")

### A1. Cadastro do imóvel/leilão (intake estruturado)
- **Objetivo de negócio:** registrar o imóvel, o leilão (1º/2º), edital, matrícula e fontes para análise.
- **Status:** VALIDADO.
- **Implementado:** CRUD completo; wizard de 5 etapas (`PropertyWizard.tsx`); cadastro transacional `POST /api/imoveis/completo`; edição cadastral; eventos/histórico (`DomainEvent`/`EntityHistory`). Modelos `Property`, `Auction`, `AuctionNotice`, `PropertyRegistration`, `PropertySource`.
- **Parcial:** —
- **Falta:** snapshot de intake versionado e detecção de mudança (é da F0/radar, ver F0).
- **Dependências:** nenhuma.
- **Riscos:** baixo.
- **Concluída quando:** (já atende) cadastro transacional + histórico com testes verdes.
- **Refs:** `backend/app/main.py` (`/api/imoveis*`), `tests/test_cadastro_completo.py`, `frontend/src/pages/PropertyWizard.tsx`.

### A2. Cofre documental (upload, versionamento, chunking, embedding)
- **Objetivo:** guardar documentos do imóvel com versões rastreáveis e indexação para RAG.
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** upload, nova versão, hash SHA-256, chunking, embedding na ingestão (falha de embedding não quebra), metadados de extração. `Document`/`DocumentVersion`/`DocumentChunk`.
- **Parcial:** não há campos de **validade**, **confidencialidade** nem relação **supersedes** no modelo; não há exclusão de documento via API.
- **Falta:** validade/validade temporal, confidencialidade, `supersedes`, período coberto, protocolo.
- **Dependências:** PostgreSQL/pgvector.
- **Riscos:** médio (gaps são requisitos da F2 evoluída).
- **Concluída quando:** campos de ciclo de vida documental + testes.
- **Refs:** `backend/app/documents/pipeline.py`, `tests/test_documents.py`, `tests/test_chunk_embedding.py`.

### A3. OCR + extração documental estruturada
- **Objetivo:** transformar PDF/edital/matrícula em dados estruturados rastreáveis.
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** detecção determinística de extração insuficiente (`assess_extraction_quality`); OCR local-first (Tesseract/Poppler) com import-guard; extração estruturada que grava `PropertyRegistration`/`AuctionNotice` + `Evidence` com referência obrigatória.
- **Parcial:** OCR **desligado por padrão** (`ocr_enabled=False`) e dependências de sistema não provisionadas no Dockerfile.
- **Falta:** OCR operante por padrão; extração sem depender de LLM (hoje a extração de campos exige chave).
- **Dependências:** Tesseract/Poppler (sistema); `OPENAI_API_KEY` (extração de campos).
- **Riscos:** médio (extração estruturada inócua sem LLM).
- **Concluída quando:** OCR provisionado + extração com teste de documento escaneado real.
- **Refs:** `backend/app/documents/normalizer.py`, `backend/app/documents/ocr.py`, `backend/app/extraction.py`, `tests/test_extraction.py`, `tests/test_document_intelligence.py`.

### A4. RAG híbrido (vetor + texto) e retrieval direcionado ao checklist
- **Objetivo:** recuperar contexto documental relevante para os agentes e o checklist.
- **Status:** VALIDADO.
- **Implementado:** busca híbrida pgvector + full-text PT com score ponderado; retrieval por item do checklist (limite por item + teto global + diversidade por documento); fallback textual determinístico sem chave.
- **Parcial:** qualidade vetorial depende de `OPENAI_API_KEY` + chunks embeddados.
- **Falta:** —
- **Dependências:** pgvector; chave (para vetorial).
- **Riscos:** baixo.
- **Concluída quando:** (atende) testes de recuperação verdes.
- **Refs:** `backend/app/rag/retriever.py`, `rag/service.py`, `rag/checklist_retrieval.py`, `tests/test_rag.py`, `tests/test_checklist_retrieval.py`.

### A5. Agentes LLM + orquestração (LangGraph)
- **Objetivo:** interpretar documentos/contexto por domínio (documental, jurídico, financeiro, mercado, checklist).
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** 5 agentes + Supervisor + grafo LangGraph (`LOAD_CONTEXT→RETRIEVE_RAG→RUN_AGENTS→CONSOLIDATE`); degradação graciosa sem chave (status `SEM_CHAVE`); persistência de `LLMRun`, evidências e findings; endpoints `/analisar` e por agente.
- **Parcial:** sem `OPENAI_API_KEY` os agentes só registram ausências (interpretação inócua); custo/rastreabilidade de LLM dependem de execução real.
- **Falta:** validação ampla da qualidade de interpretação (depende de LLM real/custo).
- **Dependências:** `OPENAI_API_KEY` (interpretação real).
- **Riscos:** médio (comportamento rico só com chave).
- **Concluída quando:** E2E com LLM real por domínio + métricas de custo (já há E2E histórico no 633).
- **Refs:** `backend/app/ai/agents.py`, `ai/graph.py`, `ai/orchestrator.py`, `ai/gateway.py`, `tests/test_*_agent.py`, `tests/test_orchestration_graph.py`.

### A6. Checklist Mestre (27 canonical_key)
- **Objetivo:** base canônica de verificação do método Radar, versionada e rastreável.
- **Status:** VALIDADO.
- **Implementado:** 27 `canonical_key`; execução/resultado versionados (`item_version`, `previous_result_id`); estados canônicos; persistência de findings do agente com exigência de evidência.
- **Parcial:** `applicable = True` fixo para todos os itens (sem aplicabilidade por modalidade).
- **Falta:** aplicabilidade por modalidade/UF/fase; criticidade/hard stop; critérios de aprovação/reprovação; dependências entre itens (checklist dinâmico — F5/épico D).
- **Dependências:** nenhuma.
- **Riscos:** médio (expansão deve ser aditiva, preservando os 27).
- **Concluída quando:** checklist dinâmico com aplicabilidade por modalidade + testes (onda futura).
- **Refs:** `backend/app/checklist.py`, `tests/test_checklist.py`, `tests/test_checklist_agent.py`.

### A7. Risk Engine (determinístico)
- **Objetivo:** derivar riscos rastreáveis a partir do checklist.
- **Status:** VALIDADO.
- **Implementado:** motor puro; gera risco só de itens `RISCO_IDENTIFICADO`/`ATENCAO` **com evidência**; persistência versionada por `analysis_version`.
- **Parcial:** emite apenas `ALTA`/`MEDIA` (nunca `CRITICA`/`BAIXA`); risco só nasce do checklist com evidência.
- **Falta:** riscos de outras fontes (financeiro/mercado/due diligence) e severidade crítica/baixa; score por dimensão (F8).
- **Dependências:** checklist.
- **Riscos:** médio (cobertura limitada de severidade).
- **Concluída quando:** score multidimensional da F8 + testes.
- **Refs:** `backend/app/risk_engine.py`, `services.recalculate_risks`, `tests/test_risk_engine.py`.

### A8. Verdict Engine (determinístico)
- **Objetivo:** veredito explicável/rastreável por versão de análise.
- **Status:** VALIDADO.
- **Implementado:** estados `FAVORAVEL/ATENCAO/DESFAVORAVEL/INCONCLUSIVO` por precedência; agrega riscos/pendências/evidências; snapshot financeiro; reconciliação histórica idempotente (restrita ao 633/V8).
- **Parcial:** não há comitê multidimensional, score por dimensão, hard stops explícitos nem decisão humana versionada (isso é F8/Onda 6).
- **Falta:** comitê/gates/score/decisão humana (F8).
- **Dependências:** risco + checklist + financeiro.
- **Riscos:** médio (veredito ≠ decisão de comitê).
- **Concluída quando:** F8 implementada com hard stops + decisão versionada.
- **Refs:** `backend/app/verdict_engine.py`, `services.create_verdict`, `tests/test_verdict_engine.py`, `tests/test_verdict_evidence_endpoint.py`.

### A9. Motor financeiro determinístico
- **Objetivo:** custo total, resultado líquido, margem, ROI, yield, break-even e preço máximo de aquisição.
- **Status:** VALIDADO.
- **Implementado:** breakdown anti-dupla-contagem; resultado líquido de venda (corretagem + tributo parametrizável); margem/ROI/yield; break-even; preço máximo por meta (`LUCRO_MINIMO`/`MARGEM_MINIMA`/`ROI_MINIMO`); classificação de custo (informado/estimado/desconhecido); cenário BASE.
- **Parcial:** cenários OTIMISTA/PESSIMISTA só com premissas explícitas (por desenho).
- **Falta:** **TIR/VPL/fluxo descontado**, **análise de sensibilidade** e **parametrização por jurisdição/ato/vigência** (custos são `COST_KEYS` fixas).
- **Dependências:** cadastro de leilão/custos/comparáveis.
- **Riscos:** médio (parametrização fiscal é o maior gap — exige fonte oficial).
- **Concluída quando:** TIR/VPL/sensibilidade + parâmetros fiscais versionados (Onda 5/épico H).
- **Refs:** `backend/app/finance.py`, `services.build_finance`, `tests/test_finance.py`, `tests/test_finance_assumptions.py`, `tests/test_e2e_financeiro.py`.

### A10. Mercado (comparáveis)
- **Objetivo:** consolidar comparáveis de venda/aluguel com sinalização de qualidade da amostra.
- **Status:** VALIDADO.
- **Implementado:** média/mediana, preço/m², qualidade da amostra (mínimo 7, coeficiente de variação), rastreabilidade de fonte; nunca afirma valuation definitivo.
- **Parcial:** sem ajuste por atributos (área/estado/localização).
- **Falta:** valuation assistido/ajuste hedônico; liquidez estimada.
- **Dependências:** cadastro manual de comparáveis.
- **Riscos:** baixo.
- **Concluída quando:** (atende) para o escopo atual; valuation avançado é evolução.
- **Refs:** `backend/app/market.py`, `backend/app/routers/market.py`, `tests/test_market.py`.

### A11. Ocupação
- **Objetivo:** registrar situação de ocupação e insumos de desocupação.
- **Status:** VALIDADO.
- **Implementado:** registro append com status/perfil/custo/prazo informados; alimenta `desocupacao` no financeiro.
- **Parcial:** não calcula custo/prazo (apenas registra o informado).
- **Falta:** classificação assistida; vínculo automático com pós-arrematação.
- **Dependências:** nenhuma.
- **Riscos:** baixo.
- **Refs:** `backend/app/main.py` (`/ocupacao`), `tests/test_occupancy.py`.

### A12. Evidências e rastreabilidade
- **Objetivo:** ancorar toda conclusão a documento/versão/chunk.
- **Status:** VALIDADO.
- **Implementado:** `Evidence`/`EvidenceLink`; normalização de evidência documental; visão legível no veredito.
- **Falta:** —
- **Refs:** `backend/app/evidence.py`, `tests/test_evidence.py`.

### A13. Histórico, eventos e reanálise incremental
- **Objetivo:** trilha de eventos + reanálise apenas do que foi afetado.
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** `DomainEvent`/`EntityHistory`; `ImpactAnalyzer` (mapa evento→domínios); `IncrementalAnalysisService`; endpoint de reanálise por evento.
- **Parcial:** `affected_checklist_keys` sempre vazio (não infere keys por evento).
- **Falta:** inferência de itens de checklist afetados.
- **Refs:** `backend/app/impact.py`, `incremental.py`, `tests/test_impact_analyzer.py`, `tests/test_incremental_analysis.py`.

### A14. Memória histórica / knowledge
- **Objetivo:** aprender com casos passados (busca textual/semântica/híbrida).
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** `KnowledgeMemoryService` (casos/outcomes/regras; busca híbrida).
- **Parcial:** **sem endpoint REST** dedicado (serviço de domínio não exposto).
- **Falta:** superfície HTTP + uso no fluxo.
- **Refs:** `backend/app/knowledge_memory.py`, `tests/test_knowledge_memory.py`.

---

## MÓDULO B — Jurídico

### B1. Processos + correlação determinística
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** CRUD de processos/movimentações (append-only); correlação `ALTA/MEDIA/BAIXA/NAO_CONFIRMADA`.
- **Parcial:** correlação `ALTA` (match por CPF/CNPJ) é **inalcançável hoje** porque o perfil do imóvel não guarda documento do proprietário → fica em `MEDIA/BAIXA` por nome+local.
- **Falta:** CPF/CNPJ estruturado do proprietário; cadeia registral.
- **Refs:** `backend/app/legal_correlation.py`, `tests/test_legal_correlation.py`, `tests/test_processes.py`.

### B2. Integração Judicial API / DataJud
- **Status:** IMPLEMENTADO PARCIALMENTE / BLOQUEADO (consulta real depende de serviço/credencial).
- **Implementado:** consumidor HTTP; persiste processos/sinais; degradação graciosa (`disponivel=false`) se indisponível; sinal processual nunca confirma gravame (vira `ATENCAO` no checklist).
- **Parcial/Bloqueado:** a Judicial API (módulo `judicial_api`/DataJud) é externa; consulta real exige o serviço de pé + credencial DataJud.
- **Refs:** `backend/app/judicial_client.py`, `judicial_integration.py`, `tests/test_judicial_integration_pg.py`, `tests/test_consult_judicial_endpoint.py`.

### B3. Central Jurídica (biblioteca + referências contextuais)
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** catálogo curado seedado idempotente (**5 fontes / 11 dispositivos / 8 regras**); referências por `canonical_key` e por contexto; busca vetorial/textual; vínculo regra↔checklist.
- **Parcial:** `LEGAL_CONTEXTS` não inclui modalidades; curadoria ampla ("136/45 regras") **não** implementada.
- **Falta:** vigência/redação histórica/jurisprudência estruturada; aplicabilidade por modalidade (Central Jurídica 2.0 — Onda 3).
- **Refs:** `backend/app/legal_catalog.py`, `legal_service.py`, `routers/legal_central.py`, `tests/test_central_juridica.py`.

---

## MÓDULO C — Pós-Aquisição

### C1. Pós-arrematação (etapas, custos, contatos, consultorias, minutas)
- **Status:** VALIDADO.
- **Implementado:** ativação sob demanda (`PostAuction` único por imóvel); etapas; custos previsto/realizado/pago; contatos + tentativas (append-only); consultorias + propostas; minutas versionadas; resumo financeiro consistente com `build_finance`.
- **Parcial:** minutas **não** são geradas por IA (só armazenam versões); lucro/ROI dependem de `expected_sale_value` informado.
- **Falta:** modelagem registral formal (F10) e reforma/regularização dedicada (F11).
- **Refs:** `backend/app/main.py` (`/pos-arrematacao*`), `services.post_auction_cost_summary`, `tests/test_pos_arrematacao.py`.

### C2. Due diligence integrada (4 frentes)
- **Status:** IMPLEMENTADO PARCIALMENTE.
- **Implementado:** orquestrador de leitura das 4 frentes (MATRICULA/JUDICIAL/PREFEITURA/LOCALIZACAO); reflete pendência como `ATENCAO` no checklist (nunca `CONFIRMADO`); checklist de localização (11 critérios); geocodificação Google Maps.
- **Parcial/Bloqueado:** Google Maps `NAO_CONFIGURADO` sem key (links externos sempre disponíveis); **RI Digital e Prefeitura não têm cliente HTTP** (manual/`NAO_CONFIGURADO`).
- **Falta:** clientes de RI/Prefeitura; vistoria estruturada; certidões contextuais.
- **Refs:** `backend/app/services.py` (`due_diligence_overview`), `geocoding_client.py`, `tests/test_due_diligence.py`.

---

## MÓDULO D — Operação e Fornecedores

### D1. Leiloeiros + portais + credenciais seguras (TASK 75)
- **Status:** VALIDADO.
- **Implementado:** cadastro de leiloeiros/portais/documentos; credencial cifrada (Fernet) com `PORTAL_SECRET_KEY` (falha-fechada); endpoint de reveal protegido por `PORTAL_ADMIN_TOKEN`; segredo nunca em log/LLM/listagem.
- **Falta:** uso automatizado da credencial (apenas armazenamento/recuperação manual, por desenho).
- **Refs:** `backend/app/main.py` (`/api/leiloeiros*`), `secrets_crypto.py`, `tests/test_task75_backend.py`, `tests/test_task752_crud.py`.

---

## MÓDULO E — Interface (Frontend)

### E1. Dossiê do imóvel + hubs + seções por domínio
- **Status:** VALIDADO.
- **Implementado:** 21 páginas/seções (dossiê, financeiro, jurídico, riscos, veredito, mercado, ocupação, documentos, histórico, checklist, due diligence, pós-arrematação, leiloeiros, Central Jurídica); 137 testes Vitest; `tsc` limpo.
- **Parcial:** sem tela de workflow/oportunidades (não há backend exposto); modalidade é input de texto livre.
- **Falta:** dashboard de oportunidades/workflow; UI de modalidade (select).
- **Refs:** `frontend/src/pages/*`, `frontend/src/components/*`, testes `*.test.tsx`.

---

## MÓDULO F — Fundação de Plataforma (Ciclo 2)

### F-M0. Modularização da API + CI
- **Status:** VALIDADO (Onda 0).
- **Implementado:** routers por domínio (health, hubs, Central Jurídica, mercado) sob guard-rail de contrato OpenAPI (99 paths); CI GitHub Actions (migrations+pytest / tsc+vitest).
- **Parcial:** modularização do restante de `main.py` segue contínua (~83 paths ainda em `main.py`).
- **Refs:** `backend/app/routers/*`, `.github/workflows/ci.yml`, `tests/contract/test_openapi_contract.py`.

### F-B1. Domínio Opportunity + Workflow Engine (puro)
- **Status:** IMPLEMENTADO PARCIALMENTE (Onda 1).
- **Implementado:** modelos `Opportunity`/`OpportunityWorkflow`/`WorkflowTransition`; `opportunity_id` nullable nas 9 tabelas; `workflow_rules.py`+`workflow_engine.py` puros (F0–F13, gates, hard stops, invariante ADR-004); testes de isolamento/engine.
- **Parcial / não exposto:** o workflow engine **não está ligado a nenhum router/serviço** — é fundação pura, ainda não operacional ponta a ponta (sem `workflow_service`, sem endpoints, sem UI).
- **Falta:** serviço `apply_transition`/`create_opportunity`, endpoints, dossiê por oportunidade, UI; backfill (Gate 2 — bloqueado).
- **Refs:** `backend/app/workflow_engine.py`, `workflow_rules.py`, `models.py` (Opportunity*), `tests/test_workflow_engine.py`, `tests/test_opportunity_isolation.py`.

### F-F1. Modalidades de aquisição (F1)
- **Status:** ESPECIFICADO (planejado; Onda 2).
- **Implementado:** apenas o **campo** `modality` (string livre, sem enum/validação); uma regra (`MODALIDADE_INDEFINIDO`) no engine puro não-ligado.
- **Falta:** vocabulário canônico, classificação com evidência, aplicabilidade por modalidade no checklist e nas regras jurídicas (ver `docs/PLAN-WAVE-2-MODALIDADES.md`).
- **Refs:** `docs/PLAN-WAVE-2-MODALIDADES.md`, `docs/MATRIZ-CHECKLIST-MODALIDADE.md`.

---

## MÓDULO G — Transversais ausentes/parciais (fases do roadmap F0–F13)

| Feature | Fase | Status | Observação (código) |
|---|---|---|---|
| G1. Radar/descoberta/ingestão/dedupe/alertas | F0 | NÃO INICIADO (cadastro existe; radar não) | Sem snapshot/diff/dedupe; portais só backlog (`REVISAO-ANOTACOES-LEILAO`) |
| G2. Classificação de modalidade | F1 | ESPECIFICADO | Ver F-F1 |
| G3. Comitê/decisão multidimensional + hard stops | F8 | EM DESENVOLVIMENTO (Verdict existe; comitê não) | Sem score por dimensão, decisão humana versionada |
| G4. Lance/pagamento | F9 | NÃO INICIADO | Sem modelo de resultado de leilão/pagamento |
| G5. Transferência/registro formal | F10 | IMPLEMENTADO PARCIALMENTE | Pós-arrematação cobre etapas/custos; falta modelagem registral |
| G6. Reforma/regularização | F11 | IMPLEMENTADO PARCIALMENTE | Posse/notificação existem; reforma sem modelo dedicado |
| G7. Exploração/saída (venda/locação/holding) | F12 | NÃO INICIADO | Sem modelo de venda/locação/resultado realizado |
| G8. Encerramento/dossiê exportável | F13 | IMPLEMENTADO PARCIALMENTE | Status/histórico existem; falta dossiê exportável + projetado×realizado |
| G9. Autenticação / RBAC / multiusuário | Transversal | NÃO INICIADO | Nenhum usuário/login no código; `actor` é texto |
| G10. Observabilidade (métricas/tracing/alertas) | Transversal | IMPLEMENTADO PARCIALMENTE | Há logging estruturado; sem métricas/tracing |
| G11. Segurança de upload (tamanho/MIME/streaming) | Transversal | IMPLEMENTADO PARCIALMENTE | Valida extensão; sem limite de tamanho/MIME explícito |
| G12. Parâmetros fiscais por jurisdição/vigência | F7/épico H | NÃO INICIADO | `COST_KEYS` fixas; sem tabela de parâmetros |

---

## Resumo de status por feature (contagem canônica)

> **Denominador canônico = 30 funcionalidades.** Lista fechada e numerada abaixo (sem dupla
> contagem). `F-F1` e `G2` são a MESMA feature (modalidade) — conta uma vez. `G5/G6/G8/G10/G11/G12`
> são subitens de evolução de features-mãe e **não** entram no denominador (estão refletidos nos
> gaps). Os percentuais derivados estão em `PRODUCT-DASHBOARD.md`.

As 30 features: A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12, A13, A14, B1, B2, B3, C1, C2,
D1, E1, F-M0, F-B1, F-F1, G1(F0), G3(F8), G4(F9), G7(F12), G9(auth), G12(parâmetros fiscais).

| Status | Qtde | Features |
|---|---|---|
| **VALIDADO** | 12 | A1, A4, A6, A7, A8, A9, A10, A11, A12, C1, D1, E1 |
| **IMPLEMENTADO PARCIALMENTE** | 11 | A2, A3, A5, A13, A14, B1, B2, B3, C2, F-M0, F-B1 |
| **ESPECIFICADO** | 1 | F-F1 (= G2, modalidade) |
| **EM DESENVOLVIMENTO** | 1 | G3 (F8 comitê) |
| **NÃO INICIADO** | 5 | G1 (F0), G4 (F9), G7 (F12), G9 (auth), G12 (parâmetros fiscais) |
| **Total** | **30** | — |

> B2 (Judicial) e C2 (due diligence) têm componentes **BLOQUEADOS** (dependem de serviço/credencial
> externa), mas estão classificados pela parte já implementada; o caráter bloqueado é registrado no
> dashboard e no roadmap. A metodologia de contagem e os percentuais são consolidados em
> `PRODUCT-DASHBOARD.md`.
