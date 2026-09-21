from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AnalysisComparison:
    property_id: int
    from_version: int
    to_version: int
    changed_domains: list[str]
    added_evidence_ids: list[int]
    removed_evidence_ids: list[int]
    added_risk_ids: list[int]
    removed_risk_ids: list[int]
    previous_verdict: str | None
    current_verdict: str | None
    previous_pending_items: list[str]
    current_pending_items: list[str]
    changes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _stable_unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _ids(values: Iterable[Any]) -> set[int]:
    result: set[int] = set()
    for value in values or []:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _canonical_changes(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    try:
        return json.loads(stripped)
    except (TypeError, ValueError, json.JSONDecodeError):
        return stripped


def _verdict_overall(verdict: Any) -> str | None:
    value = _value(verdict, "overall") if verdict is not None else None
    return str(value) if value is not None else None


def _pending(verdict: Any) -> list[str]:
    values = _value(verdict, "pending_items", []) if verdict is not None else []
    return _stable_unique(str(value) for value in (values or []) if value is not None)


class AnalysisComparisonService:
    """Compara snapshots persistidos sem consultar fontes externas ou reinterpretar textos."""

    def compare(
        self,
        previous_analysis: Any,
        current_analysis: Any,
        previous_verdict: Any = None,
        current_verdict: Any = None,
        previous_risks: Iterable[Any] = (),
        current_risks: Iterable[Any] = (),
    ) -> AnalysisComparison:
        previous_property = _value(previous_analysis, "property_id")
        current_property = _value(current_analysis, "property_id")
        if previous_property != current_property:
            raise ValueError("As análises devem pertencer ao mesmo imóvel")
        from_version = int(_value(previous_analysis, "version"))
        to_version = int(_value(current_analysis, "version"))
        if from_version == to_version:
            raise ValueError("As análises devem possuir versões diferentes")

        previous_domains = list(_value(previous_analysis, "affected_domains", []) or [])
        current_domains = list(_value(current_analysis, "affected_domains", []) or [])
        previous_evidence = _ids(_value(previous_analysis, "evidence_ids", []) or [])
        current_evidence = _ids(_value(current_analysis, "evidence_ids", []) or [])
        previous_risk_ids = _ids(_value(risk, "id") for risk in (previous_risks or []) if _value(risk, "id") is not None)
        current_risk_ids = _ids(_value(risk, "id") for risk in (current_risks or []) if _value(risk, "id") is not None)
        previous_changes = _canonical_changes(_value(previous_analysis, "changes", ""))
        current_changes = _canonical_changes(_value(current_analysis, "changes", ""))
        return AnalysisComparison(
            property_id=int(current_property),
            from_version=from_version,
            to_version=to_version,
            changed_domains=_stable_unique(previous_domains + current_domains),
            added_evidence_ids=sorted(current_evidence - previous_evidence),
            removed_evidence_ids=sorted(previous_evidence - current_evidence),
            added_risk_ids=sorted(current_risk_ids - previous_risk_ids),
            removed_risk_ids=sorted(previous_risk_ids - current_risk_ids),
            previous_verdict=_verdict_overall(previous_verdict),
            current_verdict=_verdict_overall(current_verdict),
            previous_pending_items=_pending(previous_verdict),
            current_pending_items=_pending(current_verdict),
            changes={"before": previous_changes, "after": current_changes, "changed": previous_changes != current_changes},
        )
