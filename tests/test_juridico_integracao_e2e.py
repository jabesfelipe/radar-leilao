"""Integração E2E (nível de serviço) do fluxo jurídico:

    Judicial API (mock) → LegalProcess + correlação → Evidência/Sinal →
    Checklist (diligência) → Risk Engine → Verdict.

Usa a fixture `db` (PostgreSQL real, rollback por teste). Nenhum LLM e nenhum
DataJud real: o cliente HTTP é substituído por um fake. Não toca dados reais.
"""
from __future__ import annotations

from sqlalchemy import select

from backend.app import models
from backend.app.judicial_client import JudicialSearchOutcome
from backend.app.judicial_integration import JudicialIntegrationService
from backend.app.services import (
    build_verdict_decision,
    create_execution,
    ensure_checklist_master,
    juridical_overview,
    recalculate_risks,
)


class _FakeClient:
    def __init__(self, outcome):
        self._outcome = outcome

    def search(self, criteria):
        return self._outcome


def _outcome_penhora(owner_cpf: str | None = None):
    parties = [
        {"name": "BANCO X", "role": "PLAINTIFF"},
        {"name": "JOÃO DA SILVA", "role": "DEFENDANT", **({"cpf": owner_cpf} if owner_cpf else {})},
    ]
    return JudicialSearchOutcome(
        search_id="s-e2e",
        status="COMPLETED",
        processes=[{
            "process_number": "0000009-99.2021.8.16.0001",
            "tribunal": "TJPR",
            "comarca": "Curitiba",
            "uf": "PR",
            "class_name": "Execução Fiscal",
            "subjects": [{"name": "Penhora"}],
            "parties": parties,
            "movements": [{"movement_date": "2026-03-01", "description": "Penhora efetivada sobre bem"}],
        }],
        signals=[
            {"signal_code": "PENHORA", "severity": "HIGH", "confidence": 0.85,
             "evidence_text": "Movimento menciona penhora", "tribunal": "TJPR",
             "process_number": "0000009-99.2021.8.16.0001"},
            {"signal_code": "PROPERTY_PENHORA_EVIDENCE", "severity": "HIGH", "confidence": 0.75,
             "evidence_text": "Evidência patrimonial de penhora", "tribunal": "TJPR",
             "process_number": "0000009-99.2021.8.16.0001"},
        ],
        sources=[{"tribunal": "TJPR", "status": "SUCCESS"}],
    )


def _property_with_registration(db, holder="JOÃO DA SILVA", comarca="Curitiba"):
    prop = models.Property(title="Imóvel E2E Jur", address="Rua K", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(prop); db.flush()
    db.add(models.PropertyRegistration(property_id=prop.id, holder=holder, comarca=comarca))
    db.flush()
    return prop


def test_fluxo_completo_sinal_gera_pendencia_risco_e_veredito(db):
    ensure_checklist_master(db)
    prop = _property_with_registration(db)
    # Execução de checklist corrente (como numa análise V1).
    create_execution(db, prop, triggered_by="MANUAL", analysis_version=1)

    service = JudicialIntegrationService(db, client=_FakeClient(_outcome_penhora()))
    result = service.consult_for_property(prop, {"name": "JOÃO DA SILVA"})
    db.flush()

    # 1) Processo persistido com correlação (nome+comarca+UF compatível → MEDIA).
    proc = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == prop.id)).one()
    assert proc.correlation_level == "MEDIA"
    assert proc.link_origin == "AUTOMATICA"
    assert result.processes_relevant == 1

    # 2) Evidência jurídica rastreável AO PROCESSO (EvidenceLink target LegalProcess).
    links = db.scalars(select(models.EvidenceLink).where(models.EvidenceLink.target_type == "LegalProcess", models.EvidenceLink.target_id == proc.id)).all()
    assert links, "sinal deve estar vinculado ao processo"

    # 3) Checklist jurídico marcado como ATENCAO (diligência), não CONFIRMADO.
    execution = db.scalars(select(models.ChecklistExecution).where(models.ChecklistExecution.property_id == prop.id).order_by(models.ChecklistExecution.id.desc())).first()
    restricao = next((r for r in execution.results if r.item.canonical_key == "PENHORA_INDISPONIBILIDADE"), None)
    assert restricao is not None
    assert restricao.state == "ATENCAO"
    # evidência vinculada ao resultado do checklist
    assert db.scalars(select(models.ChecklistEvidence).where(models.ChecklistEvidence.checklist_result_id == restricao.id)).first() is not None

    # 4) Risk Engine gera risco jurídico (ATENCAO + evidência) ao recalcular a versão.
    riscos = recalculate_risks(db, prop, analysis_version=1)
    db.flush()
    juridicos = [r for r in riscos if r.category.lower() == "juridico"]
    assert juridicos, "deve haver risco jurídico a partir do checklist em ATENCAO"
    assert juridicos[0].evidence_id is not None

    # 5) Veredito determinístico reflete pendência/risco (ATENCAO → não FAVORAVEL).
    decision = build_verdict_decision(db, prop, analysis_version=1, evidence_ids=[])
    assert decision.overall in {"ATENCAO", "INCONCLUSIVO", "DESFAVORAVEL"}

    # 6) Visão jurídica legível: situação NÃO confirmada, impacto não quantificado.
    overview = juridical_overview(db, prop)
    assert overview["processos_encontrados"] == 1
    assert overview["processos_relevantes"] == 1
    assert overview["situacao_imovel"] == "NAO_CONFIRMADA"
    assert overview["impacto_financeiro"] == "NAO_QUANTIFICADO"
    assert overview["correlacao"] == "MEDIA"


def test_confirmacao_manual_do_checklist_e_preservada(db):
    ensure_checklist_master(db)
    prop = _property_with_registration(db)
    create_execution(db, prop, triggered_by="MANUAL", analysis_version=1)
    execution = db.scalars(select(models.ChecklistExecution).where(models.ChecklistExecution.property_id == prop.id).order_by(models.ChecklistExecution.id.desc())).first()
    restricao = next(r for r in execution.results if r.item.canonical_key == "PENHORA_INDISPONIBILIDADE")
    # Usuário confirmou manualmente antes da consulta.
    restricao.state = "CONFIRMADO"
    restricao.answer = "Validado na matrícula."
    db.flush()

    service = JudicialIntegrationService(db, client=_FakeClient(_outcome_penhora()))
    service.consult_for_property(prop, {"name": "JOÃO DA SILVA"})
    db.flush()

    db.refresh(restricao)
    # A consulta NÃO rebaixa a confirmação manual.
    assert restricao.state == "CONFIRMADO"
    assert restricao.answer == "Validado na matrícula."


def test_vinculo_manual_preserva_correlacao_automatica(db):
    ensure_checklist_master(db)
    prop = _property_with_registration(db)
    create_execution(db, prop, triggered_by="MANUAL", analysis_version=1)
    service = JudicialIntegrationService(db, client=_FakeClient(_outcome_penhora()))
    service.consult_for_property(prop, {"name": "JOÃO DA SILVA"})
    db.flush()
    proc = db.scalars(select(models.LegalProcess).where(models.LegalProcess.property_id == prop.id)).one()
    nivel = proc.correlation_level
    # Simula vínculo manual (como o endpoint faz): muda origem, preserva correlação.
    proc.link_origin = "VALIDADA"
    db.flush()
    db.refresh(proc)
    assert proc.link_origin == "VALIDADA"
    assert proc.correlation_level == nivel  # correlação determinística intacta
