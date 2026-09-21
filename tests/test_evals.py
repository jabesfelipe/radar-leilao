import inspect

from backend.app.evals import AgentEvalService


def valid_result():
    return {
        "agent": "documental",
        "facts": [
            {
                "kind": "fato",
                "statement": "A matrícula está no documento.",
                "confidence": "ALTA",
                "chunk_ids": [7],
            }
        ],
        "evidence_ids": [7],
        "interpretation": "",
        "pending": [],
        "llm_used": True,
        "model": "fake-model",
        "llm_call": {"status": "CONCLUIDO"},
        "retrieved_chunk_ids": [7],
    }


def test_eval_result_valido():
    result = AgentEvalService().evaluate(valid_result(), expected_agent="documental", expected_status="CONCLUIDO", evidence_required=True)

    assert result.passed is True
    assert all(result.checks.values())
    assert result.failures == []


def test_resultado_sem_agent_falha_check_de_presenca():
    payload = valid_result()
    payload["agent"] = ""

    result = AgentEvalService().evaluate(payload)

    assert result.passed is False
    assert result.checks["agent_present"] is False
    assert any("agent_present" in failure for failure in result.failures)


def test_resultado_sem_evidencia_quando_exigida_falha():
    payload = valid_result()
    payload["evidence_ids"] = []
    payload["facts"][0]["chunk_ids"] = []

    result = AgentEvalService().evaluate(payload, evidence_required=True)

    assert result.passed is False
    assert result.checks["evidence_traceable"] is False
    assert result.checks["structure_valid"] is True


def test_resultado_com_erro_falha_sem_chamada_externa():
    payload = valid_result()
    payload["llm_used"] = False
    payload["llm_call"] = {"status": "ERRO", "error_message": "provider falhou"}

    result = AgentEvalService().evaluate(payload)

    assert result.passed is False
    assert result.checks["no_unexpected_error"] is False
    assert any("erro inesperado" in failure for failure in result.failures)


def test_resultado_invalido_falha_estrutura_e_finding():
    payload = valid_result()
    payload["facts"] = [{"kind": "inventado", "statement": ""}]
    payload["evidence_ids"] = [0, "7"]
    payload["llm_used"] = "sim"

    result = AgentEvalService().evaluate(payload)

    assert result.passed is False
    assert result.checks["structure_valid"] is False
    assert result.checks["evidence_traceable"] is False
    assert result.checks["findings_traceable"] is False


def test_multiplos_checks_e_status_esperado_sao_reportados():
    payload = valid_result()
    payload["agent"] = "mercado"
    payload["llm_call"] = {"status": "SEM_CHAVE"}

    result = AgentEvalService().evaluate(payload, expected_agent="documental", expected_status="CONCLUIDO", evidence_required=True)

    assert result.passed is False
    assert result.checks["agent_expected"] is False
    assert result.checks["status_expected"] is False
    assert result.checks["no_unexpected_error"] is True
    assert len(result.failures) >= 2


def test_eval_deterministico_para_mesma_entrada():
    service = AgentEvalService()
    first = service.evaluate(valid_result(), expected_agent="documental", evidence_required=True)
    second = service.evaluate(valid_result(), expected_agent="documental", evidence_required=True)

    assert first == second
    assert list(first.checks) == [
        "agent_present",
        "agent_expected",
        "structure_valid",
        "evidence_traceable",
        "findings_traceable",
        "status_expected",
        "no_unexpected_error",
    ]


def test_evaluate_many_agrega_resultados_sem_regras_de_negocio():
    service = AgentEvalService()
    result = service.evaluate_many([valid_result(), valid_result()], expected_agents=["documental", "documental"], evidence_required=True)

    assert result.passed is True
    assert result.checks == {"result_0": True, "result_1": True}


def test_evals_nao_importam_llm_rag_ou_langgraph():
    from backend.app import evals

    source = inspect.getsource(evals)
    assert "LLMGateway" not in source
    assert "RAGService" not in source
    assert "LangGraph" not in source
    assert "langgraph" not in source.lower()
