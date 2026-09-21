from types import SimpleNamespace

from backend.app import models
from backend.app.verdict_engine import VerdictEngine


def risk(severity, risk_id=1, evidence_id=10, status="ATIVO"):
    return SimpleNamespace(id=risk_id, severity=severity, evidence_id=evidence_id, status=status)


def checklist(state="PENDENTE", question="Pergunta pendente", applicable=True):
    return SimpleNamespace(state=state, applicable=applicable, item=SimpleNamespace(question=question))


def test_nenhum_risco_pendencia_e_evidencia_suficiente_favoravel():
    result = VerdictEngine().evaluate(1, 2, evidence_ids=[8], financial={"custo_total": 100})
    assert result.overall == "FAVORAVEL"
    assert result.risk_ids == []
    assert result.evidence_ids == [8]


def test_risco_media_alta_e_critica_respeitam_prioridade():
    assert VerdictEngine().evaluate(1, 2, risks=[risk("MEDIA")], evidence_ids=[8]).overall == "ATENCAO"
    assert VerdictEngine().evaluate(1, 2, risks=[risk("ALTA")], evidence_ids=[8]).overall == "ATENCAO"
    assert VerdictEngine().evaluate(1, 2, risks=[risk("CRITICA")], evidence_ids=[8]).overall == "DESFAVORAVEL"


def test_pendencia_sem_risco_e_sem_evidencia_sao_inconclusivos():
    assert VerdictEngine().evaluate(1, 2, checklist_results=[checklist()]).overall == "INCONCLUSIVO"
    assert VerdictEngine().evaluate(1, 2).overall == "INCONCLUSIVO"


def test_risco_e_pendencia_preservam_prioridade_do_risco():
    assert VerdictEngine().evaluate(1, 2, risks=[risk("CRITICA")], checklist_results=[checklist()], evidence_ids=[8]).overall == "DESFAVORAVEL"
    assert VerdictEngine().evaluate(1, 2, risks=[risk("ALTA")], checklist_results=[checklist()], evidence_ids=[8]).overall == "ATENCAO"


def test_ids_financeiro_pendencias_e_versionamento_sao_preservados():
    result = VerdictEngine().evaluate(
        property_id=7,
        analysis_version=12,
        risks=[risk("ALTA", risk_id=3, evidence_id=10)],
        evidence_ids=[10, 11, 11],
        pending_items=["pendência formal"],
        financial={"custo_total": 100, "pendencias": ["preço máximo pendente"]},
    )
    assert result.property_id == 7
    assert result.analysis_version == 12
    assert result.risk_ids == [3]
    assert result.evidence_ids == [10, 11]
    assert result.pending_items == ["pendência formal", "preço máximo pendente"]
    assert result.financial["custo_total"] == 100


def test_nao_aplicavel_e_risco_inativo_nao_degradam_veredito():
    result = VerdictEngine().evaluate(1, 2, risks=[risk("CRITICA", status="INATIVO")], checklist_results=[checklist("NAO_APLICAVEL", applicable=False)], evidence_ids=[8])
    assert result.overall == "FAVORAVEL"


def test_engine_e_deterministico_e_sem_llm_rag():
    import inspect
    from backend.app import verdict_engine
    first = VerdictEngine().evaluate(1, 2, risks=[risk("ALTA")], evidence_ids=[8]).to_dict()
    second = VerdictEngine().evaluate(1, 2, risks=[risk("ALTA")], evidence_ids=[8]).to_dict()
    assert first == second
    source = inspect.getsource(verdict_engine)
    assert "LLM" not in source
    assert "RAG" not in source
    assert "Agent" not in source


def test_create_verdict_persiste_decisao_do_engine_sem_sintese_llm(monkeypatch):
    from backend.app import services

    class ScalarResult:
        def all(self):
            return [models.Risk(id=4, property_id=1, analysis_version=2, severity="CRITICA", evidence_id=9, status="ATIVO")]

    class Db:
        def __init__(self):
            self.added = []
        def scalars(self, statement):
            return ScalarResult()
        def add(self, item):
            self.added.append(item)
        def flush(self):
            pass

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    analysis = models.Analysis(id=10, property_id=1, version=2, evidence_ids=[9])
    monkeypatch.setattr(services, "latest_execution", lambda prop: None)
    monkeypatch.setattr(services, "build_finance", lambda prop: {"custo_total": 100, "pendencias": []})
    verdict = services.create_verdict(Db(), prop, analysis, {"summary": "texto que não decide"})
    assert verdict.overall == "DESFAVORAVEL"
    assert verdict.analysis_version == 2
    assert verdict.risk_ids == [4]
    assert verdict.evidence_ids == [9]
