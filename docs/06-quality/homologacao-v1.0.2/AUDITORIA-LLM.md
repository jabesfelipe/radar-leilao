# Auditoria de IA (LLM, embeddings, RAG e agentes) — Radar Leilão v1.0.2

Baseline: `main` @ `8894096`. **Atualizado após a rodada de correções P0/P1** (branch `homologacao-v1.0.2`, sem commit/deploy).
**Nenhuma chamada real à OpenAI foi feita** (sem chave autorizada).

Como ler as evidências:

- **EXECUTADO**: rodei no backend real local (PostgreSQL + pgvector, sem chave) ou em teste automatizado.
- **CÓDIGO**: li o código, sem executar.
- **NÃO VALIDADO**: depende de OpenAI real ou da VPS.

Situação: **CORRIGIDO** (com teste), **PARCIAL**, **FALHA** (ainda aberta), **NÃO VALIDADO**, **OK** (já estava correto).
Testes com mock não contam como prova de integração real; os testes de privacidade e custo usam um provider **falso que captura o que seria enviado**, e só provam a fronteira de saída.

## 1. Veredito

O pipeline continua **sem comprovação com a OpenAI real**. O que mudou: os defeitos que faziam a IA **parecer** funcionar quando não funciona
foram corrigidos e provados localmente (status honesto, `category`, recuperação de contexto, estados de documento, OCR explícito,
minimização de dados, orçamento). Falta a prova de integração real (`ia-real.spec.ts`, **NÃO EXECUTADO**).

## 2. Matriz

| Funcionalidade | Situação | Evidência | Problema residual / próximo passo | Prio. |
|---|---|---|---|---|
| Status da análise (concluída/parcial/falha) | **CORRIGIDO** | EXECUTADO: sem chave, `/analisar` → `status: "falha"`, `codigo: IA_INDISPONIVEL`, `agentes_ok: 0`; `tests/test_analysis_status.py` (função pura + HTTP real + parametrizado); E2E `correcoes.spec.ts` | Contrato novo: `status` ∈ `concluida`/`parcial`/`falha` e `status_detalhe`. Clientes antigos que esperavam sempre "concluida" precisam ser revisados | — |
| Falha dos agentes refletida no consolidado | **CORRIGIDO** | O status vem das chamadas reais (`llm_runs`); `parcial` lista quais agentes falharam; persistido em `analyses.token_usage` e exibido no Histórico | — | — |
| "Em processamento" | **CORRIGIDO** (leitura) | `GET /api/imoveis/{id}` devolve `analise_em_processamento` (lock advisory da operação, `tests/test_analysis_status.py::test_is_running...`) e a UI acompanha até terminar | A execução continua **síncrona**; não há progresso por agente | P1 |
| Metadata `category` nos chunks | **CORRIGIDO** | `documents/categories.py`: todo chunk novo grava `category` + `domains`; `tests/test_rag_category_and_recall.py`; E2E: o agente jurídico passou a recuperar trechos filtrando por categoria | Chunks **antigos** (sem as chaves) continuam elegíveis a qualquer domínio (decisão de compatibilidade); não houve backfill | — |
| Recuperação RAG sem embedding | **CORRIGIDO** para consultas genéricas | A consulta padrão usa OR entre termos; sem nenhuma correspondência, devolve os primeiros trechos dos documentos prontos, **marcados `match_type=posicional` e sinalizados** (`reason`). Consulta explícita continua estrita (não inventa contexto). E2E: `chunks_recuperados > 0` (antes `[]`) | A contingência não é relevância: é contexto bruto, limitado a 8 trechos. Com embeddings, a busca vetorial substitui | — |
| RAG com embedding | **NÃO VALIDADO** | CÓDIGO: busca híbrida 70% vetor / 30% texto | Executar `ia-real.spec.ts` | P0 |
| Estado do documento | **CORRIGIDO** | Etapas explícitas `upload → OCR → extração → chunking → embedding → indexação` e `pronto_para_analise` (`documents/readiness.py`); `tests/test_document_readiness.py` | — | — |
| "Indexado" só com embedding completo | **CORRIGIDO** | Antes, um único vetor marcava `INDEXADO`. Agora só quando **todos** os chunks têm vetor; parcial → `INDEXADO_PARCIAL`; sem vetor → `PRONTO_SEM_EMBEDDING` | — | — |
| Documento sem texto/OCR | **CORRIGIDO** | Novos estados `SEM_TEXTO`, `OCR_NECESSARIO`, `OCR_FALHOU`: fora do RAG, fora da fila de embeddings (sem custo inútil), reenvio do mesmo arquivo **reprocessa** em vez de reaproveitar; a análise vira `parcial` se nenhum documento está pronto | — | — |
| OCR (mecanismo) | **PARCIAL** | CÓDIGO + testes com o motor **simulado**: Tesseract local (`pytesseract` + `pdf2image`); `ocr_available()` agora exige o **binário**; limites `OCR_MAX_PAGES` (60) e timeout por página; páginas além do limite são registradas (`ocr_truncated`) | O OCR **real não foi executado** (o ambiente de teste não tem o binário). Ligar `OCR_ENABLED=true` e medir memória na VPS é decisão do operador | P1 |
| Dados pessoais no prompt | **CORRIGIDO** (identificadores) / **PARCIAL** (nomes) | `app/privacy.py`: o `LLMGateway` mascara CPF, RG, e-mail, telefone e dados bancários em **todo** chat e **todo** embedding. **Auditoria final:** `NameAliaser` pseudonimiza nomes de PF conhecidos (titular, polos de processos, ocupantes) e nomes após rótulos jurídicos ("Proprietário:", "Executado:"…) em agentes, extração e embeddings; respostas do LLM são restauradas localmente. `tests/test_privacy_minimization.py`, `tests/test_pseudonymization.py` | Nomes soltos sem rótulo/cadastro, referências parciais, endereço, nº CNJ e CNPJ **seguem identificáveis** (ver seção 3.1). Sem NER. Exige decisão do responsável | **P0** |
| Logs e erros | **CORRIGIDO** | O filtro de logging e `sanitize_error` removem segredos **e** dados pessoais; teste com CPF/e-mail/chave. CÓDIGO: nenhum log imprime conteúdo de documento ou prompt | — | — |
| Teto de custo | **PARCIAL** | `LLM_BUDGET_USD_MONTH` (soma `llm_runs` do mês; ao atingir, agentes devolvem `ORCAMENTO_EXCEDIDO`, sem chamar a OpenAI), `LLM_MAX_OUTPUT_TOKENS`; `tests/test_cost_controls_and_https.py` | Retries do SDK são invisíveis; análises simultâneas ainda podem ultrapassar o mês por uma análise; **o limite no painel da OpenAI continua obrigatório** | **P0** |
| Teto por análise / fail-closed | **CORRIGIDO** | `LLM_BUDGET_USD_PER_ANALYSIS` + `_RunBudget` no `Supervisor.run`; modelo sem preço em `llm_pricing` bloqueia (`sem_preco`); `tests/test_cost_accounting.py` | Teto só vale com preço cadastrado | — |
| Custo de embeddings | **CORRIGIDO** (estimado) | Cada embedding vira linha em `llm_runs` (`agent="embedding"`), tokens **estimados** (chars/4), preço `EMBEDDING_PRICE_PER_1M_USD`; checklist usa 1 chamada batch | Valor é estimativa; conferir com o painel da OpenAI | P1 |
| HTTPS | **PARCIAL** | `REQUIRE_HTTPS=true` → 426 em HTTP e HSTS em HTTPS (testado com requisições reais) | Colocar HTTPS no proxy é ação de infraestrutura (ver PLANO §5) | **P0** |
| Caminhos do servidor na resposta | **CORRIGIDO** | `original_path`, `normalized_path`, `fallback_reason`, `ocr_error` e dados de lease deixaram de ser devolvidos; E2E confere ausência de `/tmp/`, `/app/` | — | — |
| Configuração do provider | **PARCIAL** | `docker-compose.prod.yml` passa a repassar `LLM_REDACT_PII`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_BUDGET_USD_MONTH`, `EMBEDDING_PRICE_PER_1M_USD`, `OCR_MAX_PAGES`, `REQUIRE_HTTPS` (vazio = não configurado) | Só vale após publicar a versão corrigida | P1 |
| Chave na VPS | **NÃO VALIDADO** | Sem acesso à VPS | Comandos de leitura no PLANO §1 | P1 |
| Teste de conexão | **FALHA** (aberta) | Não existe endpoint de diagnóstico | Script do PLANO §4 (passo 3) | P1 |
| Embeddings (geração e gravação) | **NÃO VALIDADO** | Simulados (gateway falso) para provar estados; nada real | Validar com chave de teste | **P0** |
| Agentes Documental, Jurídico, Financeiro, Mercado, Checklist | **NÃO VALIDADO** | EXECUTADO: rodam e devolvem `SEM_CHAVE`; a qualidade da interpretação nunca foi vista | Validar com chave de teste | **P0** |
| Consolidação e veredito | **OK** | Veredito determinístico (`verdict_engine`); com dados vazios, `INCONCLUSIVO` | O veredito não depende do LLM | — |
| Índice vetorial | **NÃO VALIDADO** | CÓDIGO: `ivfflat lists=100`, sem HNSW | `EXPLAIN` após carga | P3 |
| Duplicação `embed_pending_chunks` | **FALHA** (aberta) | Dois módulos com o mesmo nome (`documents/embedding.py`, `rag/embeddings.py`) | Unificar | P3 |

## 3. Testes que provam as correções (todos sem chave)

| Arquivo | Prova |
|---|---|
| `tests/test_analysis_status.py` | Status por cenário (todos ok, parcial, sem chave, erro, orçamento, documentos não prontos); HTTP real; status persistido; "em processamento" pelo lock |
| `tests/test_document_readiness.py` | Pipeline real: texto digital, arquivo vazio, PDF sem texto com OCR desligado/indisponível/ok/falho/sem melhora, embeddings completos/parciais/falha do provider, fora do RAG e da fila, reenvio |
| `tests/test_rag_category_and_recall.py` | `category`/`domains`, filtro por domínio, chunk legado, consulta padrão (OR), contingência posicional explícita, isolamento por imóvel, consulta estrita |
| `tests/test_privacy_minimization.py` | O que seria enviado ao provider não contém CPF/e-mail/telefone; logs e erros também |
| `tests/test_cost_controls_and_https.py` | Orçamento mensal, `ORCAMENTO_EXCEDIDO`, estimativa de embedding, 426/HSTS |
| `e2e/tests/correcoes.spec.ts` | Backend e navegador reais, sem chave: ponta a ponta no celular |

## 3.1 Auditoria final: egress, isolamento e custo

### Egress de dados a terceiros

| Destino | O que sai | Proteção |
|---|---|---|
| OpenAI chat (`LLMGateway`, único caminho; sem bypass) | Texto de chunks, dados do imóvel, processos, ocupantes | Mascara CPF/RG/e-mail/telefone/banco; pseudonimiza nomes conhecidos/rotulados |
| OpenAI embeddings | Texto dos chunks e consultas | Mesma máscara/aliasing antes de embeddar; **vetores de textos com nomes desconhecidos** continuam derivados do texto |
| Judicial API (DataJud, serviço interno) | CPF/CNPJ/nome/nº do processo **em claro** | Nenhuma; ação iniciada pelo usuário. **Aceito/documentado** |
| Geocoding (Google) | Endereço + chave na query | Nenhuma. **Aceito/documentado** |
| Nome de arquivo (`documentos[].nome`), observações e movimentações | Vão ao prompt | Só regex |

**Removido de fato:** CPF, RG, e-mail, telefone, dados bancários, nomes de PF cadastrados ou rotulados.
**Permanece identificável:** nomes soltos sem rótulo/cadastro, referências parciais ("Sra. Ferreira Lima"), endereço, nº CNJ, CNPJ, empresas e entes públicos.
Regex de CPF **não** é anonimização completa; trata-se de minimização.

### Isolamento do RAG

- `HybridRetriever.search` recusa busca sem `property_id` (`ValueError`); `allow_global` não é usado pela app (teste estático).
- Por padrão só a **última versão pronta** de cada documento entra; versões bloqueadas excluídas.
- Findings do LLM só persistem se o chunk citado pertence ao imóvel (e ao conjunto recuperado); caso contrário é descartado sem 500.
- `create_evidence` exige chunk ∈ versão informada.
- **Defeito corrigido:** a cláusula `:has_embedding OR texto` do SQL não tinha parênteses, então com embedding os filtros de imóvel/versão/estado eram ignorados (a busca vetorial podia devolver trechos de outro imóvel). Achado pelo teste negativo e corrigido em `rag/retriever.py`.
- Testes negativos: `tests/test_rag_isolation.py`.
- **Risco aceito:** download `GET /api/documentos/versoes/{id}/arquivo` sem checagem de dono (sistema single-tenant); `latest_execution(prop)` vs analysis_id; `KnowledgeMemoryService` sem chamadores.

### Contabilização de custo: caminhos remanescentes sem contagem exata

- Retries automáticos do SDK (`llm_max_retries=1`) não aparecem em `llm_runs`.
- Tokens de embeddings são estimados.
- Análises simultâneas podem passar do teto mensal pelo valor de cada uma.
- `analysis.token_usage` não inclui embeddings (estão em `llm_runs`).
- `rag/embeddings.embed_pending_chunks` alternativo, sem chamadores: não reativar sem passar pelo gateway.
- Limites de taxa são em memória por processo.
- Monitoramento: `GET /api/monitoring/rag` → `orcamento_llm`.

## 4. O que ainda falta para comprovar a IA

1. Chave de teste com teto de gasto (ver `PLANO-ATIVACAO-OPENAI.md`).
2. Executar `e2e/tests/ia-real.spec.ts` (**NÃO EXECUTADO**, 7 testes gated).
3. Decisão do responsável sobre nomes dentro dos documentos (risco residual).
4. Publicar a versão corrigida (esta rodada **não** foi publicada) e, na VPS, validar OCR e HTTPS.
