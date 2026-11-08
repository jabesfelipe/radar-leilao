"""Estimativa condominial parametrizada (Etapa C) + alertas de idade.

Determinístico, sem LLM. A estimativa é SEMPRE ESTIMADO (nunca passivo confirmado):
calcula três cenários (conservador/provável/otimista), com memória de cálculo,
premissas e grau de confiança. Consome os parâmetros do catálogo central
(``parameters.resolve``) e grava o snapshot dos parâmetros usados
(``parameters.resolve_detail``) para auditoria/imutabilidade.

Separação rigorosa (campos de CONTEXTO, nunca prova de dívida):
idade do imóvel ≠ idade do condomínio ≠ tempo de financiamento ≠ período de
inadimplência. O período de inadimplência é um PARÂMETRO explícito — nunca derivado
da idade do imóvel nem do tempo de financiamento.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from . import models, parameters as params

ZERO = Decimal("0")


class EstimateError(ValueError):
    """Entrada inválida para a estimativa condominial."""


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _json_safe(value: Any) -> Any:
    """Converte Decimal→str recursivamente para persistência em coluna JSON."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def compute_condominium_estimate(
    db: Session,
    *,
    monthly_reference: Decimal | None = None,
    months_delinquent: int | None = None,
    safety_margin_pct: Decimal | None = None,
    municipality_id: int | None = None,
    property_age_years: int | None = None,
    condominium_age_years: int | None = None,
    financing_age_years: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Calcula a estimativa condominial (3 cenários) de forma determinística.

    Qualquer parâmetro ausente é resolvido pelo catálogo central (com precedência por
    município quando informado). Retorna os cenários, a memória de cálculo, o grau de
    confiança e o snapshot dos parâmetros efetivamente usados. NUNCA marca a estimativa
    como passivo confirmado."""
    snapshot: list[dict[str, Any]] = []

    def _resolve(key: str, default: Any) -> Any:
        detail = params.resolve_detail(db, key, municipality_id=municipality_id, default=default, now=now)
        snapshot.append(detail)
        return detail["value"]

    # Período de inadimplência: PARÂMETRO explícito (nunca derivado de idade).
    if months_delinquent is None:
        months_delinquent = int(_resolve("condominio.periodo_presumido_meses", 12) or 12)
    if safety_margin_pct is None:
        safety_margin_pct = _dec(_resolve("condominio.margem_seguranca_pct", Decimal("0.10"))) or Decimal("0.10")
    otimista_factor = _dec(_resolve("condominio.fator_otimista", Decimal("0.70"))) or Decimal("0.70")

    monthly = _dec(monthly_reference)
    monthly_source = "INFORMADO" if monthly is not None else "ESTIMADO"
    if monthly is None:
        # Sem valor de referência informado nem parâmetro: não há base para estimar.
        param_monthly = _resolve("condominio.valor_mensal_referencia", None)
        monthly = _dec(param_monthly)

    memoria: dict[str, Any] = {
        "valor_mensal_referencia": str(monthly) if monthly is not None else None,
        "origem_valor_mensal": monthly_source,
        "meses_inadimplencia_presumidos": months_delinquent,
        "margem_seguranca_pct": str(safety_margin_pct),
        "fator_otimista": str(otimista_factor),
        "formula": "provavel = valor_mensal * meses; conservador = provavel * (1 + margem); otimista = provavel * fator_otimista",
        # Contexto registrado SEPARADAMENTE (não entra no cálculo de dívida):
        "contexto": {
            "idade_imovel_anos": property_age_years,
            "idade_condominio_anos": condominium_age_years,
            "tempo_financiamento_anos": financing_age_years,
            "nota": "Idade do imóvel/condomínio/financiamento são contexto de INCERTEZA, não prova de inadimplência.",
        },
    }

    if monthly is None or months_delinquent is None:
        return {
            "possivel": False,
            "motivo": "Sem valor mensal de referência (informado ou parametrizado): estimativa não calculável.",
            "cenarios": None,
            "confianca": "BAIXA",
            "memoria_calculo": memoria,
            "parametros_usados": snapshot,
            "natureza": "ESTIMATIVA_OPERACIONAL",
            "status": "ESTIMADO",
        }

    meses = Decimal(months_delinquent)
    provavel = (monthly * meses).quantize(Decimal("0.01"))
    conservador = (provavel * (Decimal("1") + safety_margin_pct)).quantize(Decimal("0.01"))
    otimista = (provavel * otimista_factor).quantize(Decimal("0.01"))

    # Grau de confiança: valor informado + sem dispersão de premissas => maior confiança.
    confidence = "MEDIA" if monthly_source == "INFORMADO" else "BAIXA"
    if monthly_source == "INFORMADO" and months_delinquent <= 12:
        confidence = "ALTA"

    return {
        "possivel": True,
        "cenarios": {
            "conservador": conservador,
            "provavel": provavel,
            "otimista": otimista,
        },
        "confianca": confidence,
        "memoria_calculo": memoria,
        "parametros_usados": snapshot,
        "monthly_source": monthly_source,
        "months_delinquent": months_delinquent,
        "safety_margin_pct": safety_margin_pct,
        # Marcação inegociável: estimativa NUNCA é passivo confirmado.
        "natureza": "ESTIMATIVA_OPERACIONAL",
        "status": "ESTIMADO",
        "ressalva": "Valor ESTIMADO por parâmetros; não comprova existência de dívida condominial.",
    }


def persist_condominium_estimate(
    db: Session,
    prop: "models.Property",
    *,
    computed: dict[str, Any],
    monthly_reference: Decimal | None,
    property_age_years: int | None,
    condominium_age_years: int | None,
    financing_age_years: int | None,
    justification: str | None,
    evidence_id: int | None = None,
) -> models.CondominiumEstimate:
    """Persiste o snapshot da estimativa (imutável por design: cada registro guarda
    os parâmetros usados). Não altera estimativas anteriores."""
    cenarios = computed.get("cenarios") or {}
    item = models.CondominiumEstimate(
        property_id=prop.id,
        monthly_reference=monthly_reference,
        monthly_source=computed.get("monthly_source", "ESTIMADO"),
        months_delinquent=computed.get("months_delinquent"),
        safety_margin_pct=computed.get("safety_margin_pct"),
        property_age_years=property_age_years,
        condominium_age_years=condominium_age_years,
        financing_age_years=financing_age_years,
        scenario_conservador=cenarios.get("conservador"),
        scenario_provavel=cenarios.get("provavel"),
        scenario_otimista=cenarios.get("otimista"),
        confidence=computed.get("confianca", "BAIXA"),
        # Serializa para JSON-safe (Decimal → str) preservando a memória/snapshot.
        assumptions=_json_safe({"memoria_calculo": computed.get("memoria_calculo"), "parametros_usados": computed.get("parametros_usados")}),
        justification=justification,
        evidence_id=evidence_id,
    )
    db.add(item)
    db.flush()
    return item


def age_alerts(db: Session, *, property_age_years: int | None, age_known: bool, municipality_id: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Alertas de idade PARAMETRIZÁVEIS. Respeita a qualidade da informação: se a
    idade for desconhecida/estimada (``age_known`` False), NÃO gera alerta conclusivo
    (coerente com SPEC-HARD-STOPS: nada conclusivo sem evidência). A idade eleva a
    INCERTEZA de manutenção — registrada separada de dívidas confirmadas."""
    limite1 = int(params.resolve(db, "checklist.idade_alerta_1_anos", municipality_id=municipality_id, default=10, now=now) or 10)
    limite2 = int(params.resolve(db, "checklist.idade_alerta_2_anos", municipality_id=municipality_id, default=15, now=now) or 15)
    if not age_known or property_age_years is None:
        return {
            "nivel": None,
            "conclusivo": False,
            "mensagem": "Idade do imóvel desconhecida/estimada: alerta não conclusivo (sem evidência).",
            "limites": {"nivel_1_anos": limite1, "nivel_2_anos": limite2},
        }
    nivel = None
    if property_age_years >= limite2:
        nivel = "ATENCAO_FORTE"
    elif property_age_years >= limite1:
        nivel = "ATENCAO"
    mensagem = (
        f"Imóvel com {property_age_years} anos: maior incerteza de manutenção/reforma."
        if nivel else f"Imóvel com {property_age_years} anos: abaixo do limite de alerta."
    )
    return {
        "nivel": nivel,
        "conclusivo": True,
        "mensagem": mensagem,
        "limites": {"nivel_1_anos": limite1, "nivel_2_anos": limite2},
        "nota": "Incerteza de manutenção — não é dívida confirmada.",
    }
