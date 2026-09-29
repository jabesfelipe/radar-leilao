"""TASK FINAL — contrato do endpoint POST /api/imoveis/{id}/processos/consultar.

Valida (sem rede, serviço mockado):
- indisponibilidade da Judicial API -> 200 com disponivel=false (NÃO bloqueia);
- erro do chamador (4xx da Judicial) -> 502;
- sucesso -> agrega o resumo da consulta;
- ausência total de critério -> 400.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app import models
from backend.app.judicial_client import JudicialApiError, JudicialApiUnavailable
from backend.app.judicial_integration import JudicialConsultResult
from backend.app.main import JudicialConsultRequest, consult_judicial


class FakeDb:
    def __init__(self, prop):
        self.prop = prop
        self.committed = False
        self.rolled_back = False

    def get(self, model, identifier):
        if model is models.Property and self.prop and self.prop.id == identifier:
            return self.prop
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _prop(pid=633):
    return models.Property(id=pid, title="Imóvel", address="Rua", city="Curitiba", state="PR")


def test_criterio_ausente_retorna_400():
    db = FakeDb(_prop())
    with pytest.raises(HTTPException) as exc:
        consult_judicial(633, JudicialConsultRequest(), db)
    assert exc.value.status_code == 400


def test_indisponibilidade_nao_bloqueia(monkeypatch):
    db = FakeDb(_prop())

    def _raise(self, prop, criteria):
        raise JudicialApiUnavailable("timeout")

    monkeypatch.setattr("backend.app.main.JudicialIntegrationService.consult_for_property", _raise)
    out = consult_judicial(633, JudicialConsultRequest(process_number="1"), db)

    assert out["disponivel"] is False
    assert out["status"] == "INDISPONIVEL"
    assert out["processos_criados"] == 0
    assert db.rolled_back is True   # transação revertida
    assert db.committed is False    # nada é comitado numa indisponibilidade


def test_erro_do_chamador_retorna_502(monkeypatch):
    db = FakeDb(_prop())

    def _raise(self, prop, criteria):
        raise JudicialApiError("400 BAD_REQUEST")

    monkeypatch.setattr("backend.app.main.JudicialIntegrationService.consult_for_property", _raise)
    with pytest.raises(HTTPException) as exc:
        consult_judicial(633, JudicialConsultRequest(process_number="1"), db)
    assert exc.value.status_code == 502


def test_sucesso_agrega_resumo(monkeypatch):
    db = FakeDb(_prop())
    resultado = JudicialConsultResult(
        status="COMPLETED", search_id="abc",
        processes_created=2, processes_updated=1, signals_created=3,
        sources=[{"tribunal": "TJPR", "status": "SUCCESS"}], warnings=[], reanalyze={},
    )

    def _ok(self, prop, criteria):
        # confirma que o UF do imóvel é usado como padrão quando não informado
        assert criteria["uf"] == "PR"
        return resultado

    monkeypatch.setattr("backend.app.main.JudicialIntegrationService.consult_for_property", _ok)
    out = consult_judicial(633, JudicialConsultRequest(process_number="1"), db)

    assert out["disponivel"] is True
    assert out["search_id"] == "abc"
    assert out["processos_criados"] == 2
    assert out["processos_atualizados"] == 1
    assert out["sinais_criados"] == 3
    assert db.committed is True
