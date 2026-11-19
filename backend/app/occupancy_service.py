"""Ocupação do imóvel (v1.0.12, Fase D).

- Status do registro de ocupação (``OccupancyAnalysis.status``): os antigos (OCUPADO, DESOCUPADO, DESCONHECIDO) continuam
  válidos; entram OCUPADO_CONFIRMADO, OCUPADO_TERCEIROS e NAO_VERIFICADO.
- Verificação (fonte, data, observação, responsável) fica numa ``Evidence`` vinculada ao registro: nenhuma coluna nova.
- "Possíveis ocupantes": pessoas físicas citadas nos documentos do imóvel (hoje, a matrícula), com o papel declarado, o ato e o
  trecho original. É sugestão: nunca afirma ocupação e não alimenta checklist nem financeiro.
"""
from __future__ import annotations

import re
from typing import Any

from . import models

OCUPADO, OCUPADO_CONFIRMADO, OCUPADO_TERCEIROS, DESOCUPADO, NAO_VERIFICADO, DESCONHECIDO = (
    "OCUPADO", "OCUPADO_CONFIRMADO", "OCUPADO_TERCEIROS", "DESOCUPADO", "NAO_VERIFICADO", "DESCONHECIDO")
STATUS_LABELS = {OCUPADO: "Ocupado", OCUPADO_CONFIRMADO: "Ocupação confirmada", OCUPADO_TERCEIROS: "Ocupado por terceiros",
                 DESOCUPADO: "Desocupado", NAO_VERIFICADO: "Não verificado", DESCONHECIDO: "Desconhecido"}
OCCUPIED_STATUSES = frozenset({OCUPADO, OCUPADO_CONFIRMADO, OCUPADO_TERCEIROS})
VACANT_STATUSES = frozenset({DESOCUPADO, "LIVRE"})
AVISO_POSSIVEIS_OCUPANTES = ("Estas pessoas foram identificadas nos documentos do imóvel. Esta informação é apenas uma sugestão e não "
                             "confirma ocupação atual.")
_VERIFY_PREFIX = "Verificação de ocupação"


def verification_evidence(db, prop: models.Property, status: str, verification) -> models.Evidence:
    """Evidence (origem CADASTRO) com a verificação informada pelo usuário."""
    from .privacy import redact_pii
    parts = [f"{_VERIFY_PREFIX}: {STATUS_LABELS.get(status, status)}", f"fonte: {verification.fonte.strip()}"]
    if verification.data:
        parts.append(f"data: {verification.data.strftime('%d/%m/%Y')}")
    if verification.responsavel:
        parts.append(f"responsável: {verification.responsavel.strip()}")
    fact = "; ".join(parts) + "."
    evidence = models.Evidence(property_id=prop.id, category="DESOCUPACAO", fact=fact,
                               interpretation=redact_pii(verification.observacao.strip(), force=True) if verification.observacao else None,
                               confidence="MEDIA", origin="CADASTRO", agent="cadastro_ocupacao")
    db.add(evidence)
    db.flush()
    return evidence


def verification_of(db, occupancy: models.OccupancyAnalysis) -> dict[str, Any] | None:
    """Verificação registrada (lida da Evidence vinculada), ou None."""
    if occupancy.evidence_id is None:
        return None
    evidence = db.get(models.Evidence, occupancy.evidence_id)
    if evidence is None or not str(evidence.fact or "").startswith(_VERIFY_PREFIX):
        return {"evidence_id": occupancy.evidence_id, "fonte": None, "data": None, "responsavel": None, "observacao": None} if evidence else None
    fields = dict(re.findall(r"(fonte|data|responsável): ([^;]+?)(?=;|\.$)", evidence.fact))
    return {"evidence_id": evidence.id, "fonte": fields.get("fonte"), "data": fields.get("data"), "responsavel": fields.get("responsável"),
            "observacao": evidence.interpretation}


def possible_occupants(db, property_id: int) -> dict[str, Any]:
    """Pessoas físicas citadas na matrícula, agrupadas por nome, com papel, ato, data e trecho. Não confirma ocupação."""
    from .registry_chain import fold
    from .registry_timeline import timeline_for_property
    timeline = timeline_for_property(db, property_id)
    people: dict[str, dict[str, Any]] = {}
    for event in timeline.get("eventos", []):
        for party in event.get("partes", []):
            if party.get("tipo_pessoa") != "FISICA":
                continue
            key = " ".join(fold(party["nome"]).split())
            entry = people.setdefault(key, {"nome": party["nome"], "papeis": [], "origens": []})
            if party["papel_descricao"] not in entry["papeis"]:
                entry["papeis"].append(party["papel_descricao"])
            entry["origens"].append({"documento": (event.get("documento") or {}).get("nome"), "document_version_id": (event.get("documento") or {}).get("document_version_id"),
                                     "ato": event["ato"], "tipo_ato": event["tipo_descricao"], "data": event.get("data"), "papel": party["papel_descricao"],
                                     "como_identificado": party["como_identificado"], "trecho": event["trecho"], "chunk_id": event.get("chunk_id")})
    occupancy = db.query(models.OccupancyAnalysis).filter(models.OccupancyAnalysis.property_id == property_id).order_by(models.OccupancyAnalysis.id.desc()).first()
    return {"property_id": property_id, "aviso": AVISO_POSSIVEIS_OCUPANTES, "possiveis_ocupantes": list(people.values()),
            "fonte": "matrícula anexada" if timeline.get("disponivel") else None,
            "motivo": None if timeline.get("disponivel") else timeline.get("motivo"),
            "situacao_registrada": {"status": occupancy.status, "status_label": STATUS_LABELS.get(str(occupancy.status or "").upper(), occupancy.status)}
            if occupancy is not None else None,
            "observacao": "O checklist (itens 11 e 27) e o financeiro usam só o registro de ocupação confirmado pelo usuário."}
