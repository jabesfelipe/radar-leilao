from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


_MISSING = object()
_REQUIRED_FIELDS = ("agent", "facts", "evidence_ids", "pending", "llm_used")
_FINDING_KINDS = {"fato", "interpretacao", "hipotese", "ausencia"}
_CONFIDENCES = {"ALTA", "MEDIA", "BAIXA"}


@dataclass(frozen=True)
class EvalResult:
    passed: bool
    checks: dict[str, bool]
    failures: list[str] = field(default_factory=list)


class AgentEvalService:
    """Avalia estrutura e rastreabilidade de resultados já produzidos por Agents."""

    def evaluate(
        self,
        result: Any,
        *,
        expected_agent: str | None = None,
        expected_status: str | None = None,
        evidence_required: bool = False,
    ) -> EvalResult:
        checks: dict[str, bool] = {}
        failures: list[str] = []

        agent = self._value(result, "agent")
        facts = self._value(result, "facts")
        evidence_ids = self._value(result, "evidence_ids")
        pending = self._value(result, "pending")
        llm_used = self._value(result, "llm_used")
        llm_call = self._value(result, "llm_call", None)

        checks["agent_present"] = isinstance(agent, str) and bool(agent.strip())
        if expected_agent is not None:
            checks["agent_expected"] = checks["agent_present"] and agent == expected_agent
        else:
            checks["agent_expected"] = True

        checks["structure_valid"] = self._valid_structure(facts, evidence_ids, pending, llm_used)
        checks["evidence_traceable"] = self._valid_ids(evidence_ids) and (
            not evidence_required or bool(evidence_ids)
        )
        checks["findings_traceable"] = self._valid_findings(facts)
        checks["status_expected"] = self._status_matches(llm_call, result, expected_status)
        checks["no_unexpected_error"] = self._no_unexpected_error(result, llm_call)

        messages = {
            "agent_present": "agent ausente ou vazio",
            "agent_expected": "agent diferente do esperado",
            "structure_valid": "estrutura obrigatória do resultado é inválida",
            "evidence_traceable": "evidências ausentes ou IDs de evidência inválidos",
            "findings_traceable": "finding sem estrutura ou rastreabilidade válida",
            "status_expected": "status do resultado diferente do esperado",
            "no_unexpected_error": "resultado contém erro inesperado",
        }
        for name, passed in checks.items():
            if not passed:
                failures.append(f"{name}: {messages[name]}")
        return EvalResult(passed=all(checks.values()), checks=checks, failures=failures)

    def evaluate_many(
        self,
        results: Iterable[Any],
        *,
        expected_agents: Iterable[str] | None = None,
        evidence_required: bool = False,
    ) -> EvalResult:
        expected = list(expected_agents or [])
        evaluations = [
            self.evaluate(
                result,
                expected_agent=expected[index] if index < len(expected) else None,
                evidence_required=evidence_required,
            )
            for index, result in enumerate(results)
        ]
        checks = {f"result_{index}": evaluation.passed for index, evaluation in enumerate(evaluations)}
        failures = [
            f"result_{index}: {failure}"
            for index, evaluation in enumerate(evaluations)
            for failure in evaluation.failures
        ]
        return EvalResult(passed=all(checks.values()) if checks else True, checks=checks, failures=failures)

    @staticmethod
    def _value(result: Any, name: str, default: Any = _MISSING) -> Any:
        if isinstance(result, Mapping):
            if name in result:
                return result[name]
        else:
            value = getattr(result, name, _MISSING)
            if value is not _MISSING:
                return value
        return default

    @classmethod
    def _valid_structure(cls, facts: Any, evidence_ids: Any, pending: Any, llm_used: Any) -> bool:
        return (
            isinstance(facts, list)
            and isinstance(evidence_ids, list)
            and isinstance(pending, list)
            and isinstance(llm_used, bool)
        )

    @staticmethod
    def _valid_ids(values: Any) -> bool:
        return isinstance(values, list) and all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in values)

    @classmethod
    def _valid_findings(cls, facts: Any) -> bool:
        if not isinstance(facts, list):
            return False
        for finding in facts:
            if not isinstance(finding, Mapping):
                return False
            if not isinstance(finding.get("statement"), str) or not finding["statement"].strip():
                return False
            if finding.get("kind") not in _FINDING_KINDS:
                return False
            if finding.get("confidence", "MEDIA") not in _CONFIDENCES:
                return False
            if not cls._valid_ids(finding.get("chunk_ids", [])):
                return False
        return True

    @classmethod
    def _status_matches(cls, llm_call: Any, result: Any, expected_status: str | None) -> bool:
        if expected_status is None:
            return True
        status = cls._value(llm_call, "status") if llm_call is not None else cls._value(result, "status")
        return status == expected_status

    @classmethod
    def _no_unexpected_error(cls, result: Any, llm_call: Any) -> bool:
        if cls._value(result, "error", None):
            return False
        if cls._value(result, "exception", None):
            return False
        status = cls._value(llm_call, "status") if llm_call is not None else cls._value(result, "status")
        return status != "ERRO"
