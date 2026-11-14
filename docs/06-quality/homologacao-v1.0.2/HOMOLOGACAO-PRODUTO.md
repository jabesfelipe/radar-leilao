# Homologação de produto — Radar Leilão v1.0.2

Baseline preservada: `main` @ `8894096`, tag `v1.0.2`. **Sem deploy, sem release, sem merge, sem tag, sem commit/push, OpenAI não ativada, nenhuma análise paga, imóvel real não utilizado.**
Trabalho na branch local `homologacao-v1.0.2`. Detalhes: [AUDITORIA-MOBILE.md](AUDITORIA-MOBILE.md), [AUDITORIA-LLM.md](AUDITORIA-LLM.md), [PLANO-ATIVACAO-OPENAI.md](PLANO-ATIVACAO-OPENAI.md).

> **Esta versão do documento reflete a rodada de correções P0/P1.** O diagnóstico original (antes das correções) está no histórico do arquivo.
> As correções existem **somente nesta branch local**: a v1.0.2 publicada na VPS **continua com os defeitos originais** até uma nova versão ser publicada.

## 1. O Radar está pronto para analisar um imóvel real?

**Ainda não, mas o que impedia o Radar de dizer a verdade foi corrigido.** O Radar agora não finge ter analisado: sem IA o resultado é "falha",
com falha parcial é "parcial", e documentos sem texto ou OCR aparecem como "não prontos". O que falta é de outra natureza: **prova com a OpenAI real**,
decisão sobre dados pessoais, HTTPS e teste em aparelhos reais.

Bloqueadores restantes para o **primeiro imóvel real**:

1. **Integração real com a OpenAI NÃO VALIDADA** (embeddings, 5 agentes, tokens, custos). Exige chave autorizada.
2. **Dados pessoais**: identificadores (CPF, RG, e-mail, telefone, dados bancários) e partes de processo são mascarados, mas **nomes dentro do texto dos documentos seguem para a OpenAI**. Exige decisão do responsável.
3. **HTTPS**: a homologação roda em HTTP. `REQUIRE_HTTPS=true` existe e foi testado, mas o TLS no proxy é ação de infraestrutura (não feita).
4. **iPhone e Android reais**: só Chrome emulado foi testado.
5. **OCR real** não executado (o ambiente de teste não tem Tesseract); com OCR desligado, matrícula escaneada fica "OCR necessário" (explícito, mas sem leitura).
6. **Publicar** a versão corrigida (nova tag) antes de usar a VPS — fora do escopo desta rodada.

## 2. Problemas corrigidos nesta rodada (com evidência)

| # | Item solicitado | Resultado | Evidência |
|---|---|---|---|
| 1 | Falso status "concluída" | **CORRIGIDO** | `status` calculado das chamadas reais: `concluida` / `parcial` / `falha`; sem chave → `falha` + `IA_INDISPONIVEL`. `tests/test_analysis_status.py` (16 casos), E2E `correcoes.spec.ts` 3 e UI 390 px |
| 2 | Falhas dos agentes no consolidado | **CORRIGIDO** | Mesma lógica; `parcial` lista os agentes que falharam; persistido em `analyses.token_usage` e exibido no Histórico |
| 3 | Concluída / parcial / falha / em processamento | **CORRIGIDO** | "Em processamento" via lock advisory (`GET /api/imoveis/{id}` → `analise_em_processamento`); UI atualiza sozinha; `test_is_running_detecta_analise_em_andamento_pelo_lock` |
| 4 | `category` nos chunks | **CORRIGIDO** | `documents/categories.py`; `tests/test_rag_category_and_recall.py`; E2E: agente jurídico recupera trechos (antes 0) |
| 5 | Filtros e recuperação do RAG | **CORRIGIDO** para consultas genéricas | Consulta padrão em OR + contingência posicional **sinalizada** (`match_type`, `reason`); consulta explícita continua estrita. Com embeddings reais: **NÃO VALIDADO** |
| 6 | Estados upload/OCR/extração/chunking/embedding/indexação | **CORRIGIDO** | `documents/readiness.py`; `tests/test_document_readiness.py` (13 casos); UI com lista de etapas |
| 7 | Documento sem processamento não é "pronto" | **CORRIGIDO** | `SEM_TEXTO`/`OCR_NECESSARIO`/`OCR_FALHOU`: fora do RAG, da fila de embeddings e da contagem de prontos; "Indexado" só com **todos** os chunks vetorizados |
| 8–9 | Dados pessoais nos prompts | **CORRIGIDO** (identificadores) / **PARCIAL** (nomes) | `app/privacy.py` no `LLMGateway` (chat **e** embeddings); `tests/test_privacy_minimization.py` com provider falso capturando o envio |
| 10 | HTTPS | **PARCIAL** | `REQUIRE_HTTPS` → 426 em HTTP, HSTS em HTTPS (`tests/test_cost_controls_and_https.py`). Revisão do proxy: cookie sem `Secure`, sem HSTS no template de produção (**não alterados**) |
| 11 | Limites e orçamento OpenAI | **PARCIAL** | `LLM_BUDGET_USD_MONTH` (→ `ORCAMENTO_EXCEDIDO`), `LLM_MAX_OUTPUT_TOKENS`, estimativa de custo de embedding. **Limite no painel da OpenAI continua obrigatório** |
| 12 | Logs sem credenciais/conteúdo sensível | **CORRIGIDO** | Filtro de logs e `sanitize_error` removem segredos **e** dados pessoais; nenhum log imprime prompt/documento (revisão de código) |
| 13–15 | OCR: auditoria, mecanismo, falhas, "sem texto não é processado" | **PARCIAL** | Mecanismo: Tesseract local; `ocr_available()` exige o binário; `OCR_MAX_PAGES`, timeout por página, truncamento registrado; falha/sem melhora → `OCR_FALHOU`. **Motor real não executado** |
| 16 | Histórico cortado | **CORRIGIDO** | E2E 375/390/412/768/1280 (rodada anterior); 7 viewports: ver §3 |
| 17 | Oportunidades | **CORRIGIDO** | idem |
| 18 | Central Jurídica e Due Diligence no tablet | **CORRIGIDO** | idem (causa: grids sem coluna explícita; cartões da Due Diligence) |
| 19 | Zoom do iOS (fonte < 16 px) | **CORRIGIDO** | 0 campos < 16 px nas telas verificadas em ≤ 430 px |
| 20 | Reexecução nas resoluções | **FEITO** | 5 viewports, 122 testes E2E (rodada anterior); depois 7 viewports: 164/166 e, após correção, 360×800 6/6 (§3) |

Também corrigido (efeito de segurança): a API deixou de devolver `original_path`/`normalized_path`/mensagens brutas de erro (topologia do servidor).

## 3. Testes executados (nesta rodada)

| Suíte | Resultado |
|---|---|
| Backend `pytest` (cópia da árvore **sem `.env`**, PostgreSQL 16 + pgvector, `alembic upgrade head`) | **1049 passed, 3 skipped** na rodada P0/P1; **1100 passed, 3 skipped** após a auditoria final (§6.1) (antes: 990 passed, 2 skipped). 60 testes novos em 5 arquivos, 0 falhas (a diferença de 1 no total e nos "pulados" vem de um teste que só roda com o `.env` do repositório; esta rodada usou cópia sem `.env`) |
| Frontend `tsc -b` + `vitest run` + `vite build` (reexecutado após o ajuste de CSS do Histórico) | **tsc OK (exit 0); 29 arquivos / 177 testes passaram; build OK** |
| E2E de navegador, 7 viewports (360, 375, 390, 412, 430, 768, 1366), Chrome real + backend real, sem chave | **164 passaram, 2 falharam** (Histórico em 360×800, overflow de 11 px). Após a correção de CSS, `-g "android-360x800"`: **6/6 passaram**. Bateria completa **não** reexecutada depois da correção |
| E2E, rodada anterior com 5 viewports | 122 passaram, 0 falharam, 7 pulados (IA real, gated) |
| E2E com OpenAI real (`ia-real.spec.ts`) | **NÃO EXECUTADO** |

**Testes existentes que precisei alterar (e por quê):**

- `test_integration_flows.py`, `test_cadastro_completo.py`: afirmavam `status == "concluida"` com **zero** agentes executados — exatamente o bug. Passam a exigir `falha`/`IA_INDISPONIVEL` sem chave; o orquestrador simulado ganhou uma chamada bem-sucedida para o caso "concluída".
- `test_document_intelligence.py`: o motor de OCR falso aceita os novos parâmetros (limite de páginas e timeout) e os testes passam a conferi-los.
- `DocumentsSection.test.tsx`: deixou de exigir a exibição do caminho interno do servidor.

**Compatibilidade com a v1.0.2:** nenhuma migration; o contrato OpenAPI (teste de baseline de rotas) continua idêntico; `POST /analisar` só **acrescenta** `status_detalhe` e o `status` passa a poder valer `parcial`/`falha` (mudança de comportamento intencional); `GET /api/imoveis/{id}` acrescenta `analise_em_processamento` e `analise_ultima`; as respostas de documentos acrescentam `processamento` e **omitem** os caminhos internos.

**Lacunas de teste:** OCR real; embeddings e agentes com OpenAI real; Safari iOS/Chrome Android reais; cadastro completo pelo wizard em navegador; Docker/nginx (HTTPS no proxy); 3 testes pulados no backend (já existiam).

## 4. Fluxo cadastro → parecer (após as correções)

| Etapa | Situação |
|---|---|
| Cadastrar imóvel (wizard) | **PARCIAL** — abre e tem layout correto; preenchimento completo pela UI **NÃO VALIDADO** |
| Enviar documentos | **OK** para texto; PDF escaneado é aceito e marcado "OCR necessário" |
| Processar documento | **CORRIGIDO** — etapas explícitas e "pronto para análise" |
| Extrair matrícula/edital estruturados | **FALHA** (aberta) — sem botão na UI |
| Gerar embeddings | **NÃO VALIDADO** (exige chave) |
| Dados financeiros/mercado | **PARCIAL** — sem eles os agentes só devolvem pendências |
| Executar análise | **CORRIGIDO** quanto à honestidade; **síncrona** e sem progresso por agente |
| Ler parecer e veredito | **PARCIAL** — veredito `INCONCLUSIVO` explica agora se a IA não rodou |

## 5. Problemas remanescentes e riscos

| Risco / problema | Gravidade | Observação |
|---|---|---|
| Nomes sem rótulo/cadastro, referências parciais, endereço, CNJ e CNPJ vão à OpenAI (nomes conhecidos/rotulados são pseudonimizados) | **Alto** | Sem NER; decisão do responsável; use imóvel fictício primeiro |
| HTTP em produção (dados pessoais em trânsito sem TLS) | **Alto** | `REQUIRE_HTTPS` pronto; TLS é infra |
| Sem prova com a OpenAI real | **Alto** | Todo o caminho de IA é simulado/local |
| Custo: embeddings estimados; retries do SDK e análises simultâneas não são vistos com exatidão | Médio | Teto mensal + por análise + fail-closed; painel da OpenAI obrigatório |
| OCR real não executado; impacto de memória na VPS desconhecido | Médio | Manter `OCR_ENABLED=false` até testar |
| Chunks antigos (sem `category`) ficam elegíveis a qualquer domínio | Baixo | Compatibilidade; sem backfill |
| Contingência posicional entrega contexto bruto quando nada casa | Baixo | Sinalizada (`match_type`, `reason`) |
| Texto desatualizado da Administração; escrita admin não validada | Médio | Não tratado |
| Análise síncrona (timeout do proxy 300 s com 5 agentes reais) | Médio | **NÃO VALIDADO** |
| Aparelhos reais não testados | Médio | Chrome emulado apenas |
| Mudanças só locais (sem commit) | — | Aguardam autorização; a VPS segue na v1.0.2 original |

## 6. Arquivos modificados

**Backend (novos):** `app/privacy.py`, `app/https_guard.py`, `app/ai/analysis_status.py`, `app/ai/budget.py`, `app/documents/categories.py`, `app/documents/readiness.py`.
**Backend (alterados):** `main.py`, `config.py`, `logging_config.py`, `ai/{agents,gateway,graph,orchestrator}.py`, `documents/{pipeline,embedding,ocr,states,worker}.py`, `rag/{retriever,service}.py`.
**Infra/config (repositório, sem deploy):** `docker-compose.prod.yml`, `.env.prod.example`.
**Frontend:** `styles.css`, `pages/{DocumentsSection,HistorySection,PropertyDetailPage}.tsx`, `services/{analysisStatus(novo),documents,history,properties}.ts`.
**Testes (novos):** `tests/test_{analysis_status,document_readiness,rag_category_and_recall,privacy_minimization,cost_controls_and_https}.py`, `e2e/tests/{correcoes,mobile,mobile-detalhe,fluxo,ia-real,helpers}`.
**Testes (alterados):** `test_integration_flows.py`, `test_cadastro_completo.py`, `test_document_intelligence.py`, `DocumentsSection.test.tsx`, `PropertyDetailPage.test.tsx`.
**Docs:** os quatro documentos desta pasta.

## 6.1 Auditoria final de segurança e pré-ativação LLM

**Defeito de isolamento encontrado e corrigido:** em `HybridRetriever.search`, a cláusula `:has_embedding OR <texto>` não tinha parênteses; com embedding, os filtros de imóvel, versão e estado eram ignorados e a **busca vetorial do imóvel A podia devolver trechos do imóvel B**. Descoberto pelo novo teste negativo (`test_busca_vetorial_tambem_e_isolada_por_imovel`), corrigido e coberto. Afetava qualquer busca com chave OpenAI ativa (antes disso nunca foi exercitado).

Outras mudanças: pseudonimização reversível de nomes (`NameAliaser`); busca recusa falta de `property_id`; só a última versão pronta no RAG; chunks citados pelo LLM validados; embeddings registrados em `llm_runs`; `LLM_BUDGET_USD_PER_ANALYSIS`; orçamento fail-closed sem preço; checklist com 1 chamada batch de embeddings; OCR uma página por vez; `orcamento_llm` em `GET /api/monitoring/rag`; doc `docs/04-operations/https-ocr-monitoramento.md`; `CHECKLIST-PRIMEIRO-IMOVEL.md`.

**Testes:** backend completo, cópia sem `.env`: **1100 passed, 3 skipped, 0 falhas** (novos: `test_rag_isolation.py`, `test_pseudonymization.py`, `test_cost_accounting.py`). Frontend e E2E **não foram reexecutados** nesta etapa (sem mudança de UI; último resultado: 177 testes e 122 E2E passados).

**Arquivos novos/alterados nesta etapa (backend):** `privacy.py`, `privacy_context.py`, `ai/{usage,gateway,budget,agents}.py`, `ai/providers/openai_provider.py`, `extraction.py`, `documents/{embedding,ocr,worker}.py`, `rag/{retriever,checklist_retrieval}.py`, `services.py`, `main.py`, `routers/monitoring.py`, `config.py`, `docker-compose.prod.yml`, `.env.prod.example`.

**Bloqueadores restantes:** (1) integração OpenAI real nunca validada; (2) OCR Tesseract real nunca executado; (3) HTTPS/TLS e cookie `Secure` no proxy: ação do operador; (4) nomes soltos, endereço, CNJ, CNPJ identificáveis; Judicial API e Geocoding sem redação; (5) download de documento sem checagem de dono (single-tenant); (6) sem iPhone/Android reais; worker sem healthcheck; (7) tudo local, sem commit/publicação.

**Recomendação objetiva: NÃO pronto para documentos reais. Pronto apenas para ativação controlada com imóvel fictício**, após os gates do `CHECKLIST-PRIMEIRO-IMOVEL.md` (publicar a versão, HTTPS, teto no painel da OpenAI, preços cadastrados).

## 7. Recomendação

1. Revisar o diff e **autorizar o commit** na branch (nada foi commitado).
2. Decidir a política de nomes em documentos e quem prepara HTTPS no proxy.
3. Publicar como nova versão (decisão sua), só então executar o `PLANO-ATIVACAO-OPENAI.md` com imóvel **fictício** primeiro.
4. Testar em iPhone e Android reais.
