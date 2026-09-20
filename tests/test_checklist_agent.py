import json

import pytest
from fastapi import HTTPException

from backend.app import models
from backend.app.ai.agents import ChecklistAgent
from backend.app.ai.contracts import AgentResponse, Finding
from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app.checklist import CHECKLIST_STATES


class Provider:
    def __init__(self, content):
        self.content = content
        self.messages = []

    def structured_chat(self, schema, messages, **kwargs):
        self.messages = messages
        return ProviderResponse(content=self.content, input_tokens=18, output_tokens=8, request_id="checklist-run")

    def chat(self, *args, **kwargs):
        return ProviderResponse(content="")

    def embed(self, texts):
        return []


class Db:
    def get(self, *args):
        return None


def checklist_context():
    return [{"canonical_key": "EDITAL_LIDO", "question": "O edital foi lido?", "category": "DOCUMENTAL", "active": True, "applicable": True, "item_version": 1}]


def test_checklist_agent_recebe_regras_e_preserva_canonical_key_estado():
    response = AgentResponse(findings=[Finding(kind="fato", statement="O edital foi lido", checklist_key="EDITAL_LIDO", checklist_state="CONFIRMADO", chunk_ids=[4], page=2, section="Edital", evidence_excerpt="trecho")])
    provider = Provider(response)
    result = ChecklistAgent(Db(), LLMGateway(provider, "fake", "checklist-model")).run(1, "evidência", [4], checklist_context())
    payload = json.loads(provider.messages[1]["content"])
    assert result.agent == "checklist"
    assert result.facts[0]["checklist_key"] == "EDITAL_LIDO"
    assert result.facts[0]["checklist_state"] == "CONFIRMADO"
    assert payload["checklist_mestre"][0]["canonical_key"] == "EDITAL_LIDO"
    assert result.llm_call.total_tokens == 26


def test_checklist_agent_prompt_proibe_regra_e_estado_inventados():
    provider = Provider(AgentResponse(findings=[Finding(kind="ausencia", statement="Não há evidência suficiente")]))
    ChecklistAgent(Db(), LLMGateway(provider, "fake", "modelo")).run(1, "", [], checklist_context())
    prompt = provider.messages[0]["content"]
    for expected in ("canonical_key", "Não crie regras", "NAO_APLICAVEL", "evidência suficiente", "chunk_ids"):
        assert expected in prompt
    for state in CHECKLIST_STATES:
        assert state in prompt


def test_checklist_agent_sem_gateway_retorna_ausencia():
    result = ChecklistAgent(Db(), None).run(1, "", [], checklist_context())
    assert result.llm_call.status == "SEM_CHAVE"
    assert result.facts[0]["kind"] == "ausencia"


def test_checklist_agent_resposta_invalida_retorna_erro():
    result = ChecklistAgent(Db(), LLMGateway(Provider({"findings": [{"statement": {"invalido": True}}]}), "fake", "modelo")).run(1, "", [], checklist_context())
    assert result.llm_used is False
    assert result.llm_call.status == "ERRO"


def test_persistencia_checklist_valida_chave_estado_e_evidence(monkeypatch):
    from backend.app.services import persist_checklist_agent_findings

    class FakeDb:
        def __init__(self):
            self.added = []
            self.chunk = models.DocumentChunk(id=4, document_version_id=3, page=2, section="Edital", content="edital lido")
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
    analysis = models.Analysis(id=10, property_id=1, evidence_ids=[])
    item = models.ChecklistItem(id=20, canonical_key="EDITAL_LIDO", question="O edital foi lido?", active=True)
    result = models.ChecklistResult(id=30, item=item, applicable=True, state="PENDENTE", confidence="MEDIA")
    execution = models.ChecklistExecution(id=40, results=[result])
    evidence = models.Evidence(id=99, property_id=1, document_version_id=3, chunk_id=4)
    monkeypatch.setattr("backend.app.evidence.normalize_documentary_evidence", lambda **kwargs: evidence)
    ids = persist_checklist_agent_findings(db, prop, analysis, execution, [{"kind": "fato", "statement": "Edital lido", "confidence": "ALTA", "checklist_key": "EDITAL_LIDO", "checklist_state": "CONFIRMADO", "chunk_ids": [4]}])
    assert ids == [99]
    assert result.state == "CONFIRMADO"
    assert result.answer == "Edital lido"
    assert analysis.evidence_ids == [99]
    assert any(isinstance(item, models.ChecklistEvidence) and item.checklist_result_id == 30 and item.evidence_id == 99 for item in db.added)


def test_persistencia_checklist_rejeita_chave_estado_evidence_ausentes(monkeypatch):
    from backend.app.services import persist_checklist_agent_findings

    class DbWithoutEvidence:
        def get(self, *args):
            return None
        def add(self, item):
            raise AssertionError("não deve persistir sem evidência")
        def flush(self):
            pass

    prop = models.Property(id=1)
    analysis = models.Analysis(id=10, property_id=1, evidence_ids=[])
    item = models.ChecklistItem(id=20, canonical_key="EDITAL_LIDO", question="O edital foi lido?", active=True)
    result = models.ChecklistResult(id=30, item=item, applicable=True, state="PENDENTE", confidence="MEDIA")
    execution = models.ChecklistExecution(id=40, results=[result])
    findings = [
        {"statement": "inventada", "checklist_key": "CHAVE_INEXISTENTE", "checklist_state": "CONFIRMADO", "chunk_ids": [4]},
        {"statement": "estado inventado", "checklist_key": "EDITAL_LIDO", "checklist_state": "RESPONDIDO", "chunk_ids": [4]},
        {"statement": "sem fonte", "checklist_key": "EDITAL_LIDO", "checklist_state": "CONFIRMADO", "chunk_ids": []},
    ]
    assert persist_checklist_agent_findings(DbWithoutEvidence(), prop, analysis, execution, findings) == []
    assert result.state == "PENDENTE"


def test_endpoint_checklist_cria_nova_execucao_e_isola_analysis(monkeypatch):
    from backend.app.main import run_checklist_agent

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    analysis = models.Analysis(id=10, property_id=1, version=3, agents_executed=[])
    item = models.ChecklistItem(id=20, canonical_key="EDITAL_LIDO", question="O edital foi lido?", category="DOCUMENTAL", active=True)
    old_result = models.ChecklistResult(id=12, item=item, state="PENDENTE", applicable=True)
    old_execution = models.ChecklistExecution(id=11, results=[old_result])
    new_result = models.ChecklistResult(id=30, item=item, state="CONFIRMADO", applicable=True, previous_result_id=12)
    new_execution = models.ChecklistExecution(id=21, analysis_version=3, triggered_by="AGENTE_CHECKLIST", results=[new_result])

    class FakeDb:
        def get(self, model, identifier):
            if model is models.Property:
                return prop
            if model is models.Analysis:
                return analysis
            return None
        def add(self, item):
            pass
        def flush(self):
            pass
        def commit(self):
            pass

    class Retrieval:
        context = "evidência do edital"
        chunk_ids = [4]

    class FakeRag:
        def __init__(self, db):
            pass
        def retrieve_context(self, *args, **kwargs):
            assert kwargs["filters"].property_id == 1
            assert kwargs["filters"].category == "checklist"
            return Retrieval()

    response = AgentResponse(findings=[Finding(kind="fato", statement="Edital lido", checklist_key="EDITAL_LIDO", checklist_state="CONFIRMADO", chunk_ids=[4])])
    run = models.LLMRun(id=90)
    monkeypatch.setattr("backend.app.main.latest_execution", lambda prop: old_execution)
    monkeypatch.setattr("backend.app.main.create_execution", lambda *args: new_execution)
    monkeypatch.setattr("backend.app.main.RAGService", FakeRag)
    monkeypatch.setattr("backend.app.main.build_gateway", lambda: LLMGateway(Provider(response), "fake", "modelo"))
    monkeypatch.setattr("backend.app.main.persist_llm_runs", lambda *args: [run])
    monkeypatch.setattr("backend.app.main.persist_checklist_agent_findings", lambda *args: [55])
    result = run_checklist_agent(1, 10, FakeDb())
    assert result["status"] == "CONCLUIDO"
    assert result["execution_id"] == 21
    assert result["evidence_ids"] == [55]
    assert result["checklist"][0]["previous_result_id"] == 12
    assert analysis.agents_executed == ["checklist"]


def test_endpoint_checklist_rejeita_analysis_de_outro_imovel():
    from backend.app.main import run_checklist_agent

    prop = models.Property(id=1, title="Imóvel", address="Rua", city="São Paulo", state="SP")
    other_analysis = models.Analysis(id=10, property_id=2, version=1)

    class FakeDb:
        def get(self, model, identifier):
            if model is models.Property:
                return prop
            if model is models.Analysis:
                return other_analysis
            return None

    with pytest.raises(HTTPException) as error:
        run_checklist_agent(1, 10, FakeDb())
    assert error.value.status_code == 404
