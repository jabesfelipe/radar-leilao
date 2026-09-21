from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable
import unicodedata


VERDICT_STATES = ("FAVORAVEL", "ATENCAO", "DESFAVORAVEL", "INCONCLUSIVO")


@dataclass(frozen=True)
class VerdictDecision:
    property_id: int
    analysis_version: int
    overall: str
    summary: str
    what_is_known: str
    what_is_unknown: str
    pending_items: list[str]
    financial: dict[str, Any]
    risk_ids: list[int]
    evidence_ids: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().upper()


class VerdictEngine:
    """Motor puro que decide o estado a partir de resultados já persistidos."""

    def evaluate(
        self,
        property_id: int,
        analysis_version: int,
        risks: Iterable[Any] = (),
        checklist_results: Iterable[Any] = (),
        pending_items: Iterable[str] = (),
        evidence_ids: Iterable[int] = (),
        financial: dict[str, Any] | None = None,
    ) -> VerdictDecision:
        current_risks = [risk for risk in risks if _normalize(_value(risk, "status", "ATIVO")) not in {"INATIVO", "SUPERADO"}]
        risk_ids = _unique(_value(risk, "id") for risk in current_risks if _value(risk, "id") is not None)
        risk_evidence_ids = [
            _value(risk, "evidence_id")
            for risk in current_risks
            if _value(risk, "evidence_id") is not None
        ]
        checklist_pending = [
            _value(_value(result, "item"), "question")
            for result in checklist_results
            if _value(result, "applicable", True) and _normalize(_value(result, "state")) in {"PENDENTE", "EM_ANALISE"} and _value(result, "item") is not None
        ]
        finance = dict(financial or {})
        pending = _unique([item for item in list(checklist_pending) + list(pending_items) + list(finance.get("pendencias", []) or []) if item])
        all_evidence_ids = _unique(list(evidence_ids) + risk_evidence_ids)
        severities = {_normalize(_value(risk, "severity")) for risk in current_risks}
        if "CRITICA" in severities:
            overall = "DESFAVORAVEL"
        elif severities:
            overall = "ATENCAO"
        elif pending:
            overall = "INCONCLUSIVO"
        elif not all_evidence_ids:
            overall = "INCONCLUSIVO"
        else:
            overall = "FAVORAVEL"
        known = "Evidências e resultados determinísticos registrados na análise." if all_evidence_ids else "Nenhuma evidência suficiente foi registrada na análise."
        unknown = "; ".join(pending) if pending else ""
        summary = f"Veredito determinístico da Analysis V{analysis_version}: {overall}."
        if pending:
            summary += f" {len(pending)} pendência(s) registrada(s)."
        if current_risks:
            summary += f" {len(current_risks)} risco(s) ativo(s) considerado(s)."
        return VerdictDecision(
            property_id=property_id,
            analysis_version=analysis_version,
            overall=overall,
            summary=summary,
            what_is_known=known,
            what_is_unknown=unknown,
            pending_items=pending,
            financial=finance,
            risk_ids=[int(value) for value in risk_ids],
            evidence_ids=[int(value) for value in all_evidence_ids],
        )
