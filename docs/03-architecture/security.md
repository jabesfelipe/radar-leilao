# Segurança

Estado da segurança na aplicação e no ambiente de homologação. Auditoria detalhada de exposição:
[specs/SECURITY-EXPOSURE-AUDIT.md](specs/SECURITY-EXPOSURE-AUDIT.md). Infraestrutura: [../04-operations/infrastructure.md](../04-operations/infrastructure.md#12-segurança-e-limitações).

## Camadas existentes

| Camada | Descrição |
|---|---|
| Portão do proxy | sem cookie `radar_gate` válido (obtido em `/acesso?k=<GATE_KEY>`), o proxy responde 403 em tudo |
| JWT | HS256, expira em 480 min; `JWT_SECRET_KEY` obrigatório (503 sem ele); senhas com bcrypt |
| RBAC | ADMIN, ANALISTA, OPERADOR e CONSULTA com permissões `admin:write`, `admin:parameters`, `debt:query`, `user:manage`, `analysis:write`, `read` ([auth-users](../02-product/modules/auth-users.md)) |
| Rate limit | 10 requisições por minuto no login (burst 5) |
| Docs ocultas | `/docs`, `/redoc` e `/openapi.json` respondem 404 pelo proxy |
| Download autenticado | `GET /api/documentos/versoes/{id}/arquivo` exige JWT e só serve arquivos dentro do storage |
| Segredos de portais | Fernet em coluna separada; histórico guarda só `has_secret`; recuperação com token dedicado |
| Rede | PostgreSQL e backend sem porta pública; UFW com SSH e 80/tcp |
| Deploy | usuário `radar` sem senha e com chave restrita; token do GHCR passa pela stdin do SSH e não fica em disco; `VPS_KNOWN_HOSTS` fixa a host key |

## Lacunas conhecidas (verdadeiras hoje)

1. **148 de 184 rotas não exigem credencial no backend** (36 exigem: 21 JWT e 15 RBAC). Isso inclui ~112 endpoints de `main.py` e os hubs. A proteção real dessas rotas é o portão do proxy. Fechá-las é pendência antes de qualquer acesso público.
2. **HTTP sem TLS**: senha, JWT e cookie do portão trafegam em texto claro.
3. **JWT em `localStorage`**: exposto a XSS.
4. **`X-Admin-Token`** legado ainda aceito como fallback ([plano de desativação](../04-operations/operations.md#3-desativação-controlada-do-x-admin-token-legado)).
5. **Cookie do portão** capturado dá acesso às rotas legadas sem JWT.
6. Ambiente de testes: **não usar dados sensíveis**.

## Práticas obrigatórias
- Nunca versionar `.env`, chaves privadas, tokens, `GATE_KEY` nem senhas; este repositório é público.
- Segredos da aplicação vivem só na VPS (`.env.prod`, modo 600) e no GitHub (Secrets).
- Ao documentar, use `<VPS_HOST>` no lugar do IP e não cole saída de comandos que contenha segredos.
