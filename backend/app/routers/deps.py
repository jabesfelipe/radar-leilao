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


def ensure_evidence_of_property(db: Session, property_id: int, evidence_id: int | None) -> None:
    """Evidência citada num cadastro (dívida, processo, matrícula...) tem de ser do MESMO imóvel.

    Sem esta checagem, um registro do imóvel A podia apontar evidência (e o trecho do documento) do imóvel B
    (sonda de isolamento da homologação v1.0.4). ``None`` = sem evidência, permitido."""
    if evidence_id is None:
        return
    evidence = db.get(models.Evidence, evidence_id)
    if evidence is None or evidence.property_id != property_id:
        raise HTTPException(422, "Evidência não encontrada para este imóvel")
