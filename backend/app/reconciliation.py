"""Reconciliação histórica controlada de Vereditos (manutenção one-off).

Contexto (TASK 74): o Veredito V8 do imóvel 633 foi persistido usando a
ChecklistExecution errada (uma execução antiga, all-PENDENTE), enquanto a
execução correta da V8 (1153) tem 7 CONFIRMADO / 20 PENDENTE. As Tasks 73 e
73.1 corrigiram o CÓDIGO para novas execuções; aqui corrigimos apenas o
SNAPSHOT histórico já persistido, de forma:

- determinística (sem LLM, reutiliza VerdictEngine/RiskEngine/execution_for_version);
- controlada (limitada a um property_id + analysis_version explícitos);
- idempotente (rodar duas vezes produz o mesmo estado; não cria Analysis/execução/evento novos);
- transacional (commit único ao final; rollback em erro).

NÃO cria endpoint público, NÃO é automático para todas as propriedades, NÃO
gera V9, NÃO altera versões anteriores. É um mecanismo interno de manutenção.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .services import (
    build_verdict_decision,
    execution_for_version,
    recalculate_risks,
)


@dataclass
class ReconcileResult:
    property_id: int
    analysis_version: int
    execution_id: int | None
    verdict_id: int | None
    pending_before: int | None
    pending_after: int | None
    risks_recalculated: bool
    changed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "analysis_version": self.analysis_version,
            "execution_id": self.execution_id,
            "verdict_id": self.verdict_id,
            "pending_before": self.pending_before,
            "pending_after": self.pending_after,
            "risks_recalculated": self.risks_recalculated,
            "changed": self.changed,
        }


def _risk_signature(risk: models.Risk) -> tuple:
    # Assinatura determinística de um risco (o que o RiskEngine produz de forma
    # reprodutível). Serve para comparar o conjunto persistido com o recalculado
    # sem depender de ids/ordem.
    return (risk.origin, risk.category, risk.severity, risk.status, risk.description, risk.evidence_id)


def _reconcile_risks_if_needed(db: Session, prop: models.Property, analysis_version: int, execution) -> bool:
    """Recalcula os Risks da versão SOMENTE se o conjunto persistido divergir do
    que o RiskEngine produz a partir da execução correta. Idempotente.

    Reutiliza recalculate_risks (Task 73.1). Como recalculate_risks adiciona (não
    substitui), removemos os Risks da própria versão antes de recriar, garantindo
    que rodar de novo não duplique.
    """
    from .risk_engine import RiskEngine

    persisted = list(
        db.scalars(
            select(models.Risk).where(
                models.Risk.property_id == prop.id,
                models.Risk.analysis_version == analysis_version,
            )
        ).all()
    )

    expected_candidates = RiskEngine().evaluate(
        property_id=prop.id,
        checklist_results=execution.results if execution else [],
    )
    expected_sig = sorted(
        (
            f"{c.origin}:{c.risk_key}",
            c.domain,
            c.severity,
            c.status,
            f"[{c.risk_key}] {c.title}: {c.description}",
            c.evidence_ids[0] if c.evidence_ids else None,
        )
        for c in expected_candidates
    )
    persisted_sig = sorted(_risk_signature(r) for r in persisted)

    if persisted_sig == expected_sig:
        return False  # já consistente, não mexe

    for risk in persisted:
        db.delete(risk)
    db.flush()
    recalculate_risks(db, prop, analysis_version)
    return True


def reconcile_verdict(db: Session, property_id: int, analysis_version: int) -> ReconcileResult:
    """Reconciliação determinística e idempotente do Veredito de UMA versão.

    Atualiza o snapshot do Verdict existente da versão (in place), usando a
    ChecklistExecution correta da versão e os Risks consistentes daquela versão.
    Não cria Analysis/execução/evento; não roda LLM; não gera V9. Transacional.
    """
    prop = db.get(models.Property, property_id)
    if prop is None:
        raise ValueError(f"Imóvel {property_id} não encontrado")

    # Fonte de verdade: consulta por versão no banco (não a relationship em memória).
    execution = execution_for_version(prop, analysis_version, db=db)

    verdict = db.scalar(
        select(models.Verdict)
        .where(
            models.Verdict.property_id == property_id,
            models.Verdict.analysis_version == analysis_version,
        )
        .order_by(models.Verdict.id.desc())
    )
    pending_before = len(verdict.pending_items) if verdict and verdict.pending_items is not None else None

    try:
        # 1) Garante riscos consistentes com a execução correta (idempotente).
        risks_recalculated = _reconcile_risks_if_needed(db, prop, analysis_version, execution)

        # 2) Recalcula a decisão determinística (mesma regra do create_verdict).
        evidence_ids = verdict.evidence_ids if verdict else []
        decision = build_verdict_decision(db, prop, analysis_version, evidence_ids)
        data = decision.to_dict()

        changed = False
        if verdict is None:
            # Sem verdict para a versão: cria o snapshot correto (não cria Analysis).
            verdict = models.Verdict(**data)
            db.add(verdict)
            changed = True
        else:
            # Atualiza in place apenas os campos determinísticos do snapshot.
            for field, value in data.items():
                if getattr(verdict, field) != value:
                    setattr(verdict, field, value)
                    changed = True
        db.flush()

        pending_after = len(verdict.pending_items) if verdict.pending_items is not None else None
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReconcileResult(
        property_id=property_id,
        analysis_version=analysis_version,
        execution_id=execution.id if execution else None,
        verdict_id=verdict.id if verdict else None,
        pending_before=pending_before,
        pending_after=pending_after,
        risks_recalculated=risks_recalculated,
        changed=changed,
    )
