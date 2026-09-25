"""Regressão da seleção determinística da ChecklistExecution (TASK 71).

latest_execution não pode depender da ordem incidental do relacionamento ORM:
deve escolher a maior analysis_version e, em empate, o maior id. O Veredito deve
usar a execução correspondente à analysis.version (execução antiga não pode
contaminar o veredito de uma análise nova).
"""
from __future__ import annotations

from types import SimpleNamespace

from backend.app import models, services


class FakeProperty:
    """Property mínima com checklist_executions em ordem arbitrária (não ordenada)."""

    def __init__(self, executions, prop_id=633):
        self.id = prop_id
        self.checklist_executions = executions


def _exec(exec_id, analysis_version, results=None):
    return SimpleNamespace(id=exec_id, analysis_version=analysis_version, results=results or [])


def test_latest_execution_escolhe_maior_analysis_version_fora_de_ordem():
    # Execuções propositalmente fora de ordem no relacionamento ORM.
    execs = [_exec(10, 6), _exec(12, 8), _exec(11, 7)]
    prop = FakeProperty(execs)
    latest = services.latest_execution(prop)
    assert latest.id == 12
    assert latest.analysis_version == 8


def test_latest_execution_desempata_por_maior_id():
    # Mesma analysis_version -> vence o maior id (desempate defensivo).
    execs = [_exec(30, 8), _exec(31, 8), _exec(29, 8)]
    prop = FakeProperty(execs)
    latest = services.latest_execution(prop)
    assert latest.id == 31


def test_latest_execution_trata_version_none_como_menor():
    execs = [_exec(5, None), _exec(6, 1)]
    prop = FakeProperty(execs)
    assert services.latest_execution(prop).id == 6
    # só None -> retorna a existente sem quebrar
    assert services.latest_execution(FakeProperty([_exec(9, None)])).id == 9


def test_latest_execution_sem_execucoes_retorna_none():
    assert services.latest_execution(FakeProperty([])) is None


def test_execution_for_version_seleciona_execucao_da_versao():
    execs = [_exec(10, 6), _exec(12, 8), _exec(11, 7)]
    prop = FakeProperty(execs)
    # a versão 7 deve trazer a execução 11 (não a mais recente = 12/v8)
    assert services.execution_for_version(prop, 7).id == 11
    assert services.execution_for_version(prop, 8).id == 12


def test_execution_for_version_empate_por_maior_id():
    execs = [_exec(40, 8), _exec(42, 8), _exec(41, 8)]
    prop = FakeProperty(execs)
    assert services.execution_for_version(prop, 8).id == 42


def test_execution_for_version_fallback_para_mais_recente_quando_versao_ausente():
    execs = [_exec(10, 6), _exec(12, 8)]
    prop = FakeProperty(execs)
    # não existe execução para v99 -> cai para a mais recente (v8/id12)
    assert services.execution_for_version(prop, 99).id == 12


def test_create_verdict_usa_execucao_da_versao_da_analise(monkeypatch):
    # V8 confirma 7 itens; uma execução ANTIGA (v7) com tudo pendente não pode
    # contaminar o veredito da V8.
    def result(state):
        return SimpleNamespace(state=state, applicable=True, item=SimpleNamespace(question="q"))

    exec_v7 = _exec(70, 7, results=[result("PENDENTE") for _ in range(27)])
    exec_v8 = _exec(80, 8, results=[result("CONFIRMADO") for _ in range(7)] + [result("PENDENTE") for _ in range(20)])
    prop = FakeProperty([exec_v8, exec_v7])  # ordem arbitrária

    capturado = {}

    class FakeEngine:
        def evaluate(self, **kwargs):
            capturado["checklist_results"] = kwargs.get("checklist_results")
            capturado["analysis_version"] = kwargs.get("analysis_version")
            return SimpleNamespace(to_dict=lambda: {"property_id": prop.id, "analysis_version": kwargs.get("analysis_version"), "overall": "INCONCLUSIVO", "summary": "", "pending_items": [], "financial": {}, "risk_ids": [], "evidence_ids": []})

    class ScalarResult:
        def all(self):
            return []

    class Db:
        def __init__(self):
            self.added = []
        def scalars(self, statement):
            return ScalarResult()
        def add(self, item):
            self.added.append(item)
        def flush(self):
            pass

    analysis = models.Analysis(id=800, property_id=633, version=8, evidence_ids=[])
    monkeypatch.setattr(services, "VerdictEngine", FakeEngine)
    monkeypatch.setattr(services, "build_finance", lambda prop: {})

    services.create_verdict(Db(), prop, analysis, None)

    # deve ter usado a execução da V8 (7 CONFIRMADO + 20 PENDENTE), não a V7 (27 PENDENTE)
    states = [r.state for r in capturado["checklist_results"]]
    assert capturado["analysis_version"] == 8
    assert states.count("CONFIRMADO") == 7
    assert states.count("PENDENTE") == 20
    assert len(states) == 27
