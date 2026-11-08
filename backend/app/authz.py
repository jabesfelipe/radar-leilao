"""Camada de autorização administrativa (Etapa D — segurança).

O produto ainda NÃO possui um provedor de identidade (login/usuários/sessão/JWT) — essa
infraestrutura é da frente de auth/RBAC (Onda 11). Esta camada implementa a
**autorização por papel/permissão** sobre o mecanismo de credencial já existente
(``X-Admin-Token``), de forma real e testável, sem inventar um provedor de identidade.

Como funciona:
  - O portador apresenta ``X-Admin-Token``. O token é mapeado para um PAPEL
    (``settings.admin_api_token`` → papel ``admin``). Tokens adicionais por papel podem
    ser configurados por ambiente via ``settings.authz_role_tokens`` (JSON
    papel→token) sem alterar código.
  - Cada papel concede um conjunto de PERMISSÕES. Os endpoints exigem uma permissão
    específica (``require_permission(perm)``), validada no BACKEND.
  - Falha-fechada: sem token configurado → 503; token ausente/!inválido → 401; papel
    sem a permissão → 403.

Dependência registrada (NÃO resolvida aqui): autenticação de usuários reais, sessão,
expiração/rotação de credencial e RBAC completo dependem da Onda 11. Até lá, o token é
a credencial e o papel é derivado do token. O token NUNCA é exposto em logs/respostas.
"""
from __future__ import annotations

import json

from fastapi import Depends, Header, HTTPException

from .config import settings

# Permissões administrativas (granulares). Novos domínios acrescentam permissões aqui.
PERM_ADMIN_WRITE = "admin:write"          # cadastro/edição de municípios/tipos/fontes/cobertura
PERM_PARAM_WRITE = "admin:parameters"     # alteração de parâmetros de negócio
PERM_DEBT_QUERY = "debt:query"            # executar consulta de débito

ALL_PERMISSIONS = (PERM_ADMIN_WRITE, PERM_PARAM_WRITE, PERM_DEBT_QUERY)

# Papéis → permissões. ``admin`` tem tudo; ``operador`` pode consultar/parametrizar,
# mas não alterar a estrutura de cobertura. Extensível por configuração futura.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": set(ALL_PERMISSIONS),
    "operador": {PERM_PARAM_WRITE, PERM_DEBT_QUERY},
}


def _role_tokens() -> dict[str, str]:
    """Mapa papel→token. Sempre inclui ``admin`` = ``settings.admin_api_token`` (quando
    configurado). Tokens adicionais por papel podem vir de ``settings.authz_role_tokens``
    (JSON), permitindo papéis sem recompilar — ainda provisório até a Onda 11."""
    tokens: dict[str, str] = {}
    if settings.admin_api_token:
        tokens["admin"] = settings.admin_api_token
    extra = getattr(settings, "authz_role_tokens", None)
    if extra:
        try:
            parsed = json.loads(extra) if isinstance(extra, str) else dict(extra)
            for role, tok in parsed.items():
                if role in ROLE_PERMISSIONS and isinstance(tok, str) and tok:
                    tokens[role] = tok
        except (json.JSONDecodeError, TypeError, ValueError):
            pass  # configuração inválida é ignorada (falha-fechada: papel não habilitado)
    return tokens


def resolve_role(x_admin_token: str | None) -> str:
    """Resolve o papel a partir do token. Falha-fechada. NUNCA loga o token."""
    tokens = _role_tokens()
    if not tokens:
        raise HTTPException(503, "Administração indisponível: nenhum token de autorização configurado (proteção obrigatória).")
    if not x_admin_token:
        raise HTTPException(401, "Token de administração ausente (X-Admin-Token).")
    for role, tok in tokens.items():
        if x_admin_token == tok:
            return role
    raise HTTPException(401, "Token de administração inválido (X-Admin-Token).")


def require_permission(permission: str):
    """Fábrica de dependência: exige que o papel do portador tenha ``permission``.
    Valida a autorização no backend (não confia no cliente)."""
    def _dep(x_admin_token: str | None = Header(default=None)) -> str:
        role = resolve_role(x_admin_token)
        if permission not in ROLE_PERMISSIONS.get(role, set()):
            raise HTTPException(403, f"Papel '{role}' não possui a permissão '{permission}'.")
        return role
    return _dep
