"""Router administrativo — Central de Débitos/Parâmetros (Etapa A).

Operações administrativas (municípios, tipos de débito, fontes e o catálogo central
de parâmetros). **Segurança:** a ESCRITA administrativa exige o header
``X-Admin-Token`` igual a ``settings.admin_api_token`` (falha-fechada: sem token
configurado, a escrita é recusada com 503). Isto é uma proteção **PROVISÓRIA** até a
frente de auth/RBAC (Onda 11) — está documentado e NÃO substitui RBAC real.

Leituras (listagens/consulta/resolução) são abertas (dados não sensíveis; nenhum
segredo trafega por aqui — segredos continuam em secrets_crypto). Nenhuma consulta
externa/scraping é executada: fontes são apenas cadastradas.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, parameters as params, debts_service, coverage_service
from ..config import settings
from ..database import get_db
from ..authz import require_permission, PERM_ADMIN_WRITE, PERM_PARAM_WRITE

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Autorização por PAPEL/PERMISSÃO sobre o token (authz.py). `require_admin` mantém o
# nome histórico, agora exigindo a permissão de escrita administrativa; parâmetros
# usam uma permissão própria. Falha-fechada (503 sem token / 401 inválido / 403 sem
# permissão). Dependência registrada: auth/RBAC de usuários reais é da Onda 11.
require_admin = require_permission(PERM_ADMIN_WRITE)
require_param_admin = require_permission(PERM_PARAM_WRITE)


# ---------------------------------------------------------------------------
# Municípios
# ---------------------------------------------------------------------------
@router.get("/municipios")
def list_municipalities(db: Session = Depends(get_db)):
    debts_service.seed_municipalities(db); db.commit()
    rows = db.scalars(select(models.Municipality).order_by(models.Municipality.name)).all()
    return {"total": len(rows), "itens": [schemas.MunicipalityOut.model_validate(m).model_dump() for m in rows]}


@router.post("/municipios", status_code=201)
def create_municipality(data: schemas.MunicipalityCreate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    m = models.Municipality(**data.model_dump())
    db.add(m); db.commit(); db.refresh(m)
    return schemas.MunicipalityOut.model_validate(m).model_dump()


@router.patch("/municipios/{municipality_id}")
def update_municipality(municipality_id: int, data: schemas.MunicipalityUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    m = db.get(models.Municipality, municipality_id)
    if not m:
        raise HTTPException(404, "Município não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return schemas.MunicipalityOut.model_validate(m).model_dump()


# ---------------------------------------------------------------------------
# Tipos de débito (catálogo)
# ---------------------------------------------------------------------------
@router.get("/tipos-debito")
def list_debt_types(db: Session = Depends(get_db)):
    debts_service.seed_debt_types(db); db.commit()
    rows = db.scalars(select(models.DebtType).order_by(models.DebtType.group, models.DebtType.code)).all()
    return {"total": len(rows), "itens": [schemas.DebtTypeOut.model_validate(t).model_dump() for t in rows]}


@router.post("/tipos-debito", status_code=201)
def create_debt_type(data: schemas.DebtTypeCreate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    if db.scalar(select(models.DebtType).where(models.DebtType.code == data.code)):
        raise HTTPException(409, "code já existe no catálogo de tipos de débito")
    t = models.DebtType(**data.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return schemas.DebtTypeOut.model_validate(t).model_dump()


@router.patch("/tipos-debito/{debt_type_id}")
def update_debt_type(debt_type_id: int, data: schemas.DebtTypeUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    t = db.get(models.DebtType, debt_type_id)
    if not t:
        raise HTTPException(404, "Tipo de débito não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit(); db.refresh(t)
    return schemas.DebtTypeOut.model_validate(t).model_dump()


# ---------------------------------------------------------------------------
# Fontes (apenas cadastro; nenhuma consulta externa nesta etapa)
# ---------------------------------------------------------------------------
@router.get("/fontes")
def list_sources(municipality_id: int | None = Query(default=None), debt_category: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(models.DebtSource)
    if municipality_id is not None:
        stmt = stmt.where(models.DebtSource.municipality_id == municipality_id)
    if debt_category is not None:
        stmt = stmt.where(models.DebtSource.debt_category == debt_category)
    rows = db.scalars(stmt.order_by(models.DebtSource.municipality_id, models.DebtSource.name)).all()
    return {"total": len(rows), "itens": [schemas.DebtSourceOut.model_validate(s).model_dump() for s in rows]}


@router.post("/fontes", status_code=201)
def create_source(data: schemas.DebtSourceCreate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    if not db.get(models.Municipality, data.municipality_id):
        raise HTTPException(400, "municipality_id inexistente")
    # Valida a categoria contra o catálogo de tipos (quando informada): evita fonte órfã.
    if data.debt_category is not None and not db.scalar(
        select(models.DebtType).where(models.DebtType.code == data.debt_category)
    ):
        raise HTTPException(400, f"debt_category desconhecida: {data.debt_category!r} (cadastre em tipos-debito)")
    if data.source_type not in models.DEBT_SOURCE_TYPES:
        raise HTTPException(422, f"source_type inválido: {data.source_type}")
    if data.situation not in models.DEBT_SOURCE_SITUATIONS:
        raise HTTPException(422, f"situation inválida: {data.situation}")
    s = models.DebtSource(**data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return schemas.DebtSourceOut.model_validate(s).model_dump()


@router.patch("/fontes/{source_id}")
def update_source(source_id: int, data: schemas.DebtSourceUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    s = db.get(models.DebtSource, source_id)
    if not s:
        raise HTTPException(404, "Fonte não encontrada")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("debt_category") is not None and not db.scalar(
        select(models.DebtType).where(models.DebtType.code == changes["debt_category"])
    ):
        raise HTTPException(400, f"debt_category desconhecida: {changes['debt_category']!r}")
    if changes.get("source_type") is not None and changes["source_type"] not in models.DEBT_SOURCE_TYPES:
        raise HTTPException(422, f"source_type inválido: {changes['source_type']}")
    if changes.get("situation") is not None and changes["situation"] not in models.DEBT_SOURCE_SITUATIONS:
        raise HTTPException(422, f"situation inválida: {changes['situation']}")
    for k, v in changes.items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    return schemas.DebtSourceOut.model_validate(s).model_dump()


# ---------------------------------------------------------------------------
# Parâmetros (catálogo central + resolução + histórico)
# ---------------------------------------------------------------------------
@router.get("/parametros")
def list_parameters(category: str | None = Query(default=None), key: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(models.Parameter)
    if category is not None:
        stmt = stmt.where(models.Parameter.category == category)
    if key is not None:
        stmt = stmt.where(models.Parameter.key == key)
    rows = db.scalars(stmt.order_by(models.Parameter.category, models.Parameter.key, models.Parameter.scope)).all()
    return {"total": len(rows), "itens": [schemas.ParameterOut.model_validate(p).model_dump() for p in rows]}


@router.get("/parametros/categorias")
def list_parameter_categories(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Parameter.category).distinct()).all()
    return {"categorias": sorted(set(rows))}


@router.get("/parametros/resolver")
def resolve_parameter(key: str, municipality_id: int | None = Query(default=None), debt_category: str | None = Query(default=None), db: Session = Depends(get_db)):
    return params.resolve_detail(db, key, municipality_id=municipality_id, debt_category=debt_category)


@router.get("/parametros/{parameter_id}/historico")
def parameter_history(parameter_id: int, db: Session = Depends(get_db)):
    if not db.get(models.Parameter, parameter_id):
        raise HTTPException(404, "Parâmetro não encontrado")
    rows = db.scalars(
        select(models.ParameterHistory).where(models.ParameterHistory.parameter_id == parameter_id).order_by(models.ParameterHistory.id)
    ).all()
    return {"parameter_id": parameter_id, "historico": [
        {"id": h.id, "version": h.version, "action": h.action, "previous_value": h.previous_value,
         "new_value": h.new_value, "actor": h.actor, "justification": h.justification, "created_at": h.created_at}
        for h in rows
    ]}


@router.post("/parametros", status_code=201)
def create_parameter(data: schemas.ParameterCreate, db: Session = Depends(get_db), _: str = Depends(require_param_admin)):
    try:
        payload = data.model_dump()
        justification = payload.pop("justification", None)
        param = params.create_parameter(db, payload, actor="admin", justification=justification)
    except params.ParameterError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit(); db.refresh(param)
    return schemas.ParameterOut.model_validate(param).model_dump()


@router.patch("/parametros/{parameter_id}")
def update_parameter(parameter_id: int, data: schemas.ParameterUpdate, db: Session = Depends(get_db), _: str = Depends(require_param_admin)):
    param = db.get(models.Parameter, parameter_id)
    if not param:
        raise HTTPException(404, "Parâmetro não encontrado")
    try:
        changes = data.model_dump(exclude_unset=True)
        justification = changes.pop("justification", None)
        params.update_parameter(db, param, changes, actor="admin", justification=justification)
    except params.ParameterError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit(); db.refresh(param)
    return schemas.ParameterOut.model_validate(param).model_dump()


# ---------------------------------------------------------------------------
# Cobertura municipal × tipo de débito (Etapa B)
# Leitura aberta; escrita protegida. Nenhuma consulta externa é executada aqui —
# apenas a MATRIZ de cobertura é cadastrada/consultada.
# ---------------------------------------------------------------------------
@router.get("/cobertura")
def list_coverage(municipality_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    """Matriz de cobertura (município × tipo). Semeia a cobertura inicial on-read
    (idempotente) e expõe também os tipos ativos ainda NÃO investigados."""
    debts_service.seed_all(db); db.commit()
    return coverage_service.coverage_matrix(db, municipality_id=municipality_id)


@router.post("/cobertura", status_code=201)
def create_coverage(data: schemas.CoverageCreate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    try:
        item = coverage_service.create_coverage(db, data.model_dump())
    except coverage_service.CoverageError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit(); db.refresh(item)
    return schemas.CoverageOut.model_validate(item).model_dump()


@router.patch("/cobertura/{coverage_id}")
def update_coverage(coverage_id: int, data: schemas.CoverageUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    item = db.get(models.MunicipalityCoverage, coverage_id)
    if not item:
        raise HTTPException(404, "Cobertura não encontrada")
    try:
        coverage_service.update_coverage(db, item, data.model_dump(exclude_unset=True))
    except coverage_service.CoverageError as exc:
        db.rollback(); raise HTTPException(422, str(exc)) from exc
    db.commit(); db.refresh(item)
    return schemas.CoverageOut.model_validate(item).model_dump()
