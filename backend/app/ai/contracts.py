from typing import Literal
from pydantic import BaseModel, Field

FindingKind = Literal["fato", "interpretacao", "hipotese", "ausencia"]

class Finding(BaseModel):
    kind: FindingKind
    statement: str = Field(min_length=1)
    confidence: Literal["ALTA", "MEDIA", "BAIXA"] = "MEDIA"
    chunk_ids: list[int] = Field(default_factory=list)
    page: int | None = None
    section: str | None = None
    evidence_excerpt: str | None = None
    checklist_key: str | None = None
    checklist_state: str | None = None
    risk: str | None = None

class AgentResponse(BaseModel):
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)

class VerdictResponse(BaseModel):
    summary: str = ""
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)
    risk_candidates: list[str] = Field(default_factory=list)
