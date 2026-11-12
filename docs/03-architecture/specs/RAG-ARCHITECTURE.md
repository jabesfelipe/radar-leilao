# RAG — Arquitetura de recuperação e busca vetorial (Radar Leilão)

Este documento descreve a arquitetura atual do RAG, a decisão sobre índices vetoriais
(IVFFlat × HNSW), o papel da tabela `knowledge_items` e a estratégia de busca híbrida
com isolamento por imóvel/oportunidade. Reflete o código real.

## 1. Componentes

| Componente | Arquivo | Papel |
|---|---|---|
| Ingestão | `backend/app/documents/pipeline.py` | normaliza, chunka, persiste `DocumentChunk`, gera embedding |
| Chunking | `backend/app/documents/chunker.py` | `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter(1200/160)` |
| Embedding (ingestão) | `backend/app/documents/embedding.py` | `embed_pending_chunks` idempotente (só `embedding IS NULL`) |
| Dedup/Idempotência | `backend/app/documents/dedup.py`, `states.py` | SHA-256, reaproveitamento, estados canônicos |
| Backfill controlado | `backend/app/documents/embedding_backfill.py` | cobertura + backfill dry-run (desabilitado por padrão) |
| Recuperação | `backend/app/rag/retriever.py` | busca **híbrida** (vetor + texto) com filtros |
| Memória/legal | `backend/app/knowledge_memory.py`, `legal_service.py` | `KnowledgeItem` (casos + biblioteca jurídica) |
| Observabilidade | `backend/app/routers/monitoring.py` | `/api/monitoring/rag` (cobertura, erros) |

## 2. Modelo de embeddings

- **Modelo:** `text-embedding-3-small` (`settings.embedding_model`).
- **Dimensão:** `1536` (`settings.embedding_dimensions`).
- **Coluna:** pgvector `vector(1536)` em `document_chunks.embedding` **e** `knowledge_items.embedding`.
- **Guarda de dimensão:** o pipeline descarta vetores com dimensão diferente da coluna
  (evita mistura acidental de modelos). Trocar o modelo/dimensão exige **migration
  dedicada** (a coluna é fixada no import do model); não é feito automaticamente.
- **Sem chave:** sem `OPENAI_API_KEY`, a ingestão segue por texto (chunks com
  `embedding NULL`); a busca degrada para textual (`pg_trgm`/`tsquery`). Não há
  fallback de embedding local.

## 3. Busca híbrida (`HybridRetriever`)

Combinação linear **ponderada**: `final = (vetor·0.7 + texto·0.3) / (0.7+0.3)`
(`rag_vector_weight`/`rag_text_weight`). O score de vetor usa distância de cosseno
(`embedding <=> query`), o de texto usa `ts_rank_cd` normalizado pelo máximo da
consulta.

### Filtros (isolamento)
`RetrieverFilters`: `property_id`, `document_id`, `document_type`, `document_version`,
`category` e **`opportunity_id`** (Fase 3). O isolamento por imóvel sempre restringe
`d.property_id`; o isolamento por oportunidade usa `c.metadata_json ->> 'opportunity_id'`.

- **Por que metadata e não coluna/FK:** `Document` não tem `opportunity_id` (adicionar
  exigiria migration). O chunk carrega o `opportunity_id` no `metadata_json` quando a
  ingestão ocorre em contexto de oportunidade (`pipeline.ingest(opportunity_id=...)`).
- **Comportamento seguro:** quando o filtro de oportunidade está ativo, chunks sem o
  campo (legado) **não vazam** — o escopo restrito nunca traz conteúdo de outra
  oportunidade. Sem o filtro, o comportamento anterior é preservado.

## 4. Decisão de índice vetorial: IVFFlat × HNSW

### Estado atual (medido na auditoria)
- Índice existente: `ix_document_chunks_embedding_ivfflat` — `USING ivfflat
  (embedding vector_cosine_ops) WITH (lists=100)`, criado com a tabela **vazia**.
- `knowledge_items.embedding` **não tem índice vetorial** (busca por `cosine_distance`
  faz varredura sequencial — ok para 9 itens, ruim ao crescer).
- Base atual: 1.649 chunks (552 com vetor). Nesse volume, o planner frequentemente
  ignora o índice e faz scan — diferença de latência irrelevante hoje.

### Comparação

| Critério | IVFFlat | HNSW |
|---|---|---|
| Qualidade (recall) | boa, depende de `lists`/`probes` e de treino sobre dados | superior e estável |
| Latência de consulta | boa após treino | melhor em geral |
| Tempo de construção | rápido | mais lento |
| Tamanho em disco | menor | **maior** (grafo) |
| Inserção incremental | tolera, mas degrada sem retreino (`lists` fixo) | degrada menos |
| Memória | menor | maior (grafo em memória ajuda muito) |
| Custo de manutenção | precisa `REINDEX`/retreino após carga | menor |

### Recomendação (fundamentada, não automática)
1. **MVP / < ~50k vetores:** manter **IVFFlat**, mas **recriar o índice após a carga
   inicial** (ele foi criado vazio — IVFFlat treina os centroides sobre os dados
   presentes; criado vazio tende a ficar subótimo). Ajustar `lists ≈ sqrt(n_linhas)`
   e definir `ivfflat.probes` em consulta conforme recall desejado.
2. **Crescimento / > ~100k vetores com atualização frequente:** migrar para **HNSW**
   (`USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`),
   aceitando índice maior em troca de recall/latência melhores e menos manutenção.
3. **`knowledge_items`:** criar índice vetorial (IVFFlat ou HNSW) **somente quando
   houver volume real de embeddings** — hoje são 9 itens, 0 com vetor; índice agora
   não traz ganho. Documentado como pendência de crescimento.

Qualquer troca de índice é feita por **migration dedicada e reversível**, com validação
em banco descartável, **sem** tocar os dados históricos. Nenhuma troca foi aplicada
nesta fase (apenas recomendação + testes de recuperação).

## 5. Testes de qualidade de recuperação

`tests/test_rag.py` (existente) cobre: ranking/pesos, busca textual sem API key,
busca vetorial, filtros (documento/tipo/versão/categoria), limite, ausência de
contexto, **isolamento por imóvel**, e geração de SQL com filtros combinados.

`tests/test_rag_opportunity_isolation.py` (Fase 3) cobre: SQL do filtro
`opportunity_id`, **isolamento por oportunidade** (não vaza chunk de outra
oportunidade) e preservação do comportamento sem o filtro.

Cenários de borda cobertos no conjunto RAG: documento inexistente / sem embedding /
busca textual / busca vetorial / filtro por imóvel / filtro por oportunidade /
conteúdo duplicado (dedup) / versões distintas / ausência de API key / dimensão
incompatível (guard no pipeline).

## 6. Limitações conhecidas / pendências

- Índice IVFFlat criado vazio — recriar após carga (ver §4).
- `knowledge_items` sem índice vetorial e com embeddings pendentes (sem chave).
- `Document` não tem `opportunity_id` dedicado; isolamento por oportunidade depende do
  `metadata_json` do chunk (stamp na ingestão). Promover a coluna/FK é decisão futura
  (migration 0024+).
- Backfill de embeddings ausentes é **capacidade sob demanda** (dry-run por padrão);
  não executado nesta missão.
