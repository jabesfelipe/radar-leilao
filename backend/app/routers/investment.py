"""Router do Resumo do investimento e dos riscos consolidados (v1.0.14). Somente leitura: não dispara análise, LLM nem consulta externa."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import investment_summary, risk_presenter
from ..database import get_db
from ..services import current_auction, serialize
from .deps import property_or_404

router = APIRouter(tags=["investimento"])


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
    return serialize({"property_id": property_id, **investment_summary.iptu_status(db, prop, assumptions, lines)})
