"""Monta o ``NameAliaser`` de UM imóvel a partir dos dados estruturados já cadastrados.

Fontes (somente do próprio ``property_id`` — nunca de outro imóvel):
- titular da matrícula (``PropertyRegistration.holder``);
- polos ativo/passivo dos processos (pessoa física; empresas e entes públicos ficam identificados);
- ocupantes/contatos (``OccupantContact.name``).

Sem esses cadastros o aliaser ainda aprende nomes que aparecem após rótulos jurídicos no próprio
texto enviado (``NameAliaser.learn_from_text``). Ver as limitações em ``privacy.py``.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .privacy import NameAliaser, pii_enabled


def aliaser_for_property(db: Session, property_id: int) -> NameAliaser:
    aliaser = NameAliaser(enabled=pii_enabled())
    if not aliaser.enabled or not hasattr(db, "scalars"):   # sem sessão real (testes com dublês): só o aprendizado por rótulo
        return aliaser
    holders = db.scalars(select(models.PropertyRegistration.holder).where(models.PropertyRegistration.property_id == property_id)).all()
    for holder in holders:
        aliaser.alias_for(holder, "TITULAR")
    processes = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == property_id)).all()
    for process in processes:
        aliaser.alias_for(process.polo_active, "PARTE ATIVA")
        aliaser.alias_for(process.polo_passive, "PARTE PASSIVA")
    for contact in db.scalars(select(models.OccupantContact).where(models.OccupantContact.property_id == property_id)).all():
        aliaser.alias_for(contact.name, "OCUPANTE")
    return aliaser
