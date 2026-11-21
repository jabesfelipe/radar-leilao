"""Router do Resumo do investimento e dos riscos consolidados (v1.0.14). Somente leitura: não dispara análise, LLM nem consulta externa."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import checklist_priority, document_status, investment_summary, market_research, risk_presenter
from ..search import service as search_service
from ..database import get_db
from ..services import current_auction, serialize
from .deps import property_or_404

router = APIRouter(tags=["investimento"])


class ResearchRequest(BaseModel):
    tipos: list[str] | None = None   # VENDA, ALUGUEL, CONDOMINIO, IPTU_PORTAL (vazio = todos)


@router.get("/api/imoveis/{property_id}/resumo-investimento")
def get_investment_summary(property_id: int, db: Session = Depends(get_db)):
    """Resposta do Resumo: arrematar?, preço máximo, lucro, ROI, margem, principal risco, pendências, IPTU, condomínio, mercado,
    Financeiro por natureza e riscos consolidados. Cada número traz o tipo de dado (fato, dado manual, estimativa, inferência, desconhecido)."""
    prop = property_or_404(db, property_id)
    return serialize(investment_summary.summary(db, prop))


@router.get("/api/imoveis/{property_id}/riscos-consolidados")
def get_consolidated_risks(property_id: int, db: Session = Depends(get_db)):
    """Riscos em linguagem simples: um por assunto, no estado mais recente, com o que fazer. Sem códigos internos."""
    from ..viability import market_intelligence
    prop = property_or_404(db, property_id)
    lines = market_intelligence(db, prop).get("custos") or []
    return serialize({"property_id": property_id, **risk_presenter.for_property(db, prop, cost_lines=lines)})


@router.get("/api/imoveis/{property_id}/iptu/situacao")
def get_iptu_status(property_id: int, db: Session = Depends(get_db)):
    """Situação do IPTU (consultado, consulta assistida, pendente, não encontrado, falha ou necessita informação) e para onde o valor vai."""
    from ..viability import market_intelligence
    prop = property_or_404(db, property_id)
    auction = current_auction(prop)
    assumptions = (getattr(auction, "financial_assumptions", None) or {}) if auction else {}
    lines = market_intelligence(db, prop).get("custos") or []
    out = investment_summary.iptu_status(db, prop, assumptions, lines)
    if out.get("portal") is None:
        out["portal_pesquisado"] = market_research.history(db, property_id, limit=20)["portais_iptu"]
    return serialize({"property_id": property_id, **out})


@router.get("/api/pesquisa/provedores")
def get_search_providers():
    """Situação dos provedores de pesquisa externa (principal e alternativo), sem expor chave."""
    return search_service.status()


@router.get("/api/imoveis/{property_id}/pesquisa-automatica")
def get_research_history(property_id: int, db: Session = Depends(get_db)):
    """Consultas externas já feitas para o imóvel: provedor, status, data, validade do cache e resultados (URL, título, data)."""
    property_or_404(db, property_id)
    return serialize(market_research.history(db, property_id))


@router.post("/api/imoveis/{property_id}/pesquisa-automatica")
def run_research(property_id: int, data: ResearchRequest | None = None, db: Session = Depends(get_db)):
    """Pesquisa venda, aluguel, condomínio e portal do IPTU deste imóvel (um imóvel por chamada; cache evita repetir).
    Anúncios utilizáveis viram comparáveis com fonte, URL e data. Sem provedor configurado: NAO_CONFIGURADO, nada é gravado."""
    prop = property_or_404(db, property_id)
    kinds = tuple(k for k in (data.tipos if data and data.tipos else market_research.KINDS) if k in market_research.KINDS)
    out = market_research.run(db, prop, kinds=kinds or market_research.KINDS)
    db.commit()
    return serialize({"property_id": property_id, **out})


@router.get("/api/imoveis/{property_id}/checklist-prioritario")
def get_prioritized_checklist(property_id: int, db: Session = Depends(get_db)):
    """Checklist ordenado por prioridade (P0 bloqueadores a P3 complementares), com explicação, próxima ação e responsável."""
    prop = property_or_404(db, property_id)
    return serialize(checklist_priority.for_property(prop))


@router.get("/api/imoveis/{property_id}/documentos/situacao")
def get_document_situation(property_id: int, db: Session = Depends(get_db)):
    """Situação documental: recebidos, analisados, obrigatórios, pendentes, incompletos, evidências e próximas ações."""
    prop = property_or_404(db, property_id)
    return serialize({"property_id": property_id, **document_status.for_property(db, prop)})
