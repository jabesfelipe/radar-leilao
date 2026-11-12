# Testes

## Como executar

Backend (a partir da raiz do repositório, com PostgreSQL + pgvector disponível; o CI usa `pgvector/pgvector:pg16`):

```bash
pip install -r backend/requirements.txt
export DATABASE_URL=postgresql+psycopg://radar:radar@localhost:5432/radar_test
export RAG_TEST_DATABASE_URL=$DATABASE_URL
export PYTHONPATH=$PWD
psql -h localhost -U radar -d radar_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
(cd backend && alembic upgrade head)
pytest -q tests
```

Frontend:

```bash
cd frontend
npm ci
npx tsc -b      # checagem de tipos
npm test        # vitest
```

No ambiente local com Docker, os mesmos testes rodam contra o banco do compose (ver [getting-started.md](getting-started.md)). Os testes devem usar banco de teste, nunca o banco `radar_leilao` com dados preservados.

## O que o CI executa (`.github/workflows/ci.yml`)

| Job | Passos |
|---|---|
| backend | PostgreSQL + pgvector descartável; migrations `0001` a head; `alembic downgrade -1` e `upgrade head`; `pytest -q tests` |
| frontend | `npm ci`, `npx tsc -b`, `npm test` |
| docker | valida o compose de produção (modo build e modo imagem publicada), nginx do proxy com `GATE_KEY` de tamanho real, sintaxe dos scripts (`bash -n`), `actionlint`, build das imagens de produção (sem push) |

O CI roda em push e pull request na `main` e é reutilizado pelo `release.yml`. Não usa secrets reais; LLM e integrações externas ficam desligados.

## Estratégia e cobertura

Estratégia, mapa de testes e números atuais: [../06-quality/README.md](../06-quality/README.md).

## Testes de política e contrato que protegem a documentação e o deploy

- `tests/contract/test_openapi_contract.py` compara a API com `tests/contract/openapi_baseline.json` (144 paths). Adicionar ou remover endpoint exige atualizar o baseline na mesma entrega.
- `tests/test_release_workflow_policy.py` exige que existam somente `ci.yml` e `release.yml` em `.github/workflows` e que os scripts `.sh` tenham modo 100755.

## Portão de segurança nos testes

O app registra o `security_gate` como dependência global (default-deny, ver [security.md](../03-architecture/security.md)). Para não repetir login em centenas de testes de domínio, `tests/conftest.py` substitui o portão por um no-op via `app.dependency_overrides` (mesmo mecanismo usado para `get_db`) em todos os testes **exceto** os marcados com `@pytest.mark.security_gate`, que rodam com o portão real (`tests/test_security_gate.py`). As dependências por rota (RBAC de admin, usuários, oportunidades) ficam ativas em todos os testes.

Testes de segurança e concorrência do hardening: `tests/test_security_gate.py`, `test_upload_security.py`, `test_openai_hardening.py` (sem chamadas pagas: dublês/mocks), `test_concurrency_hardening.py` (conexões PostgreSQL independentes para lock, claim e seed), além de `frontend/src/services/session.test.ts` e `components/SecurityNotice.test.tsx`.

Ao criar uma rota nova, rode `pytest tests/test_security_gate.py`: o inventário falha se algo ficar público sem estar em `PUBLIC_ROUTES` e se uma regra de política deixar de casar com uma rota real.

## Rodando o backend sem Docker (Linux/WSL)

Qualquer PostgreSQL 16 com `pgvector` e `pg_trgm` serve (o pacote `pgserver` do PyPI **não** inclui `pg_trgm`; os `.deb` `postgresql-16` e `postgresql-16-pgvector` do Ubuntu 24.04 podem ser extraídos com `dpkg -x` sem root). Depois: `alembic upgrade head` em `backend/`, definir `DATABASE_URL` e `RAG_TEST_DATABASE_URL` e `pytest -q tests` na raiz.
