from __future__ import annotations

from typing import Any
from . import models
from .services import record_event, record_history


def normalize_documentary_evidence(
    db,
    property_id: int,
    document_version_id: int,
    category: str,
    fact: str,
    confidence: str = "MEDIA",
    chunk_id: int | None = None,
    page: int | None = None,
    section: str | None = None,
    source_excerpt: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    relation: str = "SUSTENTA",
) -> models.Evidence:
    """Cria uma Evidence documental normalizada sem interpretar seu conteúdo."""
    prop = db.get(models.Property, property_id)
    version = db.get(models.DocumentVersion, document_version_id)
    if not prop: raise ValueError("Imóvel não encontrado")
    if not version or not version.document or version.document.property_id != property_id:
        raise ValueError("DocumentVersion não pertence ao imóvel")
    chunk = None
    if chunk_id is not None:
        chunk = db.get(models.DocumentChunk, chunk_id)
        if not chunk or chunk.document_version_id != document_version_id or (chunk.document_version is not None and (chunk.document_version.document_id != version.document_id or (chunk.document_version.document is not None and chunk.document_version.document.property_id != property_id))):
            raise ValueError("DocumentChunk não pertence à DocumentVersion")
    if not fact or not str(fact).strip():
        raise ValueError("Fato da evidência é obrigatório")
    evidence = models.Evidence(property_id=property_id, document_version_id=document_version_id, chunk_id=chunk.id if chunk else None, category=category, fact=fact, confidence=confidence, page=page if page is not None else (chunk.page if chunk else None), section=section if section is not None else (chunk.section if chunk else None), source_excerpt=source_excerpt if source_excerpt is not None else (chunk.content[:1000] if chunk else None))
    db.add(evidence); db.flush()
    if target_type is not None and target_id is not None:
        db.add(models.EvidenceLink(evidence_id=evidence.id, target_type=target_type, target_id=target_id, relation=relation))
    payload: dict[str, Any] = {"evidence_id": evidence.id, "document_version_id": document_version_id, "chunk_id": evidence.chunk_id, "category": category, "target_type": target_type, "target_id": target_id}
    event = record_event(db, prop, "EVIDENCIA_DOCUMENTAL_NORMALIZADA", "Evidence", evidence.id, payload, ["documental", "juridico", "checklist"])
    record_history(db, prop, "Evidence", evidence.id, "CREATE", None, payload, event.id, evidence.id)
    return evidence
