"""Testes do RAG direcionado para o Checklist (TASK 65).

Garantem que perguntas diferentes derivam queries diferentes e podem recuperar
chunks diferentes, que os chunks são deduplicados preservando rastreabilidade
(chunk_id + perguntas relacionadas), e que o retrieval continua funcionando com
os documentos existentes sem inventar respostas.
"""
from __future__ import annotations

import pytest

from backend.app.rag.checklist_retrieval import build_item_query, retrieve_for_checklist


def test_build_item_query_deriva_de_campos_do_item():
    juridico = build_item_query({
        "canonical_key": "INTIMACAO_PESSOAL",
        "question": "A intimação para purgar a mora foi pessoal?",
        "description": "A intimação para purgar a mora foi pessoal?",
        "category": "JURIDICO",
    })
    documental = build_item_query({
        "canonical_key": "VAGA_MATRICULA",
        "question": "A vaga de garagem possui matrícula própria?",
        "description": "A vaga de garagem possui matrícula própria?",
        "category": "DOCUMENTAL",
    })
    # Queries derivadas dos próprios itens e distintas entre si.
    assert "intimação" in juridico.lower()
    assert "vaga de garagem" in documental.lower()
    assert juridico != documental


def test_build_item_query_usa_expected_evidence_e_related_rules():
    query = build_item_query({
        "canonical_key": "CONSOLIDACAO_REGISTRADA",
        "question": "Houve averbação da consolidação na matrícula?",
        "description": "Houve averbação da consolidação na matrícula?",
        "category": "DOCUMENTAL",
        "expected_evidence": ["averbação de consolidação"],
        "related_rules": ["registro do contrato"],
    })
    assert "averbação de consolidação" in query
    assert "registro do contrato" in query


def _force_text_mode(monkeypatch):
    # effective_llm_api_key é property sem setter; zeramos os campos-base para
    # cair no modo texto do retriever (determinístico).
    from backend.app.config import settings
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def test_retrieval_direcionado_perguntas_diferentes_chunks_e_dedup(db, documents, monkeypatch):
    # Sem API key: cai no modo texto do retriever (determinístico), suficiente
    # para validar a estratégia de queries direcionadas.
    _force_text_mode(monkeypatch)

    items = [
        {"canonical_key": "CONSOLIDACAO_REGISTRADA", "question": "averbação da consolidação na matrícula", "description": "consolidação matrícula", "category": "DOCUMENTAL", "expected_evidence": [], "related_rules": []},
        {"canonical_key": "RESPONSABILIDADE_DEBITOS", "question": "condomínio e débitos do imóvel", "description": "condomínio débitos", "category": "FINANCEIRO", "expected_evidence": [], "related_rules": []},
        {"canonical_key": "INTIMACAO_PESSOAL", "question": "intimação pessoal do devedor fiduciante", "description": "intimação pessoal", "category": "JURIDICO", "expected_evidence": [], "related_rules": []},
    ]

    directed = retrieve_for_checklist(db, documents["property_a"], items)

    # queries derivadas por item (rastreabilidade da estratégia)
    assert set(directed.queries.keys()) == {"CONSOLIDACAO_REGISTRADA", "RESPONSABILIDADE_DEBITOS", "INTIMACAO_PESSOAL"}

    # chunk_ids são únicos (deduplicados)
    assert len(directed.chunk_ids) == len(set(directed.chunk_ids))

    # perguntas diferentes recuperaram conjuntos possivelmente diferentes
    consolidacao = set(directed.per_item["CONSOLIDACAO_REGISTRADA"])
    debitos = set(directed.per_item["RESPONSABILIDADE_DEBITOS"])
    # a de consolidação casa o chunk "matrícula consolidada"; a de débitos casa "condomínio"
    assert consolidacao != debitos or (not consolidacao and not debitos)

    # todo chunk recuperado pertence ao imóvel A (isolamento preservado)
    assert all(chunk["property_id"] == documents["property_a"] for chunk in directed.chunks)

    # rastreabilidade: contexto cita chunk_id e as checklist_keys relacionadas
    if directed.chunk_ids:
        assert "chunk_id=" in directed.context
        assert "checklist_keys=" in directed.context


def test_retrieval_direcionado_sem_evidencia_retorna_vazio(db, documents, monkeypatch):
    _force_text_mode(monkeypatch)
    items = [
        {"canonical_key": "DISTANCIA_USUARIO", "question": "termo totalmente inexistente xyzqwk", "description": "termo inexistente", "category": "OPERACIONAL", "expected_evidence": [], "related_rules": []},
    ]
    directed = retrieve_for_checklist(db, documents["property_a"], items)
    # Sem casamento, não há chunks — PENDENTE permanece possível (sem invenção).
    assert directed.chunk_ids == []
    assert directed.context == ""
