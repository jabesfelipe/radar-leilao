"""Testes de modalidades (Onda 2 — F1): catálogo canônico, classificação
determinística com evidência, aplicabilidade de checklist por modalidade (27 keys
preservadas) e compatibilidade com legado (INDEFINIDO)."""
from __future__ import annotations

from backend.app import modality_rules as mr
from backend.app.checklist import master_items, CHECKLIST_MASTER


def test_catalogo_canonico_cinco_codigos():
    assert set(mr.MODALITIES) == {
        "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", "EXTRAJUDICIAL_OUTRA_GARANTIA",
        "JUDICIAL", "VENDA_DIRETA", "INDEFINIDO",
    }
    assert "LICITACAO" not in mr.MODALITIES  # decisão de negócio em aberto
    for code in mr.MODALITIES:
        assert code in mr.MODALITY_CATALOG and mr.MODALITY_CATALOG[code]["name"]


def test_normalize_valor_invalido_vira_indefinido():
    assert mr.normalize("qualquer-coisa") == "INDEFINIDO"
    assert mr.normalize(None) == "INDEFINIDO"
    assert mr.normalize("judicial") == "JUDICIAL"


def test_27_canonical_keys_preservadas():
    keys = [k for k, *_ in CHECKLIST_MASTER]
    assert len(keys) == 27 and len(set(keys)) == 27


def test_classificacao_sem_evidencia_permanece_indefinido():
    out = mr.classify_modality(signals_text="execução por alienação fiduciária Lei 9.514", origin=None, has_evidence=False)
    assert out["proposed"] == "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"
    assert out["modality"] == "INDEFINIDO"  # sem evidência não confirma
    assert out["needs_manual_review"] is True


def test_classificacao_com_evidencia_confirma():
    out = mr.classify_modality(signals_text="execução por alienação fiduciária Lei 9.514", origin=None, has_evidence=True)
    assert out["modality"] == "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"
    assert out["confidence"] == "ALTA" and out["needs_manual_review"] is False


def test_classificacao_judicial():
    out = mr.classify_modality(signals_text="Arrematação em hasta pública judicial, processo nº 123", origin="TJ", has_evidence=True)
    assert out["modality"] == "JUDICIAL"


def test_classificacao_sem_sinais():
    out = mr.classify_modality(signals_text="imóvel bonito 2 quartos", origin=None, has_evidence=True)
    assert out["modality"] == "INDEFINIDO" and out["confidence"] == "BAIXA"


def test_aplicabilidade_extrajudicial_vs_judicial():
    # Itens de AF são NAO_APLICAVEL no judicial; preço vil é aplicável no judicial.
    assert mr.checklist_applicability("JUDICIAL", "CONSOLIDACAO_REGISTRADA") == "NAO_APLICAVEL"
    assert mr.checklist_applicability("JUDICIAL", "INTIMACAO_PESSOAL") == "NAO_APLICAVEL"
    assert mr.checklist_applicability("JUDICIAL", "LANCE_MENOR_50_AVALIACAO") == "APLICAVEL"
    # No extrajudicial AF, preço vil é condicional (atenção), não piso.
    assert mr.checklist_applicability("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA", "LANCE_MENOR_50_AVALIACAO") == "CONDICIONAL"


def test_aplicabilidade_indefinido_mantem_tudo():
    all_keys = tuple(k for k, *_ in CHECKLIST_MASTER)
    aplicaveis = mr.applicable_checklist_keys("INDEFINIDO", all_keys)
    assert len(aplicaveis) == 27  # legado: todos aplicáveis


def test_aplicaveis_judicial_reduz_conjunto():
    all_keys = tuple(k for k, *_ in CHECKLIST_MASTER)
    aplicaveis = mr.applicable_checklist_keys("JUDICIAL", all_keys)
    assert "CONSOLIDACAO_REGISTRADA" not in aplicaveis
    assert len(aplicaveis) < 27 and len(aplicaveis) > 0


def test_hard_stops_suprimidos_por_modalidade():
    assert "CONSOLIDACAO_NAO_REGISTRADA" in mr.suppressed_hard_stops("JUDICIAL")
    assert mr.suppressed_hard_stops("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA") == ()


def test_documentos_por_modalidade():
    assert "CONSOLIDACAO" in mr.required_docs("EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA")
    assert "PROCESSO_JUDICIAL" in mr.required_docs("JUDICIAL")
    assert mr.required_docs("INDEFINIDO") == ()
