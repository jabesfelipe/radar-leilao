from decimal import Decimal
import pytest
from fastapi import HTTPException

from backend.app import models, schemas
from backend.app.services import build_finance


class FakeDb:
    def __init__(self, prop=None, history=None):
        self.prop = prop
        self.history = history or []
        self.added = []
    def get(self, model, identifier): return self.prop
    def add(self, item):
        if isinstance(item, models.OccupancyAnalysis) and item.id is None:
            item.id = len([x for x in self.added if isinstance(x, models.OccupancyAnalysis)]) + 1
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self, item): return None
    def scalars(self, statement):
        class Result:
            def __init__(self, values): self.values = values
            def all(self): return self.values
        return Result(self.history)


def property_stub():
    return models.Property(id=1, title="Imóvel Ocupação", address="Rua Ocupação", city="São Paulo", state="SP")


@pytest.mark.parametrize("status", ["OCUPADO", "DESOCUPADO", "DESCONHECIDO"])
def test_cria_todos_os_status_de_ocupacao(status):
    from backend.app.main import create_occupancy
    db = FakeDb(property_stub())
    result = create_occupancy(1, schemas.OccupancyCreate(status=status), db)
    assert result.status == status
    assert result.property_id == 1


def test_cria_ocupacao_com_custo_prazo_e_decimal():
    from backend.app.main import create_occupancy
    db = FakeDb(property_stub())
    result = create_occupancy(1, schemas.OccupancyCreate(status="OCUPADO", occupant_profile="Família", estimated_cost=Decimal("12500.50"), estimated_months=8, evidence_id=44), db)
    assert result.estimated_cost == Decimal("12500.50")
    assert result.estimated_months == 8
    event = next(item for item in db.added if isinstance(item, models.DomainEvent))
    assert event.event_type == "OCUPACAO_ATUALIZADA"
    assert event.affected_domains == ["desocupacao", "financeiro", "checklist"]


def test_imovel_inexistente():
    from backend.app.main import create_occupancy
    with pytest.raises(HTTPException) as error:
        create_occupancy(999, schemas.OccupancyCreate(status="DESCONHECIDO"), FakeDb(None))
    assert error.value.status_code == 404


def test_multiplas_atualizacoes_preservam_historico():
    from backend.app.main import get_occupancy
    prop = property_stub()
    first = models.OccupancyAnalysis(id=1, property_id=1, status="OCUPADO", estimated_cost=Decimal("1000"), estimated_months=12)
    second = models.OccupancyAnalysis(id=2, property_id=1, status="DESOCUPADO", estimated_cost=Decimal("2500"), estimated_months=4)
    result = get_occupancy(1, FakeDb(prop, [first, second]))
    assert result["situacao_atual"]["status"] == "DESOCUPADO"
    assert len(result["historico"]) == 2
    assert result["historico"][0]["status"] == "OCUPADO"


def test_build_finance_consume_somente_ultimo_custo_de_ocupacao():
    prop = property_stub()
    prop.occupancy_analyses.append(models.OccupancyAnalysis(id=1, property_id=1, status="OCUPADO", estimated_cost=Decimal("3000"), estimated_months=10))
    result = build_finance(prop)
    assert result["custos"]["desocupacao"] == Decimal("3000")


def test_get_ocupacao_sem_historico():
    from backend.app.main import get_occupancy
    result = get_occupancy(1, FakeDb(property_stub(), []))
    assert result["situacao_atual"] is None
    assert result["ultimo_registro"] is None
    assert result["historico"] == []
