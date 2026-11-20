"""Resumo do investimento (evolução da inteligência, v1.0.14).

Leitura pura e determinística: reúne, numa resposta só, o que o investidor precisa para decidir, a partir dos motores que já
existem (inteligência de mercado/viabilidade, Central de Débitos, riscos consolidados, veredito). Nada é recalculado por outra
regra e nada é gravado. Cada número leva o tipo de dado (rastreabilidade interna):

- FATO: lido de documento, edital ou fonte oficial;
- DADO_MANUAL: informado pelo usuário;
- ESTIMATIVA: calculado a partir de comparáveis, reservas ou premissas;
- INFERENCIA: conclusão do sistema sobre fatos (ex.: risco possível);
- DESCONHECIDO: não levantado. Nunca vira zero.

Blocos: IPTU (status da consulta), condomínio (taxa mensal × dívida acumulada, sempre separados), mercado (amostra, comparáveis,
yield, liquidez), Financeiro por natureza (confirmado / estimado / desconhecido / não incluído), riscos consolidados e a
recomendação (FAVORÁVEL, ATENÇÃO — INVESTIGAR, DESFAVORÁVEL, NÃO ARREMATAR).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import market as mk

FATO, DADO_MANUAL, ESTIMATIVA, INFERENCIA, DESCONHECIDO = "FATO", "DADO_MANUAL", "ESTIMATIVA", "INFERENCIA", "DESCONHECIDO"
TIPO_LABELS = {FATO: "Fato", DADO_MANUAL: "Dado manual", ESTIMATIVA: "Estimativa", INFERENCIA: "Inferência", DESCONHECIDO: "Desconhecido"}

# ------------------------------------------------------------------ IPTU
IPTU_CONSULTADO, IPTU_ASSISTIDA, IPTU_PENDENTE, IPTU_NAO_ENCONTRADO, IPTU_FALHA, IPTU_NECESSITA = (
    "CONSULTADO", "CONSULTA_ASSISTIDA", "PENDENTE_CONSULTA", "NAO_ENCONTRADO", "FALHA_CONSULTA", "NECESSITA_INFORMACAO")
IPTU_LABELS = {IPTU_CONSULTADO: "Consultado", IPTU_ASSISTIDA: "Consulta assistida", IPTU_PENDENTE: "Pendente de consulta",
               IPTU_NAO_ENCONTRADO: "Não encontrado", IPTU_FALHA: "Falha na consulta", IPTU_NECESSITA: "Necessita informação"}
_IPTU_CODES = {"IPTU", "TAXA_MUNICIPAL", "DIVIDA_ATIVA_MUNICIPAL", "OUTRO_DEBITO_MUNICIPAL"}

# ------------------------------------------------------------------ condomínio
CONDO_CONFIRMADO, CONDO_ANUNCIO, CONDO_ESTIMADO, CONDO_DESCONHECIDO = "CONFIRMADO", "ANUNCIO", "ESTIMADO", "DESCONHECIDO"
CONDO_LABELS = {CONDO_CONFIRMADO: "Informado pelo usuário", CONDO_ANUNCIO: "Anúncio do mesmo prédio", CONDO_ESTIMADO: "Estimado por imóveis parecidos",
                CONDO_DESCONHECIDO: "Desconhecido"}

# ------------------------------------------------------------------ recomendação
REC_FAVORAVEL, REC_ATENCAO, REC_DESFAVORAVEL, REC_NAO_ARREMATAR = "FAVORAVEL", "ATENCAO_INVESTIGAR", "DESFAVORAVEL", "NAO_ARREMATAR"
REC_LABELS = {REC_FAVORAVEL: "FAVORÁVEL", REC_ATENCAO: "ATENÇÃO — INVESTIGAR", REC_DESFAVORAVEL: "DESFAVORÁVEL", REC_NAO_ARREMATAR: "NÃO ARREMATAR"}

BUSCA_NAO_CONFIGURADA = {"status": "NAO_CONFIGURADO",
                         "texto": "Busca automática de anúncios não configurada: o sistema não tem um provedor de pesquisa autorizado (chave de API). "
                                  "Copiar dados de portais de anúncio sem autorização viola os termos de uso deles. Cadastre os imóveis parecidos em "
                                  "Mercado > Comparáveis; o cálculo usa só o que foi cadastrado."}


def _d(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception:  # noqa: BLE001 - valor ilegível = desconhecido
        return None


def _q(value: Decimal | None, places: str = "0.01") -> Decimal | None:
    return value.quantize(Decimal(places)) if value is not None else None


def _brl(value: Any) -> str:
    v = _d(value)
    if v is None:
        return "desconhecido"
    return "R$ " + f"{v.quantize(Decimal('0.01')):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: Any) -> str:
    v = _d(value)
    return "desconhecido" if v is None else f"{(v * 100).quantize(Decimal('0.1'))}%".replace(".", ",")


def valor(value: Any, tipo: str, origem: str | None = None) -> dict[str, Any]:
    """Valor rastreável: número + tipo de dado + origem. Sem número, o tipo é DESCONHECIDO."""
    v = _d(value)
    return {"valor": v, "tipo": tipo if v is not None else DESCONHECIDO, "tipo_label": TIPO_LABELS[tipo if v is not None else DESCONHECIDO],
            "origem": origem if v is not None else (origem or "não levantado")}


def _line(lines: list[dict], key: str) -> dict | None:
    return next((l for l in lines if l.get("chave") == key), None)


# ------------------------------------------------------------------ IPTU

def iptu_status(db, prop, assumptions: dict, cost_lines: list[dict]) -> dict[str, Any]:
    """Situação do IPTU: o que foi consultado, como consultar (portal oficial) e o que vai para Débitos e Financeiro."""
    from sqlalchemy import select
    from . import models
    from .debt_providers import select_provider, ManualAssistedProvider
    from .municipal_iptu import guidance
    from .viability import municipality_id_for
    municipality_id = municipality_id_for(db, prop)
    g = guidance(db, municipality_id) if municipality_id is not None else None
    queries = db.scalars(select(models.DebtQuery).where(models.DebtQuery.property_id == prop.id, models.DebtQuery.debt_type_code == "IPTU")
                         .order_by(models.DebtQuery.id.desc())).all()
    last = queries[0] if queries else None
    debts = [d for d in db.scalars(select(models.PropertyDebt).where(models.PropertyDebt.property_id == prop.id)).all()
             if str(d.debt_type_code or "").upper() in _IPTU_CODES and d.status not in ("QUITADO", "CANCELADO")]
    real = [d for d in debts if d.status not in ("INDISPONIVEL", "EM_VALIDACAO", "ESTIMADO", "PENDENTE")]
    amount = lambda d: d.updated_amount if d.updated_amount is not None else d.original_amount  # noqa: E731
    total = sum((_d(amount(d)) or Decimal("0") for d in real), Decimal("0")) if real else None
    inscription = (getattr(prop, "inscription", None) or "").strip() or None
    missing = []
    if municipality_id is None:
        missing.append("município do imóvel na cobertura (Admin > Municípios)")
    if not inscription:
        missing.append("inscrição imobiliária (indicação fiscal) do imóvel, em Cadastro")

    status = None
    if last is not None:
        status = {"CONCLUIDA": IPTU_CONSULTADO, "SEM_OCORRENCIA": IPTU_CONSULTADO, "PARCIAL": IPTU_CONSULTADO,
                  "REQUER_INTERVENCAO_MANUAL": IPTU_ASSISTIDA, "ERRO": IPTU_FALHA, "INDISPONIVEL": IPTU_FALHA,
                  "NAO_ENCONTRADO": IPTU_NAO_ENCONTRADO}.get(str(last.status), IPTU_PENDENTE)
    if real and status in (None, IPTU_PENDENTE, IPTU_ASSISTIDA):
        status = IPTU_CONSULTADO
    if status is None:
        status = IPTU_NECESSITA if missing else IPTU_PENDENTE
    no_debt = bool(last is not None and last.status == "SEM_OCORRENCIA" and not real)

    provider = select_provider(db, municipality_id=municipality_id, debt_type_code="IPTU")
    automatic = provider.name != ManualAssistedProvider.name
    reliab = {d.reliability for d in real}
    debt_type = FATO if reliab and reliab <= {"OFICIAL", "DOCUMENTAL"} else DADO_MANUAL
    annual = _d(assumptions.get("iptu_anual"))
    tributos, posse = _line(cost_lines, "tributos_atraso"), _line(cost_lines, "iptu_posse")

    texts = {
        IPTU_CONSULTADO: ("Consulta registrada: " + ("sem débito em aberto na fonte consultada." if no_debt else f"débito de {_brl(total)}.")),
        IPTU_ASSISTIDA: "Consulta assistida iniciada, aguardando o resultado lido no portal da prefeitura.",
        IPTU_PENDENTE: "IPTU ainda não consultado. A prefeitura não permite consulta automática: use o portal oficial e registre o resultado aqui.",
        IPTU_NAO_ENCONTRADO: "O portal não encontrou o imóvel com o identificador usado. Confira a inscrição imobiliária.",
        IPTU_FALHA: "A última consulta falhou (portal indisponível ou erro). Tente de novo mais tarde; isso não significa ausência de débito.",
        IPTU_NECESSITA: "Faltam dados para consultar: " + "; ".join(missing) + ".",
    }
    return {
        "status": status, "status_label": IPTU_LABELS[status], "texto": texts[status],
        "automatico": automatic,
        "motivo_sem_automacao": None if automatic else ((g or {}).get("motivo") or "Município sem integração automática disponível."),
        "portal": {"fonte": (g or {}).get("fonte"), "orgao": (g or {}).get("orgao"), "urls": (g or {}).get("urls") or [],
                   "identificador": (g or {}).get("identificador"), "exigencias": (g or {}).get("exigencias") or [],
                   "passos": (g or {}).get("passos") or []} if g else None,
        "dados_necessarios": missing, "inscricao_imobiliaria": inscription,
        "debito_em_aberto": valor(0 if no_debt else total, FATO if no_debt else debt_type,
                                  "consulta registrada sem ocorrência" if no_debt else ("débitos registrados na Central de Débitos" if real else None)),
        "sem_debito": no_debt,
        "valor_anual": valor(annual, DADO_MANUAL, assumptions.get("iptu_anual_origem") or "premissa do imóvel (IPTU anual)"),
        "ultima_consulta": {"status": last.status, "em": last.completed_at, "mensagem": last.message} if last is not None else None,
        "integracao": {"debitos": {"status": (tributos or {}).get("status"), "valor": (tributos or {}).get("valor"), "origem": (tributos or {}).get("origem")},
                       "financeiro_posse": {"status": (posse or {}).get("status"), "valor_anual_base": (posse or {}).get("iptu_anual_base"),
                                            "origem": (posse or {}).get("origem")}},
        "aviso": "Desconhecido nunca é zero: sem consulta, o IPTU fica fora da soma e o resultado é provisório.",
    }


# ------------------------------------------------------------------ condomínio

def _norm_address(value: Any) -> str:
    from .registry_chain import fold
    return " ".join(fold(str(value or "")).replace(",", " ").split())


def condo_analysis(prop, intel: dict, assumptions: dict) -> dict[str, Any]:
    """Taxa mensal de condomínio (confirmada, anúncio do mesmo prédio, estimada ou desconhecida) e, SEPARADA, a dívida acumulada."""
    used_ids = {r["id"] for r in (intel.get("venda") or {}).get("comparaveis", []) + (intel.get("aluguel") or {}).get("comparaveis", []) if r.get("usado")}
    comps = [c for c in prop.comparables if c.id in used_ids and c.condo_fee not in (None, "") and _d(c.condo_fee) and _d(c.condo_fee) > 0]
    subject_addr = _norm_address(prop.address)
    same = [c for c in prop.comparables if not c.excluded and c.condo_fee and subject_addr and _norm_address(c.address) == subject_addr]
    fees = [_d(c.condo_fee) for c in comps]
    n = len(fees)
    area = _d(prop.private_area_m2) or _d(prop.area_m2)
    per_m2 = [_d(c.condo_fee) / _d(c.area_m2) for c in comps if _d(c.area_m2)]
    stats = None
    if n:
        ordered = sorted(fees)
        stats = {"quantidade": n, "media": _q(sum(fees, Decimal("0")) / Decimal(n)), "mediana": _q(mk.median(fees)),
                 "faixa": {"min": _q(mk.percentile(ordered, Decimal("0.25")) if n >= 4 else ordered[0]),
                           "max": _q(mk.percentile(ordered, Decimal("0.75")) if n >= 4 else ordered[-1]), "criterio": "P25–P75" if n >= 4 else "mín–máx"},
                 "mediana_por_m2_x_area": _q(mk.median(per_m2) * area) if (per_m2 and area) else None}
    confidence = ("INSUFICIENTE" if n < 3 else "BAIXA" if n < 5 else "MEDIA" if n < mk.MIN_SAMPLE else "ALTA") if n else "SEM_DADOS"
    # Fonte única: a taxa mensal exibida é a MESMA que o Financeiro usa (viability.acquisition_costs). Anúncios do mesmo endereço
    # aparecem como referência à parte (ANÚNCIO) e não mudam o cálculo sozinhos.
    used = (intel.get("carregamento_mensal") or {})
    value, origin = _d(used.get("valor")), used.get("origem")
    if value is None:
        status = CONDO_DESCONHECIDO
    elif _d(assumptions.get("carregamento_mensal")) is not None:
        status = CONDO_CONFIRMADO
    else:
        status = CONDO_ESTIMADO
    same_ref = {"quantidade": len(same), "mediana": _q(mk.median([_d(c.condo_fee) for c in same])), "status": CONDO_ANUNCIO,
                "status_label": CONDO_LABELS[CONDO_ANUNCIO]} if same else None
    debt = _line(intel.get("custos") or [], "condominio_atraso") or {}
    debt_value = debt.get("valor")
    debt_type = (FATO if str(debt.get("fonte_valor") or "") == "DIVIDA" and str(debt.get("status")) == "INFORMADO" else
                 ESTIMATIVA if debt.get("valor_base") is not None or str(debt.get("status")) == "ESTIMADO" else DESCONHECIDO)
    insufficient = status == CONDO_DESCONHECIDO
    return {
        "taxa_mensal": {**valor(value, DADO_MANUAL if status == CONDO_CONFIRMADO else ESTIMATIVA, origin), "status": status,
                        "status_label": CONDO_LABELS[status]},
        "estimativa_insuficiente": insufficient,
        "texto": ("Estimativa insuficiente: " + (f"só {n} imóvel(is) parecido(s) com condomínio informado (mínimo 3)." if n else
                                                 "nenhum imóvel parecido com condomínio informado.") +
                  " Informe a taxa em Financeiro > Premissas ou cadastre comparáveis com o valor do condomínio.") if insufficient else
                 f"Taxa mensal: {_brl(value)} ({origin}).",
        "referencias": stats, "confianca": confidence,
        "mesmo_predio": same_ref,
        "divida_acumulada": {"valor": debt_value, "valor_base": debt.get("valor_base"), "valor_conservador": debt.get("valor_conservador"),
                             "status": debt.get("status"), "origem": debt.get("origem"), "tipo": debt_type, "tipo_label": TIPO_LABELS[debt_type]},
        "taxa_extra": {"status": DESCONHECIDO, "texto": "Taxa extra ou chamada de capital: sem fonte automática. Confirme com a administradora."},
        "busca_automatica": BUSCA_NAO_CONFIGURADA,
        "aviso": "A taxa mensal (custo enquanto o imóvel é seu) e a dívida acumulada (atrasos do dono anterior) são valores diferentes e nunca "
                 "são somados um no outro.",
    }


# ------------------------------------------------------------------ mercado

def _comps(estimate: dict) -> list[dict]:
    return [{"id": r.get("id"), "link": r.get("url") or None, "fonte": r.get("fonte"), "valor": r.get("valor"), "area_m2": r.get("area_m2"),
             "valor_m2": r.get("valor_m2"), "data_coleta": r.get("consultado_em"), "similaridade": r.get("similaridade"), "usado": r.get("usado"),
             "motivo_exclusao": r.get("motivo"), "bairro": r.get("bairro"), "tipo_preco": r.get("tipo_preco")} for r in estimate.get("comparaveis") or []]


def market_summary(intel: dict) -> dict[str, Any]:
    sale, rent, vals = intel.get("venda") or {}, intel.get("aluguel") or {}, intel.get("valores") or {}
    base = next((s for s in intel.get("cenarios") or [] if s.get("cenario") == "BASE"), {})
    market_value, rent_value = _d(vals.get("valor_mercado_estimado")), _d(vals.get("aluguel_estimado"))
    acquisition = _d(((intel.get("dimensoes") or {}).get("rentabilidade") or {}).get("aquisicao"))

    def block(est: dict) -> dict:
        stats = est.get("estatisticas_m2") or {}
        area = _d(est.get("area_referencia"))
        q = est.get("qualidade_amostra") or mk.sample_quality(est.get("quantidade_usada") or 0)
        return {"qualidade": q, "quantidade_usada": est.get("quantidade_usada"), "quantidade_total": est.get("quantidade_total"),
                "valor_estimado": est.get("valor_estimado"), "faixa": est.get("faixa"), "faixa_criterio": est.get("faixa_criterio"),
                "m2_media": _q(_d(stats.get("m2_ajustado_media"))), "m2_mediana": _q(_d(stats.get("m2_ajustado_mediana"))),
                "media_total": _q(_d(stats.get("m2_ajustado_media")) * area) if (stats.get("m2_ajustado_media") is not None and area) else None,
                "mediana_total": _q(_d(stats.get("m2_ajustado_mediana")) * area) if (stats.get("m2_ajustado_mediana") is not None and area) else None,
                "comparaveis": _comps(est), "avisos": est.get("avisos") or []}

    gross_yield = _q(rent_value * 12 / market_value, "0.0001") if (rent_value and market_value) else None
    acq_yield = _q(rent_value * 12 / acquisition, "0.0001") if (rent_value and acquisition) else None
    sale_value = _d(base.get("valor_venda"))
    origin = base.get("valor_venda_origem")
    sale_type = DADO_MANUAL if origin == "premissa do imóvel" else ESTIMATIVA
    return {
        "venda": block(sale), "aluguel": block(rent),
        "valor_venda_usado": {**valor(sale_value, sale_type, origin),
                              "texto": None if sale_value is not None else "AMOSTRA INSUFICIENTE: valor de venda desconhecido. O sistema não usa "
                                                                           "percentual sobre a avaliação do vendedor como valor de mercado."},
        "aluguel_estimado": valor(rent_value, ESTIMATIVA, "comparáveis de aluguel"),
        "yield_bruto_anual": {"sobre_valor_mercado": gross_yield, "sobre_aquisicao": acq_yield,
                              "texto": (f"Aluguel anual ≈ {_pct(gross_yield)} do valor de mercado" + (f" e {_pct(acq_yield)} do preço de compra" if acq_yield else "") + ".")
                              if gross_yield else "Yield não calculado: falta aluguel ou valor de mercado estimado."},
        "liquidez": intel.get("liquidez"),
        "busca_automatica": BUSCA_NAO_CONFIGURADA,
    }


# ------------------------------------------------------------------ Financeiro por natureza

def finance_by_nature(intel: dict) -> dict[str, Any]:
    groups: dict[str, list[dict]] = {"confirmado": [], "estimado": [], "desconhecido": [], "nao_incluido": []}
    for line in intel.get("custos") or []:
        status = str(line.get("status") or "")
        row = {"chave": line.get("chave"), "descricao": line.get("descricao"), "valor": line.get("valor"), "valor_base": line.get("valor_base"),
               "valor_conservador": line.get("valor_conservador"), "origem": line.get("origem")}
        if status == "NAO_APLICAVEL":
            groups["nao_incluido"].append({**row, "motivo": "não se aplica a este imóvel"})
        elif status == "INFORMADO":
            groups["confirmado"].append({**row, "tipo": DADO_MANUAL if "premissa" in str(line.get("origem") or "") else FATO})
        elif status == "ESTIMADO" or line.get("valor_base") is not None:
            groups["estimado"].append({**row, "tipo": ESTIMATIVA})
        else:
            groups["desconhecido"].append({**row, "tipo": DESCONHECIDO, "motivo": "sem valor: fora da soma (não é zero)"})
    return {**groups, "texto": "Confirmado = valor informado ou documentado; estimado = reserva ou cálculo; desconhecido = fora da soma; "
                               "não incluído = não se aplica."}


# ------------------------------------------------------------------ recomendação

def recommend(*, verdict_overall: str | None, verdict_code: str | None, risks: dict, missing: list[str], acquisition: Decimal | None,
              max_price: Decimal | None, max_price_provisional: bool, result: Decimal | None) -> dict[str, Any]:
    """Recomendação ao investidor. Precedência: risco crítico confirmado > inviável > risco ativo ou dado essencial faltando > favorável.
    Margem positiva nunca esconde risco nem dado faltando."""
    items = risks.get("itens") or []
    active = [i for i in items if i["situacao"] in ("CONFIRMADO", "POSSIVEL")]
    critical = [i for i in active if str(i.get("gravidade") or "").upper() == "CRITICA"]
    above = bool(acquisition is not None and max_price is not None and acquisition > max_price)
    reasons: list[str] = []
    if critical:
        code = REC_NAO_ARREMATAR
        reasons += [f"Risco crítico: {i['titulo']}." for i in critical]
    elif verdict_overall == "DESFAVORAVEL" or (above and not max_price_provisional):
        code = REC_DESFAVORAVEL
        if above:
            reasons.append(f"O lance ({_brl(acquisition)}) está acima do preço máximo estimado ({_brl(max_price)}).")
        if verdict_overall == "DESFAVORAVEL":
            reasons.append("O cálculo financeiro do veredito indica operação inviável neste preço.")
    elif active or missing or verdict_overall in (None, "ATENCAO", "INCONCLUSIVO"):
        code = REC_ATENCAO
        reasons += [f"{i['situacao_label']}: {i['titulo']}." for i in active[:4]]
        reasons += [f"Falta: {m}." for m in missing[:6]]
        if above:
            reasons.append(f"O lance ({_brl(acquisition)}) está acima do preço máximo provisório ({_brl(max_price)}).")
        if verdict_overall is None:
            reasons.append("Ainda não há análise completa do imóvel.")
    else:
        code = REC_FAVORAVEL
        reasons.append(f"Lance dentro do preço máximo ({_brl(max_price)}), sem risco ativo e sem dado essencial faltando.")
    margin_note = None
    if result is not None and result > 0 and code != REC_FAVORAVEL:
        margin_note = ("A margem estimada é positiva, mas não basta: " +
                       ("há riscos ativos" if active else "") + (" e " if active and missing else "") + ("faltam dados essenciais" if missing else "") +
                       (" e o lance passa do teto" if above and not (active or missing) else "") + ".")
    answer = {REC_FAVORAVEL: "Sim, até o preço máximo.", REC_ATENCAO: "Ainda não: investigue os pontos abaixo antes de dar lance.",
              REC_DESFAVORAVEL: "Não neste preço.", REC_NAO_ARREMATAR: "Não."}[code]
    return {"codigo": code, "label": REC_LABELS[code], "arrematar": answer, "motivos": reasons, "aviso_margem": margin_note,
            "veredito_motor": verdict_overall}


def _missing(market: dict, iptu: dict, condo: dict, intel: dict, risks: dict) -> list[str]:
    out = []
    if market["valor_venda_usado"]["valor"] is None:
        out.append("valor de venda (amostra de comparáveis insuficiente)")
    if iptu["status"] != IPTU_CONSULTADO:
        out.append(f"IPTU ({iptu['status_label'].lower()})")
    if condo["taxa_mensal"]["valor"] is None:
        out.append("taxa mensal de condomínio")
    if condo["divida_acumulada"]["tipo"] == DESCONHECIDO:
        out.append("dívida de condomínio")
    for desc in ((intel.get("dimensoes") or {}).get("custos") or {}).get("criticos_pendentes") or []:
        label = str(desc).lower()
        if not any(label[:12] in m for m in out):
            out.append(label)
    out += [i["titulo"].lower() for i in risks.get("itens") or [] if i["situacao"] == "PENDENTE_CONFIRMACAO"]
    return list(dict.fromkeys(out))


def summary(db, prop) -> dict[str, Any]:
    from . import risk_presenter
    from .services import current_auction
    from .viability import market_intelligence
    intel = market_intelligence(db, prop)
    auction = current_auction(prop)
    assumptions = (getattr(auction, "financial_assumptions", None) or {}) if auction else {}
    lines = intel.get("custos") or []
    risks = risk_presenter.for_property(db, prop, cost_lines=lines)
    iptu = iptu_status(db, prop, assumptions, lines)
    condo = condo_analysis(prop, intel, assumptions)
    market = market_summary(intel)
    ret = (intel.get("dimensoes") or {}).get("rentabilidade") or {}
    base = next((s for s in intel.get("cenarios") or [] if s.get("cenario") == "BASE"), {})
    verdict = max(prop.verdicts, key=lambda v: (v.analysis_version, v.id)) if getattr(prop, "verdicts", None) else None
    decision = ((verdict.financial or {}).get("decisao") or {}).get("recomendacao") if verdict is not None else None
    missing = _missing(market, iptu, condo, intel, risks)
    acquisition = _d(ret.get("aquisicao"))
    max_price = _d((intel.get("preco_maximo") or {}).get("recomendado"))
    provisional = bool((intel.get("preco_maximo") or {}).get("provisorio") or ret.get("preco_maximo_provisorio"))
    result = _d(base.get("resultado_liquido"))
    rec = recommend(verdict_overall=verdict.overall if verdict is not None else None, verdict_code=(decision or {}).get("codigo"), risks=risks,
                    missing=missing, acquisition=acquisition, max_price=max_price, max_price_provisional=provisional, result=result)
    actions: list[dict[str, Any]] = []
    for item in risks.get("itens") or []:
        if item["situacao"] in ("CONFIRMADO", "POSSIVEL", "PENDENTE_CONFIRMACAO") and item["o_que_fazer"]:
            actions.append({"prioridade": {"CONFIRMADO": 1, "POSSIVEL": 2, "PENDENTE_CONFIRMACAO": 3}[item["situacao"]], "tema": item["titulo"],
                            "acao": item["o_que_fazer"][0]})
    if iptu["status"] != IPTU_CONSULTADO:
        actions.append({"prioridade": 2, "tema": "IPTU", "acao": "Consultar o IPTU no portal da prefeitura e registrar o resultado em Débitos."})
    if condo["estimativa_insuficiente"]:
        actions.append({"prioridade": 2, "tema": "Condomínio", "acao": "Informar a taxa de condomínio ou cadastrar comparáveis com o valor da taxa."})
    if market["valor_venda_usado"]["valor"] is None:
        actions.append({"prioridade": 2, "tema": "Valor de venda", "acao": "Cadastrar pelo menos 3 (ideal 7 a 10) imóveis parecidos à venda em Mercado."})
    actions.sort(key=lambda a: a["prioridade"])
    margin = _d(ret.get("margem_base"))
    return {
        "property_id": prop.id,
        "recomendacao": rec,
        "numeros": {
            "lance": valor(acquisition, FATO, "edital / cadastro do leilão"),
            "preco_maximo": {**valor(max_price, ESTIMATIVA, (intel.get("preco_maximo") or {}).get("criterio")), "provisorio": provisional},
            "valor_venda": market["valor_venda_usado"],
            "lucro_estimado": valor(result, ESTIMATIVA, "cenário BASE da inteligência de mercado"),
            "roi": valor(_d(base.get("roi")), ESTIMATIVA, "resultado líquido ÷ investimento total (cenário BASE)"),
            "margem": valor(margin, ESTIMATIVA, "resultado líquido ÷ valor de venda (cenário BASE)"),
            "investimento_total": valor(_d(base.get("investimento_total")), ESTIMATIVA, "soma dos custos incluídos (cenário BASE)"),
        },
        "principal_risco": risks.get("principal"),
        "pendencias": missing,
        "proximas_acoes": actions[:8],
        "iptu": iptu, "condominio": condo, "mercado": market, "financeiro": finance_by_nature(intel), "riscos": risks,
        "tipos_dado": TIPO_LABELS,
    }
