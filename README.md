# Radar Leilão

MVP em português do Brasil para análise rastreável de imóveis em leilões extrajudiciais.

**Estado em 30/09/2026:** Tasks 2–5 integradas e correção `788d749` (seleção determinística do leilão corrente). Validação de fechamento registrada em `docs/PROJECT-STATUS.md` §21: backend 527 passed / 2 skipped, frontend 90 passed, TypeScript OK. **Validação E2E do fluxo financeiro em navegador real ainda pendente** (o projeto não possui Playwright/Cypress); o MVP NÃO é declarado encerrado até essa validação ser concluída.

A última implementação registrada é a **Task 5 — testes de integração E2E financeiro pela camada HTTP**, commit [6c5f318](https://github.com/jabesfelipe/radar-leilao/commit/6c5f31808f2a259ba0e6dfb8ace63dd484248794). O commit reporta backend 526 passed / 2 skipped, incluindo 12 cenários financeiros de integração HTTP. Os resultados foram reportados pelo executor e não equivalem a um E2E de navegador: a validação manual da UI continua pendente.

## Documentação oficial

- [SPEC — Arquitetura e Business](docs/SPEC-VIBE-CODING-RADAR-LEILAO.md) — visão de negócio e arquitetura.
- [Referência de Implementação](docs/IMPLEMENTATION-REFERENCE.md) — mapeamento da implementação existente.
- [Status do Projeto](docs/PROJECT-STATUS.md) — estado atual, validações e pendências.
- [Histórico do Projeto](docs/PROJECT-HISTORY.md) — histórico de decisões, correções e validações.
- [Workflow de Desenvolvimento](docs/DEVELOPMENT-WORKFLOW.md) — processo Kiro → commit → auditoria.
- [Backlog de Evolução](docs/EVOLUTION-BACKLOG.md) — pendências imediatas e evolução da Fase 2.

## Arquitetura local

- React + TypeScript + Vite
- FastAPI + SQLAlchemy + Pydantic
- PostgreSQL + pgvector no Docker/WSL
- Alembic
- MarkItDown + OCR Tesseract/Poppler
- RAG híbrido e retrieval direcionado do Checklist
- LangChain + LangGraph
- LLM Gateway + provider OpenAI
- cinco agentes LLM: Documental, Jurídico, Financeiro, Mercado e Checklist

## Pipeline

Imóvel → documentos → normalização/OCR → chunks/embeddings → RAG → agentes → evidências → Checklist → Risk Engine → Verdict Engine → histórico.

## Operação

Scripts principais:

```bash
./scripts/setup.sh
./scripts/start.sh
./scripts/restart.sh
./scripts/health.sh
./scripts/logs.sh
./scripts/backup.sh
./scripts/restore.sh
./scripts/stop.sh
```

O `restart.sh` preserva os volumes nomeados; não deve ser confundido com `reset.sh`, que é uma operação destrutiva explícita.

## Executar

Pré-requisitos: Docker Desktop com integração WSL habilitada.

```bash
./scripts/setup.sh
./scripts/restart.sh
./scripts/health.sh
```

Frontend: http://localhost:5173  
API/documentação: http://localhost:8000/docs

## LLM

Os fluxos determinísticos e de recuperação podem funcionar sem LLM. Para embeddings/interpretação OpenAI, configure `OPENAI_API_KEY` no `.env`. O provider é acessado pelo LLM Gateway.

## Migrations

Nunca use `Base.metadata.create_all` no runtime. O schema é controlado por Alembic:

```bash
alembic -c backend/alembic.ini upgrade head
```

A extensão vector é habilitada no PostgreSQL. Não há SQLite nem banco vetorial externo no MVP.

## Próximo passo recomendado

1. Atualizar a cópia local com `git pull --ff-only origin main`.
2. Subir o sistema e executar o roteiro E2E financeiro descrito em `docs/PROJECT-STATUS.md`.
3. Registrar evidências/resultados e corrigir somente defeitos reproduzidos.
4. Depois disso, decidir o fechamento do MVP e iniciar as tarefas de Fase 2.
