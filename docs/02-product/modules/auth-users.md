# Autenticação e usuários

**Status: implementado, com cobertura parcial das rotas** (Onda 11). Das 184 rotas, 36 exigem credencial (21 JWT e 15 RBAC) e 148 não.

## Objetivo
Identificar usuários, aplicar papéis (RBAC) e proteger rotas novas e de escrita administrativa.

## Funcionalidades
- Login por e-mail e senha (bcrypt), token JWT HS256 com expiração de 480 minutos; `JWT_SECRET_KEY` obrigatório (sem ele, 503).
- Bootstrap do primeiro administrador por variáveis de ambiente (idempotente: cria só se não houver usuários).
- Gestão de usuários (listar, criar, alterar) com `user:manage`.
- Frontend: sessão em `localStorage` (`radar.auth.token`, `radar.auth.user`); `installAuthFetch` injeta `Authorization: Bearer` nas chamadas `/api`; resposta 401 limpa a sessão e dispara o evento `radar:unauthorized`; sem sessão, a LoginPage é exibida.

## Papéis e permissões
| Papel | Permissões |
|---|---|
| ADMIN | todas: `admin:write`, `admin:parameters`, `debt:query`, `user:manage`, `analysis:write`, `read` |
| ANALISTA | `analysis:write`, `debt:query`, `read` |
| OPERADOR | `admin:parameters`, `debt:query`, `analysis:write`, `read` |
| CONSULTA | `read` |

`authorized_writer` exige JWT com `analysis:write`. Fallback legado: cabeçalho `X-Admin-Token`.

## Endpoints (`/api/auth`)
`POST /login`, `GET /me`, `GET /usuarios`, `POST /usuarios`, `PATCH /usuarios/{id}`.

## Limitações
- Cerca de 112 endpoints de `main.py` e os hubs continuam sem JWT; o portão do proxy é a barreira de borda. Fechá-los é pendência registrada em [known-limitations.md](../../06-quality/known-limitations.md).
- Token no `localStorage` (exposto a XSS) e tráfego em HTTP sem TLS.

## Código
`auth.py`, `authz.py`, `routers/auth.py`, `config.py`; frontend `session.ts`, `LoginPage`, serviço `auth`. Migration `0023_usuarios`.
