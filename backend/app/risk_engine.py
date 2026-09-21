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
        finance: dict[str, Any] | None = None,
        documents_present: bool = True,
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

        finance = finance or {}
        market_value = finance.get("valor_mercado")
        total_cost = finance.get("custo_total")
        if market_value is not None and total_cost is not None and total_cost > market_value:
            risks.append(RiskCandidate(
                risk_key="FINANCEIRO_CUSTO_ACIMA_MERCADO",
                domain="financeiro",
                title="Custo total acima do valor de mercado",
                description="O custo total determinístico supera o valor de mercado informado.",
                severity="ALTA",
                status="ATIVO",
                impact="A aquisição exige atenção financeira.",
                confidence="ALTA",
                origin="RiskEngine:FinanceEngine",
                evidence_ids=[int(value) for value in finance.get("evidence_ids", [])],
                checklist_result_ids=[],
            ))
        if not documents_present:
            risks.append(RiskCandidate(
                risk_key="DOCUMENTAL_SEM_DOCUMENTOS",
                domain="documental",
                title="Nenhum documento anexado",
                description="O dossiê do imóvel não possui documentos anexados.",
                severity="ALTA",
                status="ATIVO",
                impact="A análise documental permanece não comprovada.",
                confidence="ALTA",
                origin="RiskEngine:Documentos",
                evidence_ids=[],
                checklist_result_ids=[],
            ))
        return risks
