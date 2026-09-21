from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ConsolidatedAgentResults:
    property_id: int | None
    analysis_id: int | None
    domains: list[str]
    agents_executed: list[str]
    agent_results: list[dict[str, Any]]
    evidence_ids: list[int]
    retrieved_chunk_ids: list[int]
    interpretations: list[str]
    pending: list[str]
    errors: list[str]
    llm_used: bool
    model: str | None
    llm_runs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        try:
            marker = value if isinstance(value, (str, int, float, bool, type(None))) else repr(value)
            if marker in seen:
                continue
            seen.add(marker)
        except TypeError:
            pass
        result.append(value)
    return result


def consolidate_agent_results(
    *,
    property_id: int | None = None,
    analysis_id: int | None = None,
    domains: list[str] | None = None,
    agent_results: list[dict[str, Any]] | None = None,
    evidence_ids: list[int] | None = None,
    retrieved_chunk_ids: list[int] | None = None,
    interpretations: list[str] | None = None,
    pending: list[str] | None = None,
    errors: list[str] | None = None,
    llm_used: bool = False,
    model: str | None = None,
    llm_runs: list[dict[str, Any]] | None = None,
) -> ConsolidatedAgentResults:
    """Consolida resultados já produzidos sem interpretar ou executar qualquer componente."""
    results = deepcopy(agent_results or [])
    agents_executed = _stable_unique(
        result.get("agent") for result in results if result.get("agent")
    )
    return ConsolidatedAgentResults(
        property_id=property_id,
        analysis_id=analysis_id,
        domains=_stable_unique(domains or []),
        agents_executed=agents_executed,
        agent_results=results,
        evidence_ids=_stable_unique(evidence_ids or []),
        retrieved_chunk_ids=_stable_unique(retrieved_chunk_ids or []),
        interpretations=_stable_unique(interpretations or []),
        pending=_stable_unique(pending or []),
        errors=_stable_unique(errors or []),
        llm_used=bool(llm_used),
        model=model,
        llm_runs=deepcopy(llm_runs or []),
    )
