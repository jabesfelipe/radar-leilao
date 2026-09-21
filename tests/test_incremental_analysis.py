import pytest

from backend.app import models
from backend.app.incremental import IncrementalAnalysisService


class Db:
    def __init__(self, prop):
        self.prop = prop
        self.committed = False
        self.rolled_back = False
        self.added = []

    def get(self, model, identifier):
        if model is models.Property and identifier == self.prop.id:
            return self.prop
        return None

    def add(self, item):
        self.added.append(item)

    def flush(self):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class Orchestrator:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, property_id, domains, query, analysis_id=None):
        self.calls.append((property_id, domains, query, analysis_id))
        return self.result


def prop(property_id=1):
    return models.Property(id=property_id, title="Imóvel", address="Rua", city="São Paulo", state="SP")


def event(event_type, property_id=1, event_id=10):
    return models.DomainEvent(id=event_id, property_id=property_id, event_type=event_type, aggregate_type="Debt", aggregate_id=3, payload={"amount": 100})


def test_evento_sem_impacto_nao_cria_analise(monkeypatch):
    db = Db(prop())
    called = []
    monkeypatch.setattr("backend.app.incremental.create_analysis", lambda *args, **kwargs: called.append(True))
    result = IncrementalAnalysisService(db).run_for_event(event("EVENTO_DESCONHECIDO"))
    assert result["status"] == "IGNORADO"
    assert result["analise_executada"] is False
    assert called == []
    assert db.committed is False


def test_divida_executa_somente_dominios_do_impact_analyzer(monkeypatch):
    db = Db(prop())
    analysis = models.Analysis(id=20, property_id=1, version=2, evidence_ids=[], agents_executed=[])
    execution = models.ChecklistExecution(id=30, analysis_version=2, results=[])
    orchestrator = Orchestrator({"agent_results": [{"agent": "financeiro"}, {"agent": "checklist"}], "llm_runs": [], "evidence_ids": [], "retrieved_chunk_ids": [4], "llm_used": False})
    history = []
    monkeypatch.setattr("backend.app.incremental.create_analysis", lambda **kwargs: analysis)
    monkeypatch.setattr("backend.app.incremental.latest_execution", lambda prop: None)
    monkeypatch.setattr("backend.app.incremental.create_execution", lambda *args, **kwargs: execution)
    monkeypatch.setattr("backend.app.incremental.record_history", lambda *args, **kwargs: history.append(args[-1] if args else None))
    monkeypatch.setattr("backend.app.incremental.persist_agent_findings", lambda *args: [7])
    monkeypatch.setattr("backend.app.incremental.persist_llm_runs", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.aggregate_llm_usage", lambda runs: {"runs": 0})
    monkeypatch.setattr("backend.app.incremental.build_finance", lambda prop: {})
    monkeypatch.setattr("backend.app.incremental.recalculate_risks", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.create_verdict", lambda *args: type("Verdict", (), {"overall": "FAVORÁVEL"})())
    result = IncrementalAnalysisService(db, orchestrator=orchestrator).run_for_event(event("DIVIDA_ADICIONADA"))
    assert orchestrator.calls == [(1, ["financeiro", "checklist"], "DIVIDA_ADICIONADA", 20)]
    assert result["agentes"] == ["financeiro", "checklist"]
    assert result["analysis_id"] == 20
    assert result["execution_id"] == 30
    assert len(history) == 2
    assert event("DIVIDA_ADICIONADA").event_type == "DIVIDA_ADICIONADA"


def test_evento_concluido_marca_processado_e_preserva_causa(monkeypatch):
    db = Db(prop())
    current_event = event("CUSTO_ADICIONADO", event_id=22)
    analysis = models.Analysis(id=21, property_id=1, version=4, evidence_ids=[], agents_executed=[])
    execution = models.ChecklistExecution(id=31, analysis_version=4, results=[])
    cause_events = []
    orchestrator = Orchestrator({"agent_results": [], "llm_runs": [], "evidence_ids": [], "retrieved_chunk_ids": [], "llm_used": False})
    monkeypatch.setattr("backend.app.incremental.create_analysis", lambda **kwargs: analysis)
    monkeypatch.setattr("backend.app.incremental.latest_execution", lambda prop: None)
    monkeypatch.setattr("backend.app.incremental.create_execution", lambda *args, **kwargs: execution)
    monkeypatch.setattr("backend.app.incremental.record_history", lambda *args, **kwargs: cause_events.append(args[-1] if args else None))
    monkeypatch.setattr("backend.app.incremental.persist_agent_findings", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.persist_llm_runs", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.aggregate_llm_usage", lambda runs: {})
    monkeypatch.setattr("backend.app.incremental.build_finance", lambda prop: {})
    monkeypatch.setattr("backend.app.incremental.recalculate_risks", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.create_verdict", lambda *args: type("Verdict", (), {"overall": "FAVORÁVEL"})())
    IncrementalAnalysisService(db, orchestrator=orchestrator).run_for_event(current_event)
    assert current_event.processed is True
    assert cause_events == [22, 22]
    assert db.committed is True


def test_evento_de_outro_imovel_nao_consulta_imovel_diferente():
    db = Db(prop(1))
    with pytest.raises(ValueError):
        IncrementalAnalysisService(db).run_for_event(event("DIVIDA_ADICIONADA", property_id=2))
    assert db.prop.id == 1


def test_comparavel_nao_cria_checklist_execution(monkeypatch):
    db = Db(prop())
    analysis = models.Analysis(id=24, property_id=1, version=5, evidence_ids=[], agents_executed=[])
    orchestrator = Orchestrator({"agent_results": [{"agent": "mercado"}, {"agent": "financeiro"}], "llm_runs": [], "evidence_ids": [], "retrieved_chunk_ids": [8], "llm_used": False})
    monkeypatch.setattr("backend.app.incremental.create_analysis", lambda **kwargs: analysis)
    monkeypatch.setattr("backend.app.incremental.create_execution", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("não deve criar ChecklistExecution")))
    monkeypatch.setattr("backend.app.incremental.record_history", lambda *args, **kwargs: None)
    monkeypatch.setattr("backend.app.incremental.persist_agent_findings", lambda *args: [8])
    monkeypatch.setattr("backend.app.incremental.persist_llm_runs", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.aggregate_llm_usage", lambda runs: {"runs": 0})
    monkeypatch.setattr("backend.app.incremental.build_finance", lambda prop: {})
    monkeypatch.setattr("backend.app.incremental.recalculate_risks", lambda *args: [])
    monkeypatch.setattr("backend.app.incremental.create_verdict", lambda *args: type("Verdict", (), {"overall": "FAVORÁVEL"})())
    result = IncrementalAnalysisService(db, orchestrator=orchestrator).run_for_event(event("COMPARAVEL_ADICIONADO"))
    assert orchestrator.calls == [(1, ["mercado", "financeiro"], "COMPARAVEL_ADICIONADO", 24)]
    assert result["agentes"] == ["mercado", "financeiro"]
    assert result["execution_id"] is None
