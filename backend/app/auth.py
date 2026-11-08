"""Autenticação real (Onda 11): hashing de senha (bcrypt), JWT (HS256) e resolução
do usuário corrente a partir do header ``Authorization: Bearer <token>``.

Falha-fechada: sem ``jwt_secret_key`` configurado, a emissão/validação de token é
recusada (503) — não há sessão "aberta" por omissão. Senhas nunca trafegam/são
armazenadas em claro; o token nunca é logado. Identidade local em PostgreSQL (sem
provedor externo); o bootstrap do primeiro admin é opcional e vem do ambiente.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db
from .logging_config import get_logger

logger = get_logger("auth")

# Dependências de auth são opcionais no import (o app sobe mesmo sem elas instaladas);
# a ausência vira falha-fechada em runtime, nunca um crash de importação do módulo.
try:  # pragma: no cover - caminho de ambiente
    import bcrypt as _bcrypt
except Exception:  # pragma: no cover
    _bcrypt = None

try:  # pragma: no cover - caminho de ambiente
    import jwt as _jwt
except Exception:  # pragma: no cover
    _jwt = None


class AuthError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


# ---------------------------------------------------------------------------
# Hashing de senha (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    if _bcrypt is None:
        raise AuthError(503, "Hashing de senha indisponível: dependência 'bcrypt' não instalada.")
    if not password or len(password) < 8:
        raise AuthError(422, "A senha deve ter ao menos 8 caracteres.")
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if _bcrypt is None or not password or not password_hash:
        return False
    try:
        return _bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT (HS256)
# ---------------------------------------------------------------------------

def _require_secret() -> str:
    if _jwt is None:
        raise AuthError(503, "Autenticação indisponível: dependência 'PyJWT' não instalada.")
    if not settings.jwt_secret_key:
        raise AuthError(503, "Autenticação indisponível: JWT_SECRET_KEY não configurado (proteção obrigatória).")
    return settings.jwt_secret_key


def create_access_token(user: "models.User") -> dict[str, Any]:
    """Gera um JWT assinado para o usuário. Retorna token + metadados (sem segredo)."""
    secret = _require_secret()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = _jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.access_token_expire_minutes * 60}


def decode_token(token: str) -> dict[str, Any]:
    secret = _require_secret()
    try:
        return _jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except Exception as exc:  # PyJWT levanta subclasses de PyJWTError
        raise AuthError(401, "Token inválido ou expirado.") from exc


# ---------------------------------------------------------------------------
# Autenticação de usuário
# ---------------------------------------------------------------------------

def authenticate(db: Session, email: str, password: str) -> "models.User":
    """Autentica por e-mail + senha. Falha-fechada e com mensagem genérica (não revela
    se o e-mail existe). Usuário inativo não autentica."""
    user = db.scalar(select(models.User).where(models.User.email == (email or "").strip().lower()))
    if user is None or not user.active or not verify_password(password, user.password_hash):
        logger.info("login_falha email_hash=%s", _email_fingerprint(email))
        raise AuthError(401, "Credenciais inválidas.")
    user.last_login_at = datetime.utcnow()
    db.flush()
    logger.info("login_ok user_id=%s role=%s", user.id, user.role)
    return user


def _email_fingerprint(email: str | None) -> str:
    """Identificador não-reversível do e-mail para log de auditoria (sem expor PII)."""
    import hashlib
    return hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Resolução do usuário corrente (dependência FastAPI)
# ---------------------------------------------------------------------------

def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> "models.User | None":
    """Resolve o usuário do Bearer token, se houver um válido; caso contrário None.
    NÃO levanta — usado por camadas que aceitam token admin OU usuário (compat)."""
    token = _extract_bearer(authorization)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except HTTPException:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    user = db.get(models.User, int(sub)) if str(sub).isdigit() else None
    if user is None or not user.active:
        return None
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> "models.User":
    """Exige um Bearer token válido de um usuário ativo. Falha-fechada (401)."""
    token = _extract_bearer(authorization)
    if not token:
        raise AuthError(401, "Autenticação necessária (Authorization: Bearer).")
    payload = decode_token(token)
    sub = payload.get("sub")
    user = db.get(models.User, int(sub)) if sub and str(sub).isdigit() else None
    if user is None or not user.active:
        raise AuthError(401, "Usuário não encontrado ou inativo.")
    return user


# ---------------------------------------------------------------------------
# Bootstrap opcional do primeiro administrador (idempotente)
# ---------------------------------------------------------------------------

def ensure_bootstrap_admin(db: Session) -> bool:
    """Cria o 1º admin SOMENTE se o ambiente fornecer e-mail + senha de bootstrap e
    ainda não existir nenhum usuário. Idempotente. Sem env => nada é criado (nunca há
    credencial padrão em produção). Retorna True se criou."""
    email = settings.auth_bootstrap_admin_email
    password = settings.auth_bootstrap_admin_password
    if not email or not password:
        return False
    if db.scalar(select(models.User).limit(1)) is not None:
        return False
    db.add(models.User(
        email=email.strip().lower(), name=settings.auth_bootstrap_admin_name,
        password_hash=hash_password(password), role="ADMIN", active=True,
    ))
    db.flush()
    logger.info("bootstrap_admin criado email_hash=%s", _email_fingerprint(email))
    return True
