from sqlalchemy.orm import Session
from ..rag.service import RAGService


def buscar_evidencias(db: Session, property_id: int, consulta: str) -> list[dict]:
    """Contrato de ferramenta que pode ser exposto ao LangChain/MCP futuramente."""
    return RAGService(db).retrieve_context(consulta, property_id).chunks
