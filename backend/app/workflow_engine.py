"""Workflow Engine — máquina de estados F0–F13 (Ciclo 2 — Onda 1, fundação B1).

Motor **determinístico e puro**: sem DB, sem I/O externo, sem LLM. No espírito de
``risk_engine.py``/``verdict_engine.py``. Recebe um ``OpportunityContext`` já
montado (agregação dos domínios é responsabilidade de um serviço de leitura, fora
desta onda) e retorna decisões/avaliações imutáveis.

Funções públicas (SPEC-WORKFLOW-ENGINE §11):
  - ``compute_hard_stops(ctx)`` -> lista de hard stops ATIVOS (estado CONFIRMADO).
  - ``evaluate_phase(ctx)`` -> ``PhaseEvaluation`` (estado da fase, gate, hard
    stops, próxima ação recomendada).
  - ``can_transition(ctx, target_phase, transition_type=...)`` -> ``TransitionDecision``
    (permite/bloqueia + motivo estruturado).

Invariante inegociável (ADR-004): nenhuma transição de AVANÇO para fora de uma fase
com hard stop ATIVO é permitida, independentemente de qualquer score. Hard stop em
estado ``HIPOTESE`` (ex.: originado de LLM) **não** bloqueia; só ``CONFIRMADO``
(com evidência/validação ou determinístico) bloqueia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import workflow_rules as rules


@dataclass(frozen=True)
class HardStopSignal:
    """Um hard stop candidato e seu estado. ``CONFIRMADO`` bloqueia; ``HIPOTESE`` não.

    ``code`` deve estar em ``rules.HARD_STOPS``. ``state`` ∈ {CONFIRMADO, HIPOTESE}."""
    code: str
    state: str = "CONFIRMADO"
    detail: str = ""

    @property
    def is_blocking(self) -> bool:
        return _norm(self.state) == "CONFIRMADO" and self.code in rules.HARD_STOPS


@dataclass(frozen=True)
class OpportunityContext:
    """Contexto puro de avaliação de uma oportunidade. É montado por fora (serviço
    de leitura que agrega os domínios), nunca pelo engine. Determinístico."""
    opportunity_id: int | None = None
    current_phase: str = "F0_INTAKE"
    phase_state: str = "NAO_INICIADA"
    modality: str = "INDEFINIDO"
    status: str = "EM_PROSPECCAO"
    # Sinais que o serviço de leitura extrai dos domínios (checklist/risk/dd/finance):
    hard_stop_signals: tuple[HardStopSignal, ...] = ()
    satisfied_gates: frozenset[str] = frozenset()   # fases cujo gate de saída está satisfeito
    gate_snapshot: dict[str, Any] = field(default_factory=dict)
    score_snapshot: dict[str, Any] = field(default_factory=dict)
    committee_decision: str | None = None           # APROVADA/REPROVADA/ADIADA (F8)
    ruleset_version: str = rules.WORKFLOW_RULESET_VERSION


@dataclass(frozen=True)
class PhaseEvaluation:
    phase: str
    phase_state: str
    gate_satisfied: bool
    active_hard_stops: tuple[str, ...]
    blocked: bool
    forward_targets: tuple[str, ...]
    next_action: str
    ruleset_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "phase_state": self.phase_state,
            "gate_satisfied": self.gate_satisfied,
            "active_hard_stops": list(self.active_hard_stops),
            "blocked": self.blocked,
            "forward_targets": list(self.forward_targets),
            "next_action": self.next_action,
            "ruleset_version": self.ruleset_version,
        }


@dataclass(frozen=True)
class TransitionDecision:
    allowed: bool
    result: str                 # PERMITIDA / BLOQUEADA
    transition_type: str | None
    from_phase: str
    to_phase: str
    reason: str
    active_hard_stops: tuple[str, ...]
    ruleset_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "result": self.result,
            "transition_type": self.transition_type,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "reason": self.reason,
            "active_hard_stops": list(self.active_hard_stops),
            "ruleset_version": self.ruleset_version,
        }


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def compute_hard_stops(ctx: OpportunityContext) -> tuple[str, ...]:
    """Códigos de hard stop ATIVOS (estado CONFIRMADO e código conhecido).

    A modalidade indefinida é um hard stop determinístico sempre detectável do
    próprio contexto (não depende do serviço de leitura)."""
    active: list[str] = []
    seen: set[str] = set()

    # Determinístico a partir do contexto: modalidade indefinida.
    if _norm(ctx.modality) == "INDEFINIDO":
        active.append("MODALIDADE_INDEFINIDA")
        seen.add("MODALIDADE_INDEFINIDA")

    for signal in ctx.hard_stop_signals:
        if signal.is_blocking and signal.code not in seen:
            active.append(signal.code)
            seen.add(signal.code)
    return tuple(active)


def _blocking_hard_stops_for_phase(ctx: OpportunityContext, phase: str) -> tuple[str, ...]:
    """Hard stops ativos que bloqueiam o AVANÇO da fase informada."""
    active = set(compute_hard_stops(ctx))
    return tuple(code for code in rules.hard_stops_for_phase(phase) if code in active)


def evaluate_phase(ctx: OpportunityContext) -> PhaseEvaluation:
    """Avalia a fase corrente: estado, gate, hard stops e próxima ação. Puro."""
    phase = ctx.current_phase
    blocking = _blocking_hard_stops_for_phase(ctx, phase)
    gate_satisfied = (
        phase in ctx.satisfied_gates
        or _norm(ctx.phase_state) in {s for s in rules.PHASE_STATES_SATISFEITOS}
    )
    blocked = bool(blocking)

    if blocked:
        phase_state = "BLOQUEADA"
        next_action = "Resolver hard stop(s): " + ", ".join(blocking)
    elif gate_satisfied:
        phase_state = _norm(ctx.phase_state) if _norm(ctx.phase_state) in rules.PHASE_STATES_SATISFEITOS else "CONCLUIDA"
        targets = rules.forward_targets(phase)
        next_action = ("Avançar para " + "/".join(sorted(targets))) if targets else "Fase terminal; encerrar."
    else:
        phase_state = _norm(ctx.phase_state) or "NAO_INICIADA"
        if phase_state not in rules.PHASE_STATES:
            phase_state = "EM_ANDAMENTO"
        next_action = "Concluir o gate de saída da fase " + phase

    return PhaseEvaluation(
        phase=phase,
        phase_state=phase_state,
        gate_satisfied=gate_satisfied and not blocked,
        active_hard_stops=tuple(compute_hard_stops(ctx)),
        blocked=blocked,
        forward_targets=tuple(sorted(rules.forward_targets(phase))),
        next_action=next_action,
        ruleset_version=ctx.ruleset_version,
    )


def _decision(
    ctx: OpportunityContext,
    target_phase: str,
    transition_type: str | None,
    allowed: bool,
    reason: str,
    active_hard_stops: tuple[str, ...] = (),
) -> TransitionDecision:
    return TransitionDecision(
        allowed=allowed,
        result="PERMITIDA" if allowed else "BLOQUEADA",
        transition_type=transition_type,
        from_phase=ctx.current_phase,
        to_phase=target_phase,
        reason=reason,
        active_hard_stops=active_hard_stops,
        ruleset_version=ctx.ruleset_version,
    )


def can_transition(
    ctx: OpportunityContext,
    target_phase: str,
    transition_type: str = "AVANCO",
) -> TransitionDecision:
    """Decide se a transição é permitida. Puro e determinístico.

    Regras (SPEC §4):
      - AVANCO: destino deve estar na matriz de avanço da fase corrente; gate de
        saída satisfeito; nenhum hard stop ativo na fase; F8->F9 exige decisão
        humana APROVADA.
      - PERDA: só de F9.
      - DESCARTE: de qualquer fase não terminal (justificativa validada no serviço).
      - REABERTURA/RETROCESSO/DECISAO/ENCERRAMENTO: validação estrutural mínima aqui.
    """
    ttype = _norm(transition_type)
    origin = ctx.current_phase

    if not rules.is_phase(origin):
        return _decision(ctx, target_phase, None, False, f"Fase de origem desconhecida: {origin}")

    if ttype == "DESCARTE":
        if origin in rules.DESCARTE_ALLOWED_FROM:
            return _decision(ctx, target_phase or origin, "DESCARTE", True, "Descarte permitido (justificativa exigida pelo serviço).")
        return _decision(ctx, target_phase or origin, "DESCARTE", False, f"Descarte não permitido a partir da fase terminal {origin}.")

    if ttype == "PERDA":
        if origin in rules.PERDA_ALLOWED_FROM:
            return _decision(ctx, target_phase or origin, "PERDA", True, "Perda registrada (não arrematado) a partir de F9.")
        return _decision(ctx, target_phase or origin, "PERDA", False, "PERDA só é válida a partir de F9_LANCE_PAGAMENTO.")

    if ttype == "REABERTURA":
        if not rules.is_phase(target_phase):
            return _decision(ctx, target_phase, "REABERTURA", False, f"Fase-alvo de reabertura desconhecida: {target_phase}")
        return _decision(ctx, target_phase, "REABERTURA", True, "Reabertura registrada (append-only).")

    if ttype == "RETROCESSO":
        if not rules.is_phase(target_phase):
            return _decision(ctx, target_phase, "RETROCESSO", False, f"Fase-alvo de retrocesso desconhecida: {target_phase}")
        if rules.phase_index(target_phase) >= rules.phase_index(origin):
            return _decision(ctx, target_phase, "RETROCESSO", False, "Retrocesso exige fase-alvo anterior à corrente.")
        return _decision(ctx, target_phase, "RETROCESSO", True, "Retrocesso permitido (justificativa exigida pelo serviço).")

    if ttype == "AVANCO":
        if not rules.is_phase(target_phase):
            return _decision(ctx, target_phase, "AVANCO", False, f"Fase-alvo desconhecida: {target_phase}")
        if target_phase not in rules.forward_targets(origin):
            return _decision(ctx, target_phase, "AVANCO", False,
                             f"Avanço inválido {origin} -> {target_phase} (fora da matriz de transições).")
        blocking = _blocking_hard_stops_for_phase(ctx, origin)
        if blocking:
            return _decision(ctx, target_phase, "AVANCO", False,
                             "Avanço bloqueado por hard stop ativo: " + ", ".join(blocking), blocking)
        if not (origin in ctx.satisfied_gates or _norm(ctx.phase_state) in rules.PHASE_STATES_SATISFEITOS):
            return _decision(ctx, target_phase, "AVANCO", False, f"Gate de saída da fase {origin} não satisfeito.")
        if origin == "F8_COMITE_DECISAO" and _norm(ctx.committee_decision) != "APROVADA":
            return _decision(ctx, target_phase, "AVANCO", False,
                             "F8 -> F9 exige decisão humana APROVADA versionada.")
        return _decision(ctx, target_phase, "AVANCO", True, f"Avanço permitido {origin} -> {target_phase}.")

    return _decision(ctx, target_phase, ttype or None, False, f"Tipo de transição não suportado: {transition_type}")
