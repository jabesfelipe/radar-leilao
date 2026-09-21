from datetime import date
from decimal import Decimal
import pytest
from backend.app import models
from backend.app.ai.contracts import AgentResponse
from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app.extraction import RegistrationExtraction, NoticeExtraction, extract_document, persist_extraction

class FakeProvider:
    def __init__(self, content): self.content=content
    def structured_chat(self, schema, messages, **kwargs): return ProviderResponse(content=self.content, input_tokens=10, output_tokens=5, request_id="extract-1")
    def chat(self,*args,**kwargs): return ProviderResponse(content="")
    def embed(self,texts): return []
class FakeDb:
    def __init__(self, version): self.version=version; self.added=[]; self.prop=models.Property(id=1,title="Teste",address="Rua",city="São Paulo",state="SP")
    def get(self, model, identifier):
        if model is models.DocumentVersion: return self.version
        if model is models.Property: return self.prop
        return None
    def add(self,item):
        if isinstance(item,(models.PropertyRegistration,models.AuctionNotice,models.Evidence,models.EvidenceLink,models.DomainEvent,models.EntityHistory)) and getattr(item,"id",None) is None: item.id=len([x for x in self.added if type(x) is type(item)])+1
        self.added.append(item)
    def flush(self): pass

def version_for(property_id=1):
    document=models.Document(id=2,property_id=property_id,name="doc.txt",document_type="MATRICULA")
    return models.DocumentVersion(id=3,document_id=2,version=1,content_hash="a"*64,original_path="doc.txt",document=document)

def fake_rag(monkeypatch):
    class Retrieval:
        context="[chunk_id=9] Matrícula 123"
        chunks=[{"chunk_id":9,"page":2,"section":"AV-1","content":"Matrícula 123"}]
    class FakeRag:
        def __init__(self, db): pass
        def retrieve_context(self,*args,**kwargs): return Retrieval()
    monkeypatch.setattr("backend.app.extraction.RAGService", FakeRag)

def test_extrai_matricula_estruturada(monkeypatch):
    fake_rag(monkeypatch); output=RegistrationExtraction(registration_number="123",registry_office="RI",references=[{"field":"registration_number","value":"123","chunk_id":9,"page":2},{"field":"registry_office","value":"RI","chunk_id":9,"page":2}])
    result=extract_document(FakeDb(version_for()),1,3,"MATRICULA",LLMGateway(FakeProvider(output),"fake","modelo"))
    assert result.success and result.output.registration_number=="123" and result.call.input_tokens==10

def test_extrai_edital_com_decimais_e_datas():
    output=NoticeExtraction(identifier="E-1",appraisal_value=Decimal("300.50"),notice_date=date(2026,1,1),references=[])
    class Retrieval:
        context="edital"; chunks=[]
    class FakeRag:
        def __init__(self,db): pass
        def retrieve_context(self,*args,**kwargs): return Retrieval()
    import backend.app.extraction as module
    original=module.RAGService; module.RAGService=FakeRag
    try:
        result=extract_document(FakeDb(version_for()),1,3,"EDITAL",LLMGateway(FakeProvider(output),"fake","modelo"))
        assert result.output.appraisal_value==Decimal("300.50") and result.output.notice_date==date(2026,1,1)
    finally: module.RAGService=original

def test_resposta_invalida_e_campo_ausente():
    fake_rag(pytest.MonkeyPatch()); output={"registration_number": {"valor_invalido": True}}
    result=extract_document(FakeDb(version_for()),1,3,"MATRICULA",LLMGateway(FakeProvider(output),"fake","modelo"))
    assert result.call.status=="ERRO"

def test_sem_api_key_retorna_sem_chave(monkeypatch):
    fake_rag(monkeypatch); monkeypatch.setattr("backend.app.extraction.build_gateway", lambda: (_ for _ in ()).throw(RuntimeError("sem chave")))
    result=extract_document(FakeDb(version_for()),1,3,"MATRICULA")
    assert result.call.status=="SEM_CHAVE"

def test_isolamento_document_version():
    with pytest.raises(ValueError): extract_document(FakeDb(version_for(2)),1,3,"MATRICULA")

def test_persistencia_cria_registro_e_evidencia_rastreavel(monkeypatch):
    version=version_for(); db=FakeDb(version); prop=models.Property(id=1,title="x",address="a",city="c",state="SP")
    result=type("Result",(),{"document_type":"MATRICULA","document_version_id":3,"output":RegistrationExtraction(registration_number="123",references=[{"field":"registration_number","value":"123","chunk_id":None,"page":2}])})()
    item,evidence_ids=persist_extraction(db,prop,result)
    assert item.registration_number=="123" and len(evidence_ids)==1
    assert any(isinstance(value,models.EvidenceLink) for value in db.added)


def test_campo_preenchido_com_referencia_correspondente_sucesso(monkeypatch):
    fake_rag(monkeypatch)
    output = RegistrationExtraction(registration_number="123456", references=[{"field":"registration_number","value":"123456"}])
    result = extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(FakeProvider(output), "fake", "modelo"))
    assert result.success is True


def test_campo_preenchido_sem_referencia_retorna_erro(monkeypatch):
    fake_rag(monkeypatch)
    output = RegistrationExtraction(registration_number="123456", references=[])
    result = extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(FakeProvider(output), "fake", "modelo"))
    assert result.success is False
    assert result.call.status == "ERRO"
    assert "registration_number" in (result.call.error_message or "")


def test_campo_nulo_sem_referencia_e_permitido(monkeypatch):
    fake_rag(monkeypatch)
    output = RegistrationExtraction(registration_number=None, registry_office=None, references=[])
    result = extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(FakeProvider(output), "fake", "modelo"))
    assert result.success is True
