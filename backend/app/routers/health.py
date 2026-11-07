"""Router de health-check (M0). Contrato idêntico ao antigo `@app.get("/health")`."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "servico": "Radar Leilão API", "persistencia": "PostgreSQL + pgvector", "migrations": "Alembic"}
