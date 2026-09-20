# Radar Leilão

MVP em português do Brasil para análise rastreável de imóveis em leilões extrajudiciais, alinhado à `SPEC-VIBE-CODING-RADAR-LEILAO.md`.

## Arquitetura local

- React + TypeScript
- FastAPI + SQLAlchemy
- PostgreSQL + pgvector no Docker/WSL
- Alembic para migrations
- Documentos: original imutável + MarkItDown + Markdown + chunks
- RAG híbrido: pgvector + full-text + metadata
- LangChain + LangGraph
- LLM Gateway com OpenAI inicial e provider extensível

## Executar

Pré-requisitos: Docker Desktop com integração WSL habilitada, Python 3.12+ e Node.js 20+.

```powershell
Copy-Item .env.example .env
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
alembic -c backend\alembic.ini -x config=backend upgrade head
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Em outro terminal:

```powershell
npm.cmd install --prefix frontend
npm.cmd run dev --prefix frontend
```

Frontend: http://localhost:5173  
API/documentação: http://localhost:8000/docs

## LLM

A API funciona sem a chave para os fluxos determinísticos e recuperação full-text. Para embeddings e interpretação OpenAI, configure `OPENAI_API_KEY` no `.env`. Nenhuma chamada do provider fica espalhada na aplicação: use `LLM Gateway`.

## Migrations

Nunca use `Base.metadata.create_all` no runtime. Para aplicar o schema:

```powershell
alembic -c backend/alembic.ini upgrade head
```

A extensão `vector` é habilitada pelo init do PostgreSQL e pela migration. Não há SQLite nem banco vetorial externo.
