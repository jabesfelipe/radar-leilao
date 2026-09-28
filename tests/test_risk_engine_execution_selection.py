"""TASK 73.1 — recalculate_risks deve usar a ChecklistExecution da analysis_version
recebida, não uma execução antiga da relationship em memória (stale).

Cenário reproduzido (banco real via fixture ``db``; rollback ao final, nada
persistido; SEM LLM, SEM análise real, SEM V9):

    Property
       ↓  (prop.checklist_executions é CARREGADA antes)
    create_execution(V7)  e  create_execution(V8)  (inseridas por FK property_id)
       ↓  (relationship fica stale — não contém as novas execuções)
    recalculate_risks(db, prop, analysis_version=8)
       ↓
    RiskEngine deve receber EXCLUSIVAMENTE os resultados da execução V8

Antes da correção, recalculate_risks usava latest_execution(prop), que lia a
coleção em memória (stale) e podia entregar uma execução antiga ao RiskEngine.
A correção reutiliza execution_for_version(prop, analysis_version, db=db) (Task 73).

NÃO altera RiskEngine, VerdictEngine, Checklist Master, estados, RAG, LangGraph
nem agentes.
"""
from __future__ import annotations

from backend.app import models, services
from backend.app.risk_engine import RiskEngine


def _property(db):
    prop = models.Property(title="Imóvel T73.1", address="Rua T73.1", city="São Paulo", state="SP", area_m2=70, bedrooms=2)
    db.add(prop)
    db.flush()
    return prop


def test_recalculate_risks_usa_execucao_da_versao_e_ignora_antiga(db, monkeypatch):
    prop = _property(db)

    # 1) Força o carregamento da relationship ANTES de criar novas execuções.
    _ = list(prop.checklist_executions)
    assert _ == []

    # 2) Cria V7 e V8 por FK (property_id) — não entram na coleção já carregada.
    exec_v7 = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version=7)
    exec_v8 = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version=8)

    # relationship continua stale: nenhuma das novas execuções entrou nela.
    assert exec_v7 not in prop.checklist_executions
    assert exec_v8 not in prop.checklist_executions

    # 3) Deixa V7 e V8 distinguíveis: marca 1 item de V8 como RISCO_IDENTIFICADO com
    #    evidência (gera risco). V7 fica tudo PENDENTE (não gera risco).
    alvo_v8 = exec_v8.results[0]
    alvo_v8.state = "RISCO_IDENTIFICADO"
    evidencia = models.Evidence(property_id=prop.id, category="JURIDICO", fact="fato de teste V8", confidence="ALTA")
    db.add(evidencia)
    db.flush()
    db.add(models.ChecklistEvidence(checklist_result_id=alvo_v8.id, evidence_id=evidencia.id))
    db.flush()

    # Espia o que o RiskEngine efetivamente recebe (prova a execução escolhida).
    capturado = {}
    real_evaluate = RiskEngine.evaluate

    def spy_evaluate(self, property_id, checklist_results=()):
        resultados = list(checklist_results)
        capturado["execution_ids"] = {r.execution_id for r in resultados}
        capturado["result_ids"] = {r.id for r in resultados}
        return real_evaluate(self, property_id=property_id, checklist_results=resultados)

    monkeypatch.setattr(RiskEngine, "evaluate", spy_evaluate)

    # 4) Recalcula riscos para a V8.
    persisted = services.recalculate_risks(db, prop, analysis_version=8)

    # RiskEngine recebeu EXCLUSIVAMENTE os resultados da execução V8.
    assert capturado["execution_ids"] == {exec_v8.id}
    assert exec_v7.id not in capturado["execution_ids"]
    assert capturado["result_ids"] == {r.id for r in exec_v8.results}

    # O risco derivado do item RISCO_IDENTIFICADO de V8 foi persistido com V8.
    assert len(persisted) == 1
    assert persisted[0].analysis_version == 8
    assert alvo_v8.item.canonical_key in persisted[0].origin


def test_recalculate_risks_nao_usa_execucao_mais_recente_de_outra_versao(db):
    """Se existe uma execução MAIS NOVA (V9) porém pedimos a V8, o RiskEngine deve
    usar a V8 — nunca a mais recente por incidência."""
    prop = _property(db)
    _ = list(prop.checklist_executions)  # relationship carregada antes

    exec_v8 = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version=8)
    exec_v9 = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version=9)

    # Marca item de V9 como RISCO_IDENTIFICADO com evidência (se a seleção pegasse a
    # execução errada/mais recente, geraria risco). V8 fica sem risco.
    alvo_v9 = exec_v9.results[0]
    alvo_v9.state = "RISCO_IDENTIFICADO"
    evidencia = models.Evidence(property_id=prop.id, category="JURIDICO", fact="fato V9", confidence="ALTA")
    db.add(evidencia)
    db.flush()
    db.add(models.ChecklistEvidence(checklist_result_id=alvo_v9.id, evidence_id=evidencia.id))
    db.flush()

    persisted = services.recalculate_risks(db, prop, analysis_version=8)

    # Como o risco estava na V9 e pedimos a V8, nenhum risco deve ser gerado.
    assert persisted == []
    # sanity: as execuções existem e são distintas
    assert exec_v8.id != exec_v9.id
