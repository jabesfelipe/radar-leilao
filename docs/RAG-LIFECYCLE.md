# Radar Leilão — Ciclo de vida de documentos e RAG

Complementa `RAG-ARCHITECTURE.md` com o ciclo de vida operacional (ingestão →
dedup → chunks → embeddings → indexação) e o tratamento de reprocessamento.

## 1. Estados canônicos (`documents/states.py`)

```
RECEBIDO → EXTRAINDO → EXTRAIDO → AGUARDANDO_EMBEDDING
         → PROCESSANDO_EMBEDDING → INDEXADO → CONCLUIDO
(qualquer etapa) → ERRO | CANCELADO
(conteúdo idêntico reaproveitado) → REAPROVEITADO
```

- Compat legado: `PROCESSADO` (antigo) ≡ `CONCLUIDO` (`normalize_legacy`).
- O estado vive em `DocumentVersion.status` (coluna já existente; sem migration).
- Terminal: `INDEXADO` (houve vetor) ou `CONCLUIDO` (ingestão por texto, sem provider).

## 2. Ingestão (`documents/pipeline.py`)

1. Calcula `content_hash = SHA-256(arquivo)`.
2. **Dedup** (`documents/dedup.py`): se há versão byte-idêntica já processada do **mesmo
   documento**, reaproveita (sem recriar chunks/embeddings). Identidade de arquivo ≠
   documento de negócio — o escopo do reaproveitamento é o documento, preservando as
   relações imóvel/oportunidade/origem.
3. Persiste o original/normalizado/metadata via **abstração de storage** (local/S3).
4. Normaliza (markdown) e **chunka** (`chunker.py`): `chunk_size=1200`, `overlap=160`.
5. Cria `DocumentChunk` com metadata (property_id, document_id, version, tipo, source,
   chunk_index e, opcionalmente, `opportunity_id` para isolamento).
6. Gera embeddings dos chunks pendentes se houver provider/chave (`embed_pending_chunks`,
   idempotente — só `embedding IS NULL`). Dimensão validada contra a coluna (1536).
7. Estado final: `INDEXADO` ou `CONCLUIDO`.

## 3. Reprocessamento idempotente

- Retry é seguro: dedup + `embed_pending_chunks` (só toca chunks sem vetor) garantem que
  reprocessar não duplica.
- Versões históricas NÃO são apagadas (append-only). Nunca há limpeza automática de chunks.
- Controle de tentativas: `extraction_metadata['embedding_attempts']` (worker), erro
  saneado em `embedding_last_error`.

## 4. Worker (`documents/worker.py`, `worker_main.py`)

- Fila durável = tabela `document_versions` (sem Redis). `pending_versions` lista versões
  com chunk sem vetor que não excederam `max_attempts`.
- `process_version` é idempotente; sem provider mantém `AGUARDANDO_EMBEDDING` e **não**
  chama OpenAI; com provider gera pendentes e marca `INDEXADO`.
- Runner: `python -m app.worker_main` (polling; `--once`; SIGTERM/SIGINT graceful).
- Recuperação após reinício: estado no banco ⇒ retoma de onde parou.

## 5. Embeddings ausentes (`documents/embedding_backfill.py`)

- `coverage_report`: chunks totais/com vetor/sem vetor, cobertura %, versões pendentes,
  modelo e dimensão, provider disponível.
- `backfill_missing_embeddings`: **dry-run por padrão e desabilitado** — só executa com
  `dry_run=False` + `enabled=True` + provider. Nunca chama OpenAI por conta própria.
- **Não** foi executado backfill do histórico nesta fase (regra de preservação). Capacidade
  disponível sob decisão explícita do operador.

## 6. Observabilidade

`GET /api/monitoring/rag` (cobertura + versões em erro), `GET /api/monitoring/rag/pending`
(fila), `POST /api/monitoring/rag/reprocess` (dispara varredura assíncrona). Painel no
dashboard do frontend (RagHealthPanel).

## 7. Configuração de embeddings

- Modelo `text-embedding-3-small`, dimensão **1536** (`vector(1536)` em `document_chunks`
  e `knowledge_items`).
- Não reduzir dimensão nem migrar vetores existentes. Guard de dimensão descarta vetores
  incompatíveis (evita mistura de modelos). Troca de modelo = migration dedicada.

## 8. Estado atual medido (auditoria)

- `document_chunks` = 1.649 (552 com vetor; 1.097 sem — ingeridos sem chave).
- 4 documentos / 7 versões (todos do imóvel 633). `EL00440226CPARE.pdf` foi ingerido 3×
  antes da dedup (duplicatas históricas preservadas; dedup evita novas).
- `knowledge_items` = 9 (0 com vetor). Índice vetorial IVFFlat `lists=100` (criado vazio).

## 9. Pendências

- Recriar IVFFlat após carga inicial; avaliar HNSW ao crescer (>100k).
- Backfill de embeddings ausentes (sob decisão + chave).
- Promover `opportunity_id` a coluna/FK em `Document` (hoje via metadata do chunk) —
  decisão futura (migration 0024+).
