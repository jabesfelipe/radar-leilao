import json
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.orm import Session
from .. import models
from ..services import build_finance, serialize
from .contracts import AgentResponse
from .gateway import LLMGateway
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

class RadarAgent:
    name = "base"
    focus = "análise do imóvel"

    def __init__(self, db: Session, gateway: LLMGateway | None = None):
        self.db = db
        self.gateway = gateway

    def _property_snapshot(self, property_id: int) -> dict[str, Any]:
        prop = self.db.get(models.Property, property_id)
        if not prop:
            return {}
        return {"id": prop.id, "titulo": prop.title, "endereco": prop.address, "cidade": prop.city, "estado": prop.state, "tipo": prop.property_type, "area_m2": serialize(prop.area_m2), "quartos": prop.bedrooms, "processos": [{"numero": p.number, "assunto": p.subject, "status": p.status, "impacto": p.impact} for p in prop.processes], "comparaveis": [{"tipo": c.kind, "preco": serialize(c.price), "aluguel": serialize(c.rent), "area_m2": serialize(c.area_m2), "fonte": c.source} for c in prop.comparables], "documentos": [{"nome": d.name, "tipo": d.document_type, "status": d.status} for d in prop.documents]}

    def _run_llm(self, property_id: int, context: str, instructions: str, extra: dict[str, Any] | None = None) -> AgentResult:
        if not self.gateway:
            return AgentResult(self.name, [{"kind": "ausencia", "statement": "LLM não configurada; análise deste domínio aguarda OPENAI_API_KEY", "confidence": "BAIXA", "chunk_ids": []}], [], "LLM não configurada", ["Configurar OPENAI_API_KEY para executar a análise interpretativa"], False)
        payload = {"imovel": self._property_snapshot(property_id), "contexto_rag": context, **(extra or {})}
        messages = [{"role": "system", "content": ANALYSIS_SYSTEM_PROMPT + "\nVocê é o agente " + self.name + ". " + instructions + "\nUse somente fatos presentes no contexto ou snapshot. Para cada finding, informe chunk_ids que sustentem a afirmação; se não houver evidência, use kind=ausencia ou hipotese."}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}]
        response = self.gateway.structured_chat(AgentResponse, messages)
        parsed = response if isinstance(response, AgentResponse) else AgentResponse.model_validate(response)
        facts = [finding.model_dump() for finding in parsed.findings]
        evidence_ids = [chunk_id for finding in facts for chunk_id in finding.get("chunk_ids", [])]
        return AgentResult(self.name, facts, sorted(set(evidence_ids)), parsed.summary, parsed.pending, True, self.gateway.model)

    def run(self, property_id: int, context: str = "") -> AgentResult:
        raise NotImplementedError

class DocumentAgent(RadarAgent):
    name = "documental"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return self._run_llm(property_id, context, "Interprete edital, matrícula e documentos. Extraia fatos, localização de atos, ausência de informação e riscos documentais.")

class LegalAgent(RadarAgent):
    name = "juridico"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return self._run_llm(property_id, context, "Analise registros, consolidação, processos e possíveis riscos jurídicos sem afirmar conclusão legal sem evidência.")

class FinancialAgent(RadarAgent):
    name = "financeiro"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        prop = self.db.get(models.Property, property_id)
        finance = serialize(build_finance(prop)) if prop else {}
        return self._run_llm(property_id, context, "Interprete os resultados financeiros fornecidos. Não recalcule nem altere os números do motor determinístico.", {"financeiro_deterministico": finance})

class MarketAgent(RadarAgent):
    name = "mercado"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return self._run_llm(property_id, context, "Analise comparáveis, liquidez e mercado. Diferencie dado cadastrado de hipótese.")

class ChecklistAgent(RadarAgent):
    name = "checklist"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return self._run_llm(property_id, context, "Relacione evidências às perguntas do Checklist Mestre. Informe checklist_key e checklist_state somente quando houver suporte suficiente.")

class Supervisor:
    """Coordena agentes especializados e mantém o provider atrás do gateway."""
    def __init__(self, db: Session, gateway: LLMGateway | None = None):
        self.db = db
        self.gateway = gateway

    def run(self, property_id: int, domains: list[str], context: str = "") -> list[AgentResult]:
        available = {a.name: a for a in [DocumentAgent(self.db, self.gateway), LegalAgent(self.db, self.gateway), FinancialAgent(self.db, self.gateway), MarketAgent(self.db, self.gateway), ChecklistAgent(self.db, self.gateway)]}
        return [available[name].run(property_id, context) for name in domains if name in available]
