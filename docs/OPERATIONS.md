# Operação local — Radar Leilão

## Objetivo

Procedimento seguro para operar o Radar Leilão no Windows + WSL2 + Docker, especialmente durante desenvolvimento e validação E2E.

Prioridades:
1. preservar os dados existentes;
2. garantir que backend e frontend usem a versão atual do código;
3. aplicar o arquivo .env corretamente;
4. permitir investigação por logs;
5. tratar migrations de forma incremental e segura.

## 1. Regra mais importante: nunca apagar os volumes

O banco PostgreSQL e os documentos ficam em volumes Docker persistentes:
- postgres_data → banco PostgreSQL/pgvector;
- backend_storage → documentos persistidos pelo backend.

Comandos normais que preservam os volumes:

    ./scripts/stop.sh
    ./scripts/start.sh
    ./scripts/restart.sh
    docker compose up -d --build

Não executar para corrigir um problema comum:

    docker compose down -v
    docker volume rm ...
    ./scripts/reset.sh

reset.sh é destrutivo e existe apenas para recriar o ambiente do zero, depois de backup e confirmação explícita.

## 2. .env x .env.example

O arquivo .env.example é apenas um modelo. O Docker Compose lê .env e não .env.example. Uma chave colocada apenas no .env.example não habilita a LLM.

Criar .env se ainda não existir:

    if [ ! -f .env ]; then cp .env.example .env; fi

No .env local:

    LLM_PROVIDER=openai
    LLM_MODEL=gpt-4o-mini
    EMBEDDING_MODEL=text-embedding-3-small
    OPENAI_API_KEY=sua-chave-real

A chave real não deve ser commitada.

Conferir sem exibir a chave:

    if grep -q '^OPENAI_API_KEY=.\+' .env; then echo 'OPENAI_API_KEY configurada no .env'; else echo 'OPENAI_API_KEY NÃO configurada no .env'; fi

    docker compose exec backend sh -c 'if [ -n "$OPENAI_API_KEY" ]; then echo "OPENAI_API_KEY configurada no container"; else echo "OPENAI_API_KEY NÃO configurada no container"; fi'

## 3. Atualizar o código e garantir imagem nova

Depois de um commit novo:

    git pull
    ./scripts/restart.sh

O `start.sh`/`restart.sh` executam `docker compose up -d --build`, reconstruindo backend/frontend quando o código/Dockerfile mudam. Também é possível executar diretamente:

    docker compose up -d --build

O --build reconstrói as imagens antes de iniciar os serviços. Isso não remove named volumes. O risco de perda de dados aparece quando volumes são explicitamente removidos, especialmente com down -v. O `restart.sh` recria os containers, o que faz o `.env` ser relido (aplicando, por exemplo, a `OPENAI_API_KEY`).

## 4. Confirmar a versão atual

    docker compose ps
    ./scripts/health.sh
    curl -s http://localhost:8000/health

Swagger: http://localhost:8000/docs

## 5. Conferir migrations sem alterar dados

Antes de uma alteração estrutural no banco existente:

    ./scripts/backup.sh
    docker compose exec postgres psql -U radar -d radar_leilao -c 'select version_num from alembic_version;'
    docker compose exec backend alembic current
    docker compose exec backend alembic heads

Regra para DDL: nunca editar uma migration já aplicada para corrigir um banco existente. Se o schema precisar mudar, criar nova migration Alembic incremental, preservar os dados, validar banco existente e banco limpo.

## 6. Logs

O diagnóstico começa pelos logs do Compose. O script `scripts/logs.sh` centraliza o acesso:

    ./scripts/logs.sh status
    ./scripts/logs.sh tail
    ./scripts/logs.sh tail backend
    ./scripts/logs.sh follow backend
    ./scripts/logs.sh follow
    ./scripts/logs.sh save

O comando save grava snapshots em logs/ com timestamp (ex.: logs/radar-<timestamp>.log). O diretório logs/ é local e não deve ser versionado.

A rotação de logs dos containers é feita pelo Docker (`json-file`, `max-size=10m`, `max-file=5`), evitando crescimento indefinido. O nível de log do backend é controlado por `LOG_LEVEL` (`DEBUG|INFO|WARNING|ERROR`, padrão `INFO`).

Também é possível usar diretamente:

    docker compose logs --timestamps --tail=200 backend
    docker compose logs --timestamps --tail=200 frontend
    docker compose logs --timestamps --tail=200 postgres
    docker compose logs --timestamps --since=30m backend

## 7. O que procurar nos logs do E2E

Cadastro: POST de criação, ID do imóvel, fontes/documentos e erros de upload.
Documentos: identificação, normalização, MarkItDown/OCR, chunks, embeddings, erros de leitura e versionamento.
RAG: consulta, quantidade de chunks, filtros/metadados, reranking e erros de embedding.
LangGraph/agentes: início/fim, agente, domínio, status, erro/stack trace, evidências/chunks e versão da análise.
LLM: provider, modelo, início/fim da chamada e erro do provider.

Nunca registrar OPENAI_API_KEY, Authorization headers, credenciais de banco ou conteúdo completo de documentos sem necessidade. As mensagens de erro de LLM passam por `sanitize_error`.

## 8. Fluxo seguro para a próxima validação E2E

    git pull
    ./scripts/backup.sh
    ./scripts/restart.sh
    ./scripts/health.sh
    ./scripts/logs.sh status
    docker compose exec backend sh -c 'if [ -n "$OPENAI_API_KEY" ]; then echo "OPENAI_API_KEY configurada"; else echo "OPENAI_API_KEY NÃO configurada"; fi'

Depois abrir http://localhost:5173 e executar o fluxo do imóvel real da Caixa.

Ao terminar:

    ./scripts/logs.sh save
    ./scripts/logs.sh tail backend

## 9. Validação da LLM

O objetivo do E2E com chave real é confirmar a cadeia documentos → normalização → chunks → embeddings → RAG → LangGraph → agentes → Checklist → Risk → Verdict → Histórico.

Observar especialmente: llm_used, model, successful_runs, error_runs, chunks_retrieved, documents_considered, evidências, versão da análise e logs de erro.

## 10. Em caso de erro

Não resetar o ambiente imediatamente.

    ./scripts/logs.sh save
    ./scripts/logs.sh tail backend
    ./scripts/health.sh
    docker compose ps

Se houver suspeita de migration:

    docker compose exec backend alembic current
    docker compose exec backend alembic heads
    docker compose exec postgres psql -U radar -d radar_leilao -c 'select version_num from alembic_version;'

Preservar logs e backup, identificar o erro e só então corrigir código/migration.

## 11. Referências

- docs/LOCAL-SETUP.md — instalação e comandos básicos;
- docs/OPERATIONS.md — operação segura, rebuild, .env, logs e banco;
- docs/PROJECT-STATUS.md — estado e próxima TASK;
- docs/PROJECT-HISTORY.md — histórico das decisões e validações.
