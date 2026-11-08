"""Router de monitoramento/observabilidade mínima (Fase 2/5).

Indicadores REAIS para operação e readiness, sem stack pesada:
- ``/api/monitoring/readiness``: banco acessível (SELECT 1) + versão Alembic.
- ``/api/monitoring/rag``: cobertura de embeddings e pendências de ingestão.

Leitura exige autenticação (reusa get_current_user da Onda 11). Sem segredos nos
retornos. Não dispara processamento nem chamadas externas.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..database import get_db
from ..documents.embedding_backfill import coverage_report

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/readiness")
def readiness(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    db_ok = True
    alembic = None
    try:
        db.execute(text("SELECT 1"))
        alembic = db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:
        db_ok = False
    return {"db": db_ok, "alembic_version": alembic}


@router.get("/rag")
def rag_metrics(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    cobertura = coverage_report(db)
    documentos = db.scalar(select(func.count()).select_from(models.Document)) or 0
    versoes = db.scalar(select(func.count()).select_from(models.DocumentVersion)) or 0
    versoes_erro = db.scalar(
        select(func.count()).select_from(models.DocumentVersion).where(models.DocumentVersion.status == "ERRO")
    ) or 0
    return {
        "documentos": int(documentos),
        "versoes": int(versoes),
        "versoes_em_erro": int(versoes_erro),
        "embeddings": cobertura,
    }
