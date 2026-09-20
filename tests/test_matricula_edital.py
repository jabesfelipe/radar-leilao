from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException
from backend.app import models, schemas

class FakeDb:
    def __init__(self, prop=None, registrations=None, notices=None, history=None):
        self.prop=prop; self.registrations=registrations or []; self.notices=notices or []; self.history=history or []; self.added=[]; self.calls=0
    def get(self, model, identifier): return self.prop
    def add(self,item):
        if isinstance(item,(models.PropertyRegistration,models.AuctionNotice)) and item.id is None: item.id=len([x for x in self.added if isinstance(x,type(item))])+1
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self,item): return None
    def scalars(self,statement):
        class Result:
            def __init__(self,values): self.values=values
            def all(self): return self.values
        self.calls+=1
        if self.calls == 1: return Result(self.registrations if self.registrations else self.notices)
        return Result(self.history)

def prop(): return models.Property(id=1,title="Imóvel Estruturado",address="Rua",city="São Paulo",state="SP")

def test_matricula_completa_evento_historico():
    from backend.app.main import create_registration
    db=FakeDb(prop()); item=create_registration(1,schemas.RegistrationCreate(registration_number="12345",registry_office="1º RI",comarca="São Paulo",consultation_date=date(2026,1,2),holder="Titular",observations="Informado",document_version_id=4,evidence_id=5),db)
    assert item.registration_number=="12345" and item.document_version_id==4 and item.evidence_id==5
    event=next(x for x in db.added if isinstance(x,models.DomainEvent)); history=next(x for x in db.added if isinstance(x,models.EntityHistory))
    assert event.affected_domains==["juridico","checklist"] and history.evidence_id==5

def test_matricula_opcionais_multiplas_e_get_vazio():
    from backend.app.main import create_registration,list_registrations
    db=FakeDb(prop()); create_registration(1,schemas.RegistrationCreate(registration_number="A"),db); create_registration(1,schemas.RegistrationCreate(registration_number="B"),db)
    assert len([x for x in db.added if isinstance(x,models.PropertyRegistration)])==2
    empty=list_registrations(1,FakeDb(prop(),[],[],[])); assert empty["atual"] is None and empty["historico"]==[]

def test_edital_completo_decimal_datas_evento_historico():
    from backend.app.main import create_notice
    db=FakeDb(prop()); item=create_notice(1,schemas.AuctionNoticeCreate(identifier="EDITAL-1",notice_date=date(2026,2,1),auction_stage="2º leilão",appraisal_value=Decimal("300000.50"),minimum_value=Decimal("180000.25"),auction_date=date(2026,3,1),auctioneer="Leiloeiro",observations="Informado",document_version_id=6,evidence_id=7),db)
    assert item.appraisal_value==Decimal("300000.50") and item.auction_date==date(2026,3,1) and item.evidence_id==7
    event=next(x for x in db.added if isinstance(x,models.DomainEvent)); assert event.affected_domains==["documental","juridico","financeiro","checklist"]

def test_edital_opcionais_multiplos_get_vazio():
    from backend.app.main import create_notice,list_notices
    db=FakeDb(prop()); create_notice(1,schemas.AuctionNoticeCreate(identifier="A"),db); create_notice(1,schemas.AuctionNoticeCreate(identifier="B"),db)
    assert len([x for x in db.added if isinstance(x,models.AuctionNotice)])==2
    empty=list_notices(1,FakeDb(prop(),[],[],[])); assert empty["atual"] is None and empty["historico"]==[]

def test_imovel_inexistente():
    from backend.app.main import create_registration,create_notice
    with pytest.raises(HTTPException): create_registration(99,schemas.RegistrationCreate(registration_number="x"),FakeDb(None))
    with pytest.raises(HTTPException): create_notice(99,schemas.AuctionNoticeCreate(identifier="x"),FakeDb(None))
