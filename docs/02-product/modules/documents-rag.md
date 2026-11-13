# Documentos e RAG

**Status: implementado** (OCR desabilitado; embeddings dependem de `OPENAI_API_KEY`).

## Objetivo
Receber documentos (edital, matrícula, outros), preservá-los imutáveis, normalizá-los para texto, indexá-los e recuperar trechos para as análises.

## Funcionalidades
- Upload de documento e de novas versões (originais imutáveis, hash, versionamento).
- Normalização com MarkItDown (PDF); OCR com Tesseract quando habilitado (`OCR_ENABLED=false` hoje).
- Chunking, embeddings (`text-embedding-3-small`, 1536 dimensões) e **busca híbrida** (vetorial 0,7 e textual 0,3), com fallback textual quando não há embeddings.
- Extração estruturada de matrícula/edital e agentes de análise (ver [checklist-risks-verdict.md](checklist-risks-verdict.md)).
- Worker que processa embeddings pendentes por polling (`python -m app.worker_main`; `WORKER_INTERVAL_SECONDS=30`, `WORKER_BATCH_LIMIT=10`, `WORKER_MAX_ATTEMPTS=5`, `WORKER_LEASE_SECONDS=600`; fila na tabela `document_versions`, sem Redis nem Celery).
- Monitoramento de cobertura e fila; governança de storage (dry-run por padrão).

## Telas
Seção "Documentos" do imóvel e hub `/documentos`.

## Endpoints
`POST/GET /api/imoveis/{id}/documentos`; `POST /api/documentos/{id}/versoes`; `POST /api/imoveis/{id}/documentos/{vid}/extrair` e `GET .../extracao`; `GET /api/documentos/versoes/{vid}/arquivo` (**exige JWT**, só serve arquivos dentro do storage).
Monitoramento: `GET /api/monitoring/readiness`, `/rag`, `/rag/pending`, `/storage` (admin); `POST /api/monitoring/rag/reprocess` (`analysis:write`).

## Dados e storage
Documento, versão de documento, chunks com embedding (pgvector), evidências, `llm_runs`. Arquivos em `STORAGE_BACKEND=local` (volume `backend_storage`); S3/MinIO disponível na abstração. Ver [storage](../../04-operations/storage.md).

## Integrações
OpenAI (embeddings e LLM, opcionais), Tesseract.

## Limitações
Sem `OPENAI_API_KEY` os embeddings ficam pendentes e as análises de IA retornam `SEM_CHAVE`. OCR desabilitado. Índice IVFFlat deve ser recriado após a primeira carga ([RAG-ARCHITECTURE](../../03-architecture/specs/RAG-ARCHITECTURE.md)).

## Código
`backend/app/documents/`, `rag/` e `storage/` (pacotes), `worker_main.py`, `routers/document_files.py`, `routers/monitoring.py`. Especificações: [RAG-ARCHITECTURE](../../03-architecture/specs/RAG-ARCHITECTURE.md), [RAG-LIFECYCLE](../../03-architecture/specs/RAG-LIFECYCLE.md).
