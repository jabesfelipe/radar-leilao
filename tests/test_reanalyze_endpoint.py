"""Testes do gatilho operacional da reanálise incremental (TASK 69).

Cobrem o contrato do endpoint POST /api/imoveis/{property_id}/eventos/{event_id}/reanalisar:
- evento inexistente -> 404;
- evento de outro imóvel -> 404 (padrão da API);
- evento sem reanálise -> analise_executada=False e nenhuma Analysis criada;
- evento com reanálise -> IncrementalAnalysisService.run_for_event é chamado e o
  resultado (analysis_id/versão) é preservado no response.

Não executa LLM real: o serviço é mockado para validar somente o contrato do endpoint.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app import models
from backend.app.main import reanalyze_from_event


class FakeDb:
    """DB mínimo: resolve Property e DomainEvent por id; registra Analysis criadas."""

    def __init__(self, prop=None, event=None):
        self.prop = prop
        self.event = event
        self.added = []

    def get(self, model, identifier):
        if model is models.Property:
            return self.prop if self.prop and self.prop.id == identifier else None
        if model is models.DomainEvent:
            return self.event if self.event and self.event.id == identifier else None
        return None

    def add(self, item):
        self.added.append(item)

    def flush(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


def _prop(pid=633):
    return models.Property(id=pid, title="Imóvel", address="Rua", city="Curitiba", state="PR")


def _event(event_id=10, property_id=633, event_type="DIVIDA_ADICIONADA"):
    return models.DomainEvent(id=event_id, property_id=property_id, event_type=event_type, aggregate_type="Debt", aggregate_id=3, payload={})


def test_evento_inexistente_retorna_404():
    db = FakeDb(prop=_prop(633), event=None)
    with pytest.raises(HTTPException) as exc:
        reanalyze_from_event(633, 999, db)
    assert exc.value.status_code == 404


def test_evento_de_outro_imovel_retorna_404():
    # evento existe, mas pertence a outro imóvel -> 404 (padrão da API)
    db = FakeDb(prop=_prop(633), event=_event(event_id=11, property_id=999))
    with pytest.raises(HTTPException) as exc:
        reanalyze_from_event(633, 11, db)
    assert exc.value.status_code == 404


def test_evento_sem_reanalise_nao_cria_analise(monkeypatch):
    db = FakeDb(prop=_prop(633), event=_event(event_id=12))
    resultado = {"status": "IGNORADO", "evento_id": 12, "impacto": {"requires_reanalysis": False}, "analise_executada": False}
    chamado = {}

    def _fake_run(self, event, query=""):
        chamado["event_id"] = event.id
        return resultado

    monkeypatch.setattr("backend.app.main.IncrementalAnalysisService.run_for_event", _fake_run)
    out = reanalyze_from_event(633, 12, db)

    assert chamado["event_id"] == 12                 # serviço foi chamado com o evento certo
    assert out["analise_executada"] is False
    assert out["status"] == "IGNORADO"
    # nenhuma Analysis criada pelo endpoint (delegação pura)
    assert not any(isinstance(item, models.Analysis) for item in db.added)


def test_evento_com_reanalise_preserva_analysis_id_e_versao(monkeypatch):
    db = FakeDb(prop=_prop(633), event=_event(event_id=13, event_type="DOCUMENTO_VERSAO_ADICIONADA"))
    resultado = {
        "status": "CONCLUIDO",
        "evento_id": 13,
        "analise_executada": True,
        "analysis_id": 280,
        "versao": 9,
        "agentes": ["documental", "financeiro"],
        "veredito": "INCONCLUSIVO",
    }
    chamado = {}

    def _fake_run(self, event, query=""):
        chamado["event_id"] = event.id
        return resultado

    monkeypatch.setattr("backend.app.main.IncrementalAnalysisService.run_for_event", _fake_run)
    out = reanalyze_from_event(633, 13, db)

    assert chamado["event_id"] == 13                 # run_for_event foi chamado
    assert out["analise_executada"] is True
    assert out["analysis_id"] == 280                 # analysis_id preservado no response
    assert out["versao"] == 9                         # versão preservada
    assert out["status"] == "CONCLUIDO"


def test_imovel_inexistente_retorna_404():
    db = FakeDb(prop=None, event=_event())
    with pytest.raises(HTTPException) as exc:
        reanalyze_from_event(633, 10, db)
    assert exc.value.status_code == 404
