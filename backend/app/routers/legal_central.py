"""Router da Central Jurídica (M0 — modularização).

Biblioteca jurídica curada + referências legais EM CONTEXTO (checklist/etapa/imóvel).
Leitura determinística (sem LLM); o seed do catálogo é idempotente. Contrato idêntico
ao que vivia em ``main.py``.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import legal_service
from ..database import get_db
from ..services import serialize
from .deps import property_or_404

router = APIRouter()


@router.get("/api/juridico/biblioteca")
def legal_library(db: Session = Depends(get_db)):
    """Visão agregada da biblioteca jurídica: fontes, dispositivos, regras e a
    cobertura dos itens do Checklist Mestre com base legal. Materializa o catálogo
    curado de forma idempotente na primeira leitura (sem embeddings aqui — a
    indexação semântica roda sob demanda/offline)."""
    created = legal_service.seed_legal_catalog(db, embed=False)
    if any(created.values()):
        db.commit()
    return serialize(legal_service.library_overview(db))


@router.get("/api/juridico/biblioteca/busca")
def legal_library_search(q: str = "", contexto: str | None = None, limite: int = 20, db: Session = Depends(get_db)):
    """Busca na biblioteca jurídica (vetorial quando há embeddings/API key; caso
    contrário, busca textual determinística). ``contexto`` filtra por etapa."""
    legal_service.seed_legal_catalog(db, embed=False); db.commit()
    return serialize(legal_service.search_library(db, q, limit=limite, context=contexto))


@router.get("/api/juridico/referencias/checklist/{canonical_key}")
def legal_refs_for_checklist(canonical_key: str, db: Session = Depends(get_db)):
    """Regras + base legal aplicáveis a UM item do checklist (por canonical_key).
    É o que a UI usa para mostrar "Base legal e orientações" ao lado do item."""
    legal_service.seed_legal_catalog(db, embed=False); db.commit()
    return serialize(legal_service.references_for_checklist_key(db, canonical_key))


@router.get("/api/juridico/referencias/contexto/{contexto}")
def legal_refs_for_context(contexto: str, db: Session = Depends(get_db)):
    """Regras aplicáveis a uma etapa/contexto transversal (ex.: DESOCUPACAO, LEILAO)."""
    legal_service.seed_legal_catalog(db, embed=False); db.commit()
    return serialize(legal_service.references_for_context(db, contexto))


@router.get("/api/imoveis/{property_id}/juridico/central")
def property_legal_central(property_id: int, db: Session = Depends(get_db)):
    """Visão jurídica do imóvel enriquecida com a base legal contextual: síntese
    jurídica (reuso de juridical_overview) + referências legais por item do
    checklist com base associada. Não dispara análise nem LLM."""
    prop = property_or_404(db, property_id)
    legal_service.seed_legal_catalog(db, embed=False); db.commit()
    return serialize(legal_service.property_legal_overview(db, prop))
