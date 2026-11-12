# Radar Leilão — Storage local na VPS

> **Situação: VÁLIDO.** Movido de `docs/STORAGE-LOCAL.md`. Backend de storage: `STORAGE_BACKEND=local` (padrão), com S3/MinIO disponível na abstração.

Nesta fase os documentos ficam na própria VPS, num volume Docker persistente. A
abstração `backend/app/storage` (Local / S3 / MinIO) foi mantida para migração futura.

## 1. Onde ficam os arquivos

Volume `radar-prod_backend_storage`, montado em `/app/backend/storage` no backend e no worker:

```
/app/backend/storage
  documents/property-<id>/original/v<N>-<arquivo>     # arquivo enviado (imutável)
  documents/property-<id>/normalized/v<N>-<nome>.md   # texto extraído
  documents/property-<id>/metadata/v<N>-<nome>.json   # metadados de extração/OCR
  tmp/                                                # temporários (TMPDIR)
```
Nada fica dentro da imagem. Reiniciar ou recriar containers **não** apaga arquivos (o
volume só é removido com `docker volume rm` / `down -v`, proibidos como rotina).

## 2. Fluxos e onde passam pela abstração

| Fluxo | Implementação | Usa a abstração? |
|---|---|---|
| Upload | `POST /api/imoveis/{id}/documentos`, `POST /api/documentos/{id}/versoes` → `DocumentPipeline.ingest` | sim (`build_storage().write_bytes/write_text`) |
| Deduplicação | SHA-256 do conteúdo; reenvio idêntico reaproveita a versão (`documents/dedup.py`) | — |
| Versionamento | `v<N>-` por versão; versões antigas nunca são sobrescritas | sim |
| Extração/OCR | `DocumentNormalizer` (MarkItDown; OCR opcional `OCR_ENABLED`) lê o arquivo local; com backend remoto usa temporário | sim |
| Chunking/embeddings/RAG | no banco (`document_chunks`); embeddings pendentes pelo worker | — |
| Download/visualização | `GET /api/documentos/versoes/{id}/arquivo[?variante=normalizado]` (JWT) | sim (`exists`/`uri_for`/`read_bytes`) |
| Associação imóvel/oportunidade | `documents.property_id`; `opportunity_id` no metadata dos chunks | — |

Leituras de arquivo fora da abstração (aceitas): o normalizador/OCR recebem um `Path` local
porque as bibliotecas (MarkItDown, pdf2image, Tesseract) exigem arquivo em disco.

## 3. Segurança

- Não existe rota estática para `/storage`: o proxy não serve arquivos do volume.
- Download só com usuário autenticado e só de caminhos **dentro** da raiz configurada
  (caminhos legados fora da raiz retornam 404).
- Resposta com `Content-Disposition: attachment` e `X-Content-Type-Options: nosniff`.

## 4. Temporários

`TMPDIR` aponta para `storage/tmp` (no volume, não no disco do container).
Limpeza controlada:
```bash
scripts/prod/cleanup-temp.sh            # dry-run: lista arquivos > 1 dia
APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh
```
Nunca remove `documents/`.

## 5. Diagnóstico de órfãos

`GET /api/monitoring/storage` (ADMIN) classifica diretórios `property-<id>` em
REFERENCED / NOT_REFERENCED / UNCERTAIN. Somente leitura; nada é excluído; o imóvel 633 é
sempre protegido.

## 6. Migração futura para S3/MinIO

Definir `STORAGE_BACKEND=s3|minio` + `STORAGE_S3_*` e instalar `boto3`. Arquivos já
existentes precisariam ser copiados para o bucket (procedimento a definir; fora desta fase).
