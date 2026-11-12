# Como contribuir

Vale para pessoas e para qualquer ferramenta de IA. Detalhes em [docs/05-development/development-workflow.md](docs/05-development/development-workflow.md).

## Antes de começar
1. Configure o ambiente: [docs/05-development/getting-started.md](docs/05-development/getting-started.md).
2. Leia o módulo que vai tocar em [docs/02-product/modules](docs/02-product/modules/) e a [arquitetura](docs/03-architecture/README.md).

## Fluxo
1. Crie um branch a partir da `main`.
2. Faça mudanças pequenas e incrementais.
3. Rode os testes ([docs/05-development/testing.md](docs/05-development/testing.md)): `pytest -q tests`, `npx tsc -b` e `npm test` em `frontend/`.
4. **Atualize a documentação na mesma entrega** (tabela de "o que atualizar" em `development-workflow.md`).
5. Abra um pull request para a `main`; o CI precisa passar.

## Regras
- Português do Brasil na interface e na documentação.
- Migrations Alembic incrementais, reversíveis, nunca editadas depois de aplicadas ([guia](docs/05-development/database-migrations.md)).
- Não altere chaves canônicas do checklist.
- Mudou a API: atualize `tests/contract/openapi_baseline.json`.
- Rotas novas exigem autenticação.
- Nunca versione `.env`, dumps, chaves, tokens ou IPs de servidores; o repositório é público.
- Nunca rode `down -v`, `DROP`, `TRUNCATE` ou limpezas destrutivas no banco com dados de referência.
- Tags `v*` publicam e fazem deploy; só administradores as criam e elas são imutáveis.

## Usando um assistente de IA
Permitido, com a mesma responsabilidade: revise o que foi gerado, rode os testes e atualize a documentação. Instruções específicas de uma ferramenta ficam em arquivos próprios dela e apontam para este guia.
