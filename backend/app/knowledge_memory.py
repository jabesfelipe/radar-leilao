from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
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

    def search_cases(
        self,
        query: str | None = None,
        kind: str | None = None,
        property_type: str | None = None,
        city: str | None = None,
        state: str | None = None,
        auction_stage: str | None = None,
        verdict: str | None = None,
        limit: int = 20,
    ) -> list[models.KnowledgeItem]:
        if limit < 1:
            raise ValueError("Limit deve ser maior que zero")
        if limit > 100:
            raise ValueError("Limit máximo é 100")
        filters = {"property_type": property_type, "city": city, "state": state, "auction_stage": auction_stage, "verdict": verdict}
        statement = select(models.KnowledgeItem)
        if kind is not None:
            normalized_kind = str(kind).strip()
            if normalized_kind not in KNOWLEDGE_CASE_KINDS:
                raise ValueError(f"Tipo de memória inválido: {normalized_kind}")
            statement = statement.where(models.KnowledgeItem.kind == normalized_kind)
        for key, value in filters.items():
            if value is not None:
                statement = statement.where(models.KnowledgeItem.metadata_json[key].as_string() == str(value))
        normalized_query = str(query or "").strip()
        if normalized_query:
            text_vector = func.to_tsvector("portuguese", models.KnowledgeItem.title + " " + models.KnowledgeItem.content)
            text_query = func.plainto_tsquery("portuguese", normalized_query)
            statement = statement.where(text_vector.op("@@")(text_query))
        statement = statement.order_by(models.KnowledgeItem.created_at.desc(), models.KnowledgeItem.id.desc()).limit(limit)
        return list(self.db.scalars(statement).all())
