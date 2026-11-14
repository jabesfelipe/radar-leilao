"""Contrato dos agentes (v1.0.4): com function calling (não estrito) variações de forma não derrubam a resposta
inteira; o conteúdo continua sendo validado (citação, chunk do imóvel) na persistência."""
import pytest
from pydantic import ValidationError

from backend.app.ai.contracts import AgentResponse, Finding


def test_source_fora_da_lista_e_normalizado():
    # 1ª execução real v1.0.4: source='mercado_deterministico' derrubou todas as findings do agente de mercado.
    assert Finding(kind="fato", statement="x", source="mercado_deterministico").source == "calculo"
    assert Finding(kind="fato", statement="x", source="financeiro_deterministico").source == "calculo"
    assert Finding(kind="fato", statement="x", source="snapshot do imóvel").source == "cadastro"
    assert Finding(kind="fato", statement="x", source="contexto_rag").source == "documento"
    assert Finding(kind="fato", statement="x", source="opinião").source == "inferencia"
    assert Finding(kind="fato", statement="x", source="").source is None


def test_kind_confianca_chunk_e_pagina_tolerantes():
    f = Finding(kind="Fato", statement="x", confidence="alta", chunk_ids=["3", "abc", 4], page="2")
    assert (f.kind, f.confidence, f.chunk_ids, f.page) == ("fato", "ALTA", [3, 4], 2)
    assert Finding(kind="fact", statement="x", confidence=None, chunk_ids=None, page="?").page is None


def test_conteudo_invalido_continua_rejeitado():
    with pytest.raises(ValidationError):
        Finding(kind="opiniao_livre", statement="x")
    with pytest.raises(ValidationError):
        AgentResponse.model_validate({"findings": [{"kind": "fato", "statement": {"invalido": True}}]})
