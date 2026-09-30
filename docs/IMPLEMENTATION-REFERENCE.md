# RADAR LEILÃO — REFERÊNCIA DE IMPLEMENTAÇÃO

**Data de atualização:** 30/09/2026  
**Estado:** Task 5 integrada; testes financeiros HTTP reportados como aprovados; validação E2E manual pela UI pendente  
**Branch de referência:** main  
**Commit de referência mais recente:** 6c5f31808f2a259ba0e6dfb8ace63dd484248794  
**Validação do domínio:** Analysis V9 do imóvel 633 registrada historicamente; os testes financeiros HTTP da Task 5 não substituem o E2E financeiro manual pela UI

> Este documento complementa a SPEC. A SPEC define o método e a arquitetura; este documento mapeia a implementação efetivamente existente no repositório.

---

## 1. Stack efetivamente implementada

### Backend
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- pgvector

### Frontend
- React
- TypeScript
- Vite
- Vitest

### IA
- LangChain
- LangGraph
- gateway/provider de LLM
- OpenAI provider
- 5 agentes: Documental, Jurídico, Financeiro, Mercado e Checklist

### Documentos
- MarkItDown
- OCR com Tesseract + Poppler
- normalização para Markdown
- chunking
- embeddings
- armazenamento de chunks/embeddings no PostgreSQL/pgvector

### Operação local
- WSL2
- Docker Compose
- PostgreSQL com volume persistente
- filesystem persistente do backend
- scripts em `scripts/`

---

## 2. Mapa do backend

| Código | Responsabilidade |
|---|---|
| `backend/app/main.py` | API FastAPI, endpoints do dossiê, análise, checklist, documentos, evidências, riscos, veredito e histórico |
| `backend/app/models.py` | Modelos SQLAlchemy e relacionamentos persistidos |
| `backend/app/schemas.py` | Contratos Pydantic da API |
| `backend/app/services.py` | Serviços de domínio/orquestração; criação de análise, checklist, riscos e veredito |
| `backend/app/checklist.py` | Checklist Mestre e regras/execução estruturada |
| `backend/app/risk_engine.py` | Avaliação e persistência determinística de riscos |
| `backend/app/verdict_engine.py` | Consolidação determinística do Veredito |
| `backend/app/finance.py` | Cálculos e consolidação financeira |
| `backend/app/market.py` | Consolidação determinística de mercado |
| `backend/app/impact.py` | Impact Analyzer para reanálise incremental |
| `backend/app/incremental.py` | IncrementalAnalysisService e fluxo de reanálise por evento |
| `backend/app/analysis_comparison.py` | Comparação entre versões de análise |
| `backend/app/consolidation.py` | Consolidação de dados/resultados |
| `backend/app/evidence.py` | Criação/normalização de evidências |
| `backend/app/extraction.py` | Extração e processamento de informações documentais |
| `backend/app/knowledge_memory.py` | Memória/itens históricos reutilizáveis |
| `backend/app/config.py` | Configuração e variáveis de ambiente |
| `backend/app/database.py` | Engine/session do PostgreSQL |
| `backend/app/logging_config.py` | Configuração de logging |

---

## 3. Pipeline documental

| Código | Responsabilidade |
|---|---|
| `backend/app/documents/pipeline.py` | Pipeline principal de documentos |
| `backend/app/documents/normalizer.py` | Normalização/MarkItDown |
| `backend/app/documents/ocr.py` | OCR Tesseract + Poppler |
| `backend/app/documents/chunker.py` | Geração de chunks |
| `backend/app/documents/embedding.py` | Geração de embeddings |
| `backend/app/rag/embeddings.py` | Integração de embeddings no RAG |
| `backend/app/rag/retriever.py` | Retrieval híbrido |
| `backend/app/rag/checklist_retrieval.py` | Retrieval direcionado do Checklist |
| `backend/app/rag/service.py` | Serviço de RAG |

### Regra implementada

`original → normalização/OCR → Markdown → chunks → embeddings → PostgreSQL/pgvector → retrieval → agentes`

O original é preservado e as versões documentais permanecem rastreáveis.

---

## 4. Camada de IA

| Código | Responsabilidade |
|---|---|
| `backend/app/ai/agents.py` | Agentes especializados |
| `backend/app/ai/graph.py` | Grafo LangGraph |
| `backend/app/ai/orchestrator.py` | Orquestração |
| `backend/app/ai/gateway.py` | Gateway de LLM |
| `backend/app/ai/providers/openai_provider.py` | Provider OpenAI |
| `backend/app/ai/contracts.py` | Contratos de entrada/saída |
| `backend/app/ai/prompts.py` | Prompts |
| `backend/app/ai/costs.py` | Controle/cálculo de custos de LLM |
| `backend/app/ai/tools.py` | Ferramentas auxiliares dos agentes |

### Agentes efetivamente implementados

1. Documental
2. Jurídico
3. Financeiro
4. Mercado
5. Checklist

**Desocupação não é um sexto agente LLM no MVP.** É um domínio funcional atendido pelo fluxo existente.

---

## 5. Fluxo de análise

`POST /api/imoveis/{property_id}/analisar`

Fluxo conceitual:

`Analysis → agentes/LangGraph → evidências → ChecklistExecution → Risk Engine → Verdict Engine → histórico`

A seleção da ChecklistExecution corrente utiliza a versão semântica da Analysis quando a Session está disponível:

`property_id + analysis_version`

Isso evita dependência da ordem incidental das relationships ORM.

---

## 6. Reanálise incremental

Endpoint operacional:

`POST /api/imoveis/{property_id}/eventos/{event_id}/reanalisar`

Implementação:

- `main.py` recebe e valida o evento;
- `IncrementalAnalysisService.run_for_event()` executa a lógica;
- `ImpactAnalyzer` determina impacto/domínios;
- somente os domínios afetados são reexecutados;
- histórico é preservado;
- o evento é marcado como processado.

A implementação foi criada para permitir a validação operacional incremental, sem duplicar a lógica do serviço.

---

## 7. Checklist, riscos e Veredito

### Checklist
- 27 canonical keys no conjunto de referência do MVP.
- Estados suportados: PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO, NAO_IDENTIFICADO e NAO_APLICAVEL.
- Cada execução é versionada pela Analysis.

### Risk Engine
`backend/app/risk_engine.py`

Recebe os resultados da ChecklistExecution correspondente à versão da Analysis e persiste riscos versionados.

### Verdict Engine
`backend/app/verdict_engine.py`

Consolida:
- pendências;
- evidências;
- riscos;
- resultado determinístico;
- informações financeiras relevantes.

A LLM não decide diretamente o Veredito.

---

## 8. Evidências

A entidade `Evidence` mantém rastreabilidade para:

- documento;
- versão documental;
- chunk;
- categoria;
- fato;
- interpretação;
- hipótese;
- confiança;
- página/seção;
- trecho de origem.

A API/UI do Veredito resolve os IDs internos para informações legíveis sempre que os metadados existem.

---

## 9. Reconciliação histórica

`backend/app/reconciliation.py` é uma manutenção **one-off**, criada exclusivamente para corrigir o snapshot histórico do Veredito V8 do imóvel 633.

Guardas permanentes da função:

- `property_id == 633`;
- `analysis_version == 8`;
- não cria Verdict ausente;
- atualiza o Verdict existente in place;
- transacional;
- idempotente;
- não executa LLM;
- não cria Analysis/V9.

Essa manutenção já foi aplicada ao Verdict V8:

`28 pendências → 21 pendências`

Depois da reconciliação, a UI confirmou:
- Checklist V8: 7 CONFIRMADOS / 20 PENDENTES;
- Veredito V8: 21 pendências.

---

## 10. Frontend

Estrutura principal em `frontend/src/`.

Serviços HTTP ficam em `frontend/src/services/`, separados por domínio, incluindo:
- assessment;
- checklist;
- documents;
- finance;
- history;
- market;
- processes;
- properties;
- registration.

As telas/seções cobrem o dossiê:
- visão geral;
- leilão;
- documentos;
- matrícula;
- edital;
- processos jurídicos;
- financeiro;
- mercado;
- ocupação;
- checklist;
- riscos;
- Veredito;
- histórico.

A UI foi validada no imóvel real 633.

---

## 11. Persistência e migrations

Migrations ficam em:

`backend/migrations/versions/`

A estrutura atual possui migrations para:
- fundação;
- rastreamento de uso/custo de LLM;
- Checklist Mestre;
- financeiro;
- ocupação/histórico;
- processos jurídicos;
- matrícula/edital;
- extração documental;
- cadastro completo do imóvel;
- datas/horários do leilão;
- **persistência PostgreSQL da Judicial API (`0011_judicial_persistence`)** — tabelas
  `judicial_*` no mesmo banco/schema, sem tocar no schema do Radar; reversível.

Não foi criada migration específica para as correções Tasks 69–74.1.

### Judicial API — persistência, DataJud real e integração (Task Final)

O módulo independente `judicial_api/` (pesquisa processual multi-tribunal via
DataJud/CNJ) passou a:

- **persistir em PostgreSQL** (durável, compartilhado) via `PostgresSearchStore`
  (`judicial_api/persistence/`), reutilizando o MESMO banco do Radar. O
  `InMemorySearchStore` fica só para testes (`JUDICIAL_PERSISTENCE_BACKEND=memory`).
- **consultar o DataJud real** via `HttpxTransport` (`judicial_api/providers/http_transport.py`),
  injetado quando há `JUDICIAL_DATAJUD_API_KEY`. Fora de `local`, a API falha fechada
  sem as credenciais obrigatórias.
- **ser consumida pelo Radar por HTTP**: `backend/app/judicial_client.py` +
  `backend/app/judicial_integration.py` + endpoint
  `POST /api/imoveis/{id}/processos/consultar`. O resultado vira `LegalProcess`/
  `ProcessMovement` + `Evidence(JURIDICO)` + `DomainEvent CONSULTA_JUDICIAL_REALIZADA`,
  preservando a distinção processo × imóvel. Indisponibilidade da Judicial API não
  bloqueia as demais análises.

Deploy: serviço `judicial_api` no `docker-compose.yml` (mesma imagem do backend,
uvicorn na porta 8010, mesmo PostgreSQL). O `backend` é o dono das migrations.

---

## 12. Operação

Scripts principais:

| Script | Uso |
|---|---|
| `scripts/setup.sh` | preparação inicial |
| `scripts/start.sh` | inicialização |
| `scripts/stop.sh` | parada |
| `scripts/restart.sh` | rebuild/restart preservando volumes |
| `scripts/health.sh` | saúde do ambiente |
| `scripts/logs.sh` | logs |
| `scripts/backup.sh` | backup |
| `scripts/restore.sh` | restauração |
| `scripts/reset.sh` | reset explícito |

`restart.sh` não remove volumes nomeados. PostgreSQL e storage persistente são preservados.

---

## 13. Testes

Os testes backend ficam em `tests/` e cobrem:
- cadastro;
- documentos;
- extração;
- OCR/RAG;
- embeddings;
- agentes;
- LangGraph;
- Checklist;
- Financeiro;
- Mercado;
- Processos;
- Ocupação;
- memória;
- análise incremental;
- seleção de execução;
- Risk Engine;
- Verdict Engine;
- evidências;
- endpoint de reanálise;
- reconciliação histórica.

No fechamento da Task 74.1:

**292 passed — 0 falhas.**

### Atualização (Tasks 2–5, 30/09/2026)

Após as tasks financeiras e a integração judicial, a suíte backend cresceu:
- **526 passed, 2 skipped** (os 2 skips são os testes reais do DataJud, gated por
  `RUN_REAL_DATAJUD_TESTS`), rodando no container com PostgreSQL real e sem LLM/rede.
- Cobertura financeira: `tests/test_finance.py` (motor, incl. preço máximo
  definitivo × provisório), `tests/test_finance_assumptions.py` (persistência de
  premissas + build_finance + endpoints) e `tests/test_e2e_financeiro.py` (Task 5 —
  fluxo financeiro E2E pela camada HTTP real: premissas → PostgreSQL → resultado,
  10 cenários).
- **E2E de navegador (UI real) NÃO é automatizado**: o frontend não possui
  Playwright/Cypress; a validação de UI é manual (ver `PROJECT-STATUS` §20.6). Os
  testes HTTP não substituem a validação manual do fluxo no navegador.

Frontend:
- Vitest validado nas etapas de UI;
- TypeScript `tsc --noEmit` validado.

---

## 14. Validação E2E final — imóvel 633

Imóvel:

**COND PARQUE ARVOREDO RESIDENCIAL CLUBE**

Analysis V9:

- 5 agentes;
- LLM ativo;
- modelo registrado: gpt-4o-mini;
- 5/5 runs concluídos com sucesso;
- 8 chunks recuperados;
- 34.045 tokens;
- custo registrado: US$ 0,00650625;
- Checklist: 10 CONFIRMADOS / 17 PENDENTES;
- Veredito: INCONCLUSIVO;
- 18 pendências: 17 do Checklist + 1 financeira;
- histórico V1–V9 preservado.

A V9 comprova o fluxo real:

`documentos → RAG → 5 agentes → Checklist → Risk Engine → Verdict Engine → Histórico`

---

## 15. Limitações conhecidas e evolução

Sobre a Judicial API (Task Final): a persistência PostgreSQL, o transporte real do
DataJud e a integração HTTP com o Radar estão implementados e cobertos por testes
automatizados. A **consulta real ao DataJud** depende de credencial pública válida e
conectividade externa; o teste real é opcional (`RUN_REAL_DATAJUD_TESTS=true`) e não
foi executado contra o serviço real neste ambiente (sem credencial/conectividade) — a
validação automatizada usa mocks/fakes e PostgreSQL real.

Não são dependências para o MVP:

- pesquisa jurídica externa totalmente automática;
- MCP externo;
- Knowledge Graph dedicado;
- Redis;
- S3/MinIO;
- leilão judicial;
- scraping irrestrito;
- automação de todas as fontes externas;
- fórmula canônica de preço máximo ainda não definida na SPEC;
- comparáveis reais externos automatizados.

Esses itens pertencem à evolução/Fase 2.

---

## 16. Critério de encerramento

O MVP é considerado funcionalmente encerrado porque o sistema foi executado com um imóvel real, documentos reais e LLM real, produzindo:

`Analysis → agentes → evidências → Checklist → riscos → Veredito → histórico`

com versionamento, rastreabilidade e testes automatizados.

A partir de 28/09/2026, novas mudanças devem ser tratadas como **Fase 2 / backlog**, salvo correção de defeito crítico descoberto posteriormente.


---

## 17. Atualização financeira — Task 4 (30/09/2026)

### Arquivos principais

- `backend/app/finance.py`: cálculo do preço máximo e classificação de certeza.
- `tests/test_finance.py`: regressões de preço máximo e premissas desconhecidas.
- `frontend/src/services/finance.ts`: contrato/consumo dos campos financeiros.
- `frontend/src/pages/FinancialSection.tsx`: formulário e indicação de estado provisório/definitivo.
- `frontend/src/pages/FinancialSection.test.tsx`: testes da interface financeira.

### Contrato funcional

- Premissas financeiras são persistidas por imóvel em `auctions.financial_assumptions`.
- O cálculo expõe preço máximo e indica se ele é definitivo ou provisório.
- Custos materiais desconhecidos devem permanecer listados como pendências.
- Uma estimativa parcial não deve ser tratada como recomendação de lance nem como limite definitivo.
- As premissas usadas numa análise devem permanecer registradas no snapshot histórico.

### Evidência de qualidade

O commit da Task 4 registra resultados reportados de 514 testes backend aprovados e 2 ignorados, 95 testes frontend aprovados e TypeScript aprovado. O E2E manual de interface continua pendente e não pode ser inferido a partir dos testes unitários/integrados.

### Limites conhecidos

- Consulta real ao DataJud ainda depende de configuração e validação externa; testes gated/skipped não comprovam funcionamento real.
- A qualidade dos comparáveis de mercado e a avaliação real de liquidez/conservação permanecem itens de evolução.
- Não há declaração de fechamento do MVP até a conclusão do roteiro E2E financeiro.
