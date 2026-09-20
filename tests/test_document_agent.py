from backend.app import models
from backend.app.ai.agents import DocumentAgent
from backend.app.ai.contracts import AgentResponse, Finding
from backend.app.ai.gateway import LLMGateway, ProviderResponse

class Provider:
    def __init__(self, content): self.content=content
    def structured_chat(self, schema, messages, **kwargs): return ProviderResponse(content=self.content, input_tokens=12, output_tokens=6, request_id="doc-run")
    def chat(self,*args,**kwargs): return ProviderResponse(content="")
    def embed(self,texts): return []
class Db:
    def get(self,*args): return None

def test_document_agent_produz_fato_rastreavel():
    response=AgentResponse(findings=[Finding(kind="fato",statement="A matrícula é 123",confidence="ALTA",chunk_ids=[7],page=2,section="AV-1",evidence_excerpt="matrícula 123")])
    result=DocumentAgent(Db(),LLMGateway(Provider(response),"fake","modelo")).run(1,"contexto",[7])
    assert result.llm_used is True
    assert result.facts[0]["kind"]=="fato"
    assert result.facts[0]["chunk_ids"]==[7]
    assert result.facts[0]["page"]==2
    assert result.llm_call.total_tokens==18

def test_document_agent_sem_gateway_retorna_erro_controlado():
    result=DocumentAgent(Db(),None).run(1,"",[])
    assert result.llm_call.status=="SEM_CHAVE"
    assert result.facts[0]["kind"]=="ausencia"

def test_document_agent_resposta_estruturada_invalida():
    result=DocumentAgent(Db(),LLMGateway(Provider({"findings":[{"statement": {"invalido": True}}]}),"fake","modelo")).run(1,"contexto",[])
    assert result.llm_used is False
    assert result.llm_call.status=="ERRO"


def test_endpoint_document_agent_isolado_por_analysis(monkeypatch):
    from backend.app.main import run_document_agent
    prop=models.Property(id=1,title="Imóvel",address="Rua",city="São Paulo",state="SP")
    analysis=models.Analysis(id=10,property_id=1,version=1,scope="Documental")
    class FakeDb:
        def __init__(self): self.added=[]
        def get(self, model, identifier):
            if model is models.Property: return prop
            if model is models.Analysis: return analysis
            return None
        def add(self,item): self.added.append(item)
        def flush(self): pass
        def commit(self): pass
    class Retrieval:
        context="documento"; chunk_ids=[4]
    class FakeRag:
        def __init__(self,db): pass
        def retrieve_context(self,*args,**kwargs): return Retrieval()
    run=models.LLMRun(id=20)
    monkeypatch.setattr("backend.app.main.RAGService", FakeRag)
    monkeypatch.setattr("backend.app.main.build_gateway", lambda: LLMGateway(Provider(AgentResponse(findings=[Finding(kind="fato",statement="Fato",chunk_ids=[4])])),"fake","modelo"))
    monkeypatch.setattr("backend.app.main.persist_llm_runs", lambda *args: [run])
    monkeypatch.setattr("backend.app.main.persist_agent_findings", lambda *args: [30])
    result=run_document_agent(1,10,FakeDb())
    assert result["status"]=="CONCLUIDO"
    assert result["evidence_ids"]==[30]
    assert result["analysis_id"]==10
