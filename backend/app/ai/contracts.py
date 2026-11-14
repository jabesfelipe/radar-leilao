import unicodedata
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


def _plain(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).strip().lower()


def _normalize_source(value: Any) -> str | None:
    """Function calling não é estrito: o modelo devolveu source='mercado_deterministico' (1ª execução real v1.0.4) e o
    Literal derrubava a resposta inteira do agente. A origem declarada é só uma pista: o servidor confere a citação."""
    if value is None or str(value).strip() == "":
        return None
    text = _plain(value)
    if any(t in text for t in ("calcul", "determin", "financeiro", "mercado", "motor")):
        return "calculo"
    if any(t in text for t in ("cadastr", "imovel", "snapshot")):
        return "cadastro"
    if any(t in text for t in ("document", "contexto", "rag", "matricula", "edital")):
        return "documento"
    return "inferencia"

FindingKind = Literal["fato", "interpretacao", "hipotese", "ausencia"]
# De onde vem a informação (v1.0.4). "documento" exige chunk_ids + evidence_excerpt LITERAL; os demais nunca
# viram citação de documento (o servidor confere: ver app/citations.py e services.persist_agent_findings).
FindingSource = Literal["documento", "cadastro", "calculo", "inferencia"]

class Finding(BaseModel):
    kind: FindingKind
    source: FindingSource | None = None
    statement: str = Field(min_length=1)
    confidence: Literal["ALTA", "MEDIA", "BAIXA"] = "MEDIA"
    chunk_ids: list[int] = Field(default_factory=list)
    page: int | None = None
    section: str | None = None
    evidence_excerpt: str | None = None
    checklist_key: str | None = None
    checklist_state: str | None = None
    risk: str | None = None

    @field_validator("source", mode="before")
    @classmethod
    def _source(cls, value: Any) -> Any:
        return _normalize_source(value)

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: Any) -> Any:
        text = _plain(value)
        aliases = {"fact": "fato", "interpretation": "interpretacao", "hypothesis": "hipotese", "absence": "ausencia"}
        return aliases.get(text, text) if text else value

    @field_validator("confidence", mode="before")
    @classmethod
    def _confidence(cls, value: Any) -> Any:
        if value is None:
            return "MEDIA"
        text = _plain(value).upper()
        return {"HIGH": "ALTA", "MEDIUM": "MEDIA", "LOW": "BAIXA"}.get(text, text)

    @field_validator("chunk_ids", mode="before")
    @classmethod
    def _chunk_ids(cls, value: Any) -> Any:
        # Valores não numéricos são descartados (citação inválida), sem derrubar a resposta inteira.
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        return [int(v) for v in value if str(v).strip().isdigit()]

    @field_validator("page", mode="before")
    @classmethod
    def _page(cls, value: Any) -> Any:
        return int(value) if value is not None and str(value).strip().isdigit() else None

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
