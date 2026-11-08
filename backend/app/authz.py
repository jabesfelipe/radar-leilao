"""Autorização por papel/permissão (RBAC) — Onda 11.

A identidade real agora vem de ``auth.py`` (usuários + JWT). Esta camada concentra o
mapa PAPEL → PERMISSÕES e as dependências ``require_permission``/``require_role`` que
protegem endpoints no BACKEND (nunca confiando no cliente).

Resolução do portador (ordem):
  1. ``Authorization: Bearer <jwt>`` → usuário ativo → papel do usuário (preferencial).
  2. **Compat temporária:** ``X-Admin-Token`` == ``settings.admin_api_token`` → papel
     ADMIN; tokens adicionais por papel via ``settings.authz_role_tokens`` (JSON). Este
     caminho é um mecanismo de compatibilidade em desativação controlada — NÃO é
     identidade de usuário. Falha-fechada quando nenhum token está configurado.

Falha-fechada: sem credencial válida → 401; sem token nem usuário configurados → 503
(apenas no caminho de compat); papel sem a permissão → 403. Tokens/segredos nunca são
logados.
"""
from __future__ import annotations

import json

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db

# ---------------------------------------------------------------------------
# Permissões granulares
# ---------------------------------------------------------------------------
PERM_ADMIN_WRITE = "admin:write"          # municípios/tipos/fontes/cobertura (estrutura)
PERM_PARAM_WRITE = "admin:parameters"     # alteração de parâmetros de negócio
PERM_DEBT_QUERY = "debt:query"            # executar consulta de débito
PERM_USER_MANAGE = "user:manage"          # gerenciar usuários (criar/editar/desativar)
PERM_ANALYSIS_WRITE = "analysis:write"    # criar/registrar análises, dívidas, estimativas
PERM_READ = "read"                        # consultar (todos os papéis autenticados têm)

ALL_PERMISSIONS = (
    PERM_ADMIN_WRITE, PERM_PARAM_WRITE, PERM_DEBT_QUERY,
    PERM_USER_MANAGE, PERM_ANALYSIS_WRITE, PERM_READ,
)

# ---------------------------------------------------------------------------
# Papéis canônicos (models.USER_ROLES) → permissões explícitas.
# ADMIN: tudo. ANALISTA: cria/consulta análises e débitos. OPERADOR: registra débitos/
# consulta e parametriza. CONSULTA: somente leitura.
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ADMIN": set(ALL_PERMISSIONS),
    "ANALISTA": {PERM_ANALYSIS_WRITE, PERM_DEBT_QUERY, PERM_READ},
    "OPERADOR": {PERM_PARAM_WRITE, PERM_DEBT_QUERY, PERM_ANALYSIS_WRITE, PERM_READ},
    "CONSULTA": {PERM_READ},
}

# Aliases legados (tokens antigos / testes) → papel canônico. ``admin``→ADMIN,
# ``operador``→OPERADOR. Preserva compatibilidade do X-Admin-Token/authz_role_tokens.
_LEGACY_ROLE_ALIASES = {"admin": "ADMIN", "operador": "OPERADOR"}


def permissions_for(role: str) -> set[str]:
    canonical = _LEGACY_ROLE_ALIASES.get(role, role)
    return ROLE_PERMISSIONS.get(canonical, set())


# ---------------------------------------------------------------------------
# Compat: X-Admin-Token → papel (em desativação controlada)
# ---------------------------------------------------------------------------

def _role_tokens() -> dict[str, str]:
    """Mapa papel→token do mecanismo de compatibilidade. ``admin`` =
    ``settings.admin_api_token``; papéis extras via ``settings.authz_role_tokens``
    (JSON). Inválido/ausente ⇒ papel não habilitado (falha-fechada)."""
    tokens: dict[str, str] = {}
    if settings.admin_api_token:
        tokens["admin"] = settings.admin_api_token
    extra = getattr(settings, "authz_role_tokens", None)
    if extra:
        try:
            parsed = json.loads(extra) if isinstance(extra, str) else dict(extra)
            for role, tok in parsed.items():
                if isinstance(tok, str) and tok and (role in _LEGACY_ROLE_ALIASES or role in ROLE_PERMISSIONS):
                    tokens[role] = tok
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return tokens


def _role_from_admin_token(x_admin_token: str | None) -> str | None:
    """Resolve o papel a partir do X-Admin-Token (compat). Retorna None se não houver
    token configurado (deixa o chamador decidir 401 vs 503) ou se não casar."""
    tokens = _role_tokens()
    if not tokens:
        return None
    if not x_admin_token:
        return None
    for role, tok in tokens.items():
        if x_admin_token == tok:
            return _LEGACY_ROLE_ALIASES.get(role, role)
    return None


# ---------------------------------------------------------------------------
# Resolução do papel do portador (Bearer user OU X-Admin-Token)
# ---------------------------------------------------------------------------

def resolve_principal(authorization: str | None, x_admin_token: str | None, db: Session) -> tuple[str, str]:
    """Retorna ``(role, principal)`` onde principal descreve a origem (``user:<id>`` ou
    ``token:<papel>``). Falha-fechada. Preferência para o usuário autenticado (JWT)."""
    # 1) Bearer user (preferencial). Import local evita ciclo auth↔authz.
    from . import auth as _auth
    user = _auth.get_optional_user(authorization=authorization, db=db)
    if user is not None:
        return user.role, f"user:{user.id}"
    # 2) Compat X-Admin-Token.
    tokens = _role_tokens()
    if not tokens:
        # Nenhum usuário autenticado e nenhum token/identidade configurados: proteção
        # obrigatória indisponível (falha-fechada, 503) — preserva o contrato anterior.
        raise HTTPException(503, "Autorização indisponível: nenhuma credencial configurada (Bearer ou token).")
    role = _role_from_admin_token(x_admin_token)
    if role is None:
        if not x_admin_token:
            raise HTTPException(401, "Credencial ausente (Authorization: Bearer ou X-Admin-Token).")
        raise HTTPException(401, "Credencial inválida.")
    return role, f"token:{role}"


def require_permission(permission: str):
    """Dependência: exige que o portador (usuário JWT ou token de compat) tenha
    ``permission``. Validação exclusivamente no backend."""
    def _dep(
        authorization: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> str:
        role, _principal = resolve_principal(authorization, x_admin_token, db)
        if permission not in permissions_for(role):
            raise HTTPException(403, f"Papel '{role}' não possui a permissão '{permission}'.")
        return role
    return _dep


def require_role(*roles: str):
    """Dependência: exige que o portador tenha um dos papéis canônicos informados."""
    allowed = {_LEGACY_ROLE_ALIASES.get(r, r) for r in roles}
    def _dep(
        authorization: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> str:
        role, _principal = resolve_principal(authorization, x_admin_token, db)
        canonical = _LEGACY_ROLE_ALIASES.get(role, role)
        if canonical not in allowed:
            raise HTTPException(403, f"Papel '{role}' não autorizado. Requer: {', '.join(sorted(allowed))}.")
        return role
    return _dep
