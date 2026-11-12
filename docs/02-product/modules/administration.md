# Administração

**Status: implementado.**

## Objetivo
Manter catálogos e parâmetros que alimentam débitos, financeiro e mercado, e a matriz de cobertura municipal.

## Funcionalidades
Abas da tela: overview, municípios, cobertura, fontes, tipos (de débito) e parâmetros.
- Municípios, tipos de débito e fontes de consulta (apenas cadastro; nenhuma consulta externa).
- Matriz de cobertura município × tipo (semeada na leitura).
- Parâmetros centrais: listar, categorias, resolução por chave (com município e categoria), histórico, criação e alteração. Valores semeados em `parameter_seeds.py` (por exemplo, `mercado.amostra_minima = 7`).

## Endpoints (`/api/admin`)
`/municipios`, `/tipos-debito`, `/fontes`, `/cobertura` (GET, POST, PATCH); `/parametros`, `/parametros/categorias`, `/parametros/resolver`, `/parametros/{id}/historico` (GET), `POST/PATCH /parametros`.

## Permissões
Escrita exige `admin:write` (criação e edição de catálogos) ou `admin:parameters` (parâmetros); leitura sem JWT. A autorização aceita também o cabeçalho legado `X-Admin-Token`; o plano de desativação está em [operations.md](../../04-operations/operations.md#3-desativação-controlada-do-x-admin-token-legado).

## Divergência
A tela ainda exibe o campo "X-Admin-Token", mecanismo legado anterior ao RBAC.

## Código
`backend/app/routers/admin.py`, `parameters.py`, `parameter_seeds.py`, `coverage_service.py`; frontend `AdminPage`.
