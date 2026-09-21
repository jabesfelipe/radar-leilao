from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


RISK_SEVERITIES = ("BAIXA", "MEDIA", "ALTA", "CRITICA")


@dataclass(frozen=True)
class RiskCandidate:
    risk_key: str
    domain: str
    title: str
    description: str
    severity: str
    status: str
    impact: str
    confidence: str
    origin: str
    evidence_ids: list[int]
    checklist_result_ids: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _evidence_ids(result: Any, property_id: int) -> list[int]:
    values: list[int] = []
    for evidence in _value(result, "evidences", []) or []:
        if _value(evidence, "property_id") in (None, property_id) and _value(evidence, "id") is not None:
            values.append(int(_value(evidence, "id")))
    for link in _value(result, "evidence_links", []) or []:
        evidence_id = _value(link, "evidence_id")
        if evidence_id is not None:
            values.append(int(evidence_id))
    return list(dict.fromkeys(values))


class RiskEngine:
    """Motor de riscos puro: avalia apenas dados já calculados/cadastrados."""

    def evaluate(
        self,
        property_id: int,
        checklist_results: Iterable[Any] = (),
    ) -> list[RiskCandidate]:
        risks: list[RiskCandidate] = []
        for result in checklist_results:
            state = _value(result, "state")
            if state not in {"RISCO_IDENTIFICADO", "ATENCAO"}:
                continue
            evidence_ids = _evidence_ids(result, property_id)
            if not evidence_ids:
                continue
            item = _value(result, "item")
            key = _value(item, "canonical_key", f"CHECKLIST_RESULT_{_value(result, 'id', 'UNKNOWN')}")
            category = str(_value(item, "category", "DOCUMENTAL")).lower()
            question = _value(item, "question", key)
            severity = "ALTA" if state == "RISCO_IDENTIFICADO" else "MEDIA"
            risks.append(RiskCandidate(
                risk_key=f"CHECKLIST_{key}_{state}",
                domain=category,
                title=f"Checklist: {key}",
                description=f"{question}. Estado determinístico: {state}.",
                severity=severity,
                status="ATIVO",
                impact="Requer análise do domínio relacionado.",
                confidence=_value(result, "confidence", "MEDIA"),
                origin="RiskEngine:ChecklistResult",
                evidence_ids=evidence_ids,
                checklist_result_ids=[int(_value(result, "id"))] if _value(result, "id") is not None else [],
            ))

        return risks
