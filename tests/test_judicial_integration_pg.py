"""TASK FINAL — integração Radar → Judicial → PostgreSQL (persistência no imóvel).

Exercita o JudicialIntegrationService persistindo o resultado da Judicial API como
LegalProcess/ProcessMovement + Evidence(JURIDICO) + DomainEvent no MESMO banco do
Radar. Usa a fixture `db` (PostgreSQL real, rollback por teste). Um cliente falso
substitui a chamada HTTP. Verifica também idempotência (re-consulta não duplica).
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app import models
from backend.app.judicial_client import JudicialSearchOutcome
from backend.app.judicial_integration import JUDICIAL_SOURCE, JudicialIntegrationService


class _FakeClient:
    def __init__(self, outcome: JudicialSearchOutcome):
        self._outcome = outcome

    def search(self, criteria):
        return self._outcome


def _outcome():
    return JudicialSearchOutcome(
        search_id="s-1",
        status="COMPLETED",
        processes=[
            {
                "process_number": "0000001-11.2020.8.16.0001",
                "tribunal": "TJPR",
                "class_name": "Execução de Título Extrajudicial",
                "subjects": [{"code": "123", "name": "Penhora"}],
                "parties": [
                    {"name": "BANCO X", "role": "PLAINTIFF"},
                    {"name": "JOÃO DA SILVA", "role": "DEFENDANT"},
                ],
                "movements": [
                    {"movement_date": "2026-01-10", "description": "Penhora efetivada"},
                    {"movement_date": "2026-02-01", "description": "Intimação da parte"},
                ],
            }
        ],
        signals=[
            {"signal_code": "PENHORA", "severity": "HIGH", "confidence": 0.85,
             "evidence_text": "Evidência de penhora", "tribunal": "TJPR",
             "process_number": "0000001-11.2020.8.16.0001"},
        ],
        sources=[{"tribunal": "TJPR", "status": "SUCCESS"}],
    )


def _property(db):
    prop = models.Property(title="Imóvel J", address="Rua J", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(prop)
    db.flush()
    return prop


def test_persiste_processo_movimentos_sinal_e_evento(db):
    prop = _property(db)
    service = JudicialIntegrationService(db, client=_FakeClient(_outcome()))
    result = service.consult_for_property(prop, {"process_number": "0000001-11.2020.8.16.0001"})
    db.flush()

    assert result.processes_created == 1
    assert result.signals_created == 1

    processos = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == prop.id)).all()
    assert len(processos) == 1
    proc = processos[0]
    assert proc.source == JUDICIAL_SOURCE
    assert proc.consulted_at is not None
    assert proc.polo_passive and "JOÃO DA SILVA" in proc.polo_passive
    assert proc.polo_active and "BANCO X" in proc.polo_active
    # movimentos persistidos com a fonte da Judicial API
    assert len(proc.movements) == 2
    assert all(m.source == JUDICIAL_SOURCE for m in proc.movements)

    # sinal jurídico vira Evidence JURIDICO, preservando a distinção processo x imóvel
    evidencias = db.scalars(select(models.Evidence).where(models.Evidence.property_id == prop.id)).all()
    assert len(evidencias) == 1
    ev = evidencias[0]
    assert ev.category == "JURIDICO"
    assert "PENHORA" in ev.fact
    assert "não confirma" in (ev.interpretation or "").lower() or "nao confirma" in (ev.interpretation or "").lower()

    # DomainEvent de auditoria/reanálise
    eventos = db.scalars(
        select(models.DomainEvent).where(
            models.DomainEvent.property_id == prop.id,
            models.DomainEvent.event_type == "CONSULTA_JUDICIAL_REALIZADA",
        )
    ).all()
    assert len(eventos) == 1
    assert "juridico" in eventos[0].affected_domains


def test_reconsulta_nao_duplica_processo(db):
    prop = _property(db)
    service = JudicialIntegrationService(db, client=_FakeClient(_outcome()))
    service.consult_for_property(prop, {"process_number": "0000001-11.2020.8.16.0001"})
    db.flush()
    # Segunda consulta com o MESMO processo: atualiza no lugar, não duplica.
    result2 = service.consult_for_property(prop, {"process_number": "0000001-11.2020.8.16.0001"})
    db.flush()

    assert result2.processes_created == 0
    assert result2.processes_updated == 1
    processos = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == prop.id)).all()
    assert len(processos) == 1
    # movimentos da Judicial API são substituídos (não acumulam duplicados)
    assert len(processos[0].movements) == 2
