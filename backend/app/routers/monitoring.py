"""Router de monitoramento/observabilidade mínima (Fase 2/5).

Indicadores REAIS para operação e readiness, sem stack pesada:
- ``/api/monitoring/readiness``: banco acessível (SELECT 1) + versão Alembic.
- ``/api/monitoring/rag``: cobertura de embeddings e pendências de ingestão.

Leitura exige autenticação (reusa get_current_user da Onda 11). Sem segredos nos
retornos. Não dispara processamento nem chamadas externas.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..authz import require_permission, PERM_ADMIN_WRITE, PERM_ANALYSIS_WRITE
from ..config import settings
from ..database import SessionLocal, get_db
from ..documents.embedding_backfill import coverage_report
from ..documents.storage_governance import diagnose as storage_diagnose
from ..documents import worker as doc_worker

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _run_reprocess_scan(limit: int) -> None:
    """Executa uma varredura do worker numa sessão própria (BackgroundTask)."""
    db = SessionLocal()
    try:
        doc_worker.run_once(db, limit=limit)
    finally:
        db.close()


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


@router.get("/storage")
def storage_diagnostics(db: Session = Depends(get_db), _role: str = Depends(require_permission(PERM_ADMIN_WRITE))):
    """Diagnóstico de governança de storage (somente leitura, admin).

    Inventaria os diretórios de documentos, classifica (REFERENCED/NOT_REFERENCED/
    UNCERTAIN) e calcula o espaço recuperável. NUNCA exclui nada; o imóvel 633 é
    sempre protegido. Exige permissão administrativa."""
    report = storage_diagnose(db, settings.storage_path)
    # Não expõe caminhos absolutos completos por diretório — apenas nome, classificação,
    # tamanho e motivo (reduz vazamento de topologia do host).
    report["diretorios"] = [
        {k: v for k, v in d.items() if k != "path"} for d in report.get("diretorios", [])
    ]
    report.pop("storage_root", None)
    return report


@router.get("/rag/pending")
def rag_pending(limit: int = 50, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    """Versões de documento com embeddings pendentes (fila do worker). Somente leitura."""
    vids = doc_worker.pending_versions(db, limit=max(1, min(limit, 500)))
    return {"pendentes": len(vids), "version_ids": vids}


@router.post("/rag/reprocess")
def rag_reprocess(background: BackgroundTasks, limit: int = 10, _role: str = Depends(require_permission(PERM_ANALYSIS_WRITE))):
    """Dispara (assíncrono) uma varredura de reprocessamento de embeddings pendentes.

    Idempotente (só toca chunks sem vetor). Sem provider/chave, não chama OpenAI —
    apenas mantém o estado AGUARDANDO_EMBEDDING. Retorna imediatamente (BackgroundTask)."""
    background.add_task(_run_reprocess_scan, max(1, min(limit, 100)))
    return {"status": "agendado", "limit": max(1, min(limit, 100))}
