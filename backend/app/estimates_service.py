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


# ---------------------------------------------------------------------------------------------------------------------
# v1.0.12 (Fase E): estimativa pelo período da matrícula (aquisição → consolidação), com cenários baixo/provável/alto.
# Mesmo módulo, mesma tabela (CondominiumEstimate): baixo → scenario_otimista, provável → scenario_provavel,
# alto → scenario_conservador. A composição de custos usa provável no cenário base e alto no conservador.
# ---------------------------------------------------------------------------------------------------------------------
AVISO_ESTIMATIVA = ("Estimativa calculada com base em informações documentais e premissas configuráveis. Não representa dívida "
                    "confirmada. Solicite declaração atualizada ao condomínio.")
METODO_PERIODO = "PERIODO_MATRICULA"
_CENT = Decimal("0.01")


def _months_between(start, end) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0)
    return max(months, 0)


def _to_date(value):
    from datetime import date as _date
    if value is None or isinstance(value, _date):
        return value
    return _date.fromisoformat(str(value)[:10])


def _scenario_amounts(fee: Decimal, months: int, offset: int, juros: Decimal, multa: Decimal, correcao: Decimal) -> dict[str, Any]:
    """Cotas em atraso: as ``months`` cotas anteriores à consolidação. Juros e correção simples por mês até hoje
    (cota k tem offset + k meses): soma dos meses = months × offset + months × (months + 1) / 2."""
    n = Decimal(months)
    month_sum = n * Decimal(offset) + n * (n + 1) / Decimal(2)
    principal = (fee * n).quantize(_CENT)
    fine = (principal * multa).quantize(_CENT)
    interest = (fee * juros * month_sum).quantize(_CENT)
    correction = (fee * correcao * month_sum).quantize(_CENT)
    return {"meses_em_atraso": months, "principal": principal, "multa": fine, "juros": interest, "correcao": correction,
            "total": principal + fine + interest + correction}


def estimate_from_registry(db: Session, prop: "models.Property", *, monthly_reference: Decimal | None = None, acquisition_date=None,
                           consolidation_date=None, today=None) -> dict[str, Any]:
    """Estimativa condominial pelo período entre a aquisição e a consolidação lidas na matrícula (ou informadas).

    Valor mensal: informado > mediana do condomínio dos comparáveis > padrão do Admin (``condominio.valor_mensal_referencia``).
    Período: meses entre as datas, limitado por ``condominio.periodo_maximo_meses``. Cenários: fração do período presumida em
    atraso (``condominio.fator_cenario_baixo/provavel/alto``), mais multa, juros e correção configuráveis. O período NÃO prova
    inadimplência. A regra de responsabilidade da venda é aplicada DEPOIS do valor estimado."""
    from datetime import date as _date
    from .registry_timeline import timeline_for_property
    today = today or _date.today()
    snapshot: list[dict[str, Any]] = []

    def _param(key: str, default: Any) -> Any:
        detail = params.resolve_detail(db, key, default=default)
        snapshot.append(detail)
        return detail["value"]

    timeline = timeline_for_property(db, prop.id, today=today)
    keys = timeline.get("datas_chave") or {}
    acq = _to_date(acquisition_date) or _to_date((keys.get("aquisicao") or {}).get("data"))
    cons = _to_date(consolidation_date) or _to_date((keys.get("consolidacao") or {}).get("data"))
    acq_src = "informada" if acquisition_date else (f"matrícula ({keys['aquisicao']['ato']})" if keys.get("aquisicao") else None)
    cons_src = "informada" if consolidation_date else (f"matrícula ({keys['consolidacao']['ato']})" if keys.get("consolidacao") else None)

    fee, fee_src = _dec(monthly_reference), "INFORMADO"
    if fee is None:
        fees = sorted(_dec(c.condo_fee) for c in getattr(prop, "comparables", []) or []
                      if not getattr(c, "excluded", False) and getattr(c, "condo_fee", None) not in (None, "", 0))
        if fees:
            mid = len(fees) // 2
            fee = fees[mid] if len(fees) % 2 else ((fees[mid - 1] + fees[mid]) / 2).quantize(_CENT)
            fee_src = f"COMPARAVEIS"
    if fee is None:
        fee = _dec(_param("condominio.valor_mensal_referencia", None))
        fee_src = "ADMIN" if fee is not None else None

    cap = int(_param("condominio.periodo_maximo_meses", 60) or 60)
    factors = {"baixo": _dec(_param("condominio.fator_cenario_baixo", Decimal("0.15"))),
               "provavel": _dec(_param("condominio.fator_cenario_provavel", Decimal("0.35"))),
               "alto": _dec(_param("condominio.fator_cenario_alto", Decimal("0.70")))}
    juros = _dec(_param("condominio.juros_mensal_pct", Decimal("0.01")))
    multa = _dec(_param("condominio.multa_pct", Decimal("0.02")))
    correcao = _dec(_param("condominio.correcao_mensal_pct", Decimal("0.004")))
    idade = (timeline.get("idade") or {})
    memoria: dict[str, Any] = {
        "metodo": METODO_PERIODO, "valor_mensal_referencia": fee, "origem_valor_mensal": fee_src,
        "data_aquisicao": acq.isoformat() if acq else None, "origem_data_aquisicao": acq_src,
        "data_consolidacao": cons.isoformat() if cons else None, "origem_data_consolidacao": cons_src,
        "idade_imovel": idade.get("texto"), "teto_periodo_meses": cap, "fatores": factors,
        "juros_mensal_pct": juros, "multa_pct": multa, "correcao_mensal_pct": correcao,
        "formula": ("período = meses completos entre aquisição e consolidação (limitado ao teto); meses em atraso = período × fator do cenário "
                    "(arredondado ao inteiro, meio para cima); principal = valor mensal × meses; multa = principal × multa; juros = valor mensal × juros × Σ meses de "
                    "atraso de cada cota até hoje; correção = valor mensal × correção × Σ meses; total = principal + multa + juros + correção"),
        "nota": "O período entre a aquisição e a consolidação NÃO prova inadimplência: é a janela em que ela pode ter ocorrido.",
    }
    missing = [label for label, ok in (("valor mensal do condomínio (informe, cadastre comparáveis ou preencha o padrão no Admin)", fee is not None),
                                       ("data de aquisição (matrícula ou informada)", acq is not None),
                                       ("data de consolidação (matrícula ou informada)", cons is not None)) if not ok]
    if not missing and cons < acq:
        missing.append("datas incoerentes (consolidação anterior à aquisição)")
    elif not missing and _months_between(acq, cons) == 0:
        # Sem um mês completo entre as datas não há janela para estimar: zero aqui pareceria "sem dívida".
        missing.append("período de ao menos um mês completo entre a aquisição e a consolidação")
    base = {"metodo": METODO_PERIODO, "memoria_calculo": memoria, "parametros_usados": snapshot, "natureza": "ESTIMATIVA_OPERACIONAL",
            "status": "ESTIMADO", "aviso": AVISO_ESTIMATIVA, "ressalva": AVISO_ESTIMATIVA, "property_age_years": idade.get("anos")}
    if missing:
        return {**base, "possivel": False, "motivo": "Estimativa não calculável: falta " + "; ".join(missing) + ".", "cenarios": None,
                "confianca": "BAIXA"}
    period = min(_months_between(acq, cons), cap)
    offset = _months_between(cons, today)
    memoria.update({"periodo_meses": _months_between(acq, cons), "periodo_considerado_meses": period, "meses_desde_consolidacao": offset})
    detail = {}
    for name, factor in factors.items():
        months = int((Decimal(period) * factor).to_integral_value(rounding="ROUND_HALF_UP"))
        detail[name] = {**_scenario_amounts(fee, months, offset, juros, multa, correcao), "fator": factor}
    # Regra da venda aplicada DEPOIS da estimativa (mesma função da composição de custos).
    from .services import current_auction
    from .viability import _buyer_share, caixa_rules, REGRA_EXCEDENTE, REGRA_INTEGRAL_ACIMA
    auction = current_auction(prop)
    appraisal = _dec(auction.appraisal_value) if auction is not None else None
    rule = caixa_rules(db, prop, (auction.financial_assumptions or {}) if auction is not None else {})["condominio_atraso"]
    cap_value = (appraisal * rule["limite_pct"]).quantize(_CENT) if (appraisal is not None and rule["limite_pct"] is not None
                                                                   and rule["tipo"] in (REGRA_EXCEDENTE, REGRA_INTEGRAL_ACIMA)) else None
    for name, item in detail.items():
        buyer, seller = _buyer_share(item["total"], rule["tipo"], cap_value)
        # Principal, multa, juros e correção são TODOS estimados (nunca dívida confirmada).
        item.update({"divida_potencial": item["total"], "responsabilidade_comprador": buyer, "responsabilidade_caixa": seller,
                     "valor_no_financeiro": buyer if name != "baixo" else None, "natureza": "ESTIMATIVA_OPERACIONAL", "status": "ESTIMADO"})
    memoria["cenarios"] = detail
    confidence = "MEDIA" if fee_src in ("INFORMADO", "COMPARAVEIS") and acq_src and acq_src.startswith("matrícula") and cons_src and cons_src.startswith("matrícula") else "BAIXA"
    return {**base, "possivel": True, "confianca": confidence, "monthly_source": fee_src, "months_delinquent": period, "safety_margin_pct": None,
            "cenarios": {"conservador": detail["alto"]["total"], "provavel": detail["provavel"]["total"], "otimista": detail["baixo"]["total"]},
            "cenarios_detalhe": detail,
            "regra_venda": {"tipo": rule["tipo"], "limite_pct": rule["limite_pct"], "limite": cap_value, "fonte": rule["fonte"], "origem": rule["origem"]},
            "uso_no_financeiro": "cenário base usa o provável; conservador usa o alto (já com a regra da venda aplicada)"}


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
