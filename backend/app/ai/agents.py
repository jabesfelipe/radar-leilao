import json
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.orm import Session
from .. import models
from ..config import settings
from ..services import build_finance, serialize
from .contracts import AgentResponse
from .gateway import LLMCall, LLMGateway
from .prompts import ANALYSIS_SYSTEM_PROMPT

@dataclass
class AgentResult:
    agent: str
    facts: list[dict[str, Any]]
    evidence_ids: list[int]
    interpretation: str = ""
    pending: list[str] = field(default_factory=list)
    llm_used: bool = False
    model: str | None = None
    llm_call: LLMCall | None = None
    retrieved_chunk_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"agent": self.agent, "facts": self.facts, "evidence_ids": self.evidence_ids, "interpretation": self.interpretation, "pending": self.pending, "llm_used": self.llm_used, "model": self.model, "llm_call": self.llm_call.to_dict() if self.llm_call else None, "retrieved_chunk_ids": self.retrieved_chunk_ids}

class RadarAgent:
    name = "base"
    focus = "análise do imóvel"

    def __init__(self, db: Session, gateway: LLMGateway | None = None):
        self.db = db
        self.gateway = gateway

    def _property_snapshot(self, property_id: int) -> dict[str, Any]:
        prop = self.db.get(models.Property, property_id)
        if not prop: return {}
        return {"id": prop.id, "titulo": prop.title, "endereco": prop.address, "cidade": prop.city, "estado": prop.state, "tipo": prop.property_type, "area_m2": serialize(prop.area_m2), "quartos": prop.bedrooms, "processos": [{"numero": p.number, "assunto": p.subject, "status": p.status, "impacto": p.impact} for p in prop.processes], "comparaveis": [{"tipo": c.kind, "preco": serialize(c.price), "aluguel": serialize(c.rent), "area_m2": serialize(c.area_m2), "fonte": c.source} for c in prop.comparables], "documentos": [{"nome": d.name, "tipo": d.document_type, "status": d.status} for d in prop.documents]}

    def _run_llm(self, property_id: int, context: str, instructions: str, retrieved_chunk_ids: list[int], extra: dict[str, Any] | None = None) -> AgentResult:
        if not self.gateway:
            call = LLMCall.unavailable(settings.llm_provider, settings.llm_model, "LLM não configurada; análise deste domínio aguarda OPENAI_API_KEY")
            return AgentResult(self.name, [{"kind": "ausencia", "statement": call.error_message, "confidence": "BAIXA", "chunk_ids": []}], [], "LLM não configurada", ["Configurar OPENAI_API_KEY para executar a análise interpretativa"], False, call.model, call, retrieved_chunk_ids)
        payload = {"imovel": self._property_snapshot(property_id), "contexto_rag": context, **(extra or {})}
        messages = [{"role": "system", "content": ANALYSIS_SYSTEM_PROMPT + "\nVocê é o agente " + self.name + ". " + instructions + "\nUse somente fatos presentes no contexto ou snapshot. Para cada finding, informe chunk_ids que sustentem a afirmação; se não houver evidência, use kind=ausencia ou hipotese."}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}]
        call = self.gateway.structured_chat(AgentResponse, messages)
        if call.status != "CONCLUIDO":
            return AgentResult(self.name, [], [], "", [call.error_message or "Falha na execução do agente"], False, call.model, call, retrieved_chunk_ids)
        try:
            response = call.content
            parsed = response if isinstance(response, AgentResponse) else AgentResponse.model_validate(response)
            facts = [finding.model_dump() for finding in parsed.findings]
            evidence_ids = [chunk_id for finding in facts for chunk_id in finding.get("chunk_ids", [])]
        except Exception as exc:
            call.status = "ERRO"; call.error_type = type(exc).__name__; call.error_message = str(exc)[:2000]
            return AgentResult(self.name, [], [], "", ["Resposta estruturada inválida"], False, call.model, call, retrieved_chunk_ids)
        return AgentResult(self.name, facts, sorted(set(evidence_ids)), parsed.summary, parsed.pending, True, call.model, call, retrieved_chunk_ids)

    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        raise NotImplementedError

class DocumentAgent(RadarAgent):
    name = "documental"
    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        return self._run_llm(property_id, context, "Interprete edital, matrícula e documentos. Extraia fatos, localização de atos, ausência de informação e riscos documentais.", retrieved_chunk_ids or [])

class LegalAgent(RadarAgent):
    name = "juridico"
    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        return self._run_llm(property_id, context, "Analise registros, consolidação, processos e possíveis riscos jurídicos sem afirmar conclusão legal sem evidência.", retrieved_chunk_ids or [])

class FinancialAgent(RadarAgent):
    name = "financeiro"
    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        prop = self.db.get(models.Property, property_id)
        finance = serialize(build_finance(prop)) if prop else {}
        return self._run_llm(property_id, context, "Interprete os resultados financeiros fornecidos. Não recalcule nem altere os números do motor determinístico.", retrieved_chunk_ids or [], {"financeiro_deterministico": finance})

class MarketAgent(RadarAgent):
    name = "mercado"
    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        return self._run_llm(property_id, context, "Analise comparáveis, liquidez e mercado. Diferencie dado cadastrado de hipótese.", retrieved_chunk_ids or [])

class ChecklistAgent(RadarAgent):
    name = "checklist"
    def run(self, property_id: int, context: str = "", retrieved_chunk_ids: list[int] | None = None) -> AgentResult:
        return self._run_llm(property_id, context, "Relacione evidências às perguntas do Checklist Mestre. Informe checklist_key e checklist_state somente quando houver suporte suficiente.", retrieved_chunk_ids or [])

class Supervisor:
    def __init__(self, db: Session, gateway: LLMGateway | None = None):
        self.db = db
        self.gateway = gateway

    def run(self, property_id: int, domains: list[str], context: str = "", retrieved_chunk_ids: list[int] | None = None) -> list[AgentResult]:
        available = {a.name: a for a in [DocumentAgent(self.db, self.gateway), LegalAgent(self.db, self.gateway), FinancialAgent(self.db, self.gateway), MarketAgent(self.db, self.gateway), ChecklistAgent(self.db, self.gateway)]}
        return [available[name].run(property_id, context, retrieved_chunk_ids) for name in domains if name in available]
