# Radar Leilão — Projeção de Capacidade e Custo

Estudo de dimensionamento baseado na **estrutura real** (medições da auditoria +
configuração do RAG). Onde não há medição, está explicitamente marcado como estimativa.

## 1. Baseline medido (2026-11)

- Modelo de embedding: `text-embedding-3-small`, dimensão **1536** (`vector(1536)`).
- Vetor denso pgvector: 1536 × 4 bytes = **6.144 bytes/vetor** (+ overhead pequeno).
- Conteúdo médio de chunk: **~1.179 bytes**; metadata JSON: **~265 bytes** (medidos).
- `document_chunks`: 1.649 linhas / ~25 MB total (dados ~9,6 MB + índices ~15 MB; TOAST ~5,5 MB).
- PGDATA total ≈ 95 MB; volume de PDFs ≈ 6,3 MB (acervo do imóvel 633).
- Índices atuais em `document_chunks`: btree (pk + fk), GIN trigram (`content`), IVFFlat
  (`embedding`, `lists=100`).

## 2. Custo por chunk (totalmente embeddado) — estimativa fundamentada

| Componente | Por chunk | Base |
|---|---:|---|
| Vetor (embedding) | ~6,0 KB | 1536×4 bytes (medido) |
| Texto + metadata + linha/TOAST | ~1,6 KB | médias medidas + overhead |
| Índices (IVFFlat + GIN + btree) | ~7 KB | ordem do vetor + trigram (estimativa) |
| **Total** | **~14,6 KB/chunk** | |

> Índices são o componente que menos escala linearmente; os números de índice são
> **estimativa** (dependem de `lists`/distribuição e do tipo — IVFFlat vs HNSW).

## 3. Cenários de crescimento

| Chunks | Vetores | Texto+metadata | Índices | **Total aprox.** |
|---:|---:|---:|---:|---:|
| 10 mil (MVP) | ~60 MB | ~16 MB | ~70 MB | **~145 MB** |
| 100 mil | ~600 MB | ~160 MB | ~700 MB | **~1,4 GB** |
| 1 milhão | ~6,0 GB | ~1,6 GB | ~7,0 GB | **~14–15 GB** |

- **PDFs originais** crescem à parte (storage local ou S3), não no banco. Com dedup por
  hash, só conteúdo novo aumenta o storage.
- **Backups**: cada dump custom ≈ 25–50% do tamanho lógico do banco (compressão). Com
  retenção de N dumps, reserve ~N × (0,3–0,5 × tamanho do banco).
- **Dedup** reduz diretamente as três colunas: hoje ~66% dos chunks são redundantes
  (reingestões), então um acervo "limpo" caberia em ~1/3 do projetado.

## 4. Recursos por cenário (estimativa; não há benchmark de carga real)

| Cenário | vCPU | RAM | SSD (banco+índices+PDFs+backups) | Workers |
|---|---:|---:|---:|---:|
| MVP (≤10k chunks) | 2 | 4 GB | 40 GB | 1 |
| Crescimento (~100k) | 4 | 8 GB | 80–120 GB | 1–2 |
| Escala (~1M) | 8 | 16–32 GB | 250–400 GB | 2–4 |

- RAM: pgvector/HNSW se beneficiam de índice em memória; em ~1M, priorizar RAM.
- CPU: embeddings são I/O-bound (chamada externa); o gargalo local é a indexação e a
  busca. `UVICORN_WORKERS ≈ 2×vCPU` como ponto de partida.
- Concorrência de ingestão: 1 worker no MVP; aumentar `WORKER_BATCH_LIMIT` e nº de
  workers conforme a fila (`/api/monitoring/rag/pending`).

## 5. Critérios objetivos para escalar

- **Índice vetorial:** migrar IVFFlat → HNSW quando #vetores > ~100k ou a latência de
  busca p95 degradar; recriar índice após grandes cargas (ver `docs/RAG-ARCHITECTURE.md`).
- **Storage de PDFs:** mover para S3/MinIO quando o volume local passar de ~dezenas de GB
  ou quando precisar de DR/replicação.
- **Worker:** adicionar réplicas quando a fila pendente não drenar entre varreduras.
- **RAM do Postgres:** aumentar quando `shared_buffers`/cache hit degradar (monitorar).

## 6. Observações

- Projeção derivada de medições pontuais + fórmulas; **não** é benchmark de carga. Validar
  com teste de carga sintético antes de compromissos de SLA.
- O custo de API de embeddings (OpenAI) é externo e proporcional ao nº de chunks novos —
  fora do escopo desta missão (sem chamadas reais).
