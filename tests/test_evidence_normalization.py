import pytest
from backend.app import models
from backend.app.evidence import normalize_documentary_evidence

class FakeDb:
    def __init__(self, prop, version, chunk=None): self.prop=prop; self.version=version; self.chunk=chunk; self.added=[]
    def get(self, model, identifier):
        if model is models.Property: return self.prop
        if model is models.DocumentVersion: return self.version
        if model is models.DocumentChunk: return self.chunk
        return None
    def add(self,item):
        if getattr(item,"id",None) is None: item.id=len([x for x in self.added if type(x) is type(item)])+1
        self.added.append(item)
    def flush(self): pass

def setup(property_id=1):
    prop=models.Property(id=property_id,title="Imóvel",address="Rua",city="São Paulo",state="SP")
    doc=models.Document(id=2,property_id=property_id,name="doc.txt")
    version=models.DocumentVersion(id=3,document_id=2,version=1,content_hash="a"*64,original_path="doc.txt",document=doc)
    chunk=models.DocumentChunk(id=4,document_version_id=3,content="trecho fonte",page=7,section="AV-1",document_version=version)
    return prop,version,chunk

def test_evidence_documental_valida_com_chunk_e_vinculo():
    prop,version,chunk=setup(); db=FakeDb(prop,version,chunk)
    evidence=normalize_documentary_evidence(db,1,3,"MATRICULA","registro confirmado",confidence="ALTA",chunk_id=4,target_type="PropertyRegistration",target_id=10)
    assert evidence.property_id==1 and evidence.document_version_id==3 and evidence.chunk_id==4
    assert evidence.page==7 and evidence.section=="AV-1" and evidence.source_excerpt=="trecho fonte"
    assert any(isinstance(item,models.EvidenceLink) and item.target_id==10 for item in db.added)
    assert any(isinstance(item,models.DomainEvent) for item in db.added)
    assert any(isinstance(item,models.EntityHistory) for item in db.added)

def test_evidence_sem_chunk_preserva_source_excerpt_informado():
    prop,version,chunk=setup(); db=FakeDb(prop,version,None)
    evidence=normalize_documentary_evidence(db,1,3,"EDITAL","valor informado",source_excerpt="trecho manual",target_type="AuctionNotice",target_id=11)
    assert evidence.chunk_id is None and evidence.source_excerpt=="trecho manual"

def test_isolamento_por_document_version_e_chunk():
    prop,version,chunk=setup(property_id=2); db=FakeDb(prop,version,chunk)
    with pytest.raises(ValueError): normalize_documentary_evidence(db,1,3,"MATRICULA","fato")
    prop,version,chunk=setup(1); foreign_prop,foreign_version,foreign_chunk=setup(2)
    db=FakeDb(prop,version,foreign_chunk)
    with pytest.raises(ValueError): normalize_documentary_evidence(db,1,3,"MATRICULA","fato",chunk_id=4)

def test_evidence_historico_nao_sobrescreve():
    prop,version,chunk=setup(); db=FakeDb(prop,version,chunk)
    normalize_documentary_evidence(db,1,3,"MATRICULA","fato 1")
    normalize_documentary_evidence(db,1,3,"MATRICULA","fato 2")
    evidences=[item for item in db.added if isinstance(item,models.Evidence)]
    assert len(evidences)==2
