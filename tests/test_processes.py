from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException

from backend.app import models, schemas

class FakeDb:
    def __init__(self, prop=None, processes=None, history=None):
        self.prop = prop; self.processes = processes or []; self.history = history or []; self.added = []; self.scalar_calls = 0
    def get(self, model, identifier): return self.prop
    def add(self, item):
        if isinstance(item, models.LegalProcess) and item.id is None:
            item.id = len([x for x in self.added if isinstance(x, models.LegalProcess)]) + 1
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self, item): return None
    def scalars(self, statement):
        class Result:
            def __init__(self, values): self.values = values
            def all(self): return self.values
        self.scalar_calls += 1
        return Result(self.processes if self.scalar_calls == 1 else self.history)

def prop():
    return models.Property(id=1, title="Imóvel Processo", address="Rua Processo", city="São Paulo", state="SP")

def create(data, db):
    from backend.app.main import add_process
    return add_process(1, schemas.ProcessCreate(**data), db)

def test_cria_processo_com_todos_os_campos():
    db = FakeDb(prop())
    process = create({"number":"0001234-56.2026.8.26.0001", "court":"TJSP", "comarca":"São Paulo", "nature":"Ação anulatória", "subject":"Leilão extrajudicial", "status":"Em andamento", "polo_active":"Autor", "polo_passive":"Réu", "distribution_date":date(2026,1,10), "observations":"Cadastro manual", "source":"Consulta manual", "impact":"A avaliar", "evidence_id":9}, db)
    assert process.number == "0001234-56.2026.8.26.0001"
    assert process.comarca == "São Paulo"
    assert process.distribution_date == date(2026,1,10)
    assert process.evidence_id == 9
    event = next(item for item in db.added if isinstance(item, models.DomainEvent))
    assert event.event_type == "PROCESSO_ADICIONADO"
    assert event.affected_domains == ["juridico", "checklist", "financeiro"]
    history = next(item for item in db.added if isinstance(item, models.EntityHistory))
    assert history.entity_type == "LegalProcess"
    assert history.evidence_id == 9

def test_cria_processo_com_opcionais_ausentes():
    process = create({"number":"123"}, FakeDb(prop()))
    assert process.number == "123"
    assert process.court is None
    assert process.evidence_id is None

def test_imovel_inexistente():
    from backend.app.main import add_process
    with pytest.raises(HTTPException) as error:
        add_process(999, schemas.ProcessCreate(number="123"), FakeDb(None))
    assert error.value.status_code == 404

def test_get_sem_processos():
    from backend.app.main import list_processes
    result = list_processes(1, FakeDb(prop(), [], []))
    assert result["processos"] == []
    assert result["historico"] == []

def test_get_com_processos_e_historico():
    from backend.app.main import list_processes
    first = models.LegalProcess(id=1, property_id=1, number="123")
    second = models.LegalProcess(id=2, property_id=1, number="456")
    event = models.EntityHistory(property_id=1, entity_type="LegalProcess", entity_id=1, action="CREATE")
    result = list_processes(1, FakeDb(prop(), [first, second], [event]))
    assert [item.number for item in result["processos"]] == ["123", "456"]
    assert len(result["historico"]) == 1

def test_multiplos_processos_preservam_historico():
    db = FakeDb(prop())
    first = create({"number":"123"}, db)
    second = create({"number":"456"}, db)
    processes = [item for item in db.added if isinstance(item, models.LegalProcess)]
    events = [item for item in db.added if isinstance(item, models.DomainEvent)]
    histories = [item for item in db.added if isinstance(item, models.EntityHistory)]
    assert first.number == "123" and second.number == "456"
    assert len(processes) == 2
    assert len(events) == 2
    assert len(histories) == 2
