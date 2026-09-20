from dataclasses import dataclass
from typing import Any
from sqlalchemy.orm import Session

@dataclass
class AgentResult:
    agent: str
    facts: list[dict[str, Any]]
    evidence_ids: list[int]
    interpretation: str = ""

class RadarAgent:
    name = "base"
    def __init__(self, db: Session): self.db = db
    def run(self, property_id: int, context: str = "") -> AgentResult: raise NotImplementedError

class DocumentAgent(RadarAgent):
    name = "documental"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return AgentResult(self.name, [{"tipo": "fato", "descricao": "Contexto documental recuperado", "contexto": context}], [])

class LegalAgent(RadarAgent):
    name = "juridico"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return AgentResult(self.name, [{"tipo": "interpretacao", "descricao": "Processos e matrícula devem ser confirmados por evidências"}], [])

class FinancialAgent(RadarAgent):
    name = "financeiro"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return AgentResult(self.name, [{"tipo": "deterministico", "descricao": "Resultados devem vir do motor financeiro"}], [])

class MarketAgent(RadarAgent):
    name = "mercado"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return AgentResult(self.name, [{"tipo": "fato", "descricao": "Comparáveis cadastrados são o contexto de mercado"}], [])

class ChecklistAgent(RadarAgent):
    name = "checklist"
    def run(self, property_id: int, context: str = "") -> AgentResult:
        return AgentResult(self.name, [{"tipo": "pendencia", "descricao": "Relacionar evidências às regras do Checklist Mestre"}], [])

class Supervisor:
    """Coordena agentes por domínio; não acessa banco fora dos serviços recebidos."""
    def __init__(self, db: Session): self.db = db
    def run(self, property_id: int, domains: list[str], context: str = "") -> list[AgentResult]:
        available = {a.name: a for a in [DocumentAgent(self.db), LegalAgent(self.db), FinancialAgent(self.db), MarketAgent(self.db), ChecklistAgent(self.db)]}
        return [available[name].run(property_id, context) for name in domains if name in available]
