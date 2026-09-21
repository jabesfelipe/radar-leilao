from types import SimpleNamespace

from backend.app import models
from backend.app.risk_engine import RiskEngine, RiskCandidate


def checklist_result(state, evidence_ids, key="EDITAL_LIDO", result_id=1):
    item = SimpleNamespace(canonical_key=key, category="DOCUMENTAL", question="O edital foi lido?")
    return SimpleNamespace(
        id=result_id,
        state=state,
        confidence="ALTA",
        item=item,
        evidence_links=[SimpleNamespace(evidence_id=value) for value in evidence_ids],
        evidences=[],
    )


def test_risco_identificado_gera_risco_com_evidence():
    risks = RiskEngine().evaluate(1, [checklist_result("RISCO_IDENTIFICADO", [8])])
    assert len(risks) == 1
    assert risks[0].risk_key == "CHECKLIST_EDITAL_LIDO_RISCO_IDENTIFICADO"
    assert risks[0].severity == "ALTA"
    assert risks[0].evidence_ids == [8]
    assert risks[0].checklist_result_ids == [1]


def test_atencao_gera_risco_media():
    risks = RiskEngine().evaluate(1, [checklist_result("ATENCAO", [8])])
    assert len(risks) == 1
    assert risks[0].severity == "MEDIA"


def test_pendente_e_ausencia_de_evidencia_nao_geram_risco():
    assert RiskEngine().evaluate(1, [checklist_result("PENDENTE", [8])]) == []
    assert RiskEngine().evaluate(1, [checklist_result("RISCO_IDENTIFICADO", [])]) == []


def test_dados_financeiros_e_documentos_isolados_nao_geram_risco():
    assert RiskEngine().evaluate(1, []) == []
    assert RiskEngine().evaluate(1, [checklist_result("PENDENTE", [])]) == []


def test_multiplos_riscos_e_determinismo():
    results = [checklist_result("RISCO_IDENTIFICADO", [1], "A", 1), checklist_result("ATENCAO", [2], "B", 2)]
    first = [risk.to_dict() for risk in RiskEngine().evaluate(1, results)]
    second = [risk.to_dict() for risk in RiskEngine().evaluate(1, results)]
    assert first == second
    assert len(first) == 2


def test_recalculate_persiste_analysis_version_sem_apagar_anterior(monkeypatch):
    from backend.app import services

    class Db:
        def __init__(self):
            self.added = []
        def add(self, item):
            self.added.append(item)
        def flush(self):
            pass

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    db = Db()
    previous = models.Risk(id=3, property_id=1, analysis_version=1, category="financeiro", description="anterior")
    prop.risks = [previous]
    candidate = RiskCandidate("RULE", "financeiro", "Título", "Descrição", "ALTA", "ATIVO", "Impacto", "ALTA", "RiskEngine", [9], [])
    monkeypatch.setattr(services, "latest_execution", lambda prop: None)
    monkeypatch.setattr(services, "build_finance", lambda prop: {})
    monkeypatch.setattr(services, "RiskEngine", lambda: SimpleNamespace(evaluate=lambda **kwargs: [candidate]))
    risks = services.recalculate_risks(db, prop, 2)
    assert len(risks) == 1
    assert risks[0].analysis_version == 2
    assert risks[0].evidence_id == 9
    assert previous in prop.risks


def test_engine_nao_depende_de_llm_rag_ou_veredito():
    import inspect
    from backend.app import risk_engine
    source = inspect.getsource(risk_engine)
    assert "LLM" not in source
    assert "RAG" not in source
    assert "create_verdict" not in source
    assert "RiskEngine" in source
