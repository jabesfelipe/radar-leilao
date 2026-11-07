"""Router de Mercado (M0 — modularização).

Leitura determinística do comparativo de mercado do imóvel a partir dos
comparáveis cadastrados. Não dispara análise nem LLM. Contrato idêntico ao que
vivia em ``main.py``.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..market import calculate_market
from .deps import property_or_404

router = APIRouter()


@router.get("/api/imoveis/{property_id}/mercado")
def get_market(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    comparables = [{"kind": comparable.kind, "price": comparable.price, "rent": comparable.rent, "area_m2": comparable.area_m2} for comparable in prop.comparables]
    return {"property_id": property_id, "mercado": calculate_market(comparables)}
