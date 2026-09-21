from types import SimpleNamespace

import pytest

from backend.app.analysis_comparison import AnalysisComparisonService


def analysis(version, domains=None, evidence_ids=None, changes=""):
    return SimpleNamespace(property_id=1, version=version, affected_domains=domains or [], evidence_ids=evidence_ids or [], changes=changes)


def verdict(overall, pending=None):
    return SimpleNamespace(overall=overall, pending_items=pending or [])


def risk(risk_id):
    return SimpleNamespace(id=risk_id)


def test_analises_identicas_nao_tem_evidencias_ou_riscos_adicionados():
    result = AnalysisComparisonService().compare(analysis(1, ["financeiro"], [1, 2], "mesmo"), analysis(2, ["financeiro"], [1, 2], "mesmo"), verdict("FAVORAVEL"), verdict("FAVORAVEL"), [risk(3)], [risk(3)])
    assert result.added_evidence_ids == []
    assert result.removed_evidence_ids == []
    assert result.added_risk_ids == []
    assert result.removed_risk_ids == []
    assert result.changes["changed"] is False


def test_comparacao_detecta_evidencias_riscos_dominios_pendencias_e_veredito():
    result = AnalysisComparisonService().compare(
        analysis(1, ["financeiro", "mercado"], [1, 2], '{"cause": 1}'),
        analysis(2, ["financeiro", "juridico"], [2, 3], '{"cause": 2}'),
        verdict("INCONCLUSIVO", ["pendência antiga", "comum"]),
        verdict("ATENCAO", ["comum", "pendência nova"]),
        [risk(10), risk(11)],
        [risk(11), risk(12)],
    )
    assert result.changed_domains == ["financeiro", "mercado", "juridico"]
    assert result.added_evidence_ids == [3]
    assert result.removed_evidence_ids == [1]
    assert result.added_risk_ids == [12]
    assert result.removed_risk_ids == [10]
    assert result.previous_verdict == "INCONCLUSIVO"
    assert result.current_verdict == "ATENCAO"
    assert result.previous_pending_items == ["pendência antiga", "comum"]
    assert result.current_pending_items == ["comum", "pendência nova"]
    assert result.changes["changed"] is True


def test_comparacao_e_deterministica_e_preserva_analises():
    previous = analysis(4, ["mercado", "financeiro"], [8, 7], "texto")
    current = analysis(5, ["financeiro", "mercado"], [7, 8], "texto")
    first = AnalysisComparisonService().compare(previous, current).to_dict()
    second = AnalysisComparisonService().compare(previous, current).to_dict()
    assert first == second
    assert previous.evidence_ids == [8, 7]
    assert current.affected_domains == ["financeiro", "mercado"]


def test_comparacao_sem_veredito_preserva_ausencia():
    result = AnalysisComparisonService().compare(analysis(1), analysis(2), None, verdict("FAVORAVEL"))
    assert result.previous_verdict is None
    assert result.current_verdict == "FAVORAVEL"
    assert result.previous_pending_items == []


def test_comparacao_rejeita_imoveis_ou_versoes_invalidos():
    with pytest.raises(ValueError):
        AnalysisComparisonService().compare(analysis(1), SimpleNamespace(property_id=2, version=2))
    with pytest.raises(ValueError):
        AnalysisComparisonService().compare(analysis(1), analysis(1))


def test_comparacao_nao_depende_de_llm_ou_rag():
    import inspect
    from backend.app import analysis_comparison
    source = inspect.getsource(analysis_comparison)
    assert "LLMGateway" not in source
    assert "RAGService" not in source
    assert "Agent" not in source
