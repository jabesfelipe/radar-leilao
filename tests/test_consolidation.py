from backend.app.consolidation import consolidate_agent_results


def result(agent, **extra):
    return {"agent": agent, "facts": [], "evidence_ids": [], "pending": [], "llm_used": True, **extra}


def test_consolidacao_com_todos_os_agents_preserva_origem():
    agent_results = [result(agent) for agent in ("documental", "juridico", "financeiro", "mercado", "checklist")]
    consolidated = consolidate_agent_results(
        property_id=1,
        analysis_id=10,
        domains=["documental", "juridico", "financeiro", "mercado", "checklist"],
        agent_results=agent_results,
        evidence_ids=[1, 2, 2],
        retrieved_chunk_ids=[4, 4, 7],
        interpretations=["interpretação documental"],
        pending=["pendência"],
        errors=[],
        llm_used=True,
        model="modelo",
        llm_runs=[{"agent": "financeiro", "status": "CONCLUIDO"}],
    )
    data = consolidated.to_dict()
    assert data["agents_executed"] == ["documental", "juridico", "financeiro", "mercado", "checklist"]
    assert data["agent_results"] == agent_results
    assert data["evidence_ids"] == [1, 2]
    assert data["retrieved_chunk_ids"] == [4, 7]
    assert data["llm_runs"] == [{"agent": "financeiro", "status": "CONCLUIDO"}]
    assert data["analysis_id"] == 10


def test_consolidacao_parcial_preserva_pending_interpretations_e_erros():
    data = consolidate_agent_results(
        property_id=2,
        analysis_id=20,
        domains=["juridico", "mercado"],
        agent_results=[result("juridico", pending=["sem documento"])],
        pending=["sem documento", "sem documento"],
        interpretations=["fato interpretado", "fato interpretado"],
        errors=["falha do mercado"],
        llm_used=False,
    ).to_dict()
    assert data["agents_executed"] == ["juridico"]
    assert data["pending"] == ["sem documento"]
    assert data["interpretations"] == ["fato interpretado"]
    assert data["errors"] == ["falha do mercado"]
    assert data["llm_used"] is False


def test_consolidacao_com_agente_com_erro_nao_descarta_demais_resultados():
    erro = result("juridico", llm_used=False, llm_call={"status": "ERRO"})
    sucesso = result("financeiro", llm_call={"status": "CONCLUIDO"})
    data = consolidate_agent_results(
        property_id=3,
        domains=["juridico", "financeiro"],
        agent_results=[erro, sucesso],
        errors=["falha jurídica"],
        pending=["revisar jurídico"],
        llm_runs=[{"agent": "juridico", "status": "ERRO"}, {"agent": "financeiro", "status": "CONCLUIDO"}],
    ).to_dict()
    assert [item["agent"] for item in data["agent_results"]] == ["juridico", "financeiro"]
    assert data["errors"] == ["falha jurídica"]
    assert len(data["llm_runs"]) == 2


def test_consolidacao_nao_mutaciona_entrada_e_nao_cria_risco_ou_veredito():
    original = [result("mercado", facts=[{"kind": "fato", "statement": "dado"}])]
    snapshot = repr(original)
    data = consolidate_agent_results(agent_results=original).to_dict()
    data["agent_results"][0]["facts"][0]["statement"] = "alterado"
    assert repr(original) == snapshot
    assert "risk" not in data
    assert "verdict" not in data
    assert "risk_candidates" not in data


def test_consolidacao_vazia_e_deterministica():
    first = consolidate_agent_results(property_id=9, analysis_id=11).to_dict()
    second = consolidate_agent_results(property_id=9, analysis_id=11).to_dict()
    assert first == second
    assert first["agents_executed"] == []
    assert first["agent_results"] == []
    assert first["evidence_ids"] == []
