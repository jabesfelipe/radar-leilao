# Modelo de dados

PostgreSQL 16 com extensão pgvector. ORM SQLAlchemy 2.0 (`backend/app/models.py`); migrations Alembic em `backend/migrations/versions`.
Estado conferido: **69 tabelas** num banco novo criado por `alembic upgrade head` (igual à produção; o número 60 citado antes contava só os modelos de `models.py`, sem `alembic_version` e sem as tabelas `judicial_*`) e **24 migrations**: head `0024_analysis_version_unique` na branch de hardening; `main` e a produção estão em `0023_usuarios`. Diagrama do núcleo em [architecture.md](architecture.md#5-persistência).

## Princípios
- O imóvel (`properties`) é a entidade central; quase tudo referencia `property_id`.
- Originais e histórico não são sobrescritos: versões de documento, execuções de checklist, análises, análises financeiras e vereditos são versionados.
- `entity_history` guarda o antes/depois das edições cadastrais; `domain_events` registra eventos de domínio.
- Credenciais de portais ficam em coluna separada e cifrada (Fernet) e nunca são devolvidas em listagens, histórico, logs, evidências, LLM ou RAG.
- A oportunidade (`opportunity`, migrations 0018 e 0019) introduz o isolamento por `opportunity_id`.

## Grupos de tabelas (núcleo conferido em `models.py`)

| Grupo | Tabelas |
|---|---|
| Imóvel e leilão | `properties`, `auctions`, `property_sources`, `property_registrations`, `auction_notices` |
| Documentos e RAG | `documents`, `document_versions`, `document_chunks`, `evidences`, `evidence_links` |
| Checklist | `checklist_items`, `checklist_executions`, `checklist_results`, `checklist_evidences` |
| Jurídico | `legal_processes`, `process_movements` (mais as tabelas `judicial_*` da migration 0011 e as da Central Jurídica, 0017) |
| Financeiro e débitos | `costs`, `debts`, `financial_analyses` (mais premissas, catálogos, parâmetros e consultas: 0012, 0020, 0021, 0022) |
| Mercado e ocupação | `market_comparables`, `occupancy_analyses` |
| Análise | `risks`, `analyses`, `verdicts`, `knowledge_items`, `llm_runs`, `llm_pricing` |
| Auditoria | `domain_events`, `entity_history` |
| Leiloeiros | `auctioneers`, `portal_accesses`, `auctioneer_documents` |
| Pós-arrematação | `post_auctions`, `post_auction_stages`, `post_auction_costs`, `occupant_contacts`, `contact_attempts`, consultorias, propostas e minutas |
| Workflow | oportunidades, transições, estados de fase e decisões (0018, 0019) |
| Usuários | usuários e papéis (0023) |

A lista completa das tabelas está em `models.py` e nas migrations; este documento lista só o que foi conferido diretamente.

## Migrations

| Revisão | Tema |
|---|---|
| 0001 | fundação |
| 0002 | uso e preço de LLM |
| 0003 | checklist mestre |
| 0004 | entradas financeiras |
| 0005 | histórico de ocupação |
| 0006 | processos jurídicos |
| 0007 | matrícula e edital |
| 0008 | extração documental |
| 0009 | cadastro completo do imóvel |
| 0010 | data e hora do leilão |
| 0011 | persistência judicial |
| 0012 | premissas financeiras |
| 0013 | correlação de processo |
| 0014 | leiloeiros |
| 0015 | pós-arrematação |
| 0016 | due diligence |
| 0017 | Central Jurídica |
| 0018 | oportunidade |
| 0019 | FK de oportunidade |
| 0020 | Central de Débitos |
| 0021 | cobertura municipal |
| 0022 | consulta e estimativa |
| 0023 | usuários |
| 0024 | índice único de análise por (imóvel, oportunidade, versão); idempotente, aborta sem alterar dados se houver duplicatas |

Próxima migration livre: `0025`. As Ondas 1 e 2 do workflow reusam o schema de 0018 e 0019. Regras para novas migrations:
[../05-development/database-migrations.md](../05-development/database-migrations.md). Especificações do modelo de workflow:
[specs/MODEL-DATA-WORKFLOW.md](specs/MODEL-DATA-WORKFLOW.md), [specs/SPEC-OPPORTUNITY-DOMAIN.md](specs/SPEC-OPPORTUNITY-DOMAIN.md).

## Invariantes históricos a preservar
Imóvel 633 (COND PARQUE ARVOREDO RESIDENCIAL CLUBE), análises V1 a V9 e financeiras V1 a V9, 45 `llm_runs`, 27 `canonical_key`, 8 regras da Central Jurídica e 150 arquivos de storage.
