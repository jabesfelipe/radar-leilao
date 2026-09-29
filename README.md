# Radar Leilão

MVP em português do Brasil para análise rastreável de imóveis em leilões extrajudiciais.

**Estado:** 🟢 MVP FUNCIONALMENTE ENCERRADO — 28/09/2026

A validação E2E final foi executada com o imóvel real **COND PARQUE ARVOREDO RESIDENCIAL CLUBE (property_id=633)**, chegando à Analysis V9 com LLM real, cinco agentes, Checklist, Risk Engine, Verdict Engine e histórico versionado.

## Documentação oficial

- [SPEC — Arquitetura e Business](docs/SPEC-VIBE-CODING-RADAR-LEILAO.md) — documento mestre.
- [Referência de Implementação](docs/IMPLEMENTATION-REFERENCE.md) — onde cada capacidade está implementada no código.
- [Status do Projeto](docs/PROJECT-STATUS.md) — estado atual e critérios de encerramento.
- [Histórico do Projeto](docs/PROJECT-HISTORY.md) — decisões, correções, commits e validações.
- [Workflow de Desenvolvimento](docs/DEVELOPMENT-WORKFLOW.md) — processo Kiro → commit → auditoria.

### Regra após o fechamento

O MVP não possui uma próxima TASK funcional planejada.

Novas capacidades devem ser tratadas como **Fase 2 / backlog**, salvo correção de defeito crítico.

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

Imóvel → documentos → normalização/OCR → chunks/embeddings → RAG → agentes → evidências → Checklist → Risk Engine → Verdict Engine → histórico

## Operação

Scripts principais:

./scripts/setup.sh  
./scripts/start.sh  
./scripts/restart.sh  
./scripts/health.sh  
./scripts/logs.sh  
./scripts/backup.sh  
./scripts/restore.sh  
./scripts/stop.sh

O restart.sh preserva os volumes nomeados; não deve ser confundido com reset.sh, que é uma operação destrutiva explícita.

## Executar

Pré-requisitos: Docker Desktop com integração WSL habilitada.

    ./scripts/setup.sh
    ./scripts/restart.sh
    ./scripts/health.sh

Frontend: http://localhost:5173  
API/documentação: http://localhost:8000/docs

## LLM

Os fluxos determinísticos e de recuperação podem funcionar sem LLM. Para embeddings/interpretação OpenAI, configure OPENAI_API_KEY no .env.

O provider é acessado pelo LLM Gateway; chamadas não ficam espalhadas pelo domínio.

## Migrations

Nunca use Base.metadata.create_all no runtime. O schema é controlado por Alembic:

    alembic -c backend/alembic.ini upgrade head

A extensão vector é habilitada no PostgreSQL. Não há SQLite nem banco vetorial externo no MVP.
