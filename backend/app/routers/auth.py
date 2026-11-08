"""Router de autenticação/usuários (Onda 11).

- ``POST /api/auth/login``: e-mail + senha → JWT (bearer). Falha genérica (não revela
  se o e-mail existe). Audita sucesso/falha sem expor segredo.
- ``GET /api/auth/me``: usuário corrente + permissões efetivas (exige Bearer).
- ``GET/POST/PATCH /api/auth/usuarios``: gestão de usuários (somente ADMIN —
  permissão ``user:manage``). Validação exclusivamente no backend.

Identidade local em PostgreSQL; nenhuma credencial padrão é criada automaticamente.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..authz import require_permission, permissions_for, PERM_USER_MANAGE
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = auth.authenticate(db, data.email, data.password)
    token = auth.create_access_token(user)
    db.commit()
    return token


@router.get("/me", response_model=schemas.MeOut)
def me(current: models.User = Depends(auth.get_current_user)):
    return {"user": current, "permissions": sorted(permissions_for(current.role))}


@router.get("/usuarios")
def list_users(db: Session = Depends(get_db), _: str = Depends(require_permission(PERM_USER_MANAGE))):
    rows = db.scalars(select(models.User).order_by(models.User.email)).all()
    return {"total": len(rows), "itens": [schemas.UserOut.model_validate(u).model_dump() for u in rows]}


@router.post("/usuarios", status_code=201, response_model=schemas.UserOut)
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db), _: str = Depends(require_permission(PERM_USER_MANAGE))):
    email = data.email.strip().lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(409, "E-mail já cadastrado.")
    user = models.User(
        email=email, name=data.name or email, password_hash=auth.hash_password(data.password),
        role=data.role, active=data.active,
    )
    db.add(user); db.commit(); db.refresh(user)
    return schemas.UserOut.model_validate(user).model_dump()


@router.patch("/usuarios/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db), _: str = Depends(require_permission(PERM_USER_MANAGE))):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado.")
    changes = data.model_dump(exclude_unset=True)
    if "password" in changes and changes["password"]:
        user.password_hash = auth.hash_password(changes.pop("password"))
    else:
        changes.pop("password", None)
    for k, v in changes.items():
        setattr(user, k, v)
    db.commit(); db.refresh(user)
    return schemas.UserOut.model_validate(user).model_dump()
