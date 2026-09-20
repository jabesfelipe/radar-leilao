from sqlalchemy.orm import Session
from ..rag.service import RAGService
from .graph import build_analysis_graph

class AnalysisOrchestrator:
    def __init__(self, db: Session): self.db = db
    def run(self, property_id: int, domains: list[str], query: str = "") -> dict:
        context, chunk_ids = RAGService(self.db).context_text(query or "análise documental do imóvel", property_id)
        result = build_analysis_graph(self.db).invoke({"property_id": property_id, "domains": domains, "context": context})
        result["retrieved_chunk_ids"] = chunk_ids
        return result
