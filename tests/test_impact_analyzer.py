from backend.app.impact import ImpactAnalyzer, SUPPORTED_AGENTS, SUPPORTED_DOMAINS


def analyze(event_type, property_id=17):
    return ImpactAnalyzer().analyze(property_id, event_type, "Aggregate", 42, {"value": "data"})


def test_documento_adicionado_impacta_documental_juridico_checklist():
    result = analyze("DOCUMENTO_ADICIONADO")
    assert result.affected_domains == ["documental", "juridico", "checklist"]
    assert result.recommended_agents == ["documental", "juridico", "checklist"]


def test_documento_versao_adicionada_tem_mesmo_impacto():
    result = analyze("DOCUMENTO_VERSAO_ADICIONADA")
    assert result.affected_domains == ["documental", "juridico", "checklist"]


def test_eventos_estruturados_mapeiam_impactos_existentes():
    assert analyze("PROCESSO_ADICIONADO").affected_domains == ["juridico", "checklist", "financeiro"]
    assert analyze("DIVIDA_ADICIONADA").affected_domains == ["financeiro", "checklist"]
    assert analyze("CUSTO_ADICIONADO").affected_domains == ["financeiro", "checklist"]
    assert analyze("COMPARAVEL_ADICIONADO").affected_domains == ["mercado", "financeiro"]
    assert analyze("MATRICULA_CADASTRADA").affected_domains == ["juridico", "checklist"]
    assert analyze("EDITAL_CADASTRADO").affected_domains == ["documental", "juridico", "financeiro", "checklist"]


def test_ocupacao_nao_inventa_agente_desocupacao():
    result = analyze("OCUPACAO_ATUALIZADA")
    assert result.affected_domains == ["financeiro", "checklist"]
    assert "desocupacao" not in result.recommended_agents


def test_evento_desconhecido_e_controlado():
    result = analyze("EVENTO_NOVO_NAO_CONFIGURADO")
    assert result.affected_domains == []
    assert result.affected_checklist_keys == []
    assert result.recommended_agents == []
    assert result.requires_reanalysis is False
    assert "sem regra" in result.reason.lower()


def test_resultado_preserva_contexto_e_e_deterministico():
    first = ImpactAnalyzer().analyze(99, "DIVIDA_ADICIONADA", "Debt", 12, {"amount": 10})
    second = ImpactAnalyzer().analyze(99, "DIVIDA_ADICIONADA", "Debt", 12, {"amount": 10})
    assert first.to_dict() == second.to_dict()
    assert first.property_id == 99
    assert first.entity_type == "Debt"
    assert first.entity_id == 12
    assert first.affected_checklist_keys == []


def test_componente_nao_depende_de_llm_rag_ou_api_key():
    source = open("backend/app/impact.py", encoding="utf-8").read()
    assert "LLMGateway" not in source
    assert "RAGService" not in source
    assert "OPENAI_API_KEY" not in source
    assert set(SUPPORTED_DOMAINS) == {"documental", "juridico", "financeiro", "mercado", "checklist"}
    assert tuple(SUPPORTED_AGENTS) == SUPPORTED_DOMAINS
