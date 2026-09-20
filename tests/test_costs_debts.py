from decimal import Decimal
import pytest
from fastapi import HTTPException

from backend.app import models, schemas
from backend.app.services import build_finance

class FakeDb:
    def __init__(self, prop=None, costs=None, debts=None, history=None):
        self.prop=prop; self.costs=costs or []; self.debts=debts or []; self.history=history or []; self.added=[]; self.calls=0
    def get(self, model, identifier): return self.prop
    def add(self, item):
        if isinstance(item, (models.Cost, models.Debt)) and item.id is None: item.id=len([x for x in self.added if isinstance(x, type(item))])+1
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self, item): return None
    def scalars(self, statement):
        class Result:
            def __init__(self, values): self.values=values
            def all(self): return self.values
        self.calls += 1
        return Result(self.costs if self.calls == 1 and self.costs else (self.debts if self.calls == 1 else self.history))

def prop(): return models.Property(id=1, title="Imóvel Financeiro", address="Rua", city="São Paulo", state="SP")

def test_cria_custo_decimal_recorrente_evento_historico():
    from backend.app.main import add_cost
    db=FakeDb(prop()); item=add_cost(1, schemas.CostCreate(category="REFORMA",description="Obra",amount=Decimal("1200.50"),recurring=True), db)
    assert item.amount == Decimal("1200.50") and item.recurring is True
    event=next(x for x in db.added if isinstance(x,models.DomainEvent)); history=next(x for x in db.added if isinstance(x,models.EntityHistory))
    assert event.event_type == "CUSTO_ADICIONADO" and event.affected_domains == ["financeiro","checklist"]
    assert history.entity_type == "Cost"

def test_cria_divida_decimal_evidence_evento_historico():
    from backend.app.main import add_debt
    db=FakeDb(prop()); item=add_debt(1, schemas.DebtCreate(category="IPTU",creditor="Município",amount=Decimal("500.25"),evidence_id=8), db)
    assert item.amount == Decimal("500.25") and item.evidence_id == 8
    event=next(x for x in db.added if isinstance(x,models.DomainEvent)); history=next(x for x in db.added if isinstance(x,models.EntityHistory))
    assert event.event_type == "DIVIDA_ADICIONADA" and event.affected_domains == ["financeiro","checklist"]
    assert history.evidence_id == 8

def test_imovel_inexistente():
    from backend.app.main import add_cost, add_debt
    with pytest.raises(HTTPException): add_cost(99, schemas.CostCreate(category="OUTROS",description="x",amount=1), FakeDb(None))
    with pytest.raises(HTTPException): add_debt(99, schemas.DebtCreate(category="OUTROS",amount=1), FakeDb(None))

def test_multiplos_registros_e_get_vazio():
    from backend.app.main import add_cost, add_debt, list_costs, list_debts
    db=FakeDb(prop()); add_cost(1, schemas.CostCreate(category="ITBI",description="a",amount=Decimal("10")),db); add_cost(1, schemas.CostCreate(category="IPTU",description="b",amount=Decimal("20")),db)
    assert len([x for x in db.added if isinstance(x,models.Cost)]) == 2
    empty=FakeDb(prop(),[],[],[])
    assert list_costs(1,empty)["custos"] == []
    assert list_debts(1,empty)["dividas"] == []

def test_build_finance_consumes_custo_e_divida_preservando_ocupacao():
    p=prop(); p.costs.append(models.Cost(category="REFORMA",description="x",amount=Decimal("2000"))); p.debts.append(models.Debt(category="IPTU",amount=Decimal("500"),status="PENDENTE")); p.occupancy_analyses.append(models.OccupancyAnalysis(status="OCUPADO",estimated_cost=Decimal("300")))
    result=build_finance(p)
    assert result["custos"]["reforma"] == Decimal("2000")
    assert result["custos"]["debitos"] == Decimal("500")
    assert result["custos"]["desocupacao"] == Decimal("300")
