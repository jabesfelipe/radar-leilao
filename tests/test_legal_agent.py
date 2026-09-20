from backend.app import models
from backend.app.ai.agents import LegalAgent
from backend.app.ai.contracts import AgentResponse, Finding
from backend.app.ai.gateway import LLMGateway, ProviderResponse


class Provider:
    def __init__(self, content):
        self.content = content
        self.messages = []

    def structured_chat(self, schema, messages, **kwargs):
        self.messages = messages
        return ProviderResponse(content=self.content, input_tokens=20, output_tokens=10, request_id="legal-run")

    def chat(self, *args, **kwargs):
        return ProviderResponse(content="")

    def embed(self, texts):
        return []


class Db:
    def __init__(self, prop=None):
        self.prop = prop

    def get(self, model, identifier):
        if model is models.Property:
            return self.prop
        return None


def test_legal_agent_retorna_fato_juridico_rastreavel():
    response = AgentResponse(findings=[Finding(kind="fato", statement="Há averbação AV-3", confidence="ALTA", checklist_key="MATRICULA_AVERBACOES", checklist_state="RESPONDIDO", chunk_ids=[12], page=4, section="AV-3", evidence_excerpt="AV-3 - averbação")])
    result = LegalAgent(Db(), LLMGateway(Provider(response), "fake", "juridico-modelo")).run(1, "matrícula", [12])
    assert result.agent == "juridico"
    assert result.llm_used is True
    assert result.facts[0]["kind"] == "fato"
    assert result.facts[0]["checklist_key"] == "MATRICULA_AVERBACOES"
    assert result.facts[0]["chunk_ids"] == [12]
    assert result.facts[0]["page"] == 4
    assert result.llm_call.total_tokens == 30


def test_legal_agent_prompt_cobre_escopo_e_limites():
    provider = Provider(AgentResponse(findings=[Finding(kind="hipotese", statement="Pode haver pendência processual", chunk_ids=[3])]))
    LegalAgent(Db(), LLMGateway(provider, "fake", "modelo")).run(1, "contexto jurídico", [3])
    prompt = provider.messages[0]["content"].lower()
    for expected in ("matrícula", "edital", "processos", "movimentações", "checklist_key", "chunk_ids", "hipótese", "não invente", "validade", "nulidade", "veredito de compra", "não calcule preço"):
        assert expected in prompt


def test_legal_agent_inclui_processo_e_movimentacao_no_snapshot():
    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    process = models.LegalProcess(id=7, number="000123", court="TJSP", subject="Cobrança", status="ATIVO")
    process.movements = [models.ProcessMovement(id=8, movement_date=None, description="Despacho publicado", source="Tribunal")]
    prop.processes = [process]
    provider = Provider(AgentResponse(findings=[Finding(kind="fato", statement="Processo ativo cadastrado", chunk_ids=[])]))
    LegalAgent(Db(prop), LLMGateway(provider, "fake", "modelo")).run(1, "", [])
    payload = provider.messages[1]["content"]
    assert "000123" in payload
    assert "Despacho publicado" in payload
    assert "TJSP" in payload


def test_legal_agent_sem_gateway_retorna_erro_controlado():
    result = LegalAgent(Db(), None).run(1, "", [])
    assert result.llm_call.status == "SEM_CHAVE"
    assert result.facts[0]["kind"] == "ausencia"


def test_legal_agent_resposta_estruturada_invalida():
    result = LegalAgent(Db(), LLMGateway(Provider({"findings": [{"statement": {"invalido": True}}]}), "fake", "modelo")).run(1, "", [])
    assert result.llm_used is False
    assert result.llm_call.status == "ERRO"


def test_persistencia_juridica_normaliza_evidence_e_checklist(monkeypatch):
    from backend.app.services import persist_agent_findings

    class FakeDb:
        def __init__(self):
            self.added = []
            self.chunk = models.DocumentChunk(id=4, document_version_id=3, page=2, section="Registro", content="trecho jurídico")
            self.version = models.DocumentVersion(id=3, document_id=8)

        def get(self, model, identifier):
            if model is models.DocumentChunk and identifier == 4:
                return self.chunk
            if model is models.DocumentVersion and identifier == 3:
                return self.version
            return None

        def add(self, item):
            self.added.append(item)

        def flush(self):
            pass

    db = FakeDb()
    prop = models.Property(id=1)
    analysis = models.Analysis(id=10, property_id=1, evidence_ids=[], documents_considered=[])
    item = models.ChecklistItem(id=20, canonical_key="PROCESSO_ATIVO")
    checklist_result = models.ChecklistResult(id=30, item=item, state="PENDENTE", confidence="MEDIA")
    execution = models.ChecklistExecution(results=[checklist_result])
    evidence = models.Evidence(id=99, property_id=1, document_version_id=3, chunk_id=4)
    calls = []

    def normalize(**kwargs):
        calls.append(kwargs)
        return evidence

    monkeypatch.setattr("backend.app.evidence.normalize_documentary_evidence", normalize)
    result = persist_agent_findings(db, prop, analysis, execution, [{"agent": "juridico", "facts": [{"statement": "Processo ativo", "kind": "fato", "chunk_ids": [4], "checklist_key": "PROCESSO_ATIVO", "checklist_state": "RESPONDIDO"}]}])
    assert result == [99]
    assert calls[0]["category"] == "JURIDICO"
    assert calls[0]["target_type"] == "Analysis"
    assert checklist_result.state == "RESPONDIDO"
    assert any(isinstance(item, models.ChecklistEvidence) and item.evidence_id == 99 for item in db.added)
    assert analysis.evidence_ids == [99]


def test_endpoint_legal_agent_isolado_por_analysis_e_rag(monkeypatch):
    from backend.app.main import run_legal_agent

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    analysis = models.Analysis(id=10, property_id=1, version=1, scope="Jurídico", agents_executed=[])

    class FakeDb:
        def __init__(self):
            self.added = []

        def get(self, model, identifier):
            if model is models.Property:
                return prop
            if model is models.Analysis:
                return analysis
            return None

        def add(self, item):
            self.added.append(item)

        def flush(self):
            pass

        def commit(self):
            pass

    class Retrieval:
        context = "matrícula jurídica"
        chunk_ids = [4]

    class FakeRag:
        def __init__(self, db):
            self.filters = None

        def retrieve_context(self, *args, **kwargs):
            self.filters = kwargs["filters"]
            assert kwargs["filters"].property_id == 1
            assert kwargs["filters"].category == "juridico"
            return Retrieval()

    run = models.LLMRun(id=20)
    response = AgentResponse(findings=[Finding(kind="fato", statement="Registro", chunk_ids=[4])])
    monkeypatch.setattr("backend.app.main.RAGService", FakeRag)
    monkeypatch.setattr("backend.app.main.build_gateway", lambda: LLMGateway(Provider(response), "fake", "modelo"))
    monkeypatch.setattr("backend.app.main.persist_llm_runs", lambda *args: [run])
    monkeypatch.setattr("backend.app.main.persist_agent_findings", lambda *args: [30])
    monkeypatch.setattr("backend.app.main.latest_execution", lambda prop: None)
    result = run_legal_agent(1, 10, FakeDb())
    assert result["status"] == "CONCLUIDO"
    assert result["agente"] == "juridico"
    assert result["analysis_id"] == 10
    assert result["evidence_ids"] == [30]
    assert analysis.agents_executed == ["juridico"]
