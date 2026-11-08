"""Router de Mercado (M0 — modularização).

Leitura determinística do comparativo de mercado do imóvel a partir dos
comparáveis cadastrados. Não dispara análise nem LLM. Contrato preservado.

Etapa D: os limiares de qualidade da amostra (amostra mínima e CV de dispersão)
deixaram de ser hardcoded — são resolvidos no catálogo central de parâmetros
(``parameters.resolve``) e injetados no cálculo. O ``detalhe`` expõe a origem
resolvida (snapshot de auditoria), sem alterar o contrato existente.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import parameters as params
from ..database import get_db
from ..market import calculate_market, MIN_SAMPLE, HIGH_DISPERSION_CV
from .deps import property_or_404

router = APIRouter()


@router.get("/api/imoveis/{property_id}/mercado")
def get_market(property_id: int, db: Session = Depends(get_db)):
    prop = property_or_404(db, property_id)
    comparables = [{"kind": comparable.kind, "price": comparable.price, "rent": comparable.rent, "area_m2": comparable.area_m2} for comparable in prop.comparables]
    # Parâmetros centralizados (Etapa D): resolve com default = valor histórico.
    min_sample = int(params.resolve(db, "mercado.amostra_minima", default=MIN_SAMPLE) or MIN_SAMPLE)
    cv_raw = params.resolve(db, "mercado.cv_dispersao_alta", default=HIGH_DISPERSION_CV)
    high_cv = cv_raw if isinstance(cv_raw, Decimal) else Decimal(str(cv_raw))
    return {
        "property_id": property_id,
        "mercado": calculate_market(comparables, min_sample=min_sample, high_dispersion_cv=high_cv),
    }
