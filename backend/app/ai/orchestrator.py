from __future__ import annotations

from sqlalchemy.orm import Session

from .graph import build_analysis_graph


class AnalysisOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    def run(
        self,
        property_id: int,
        domains: list[str],
        query: str = "",
        gateway_override=None,
        analysis_id: int | None = None,
    ) -> dict:
        return build_analysis_graph(self.db, gateway_override=gateway_override).invoke(
            {
                "property_id": property_id,
                "analysis_id": analysis_id,
                "domains": domains,
                "query": query or "análise documental do imóvel",
            }
        )
