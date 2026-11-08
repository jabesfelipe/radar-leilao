"""Central de Débitos/Despesas — serviço de domínio (Etapa A).

Determinístico, sem LLM e SEM consulta externa (coletores/scraping são etapas
futuras). Responsabilidades desta etapa:
  - seed idempotente do catálogo de tipos de débito e dos municípios de cobertura
    inicial (Curitiba, São José dos Pinhais, Fazenda Rio Grande, Assis) — como DADO,
    nunca em condicionais no backend;
  - normalização/validação de um ``PropertyDebt`` (separa original × atualizado;
    marca natureza/status/confiabilidade; ESTIMADO nunca vira CONFIRMADO);
  - consolidação por NATUREZA (totais separados; nunca soma naturezas diferentes),
    combinando o legado (``Debt``) com os débitos normalizados, SEM dupla contagem.

Não altera ``Debt``/``Cost`` nem ``build_finance``: a consolidação é LEITURA.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models

ZERO = Decimal("0")

# Catálogo inicial de tipos (seed idempotente; administrável depois). canonical_cost_key
# mapeia para finance.COST_KEYS quando impacta o financeiro.
DEBT_TYPE_SEED: tuple[dict[str, Any], ...] = (
    # Municipais
    {"code": "IPTU", "label": "IPTU", "group": "MUNICIPAL", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "iptu"},
    {"code": "TAXA_MUNICIPAL", "label": "Taxa municipal", "group": "MUNICIPAL", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "debitos"},
    {"code": "DIVIDA_ATIVA_MUNICIPAL", "label": "Dívida ativa municipal", "group": "MUNICIPAL", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "debitos"},
    {"code": "OUTRO_DEBITO_MUNICIPAL", "label": "Outro débito municipal", "group": "MUNICIPAL", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "debitos"},
    # Condomínio
    {"code": "COTA_CONDOMINIAL", "label": "Cota condominial", "group": "CONDOMINIO", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "condominio"},
    {"code": "MULTA_CONDOMINIAL", "label": "Multa condominial", "group": "CONDOMINIO", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "condominio"},
    {"code": "JUROS_CONDOMINIAIS", "label": "Juros condominiais", "group": "CONDOMINIO", "default_nature": "DIVIDA_EXISTENTE", "canonical_cost_key": "condominio"},
    {"code": "DESPESA_EXTRAORDINARIA", "label": "Despesa extraordinária", "group": "CONDOMINIO", "default_nature": "OBRIGACAO_POTENCIAL", "canonical_cost_key": "condominio"},
    # Concessionárias (por padrão dívida pessoal do ocupante; não do imóvel)
    {"code": "AGUA", "label": "Água", "group": "CONCESSIONARIA", "default_nature": "OBRIGACAO_POTENCIAL", "canonical_cost_key": None, "impacts_finance": False},
    {"code": "ENERGIA", "label": "Energia", "group": "CONCESSIONARIA", "default_nature": "OBRIGACAO_POTENCIAL", "canonical_cost_key": None, "impacts_finance": False},
    {"code": "GAS", "label": "Gás", "group": "CONCESSIONARIA", "default_nature": "OBRIGACAO_POTENCIAL", "canonical_cost_key": None, "impacts_finance": False},
    {"code": "OUTRA_CONCESSIONARIA", "label": "Outra concessionária", "group": "CONCESSIONARIA", "default_nature": "OBRIGACAO_POTENCIAL", "canonical_cost_key": None, "impacts_finance": False},
    # Aquisição/regularização (custo, não "dívida")
    {"code": "ITBI", "label": "ITBI", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "itbi"},
    {"code": "CARTORIO", "label": "Cartório", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "registro"},
    {"code": "REGISTRO", "label": "Registro", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "registro"},
    {"code": "AVERBACAO", "label": "Averbação", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "registro"},
    {"code": "REGULARIZACAO", "label": "Regularização", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "outros"},
    {"code": "REFORMA", "label": "Reforma", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "reforma"},
    {"code": "DESOCUPACAO", "label": "Desocupação", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "desocupacao"},
    {"code": "OUTRA_DESPESA", "label": "Outra despesa", "group": "AQUISICAO_REGULARIZACAO", "default_nature": "CUSTO_AQUISICAO", "canonical_cost_key": "outros"},
)

# Municípios de cobertura inicial (dado; nunca lista fixa em condicional de regra).
MUNICIPALITY_SEED: tuple[dict[str, Any], ...] = (
    {"name": "Curitiba", "state": "PR", "ibge_code": "4106902", "coverage_active": True},
    {"name": "São José dos Pinhais", "state": "PR", "ibge_code": "4125506", "coverage_active": True},
    {"name": "Fazenda Rio Grande", "state": "PR", "ibge_code": "4107652", "coverage_active": True},
    {"name": "Assis", "state": "SP", "ibge_code": "3504008", "coverage_active": True},
)


def seed_debt_types(db: Session) -> int:
    """Materializa o catálogo de tipos (upsert por code; idempotente). Retorna nº criados."""
    created = 0
    for row in DEBT_TYPE_SEED:
        exists = db.scalar(select(models.DebtType).where(models.DebtType.code == row["code"]))
        if exists is not None:
            continue
        db.add(models.DebtType(
            code=row["code"], label=row["label"], group=row["group"],
            default_nature=row.get("default_nature", "DIVIDA_EXISTENTE"),
            canonical_cost_key=row.get("canonical_cost_key"),
            impacts_finance=row.get("impacts_finance", True),
        ))
        created += 1
    db.flush()
    return created


def seed_municipalities(db: Session) -> int:
    """Cadastra os municípios de cobertura inicial (idempotente por name+state)."""
    created = 0
    for row in MUNICIPALITY_SEED:
        exists = db.scalar(
            select(models.Municipality).where(
                models.Municipality.name == row["name"], models.Municipality.state == row["state"]
            )
        )
        if exists is not None:
            continue
        db.add(models.Municipality(
            name=row["name"], state=row["state"], ibge_code=row.get("ibge_code"),
            coverage_active=row.get("coverage_active", False),
        ))
        created += 1
    db.flush()
    return created


def seed_all(db: Session) -> dict[str, int]:
    """Seed idempotente de catálogo + municípios + cobertura inicial (Etapa B).

    A cobertura é semeada por último (depende de municípios e tipos existentes)."""
    from . import coverage_service  # import local evita ciclo de importação
    types = seed_debt_types(db)
    munis = seed_municipalities(db)
    coverage = coverage_service.seed_coverage(db)
    return {"debt_types": types, "municipalities": munis, "coverage": coverage}


def normalize_debt_payload(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """Valida e normaliza os campos de um PropertyDebt antes de persistir.

    Regras: tipo deve existir no catálogo; natureza default vem do tipo quando ausente;
    status/confiabilidade dentro do vocabulário; ESTIMADO ⇒ confiabilidade ESTIMADO (não
    OFICIAL); valor_atualizado nunca é inferido silenciosamente (fica None se ausente)."""
    code = data.get("debt_type_code")
    debt_type = db.scalar(select(models.DebtType).where(models.DebtType.code == code)) if code else None
    if debt_type is None:
        raise ValueError(f"Tipo de débito desconhecido: {code!r}. Cadastre em debt_types.")

    nature = (data.get("nature") or debt_type.default_nature).upper()
    if nature not in models.DEBT_NATURES:
        raise ValueError(f"Natureza inválida: {nature}")
    status = (data.get("status") or "PENDENTE").upper()
    if status not in models.DEBT_STATUSES:
        raise ValueError(f"Status inválido: {status}")
    reliability = (data.get("reliability") or "NAO_VERIFICADO").upper()
    if reliability not in models.DEBT_RELIABILITIES:
        raise ValueError(f"Confiabilidade inválida: {reliability}")
    # Invariante: um ESTIMADO não pode se apresentar como OFICIAL/DOCUMENTAL.
    if status == "ESTIMADO" and reliability in {"OFICIAL", "DOCUMENTAL"}:
        reliability = "ESTIMADO"

    out = dict(data)
    out["nature"] = nature
    out["status"] = status
    out["reliability"] = reliability
    return out


def _amount_for_total(debt: "models.PropertyDebt") -> Decimal:
    """Valor a considerar no total: atualizado quando houver, senão original. Nunca soma
    os dois (evita dupla contagem do mesmo lançamento)."""
    if debt.updated_amount is not None:
        return debt.updated_amount
    if debt.original_amount is not None:
        return debt.original_amount
    return ZERO


def consolidate(db: Session, property_id: int) -> dict[str, Any]:
    """Consolidação por NATUREZA (totais separados; nunca somados entre si).

    Combina o legado (``Debt``) com os débitos normalizados (``PropertyDebt``) SEM
    dupla contagem: o legado entra como 'confirmado/informado' conforme o status; os
    normalizados entram pela sua natureza. Estimativas NUNCA entram como passivo
    confirmado — vão para o total 'estimado' com ressalva.

    Totais expostos (naturezas diferentes, não somáveis automaticamente):
      - confirmados (dívidas existentes com status CONFIRMADO)
      - informados  (dívidas existentes com status INFORMADO/PENDENTE)
      - estimados   (nature=ESTIMATIVA_OPERACIONAL ou status=ESTIMADO)
      - despesas_previstas (nature=CUSTO_AQUISICAO)
      - nao_apurados (INDISPONIVEL/EM_VALIDACAO/sem valor)
    """
    normalized = db.scalars(select(models.PropertyDebt).where(models.PropertyDebt.property_id == property_id)).all()
    legacy = db.scalars(select(models.Debt).where(models.Debt.property_id == property_id)).all()

    tot = {"confirmados": ZERO, "informados": ZERO, "estimados": ZERO, "despesas_previstas": ZERO, "nao_apurados": ZERO}
    counts = {k: 0 for k in tot}

    for d in normalized:
        valor = _amount_for_total(d)
        if d.status in {"QUITADO", "CANCELADO"}:
            continue
        if d.status in {"INDISPONIVEL", "EM_VALIDACAO"} or (d.original_amount is None and d.updated_amount is None):
            tot["nao_apurados"] += ZERO; counts["nao_apurados"] += 1; continue
        if d.nature == "ESTIMATIVA_OPERACIONAL" or d.status == "ESTIMADO":
            tot["estimados"] += valor; counts["estimados"] += 1
        elif d.nature == "CUSTO_AQUISICAO":
            tot["despesas_previstas"] += valor; counts["despesas_previstas"] += 1
        elif d.status == "CONFIRMADO":
            tot["confirmados"] += valor; counts["confirmados"] += 1
        else:  # INFORMADO/PENDENTE e demais dívidas existentes
            tot["informados"] += valor; counts["informados"] += 1

    # Legado (Debt): entra sem dupla contagem (fonte distinta do PropertyDebt). Status
    # QUITADO fora; CONFIRMADO/PAGO? -> o Debt legado usa strings livres; mapeamos
    # conservadoramente: QUITADO/CANCELADO/PAGO fora; CONFIRMADO -> confirmados; resto -> informados.
    for d in legacy:
        status = (d.status or "PENDENTE").upper()
        if status in {"QUITADO", "CANCELADO", "PAGO"}:
            continue
        valor = d.amount or ZERO
        if status in {"ESTIMADO"}:
            tot["estimados"] += valor; counts["estimados"] += 1
        elif status in {"CONFIRMADO"}:
            tot["confirmados"] += valor; counts["confirmados"] += 1
        else:
            tot["informados"] += valor; counts["informados"] += 1

    # Exposição consolidada COM RESSALVA: soma apenas o que é passivo "real" (confirmado
    # + informado) e lista estimado/previsto/não apurado separadamente. Estimativa NUNCA
    # é apresentada como passivo confirmado.
    exposicao_passivo = tot["confirmados"] + tot["informados"]

    return {
        "property_id": property_id,
        "totais": {k: v for k, v in tot.items()},
        "contagens": counts,
        "exposicao_passivo_com_ressalva": exposicao_passivo,
        "ressalvas": [
            "Estimativas não entram como passivo confirmado.",
            "Totais de naturezas diferentes não são somados automaticamente.",
            "Valores não apurados exigem consulta/validação.",
        ],
    }
