from decimal import Decimal
import pytest
from fastapi import HTTPException
from backend.app import models, schemas

class FakeDb:
    def __init__(self, prop=None, evidence=None): self.prop=prop; self.evidence=evidence; self.added=[]
    def get(self, model, identifier):
        if model is models.Evidence: return self.evidence
        if model is models.Property: return self.prop
        return None
    def add(self,item):
        if isinstance(item,(models.Evidence,models.EvidenceLink)) and item.id is None: item.id=len([x for x in self.added if isinstance(x,type(item))])+1
        self.added.append(item)
    def flush(self): return None
    def commit(self): return None
    def refresh(self,item): return None
    def scalars(self,statement):
        class Result:
            def all(self): return []
        return Result()

def prop(): return models.Property(id=1,title="Imóvel Evidência",address="Rua",city="São Paulo",state="SP")

def test_cria_evidencia_com_campos_opcionais_decimal_evento_historico():
    from backend.app.main import create_evidence
    db=FakeDb(prop()); result=create_evidence(1,schemas.EvidenceCreate(category="DOCUMENTAL",fact="Fato registrado",interpretation="Leitura",hypothesis=None,confidence="ALTA",page=2,source_excerpt="trecho"),db)
    assert result.property_id==1 and result.fact=="Fato registrado" and result.confidence=="ALTA"
    event=next(x for x in db.added if isinstance(x,models.DomainEvent)); history=next(x for x in db.added if isinstance(x,models.EntityHistory))
    assert event.event_type=="EVIDENCIA_REGISTRADA" and history.evidence_id==result.id

def test_evidencia_referencia_document_version_e_chunk():
    from backend.app.main import create_evidence
    document=models.Document(id=1,property_id=1,name="doc.txt")
    version=models.DocumentVersion(id=2,document_id=1,version=1,content_hash="a"*64,original_path="doc.txt",document=document)
    chunk=models.DocumentChunk(id=3,document_version_id=2,content="trecho",document_version=version)
    db=FakeDb(prop()); db.get=lambda model,identifier: version if model is models.DocumentVersion else (chunk if model is models.DocumentChunk else db.prop)
    result=create_evidence(1,schemas.EvidenceCreate(fact="Fato",document_version_id=2,chunk_id=3),db)
    assert result.document_version_id==2 and result.chunk_id==3

def test_evidence_get_individual_e_links_isolado():
    from backend.app.main import get_evidence, link_evidence
    evidence=models.Evidence(id=4,property_id=1,fact="Fato",links=[])
    db=FakeDb(prop(),evidence)
    result=get_evidence(1,4,db)
    assert result["evidencia"] is evidence and result["links"] == []
    link=link_evidence(1,4,schemas.EvidenceLinkCreate(target_type="LegalProcess",target_id=10,relation="SUSTENTA"),db)
    assert link.evidence_id==4 and link.target_type=="LegalProcess"
    assert any(isinstance(item,models.DomainEvent) and item.event_type=="EVIDENCIA_VINCULADA" for item in db.added)

def test_evidence_inexistente_ou_de_outro_imovel():
    from backend.app.main import get_evidence, link_evidence
    foreign=models.Evidence(id=8,property_id=2,fact="Outro")
    db=FakeDb(prop(),foreign)
    with pytest.raises(HTTPException) as error: get_evidence(1,8,db)
    assert error.value.status_code==404
    with pytest.raises(HTTPException) as error: link_evidence(1,8,schemas.EvidenceLinkCreate(target_type="Cost",target_id=1),db)
    assert error.value.status_code==404

def test_lista_evidencia_vazia():
    from backend.app.main import list_evidence
    assert list_evidence(1,FakeDb(prop())) == []
