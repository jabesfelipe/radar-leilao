from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


KNOWLEDGE_CASE_KINDS = ("CASE_ANALYSIS", "CASE_OUTCOME", "RULE_LEARNING")


class KnowledgeMemoryService:
    """Persistência estruturada de casos, sem embeddings ou recuperação semântica."""

    def __init__(self, db: Session):
        self.db = db

    def add_case(
        self,
        kind: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> models.KnowledgeItem:
        normalized_kind = str(kind or "").strip()
        normalized_title = str(title or "").strip()
        normalized_content = str(content or "").strip()
        if normalized_kind not in KNOWLEDGE_CASE_KINDS:
            raise ValueError(f"Tipo de memória inválido: {normalized_kind}")
        if not normalized_title:
            raise ValueError("Título do caso é obrigatório")
        if len(normalized_title) > 240:
            raise ValueError("Título do caso excede 240 caracteres")
        if not normalized_content:
            raise ValueError("Conteúdo do caso é obrigatório")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("Metadata deve ser um objeto JSON")
        item = models.KnowledgeItem(
            kind=normalized_kind,
            title=normalized_title,
            content=normalized_content,
            metadata_json=dict(metadata or {}),
            embedding=None,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_case(self, case_id: int) -> models.KnowledgeItem | None:
        return self.db.get(models.KnowledgeItem, case_id)

    def list_cases(self, kind: str | None = None) -> list[models.KnowledgeItem]:
        statement = select(models.KnowledgeItem).order_by(models.KnowledgeItem.created_at.desc(), models.KnowledgeItem.id.desc())
        if kind is not None:
            normalized_kind = str(kind).strip()
            if normalized_kind not in KNOWLEDGE_CASE_KINDS:
                raise ValueError(f"Tipo de memória inválido: {normalized_kind}")
            statement = statement.where(models.KnowledgeItem.kind == normalized_kind)
        return list(self.db.scalars(statement).all())
