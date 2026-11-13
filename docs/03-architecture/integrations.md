# Integrações

Estado de cada integração, conferido em código e configuração. Diagrama: [architecture.md](architecture.md#10-integrações).

| Integração | Situação | Como funciona | Configuração |
|---|---|---|---|
| OpenAI (LLM e embeddings) | existe, **opcional** | modelos `gpt-4o-mini` e `text-embedding-3-small` (1536 dimensões); sem chave, agentes retornam `SEM_CHAVE` e embeddings ficam pendentes | `OPENAI_API_KEY` (não configurada na VPS); `LLM_TIMEOUT_SECONDS` (90) e `LLM_MAX_RETRIES` (1) configuráveis; erros classificados e sanitizados ([security.md §7](security.md#7-integração-openai)) |
| RAG híbrido | existe | pgvector + busca textual (`portuguese`): peso 0,7 vetorial e 0,3 textual; fallback textual; limites 8 e 50 | parâmetros em `config.py` |
| OCR (Tesseract) | existe, **desabilitado** | pytesseract, pdf2image, Pillow | `OCR_ENABLED=false` |
| Judicial API (DataJud) | existe | `POST {JUDICIAL_API_BASE_URL}/api/v1/judicial/search` com `X-API-Key`; serviço próprio em `judicial_api/` | `JUDICIAL_API_BASE_URL` (padrão `http://judicial_api:8010`); presente só no compose de desenvolvimento |
| Google Geocoding | existe, opcional | `geocoding_client.py` | chave Google |
| Registro de Imóveis | **sem cliente** | matrícula entra por importação manual de PDF/certidão | `REGISTRO_IMOVEIS_*` apenas no `.env.example` |
| Prefeituras | **sem cliente** | débito municipal registrado manualmente | adaptadores planejados: [SPEC-ADAPTADORES-CONSULTA-MUNICIPAL](specs/SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md) |
| Provider de débitos | manual-assistido | `debt_providers.py` | sem integração automática |
| Portais de leilão | **não integrado** | cadastro e importação manual; candidatos listados em [REVISAO-ANOTACOES-LEILAO](../02-product/specs/REVISAO-ANOTACOES-LEILAO.md) | — |
| Storage | existe | local (volume) ou S3/MinIO | `STORAGE_BACKEND` |
| GitHub Actions, GHCR | existe | build e publicação de imagens por tag | [github-actions.md](../04-operations/github-actions.md) |

## Worker
`python -m app.worker_main`: polling do banco para embeddings pendentes (`WORKER_INTERVAL_SECONDS=30`, `WORKER_BATCH_LIMIT=10`, `WORKER_MAX_ATTEMPTS=5`, `WORKER_LEASE_SECONDS=600`); `--once` executa uma varredura e sai. Cada tentativa é gravada antes do processamento; tentativas interrompidas por crash contam, têm backoff e esgotam em `ERRO` (ver [security.md §8](security.md#8-concorrência-e-duplicidade)). Fila durável na tabela `document_versions`, sem Redis nem Celery.

## Segredos de integração
Chaves vêm de variáveis de ambiente (`.env`, `.env.prod` na VPS). Credenciais de portais de leiloeiros são cifradas com Fernet (`PORTAL_SECRET_KEY`) e recuperáveis só por endpoint dedicado protegido (`PORTAL_ADMIN_TOKEN`). Nenhum valor é registrado nesta documentação.

## Regra de produto para novas integrações
Sem scraping não autorizado, sem consulta paga sem autorização, credenciais e limites. Enquanto não validada, a entrada é manual.
