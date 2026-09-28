"""TASK 74 — Reconciliação histórica controlada do Veredito V8.

Testes com banco real (fixture ``db``; rollback ao final, nada persistido; SEM
LLM, SEM análise real, SEM V9). Para manter o isolamento, o commit interno da
reconciliação é redirecionado para flush no teste (a transação da fixture segue
aberta e é revertida no final). A regra de negócio permanece a mesma.

Cobrem:
1. seleção da execução correta da versão (V8) mesmo com execução antiga presente;
2. resultado do Veredito: 20 pendências de Checklist + 1 financeira legítima = 21;
3. idempotência: rodar duas vezes produz o mesmo estado e não cria Analysis/Verdict extras;
4. preservação histórica: V1..V7 (Analysis e seus Verdicts) permanecem intactas; não cria V9.
"""
from __future__ import annotations

import pytest

from backend.app import models, services
from backend.app.reconciliation import reconcile_verdict


PENDENCIA_FINANCEIRA = "Fórmula canônica de preço máximo não está definida na SPEC; cálculo não foi inventado."


@pytest.fixture
def sem_commit(db, monkeypatch):
    # Mantém a transação da fixture aberta: o commit da reconciliação vira flush.
    monkeypatch.setattr(db, "commit", db.flush)
    return db


def _property(db):
    prop = models.Property(title="COND TESTE 633", address="Rua 633", city="São Paulo", state="SP", area_m2=70, bedrooms=2)
    db.add(prop)
    db.flush()
    return prop


def _execucao(db, prop, analysis_version, confirmados):
    """Cria uma ChecklistExecution da versão e confirma `confirmados` itens."""
    execution = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version)
    aplicaveis = [r for r in execution.results if r.applicable]
    for r in aplicaveis[:confirmados]:
        r.state = "CONFIRMADO"
    db.flush()
    return execution


def test_reconciliacao_usa_execucao_correta_da_v8(sem_commit):
    db = sem_commit
    prop = _property(db)
    # Simula o histórico: uma execução antiga (V3, tudo pendente) e a V8 (7 CONFIRMADO).
    _ = list(prop.checklist_executions)  # relationship carregada antes (stale)
    exec_v3 = _execucao(db, prop, 3, confirmados=0)
    exec_v8 = _execucao(db, prop, 8, confirmados=7)

    # Um Verdict V8 histórico ERRADO (calculado com a execução antiga): 27 pendências.
    verdict_errado = models.Verdict(
        property_id=prop.id, analysis_version=8, overall="INCONCLUSIVO", summary="antigo",
        pending_items=[f"errada-{i}" for i in range(27)], financial={}, risk_ids=[], evidence_ids=[],
    )
    db.add(verdict_errado)
    db.flush()

    result = reconcile_verdict(db, prop.id, 8)

    # A reconciliação usou a execução V8 correta (1153 no banco real; aqui exec_v8).
    assert result.execution_id == exec_v8.id
    assert result.execution_id != exec_v3.id


def test_reconciliacao_produz_20_checklist_mais_1_financeira(sem_commit):
    db = sem_commit
    prop = _property(db)
    _ = list(prop.checklist_executions)
    _execucao(db, prop, 3, confirmados=0)
    exec_v8 = _execucao(db, prop, 8, confirmados=7)
    total_aplicaveis = sum(1 for r in exec_v8.results if r.applicable)

    verdict = models.Verdict(
        property_id=prop.id, analysis_version=8, overall="INCONCLUSIVO", summary="antigo",
        pending_items=[f"errada-{i}" for i in range(total_aplicaveis)], financial={}, risk_ids=[], evidence_ids=[],
    )
    db.add(verdict)
    db.flush()

    result = reconcile_verdict(db, prop.id, 8)

    atualizado = db.get(models.Verdict, verdict.id)
    checklist_pendentes = [p for p in atualizado.pending_items if p != PENDENCIA_FINANCEIRA]
    financeiras = [p for p in atualizado.pending_items if p == PENDENCIA_FINANCEIRA]

    # 7 CONFIRMADO -> total_aplicaveis - 7 pendências de checklist (esperado 20 no 633 real).
    assert len(checklist_pendentes) == total_aplicaveis - 7
    # a pendência financeira legítima permanece
    assert len(financeiras) == 1
    # total = checklist + financeira
    assert len(atualizado.pending_items) == (total_aplicaveis - 7) + 1
    assert result.pending_after == len(atualizado.pending_items)


def test_reconciliacao_e_idempotente(sem_commit):
    db = sem_commit
    prop = _property(db)
    _ = list(prop.checklist_executions)
    _execucao(db, prop, 3, confirmados=0)
    _execucao(db, prop, 8, confirmados=7)

    verdict = models.Verdict(
        property_id=prop.id, analysis_version=8, overall="INCONCLUSIVO", summary="antigo",
        pending_items=["errada"], financial={}, risk_ids=[], evidence_ids=[],
    )
    db.add(verdict)
    db.flush()

    verdicts_antes = db.query(models.Verdict).filter_by(property_id=prop.id).count()
    analyses_antes = db.query(models.Analysis).filter_by(property_id=prop.id).count()

    r1 = reconcile_verdict(db, prop.id, 8)
    pending_1 = r1.pending_after
    r2 = reconcile_verdict(db, prop.id, 8)
    pending_2 = r2.pending_after

    # mesmo resultado nas duas execuções
    assert pending_1 == pending_2
    # a segunda execução não muda nada
    assert r2.changed is False
    # não cria Verdicts nem Analysis extras
    assert db.query(models.Verdict).filter_by(property_id=prop.id).count() == verdicts_antes
    assert db.query(models.Analysis).filter_by(property_id=prop.id).count() == analyses_antes


def test_reconciliacao_preserva_historico_v1_a_v7_e_nao_cria_v9(sem_commit):
    db = sem_commit
    prop = _property(db)
    _ = list(prop.checklist_executions)

    # Cria Analyses V1..V8 e um Verdict por versão (snapshots históricos).
    analyses = {}
    verdicts = {}
    for v in range(1, 9):
        a = services.create_analysis(db, prop, "checklist", ["checklist"], [], f"v{v}", [])
        analyses[v] = a
        confirmados = 7 if v == 8 else 0
        _execucao(db, prop, v, confirmados=confirmados)
        vd = models.Verdict(
            property_id=prop.id, analysis_version=v, overall="INCONCLUSIVO", summary=f"snapshot v{v}",
            pending_items=[f"v{v}-p"], financial={}, risk_ids=[], evidence_ids=[],
        )
        db.add(vd)
        db.flush()
        verdicts[v] = (vd.id, list(vd.pending_items), vd.summary)

    max_version_antes = db.query(models.Analysis.version).filter_by(property_id=prop.id).order_by(models.Analysis.version.desc()).first()[0]

    reconcile_verdict(db, prop.id, 8)

    # V1..V7 Verdicts intactos (id, pending_items, summary inalterados).
    for v in range(1, 8):
        vd_id, pending, summary = verdicts[v]
        atual = db.get(models.Verdict, vd_id)
        assert atual.pending_items == pending
        assert atual.summary == summary
        assert atual.analysis_version == v

    # V8 continua sendo V8; nenhuma V9 criada.
    max_version_depois = db.query(models.Analysis.version).filter_by(property_id=prop.id).order_by(models.Analysis.version.desc()).first()[0]
    assert max_version_depois == max_version_antes == 8
    assert db.query(models.Analysis).filter_by(property_id=prop.id, version=9).count() == 0
