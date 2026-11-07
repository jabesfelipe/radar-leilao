"""Dependências/helpers compartilhados pelos routers (M0 — modularização).

Centraliza utilitários usados por várias rotas (ex.: ``property_or_404``) para que
os routers não precisem importar de ``main.py`` (evita import circular). ``main.py``
também passa a reusar daqui, mantendo uma única fonte de verdade.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models


def property_or_404(db: Session, property_id: int) -> models.Property:
    prop = db.get(models.Property, property_id)
    if not prop:
        raise HTTPException(404, "Imóvel não encontrado")
    return prop
