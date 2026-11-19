"""Viabilidade financeira com inteligência de mercado (v1.0.8).

Camada de leitura, determinística e sem LLM, que junta:

- a estimativa de mercado de ``market.estimate`` (venda e aluguel, com confiança e memória de cálculo);
- custos de aquisição, posse e saída, cada um com ``status`` (INFORMADO, ESTIMADO, PENDENTE, NAO_APLICAVEL) e ``origem``;
- as condições da venda direta Caixa (limites de responsabilidade do comprador por condomínio e tributos);
- três cenários (conservador, base, otimista), preço máximo pela meta de retorno configurada e liquidez;
- uma conclusão consolidada (FAVORAVEL, DESFAVORAVEL, INCONCLUSIVO) que considera documentação, risco jurídico,
  mercado, custos, rentabilidade e liquidez.

Princípios: nada é inventado. Premissas padrão existem só onde o mercado tem referência usual e aparecem com origem
"padrão do sistema (parâmetro configurável)". Custo sem valor é PENDENTE e não entra no cenário base; no conservador
entra o teto contratual (Caixa) ou a reserva parametrizada, sempre identificada. Desconto sobre a avaliação da Caixa
é diferente de desconto sobre o valor de mercado estimado, e os dois são mostrados separados.

Consistência (v2): o cálculo financeiro do veredito (``build_finance``) usa ``verdict_finance``, que reaproveita as MESMAS
entradas (``_inputs``), a MESMA composição de custos e o MESMO cenário BASE daqui. Resultado, ROI, break-even e preço máximo
do veredito e da inteligência de mercado coincidem para as mesmas premissas.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from . import market as mk
from .finance import (GOAL_LUCRO_MINIMO, GOAL_MARGEM_MINIMA, GOAL_ROI_MINIMO, SUPPORTED_GOALS, SaleAssumptions, TAX_BASE_GANHO, TAX_BASE_VENDA,
                      canonical_cost_key)

ZERO = Decimal("0")
ONE = Decimal("1")

INFORMADO, ESTIMADO, PENDENTE, NAO_APLICAVEL = "INFORMADO", "ESTIMADO", "PENDENTE", "NAO_APLICAVEL"
FAVORAVEL, DESFAVORAVEL, INCONCLUSIVO = "FAVORAVEL", "DESFAVORAVEL", "INCONCLUSIVO"
ORIGEM_PADRAO = "padrão do sistema (parâmetro configurável)"
PREMISSA_IGUALDADE_IPTU = ("Premissa conservadora: dívida de IPTU/tributos EXATAMENTE igual ao limite é integralmente do comprador "
                           "(Caixa assume R$ 0); a regra informada não esclarece a igualdade.")

# Premissas padrão: chave no catálogo de parâmetros → (valor, descrição). Todas aparecem na saída com a origem.
DEFAULTS: dict[str, tuple[Decimal | int, str]] = {
    "mercado.desconto_negociacao": (mk.DEFAULT_NEGOTIATION_DISCOUNT, "Desconto de negociação sobre preço anunciado"),
    "mercado.similaridade_minima": (mk.DEFAULT_MIN_SIMILARITY, "Similaridade mínima para usar o comparável"),
    "venda.corretagem_pct": (Decimal("0.06"), "Corretagem na revenda (fração do valor de venda)"),
    "venda.tributo_ganho_pct": (Decimal("0.15"), "IR sobre ganho de capital, pessoa física (alíquota mínima, Lei 13.259/2016)"),
    "venda.prazo_meses": (12, "Prazo até a revenda no cenário base (meses)"),
    "cenario.prazo_conservador_fator": (Decimal("1.5"), "Multiplicador do prazo no cenário conservador"),
    "cenario.prazo_otimista_fator": (Decimal("0.75"), "Multiplicador do prazo no cenário otimista"),
    "aluguel.taxa_ocupacao": (Decimal("0.90"), "Ocupação média anual do imóvel alugado (não presume 100%)"),
    "aluguel.taxa_administracao": (Decimal("0.10"), "Taxa de administração da locação"),
    "viabilidade.roi_minimo": (Decimal("0.20"), "Retorno mínimo sobre o investimento total na revenda (meta do preço máximo)"),
    "viabilidade.reserva_registro_pct": (Decimal("0.02"), "Reserva conservadora para escritura/registro (fração da aquisição)"),
    "viabilidade.reserva_certidoes": (Decimal("600"), "Reserva conservadora para certidões (R$)"),
    "viabilidade.reserva_reforma_m2": (Decimal("250"), "Reserva conservadora de reforma (R$/m² de área privativa)"),
    "viabilidade.reserva_reforma_m2_base": (Decimal("100"), "Reserva de reparos leves no cenário base/otimista (R$/m² de área privativa)"),
    "viabilidade.reserva_desocupacao": (Decimal("5000"), "Reserva conservadora de desocupação (R$), se ocupação desconhecida"),
    # v1.0.11: referência de análise do item 21 do checklist ("grande reforma"). Premissa ajustável por imóvel ou no catálogo;
    # não é regra jurídica nem critério legal.
    "checklist.reforma_grande_pct": (Decimal("0.10"), "Referência de análise para \"grande reforma\" no checklist (fração do preço de aquisição); "
                                     "premissa ajustável, não é regra jurídica"),
    # v1.0.12 (decisão 2.2): valor de venda preliminar = avaliação × fator, só sem valor informado e sem comparáveis usáveis.
    "viabilidade.fator_venda_avaliacao": (Decimal("0.85"), "Fator de venda preliminar sobre a avaliação do vendedor (sem comparáveis suficientes)"),
    "viabilidade.margem_minima": (Decimal("0.10"), "Margem líquida mínima de referência (ressalva; não substitui a meta do investidor)"),
    "viabilidade.margem_seguranca_minima": (Decimal("0.10"), "Margem de segurança mínima de referência (ressalva)"),
}
# Premissas do catálogo SEM padrão do sistema: só valem quando o operador as preenche no Admin (senão o item segue pendente).
CATALOG_ONLY = {
    "viabilidade.itbi_aliquota": "ITBI (alíquota)", "viabilidade.regularizacao_padrao": "Regularização (reserva padrão)",
    "iptu.valor_anual_padrao": "IPTU anual padrão", "viabilidade.custos_mensais_padrao": "Custos mensais da posse (padrão)",
    "condominio.valor_mensal_referencia": "Condomínio mensal padrão",
}
ORIGEM_PRELIMINAR = "estimativa preliminar (avaliação × fator)"


def municipality_id_for(db, prop) -> int | None:
    """Município cadastrado do imóvel (nome e UF, sem acento e caixa), para parâmetros por município."""
    if db is None or prop is None or not getattr(prop, "city", None):
        return None
    try:
        from sqlalchemy import select
        from . import models
        from .registry_chain import fold
        rows = db.scalars(select(models.Municipality)).all()
        city, state = fold(str(prop.city)).strip(), str(getattr(prop, "state", "") or "").upper().strip()
        same_name = [m for m in rows if isinstance(m, models.Municipality) and fold(m.name).strip() == city]
        if state:
            match = [m for m in same_name if m.state.upper() == state]
        else:
            # Sem UF no imóvel só há município se o nome for único no cadastro (evita aplicar o ITBI de outra UF).
            match = same_name if len(same_name) == 1 else []
        return match[0].id if match else None
    except Exception:
        return None


def catalog_value(db, key: str, municipality_id: int | None = None) -> tuple[Decimal | None, str | None]:
    """(valor, origem) de uma premissa do catálogo sem padrão do sistema; (None, None) quando não preenchida."""
    if db is None:
        return None, None
    try:
        from . import parameters as params
        value = params.resolve(db, key, municipality_id=municipality_id, default=None)
        if value is None:
            return None, None
        # Origem pelo registro que de fato deu o valor: registro do município SEM valor (ou fora da vigência) cai no global e não é
        # rotulado "do município".
        municipal = False
        if municipality_id is not None:
            from sqlalchemy import select
            from . import models
            rows = db.scalars(select(models.Parameter).where(models.Parameter.key == key, models.Parameter.scope == "MUNICIPIO",
                                                             models.Parameter.municipality_id == municipality_id,
                                                             models.Parameter.status == "ATIVO")).all()
            municipal = any(params._within_validity(p) and (p.value is not None or p.default_value is not None) for p in rows)
    except Exception:
        return None, None
    where = " do município" if municipal else ""
    return _d(value), f"catálogo de parâmetros{where} ({key})"


def _d(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _brl(value: Decimal | None) -> str:
    if value is None:
        return "não informado"
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: Decimal) -> str:
    return f"{value * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%"


def _q(value: Decimal | None, places: str = "0.01") -> Decimal | None:
    return value.quantize(Decimal(places)) if isinstance(value, Decimal) else value


def resolve_premises(db, assumptions: dict | None) -> dict[str, dict]:
    """Premissas efetivas: valor do imóvel (``financial_assumptions``) > parâmetro do catálogo > padrão."""
    assumptions = assumptions or {}
    out: dict[str, dict] = {}
    for key, (default, label) in DEFAULTS.items():
        local_key = key.split(".", 1)[1]
        # A tela de premissas grava o IR como ``tributo_pct`` (base GANHO): é a mesma premissa do motor de viabilidade.
        # Com base VENDA o significado é outro (alíquota sobre a venda) e não é reaproveitado aqui.
        if key == "venda.tributo_ganho_pct" and assumptions.get(local_key) in (None, "") and str(assumptions.get("tax_base") or "GANHO").upper() == "GANHO":
            local_key = "tributo_pct"
        if assumptions.get(local_key) not in (None, ""):
            out[key] = {"valor": _d(assumptions[local_key]) if not isinstance(default, int) else int(assumptions[local_key]), "origem": "premissa do imóvel", "descricao": label}
            continue
        value, origin = default, ORIGEM_PADRAO
        if db is not None:
            try:
                from . import parameters as params
                found = params.resolve(db, key, default=None)
                if found is not None:
                    value, origin = (_d(found) if not isinstance(default, int) else int(found)), f"catálogo de parâmetros ({key})"
            except Exception:   # catálogo indisponível (sessão de teste simplificada): fica o padrão declarado
                pass
        out[key] = {"valor": value, "origem": origin, "descricao": label}
    return out


def _subject(prop) -> dict:
    return {"city": prop.city, "neighborhood": prop.neighborhood, "property_type": prop.property_type, "bedrooms": prop.bedrooms,
            "parking_spots": prop.parking_spots, "area": prop.private_area_m2 if prop.private_area_m2 else prop.area_m2,
            "area_base": "PRIVATIVA" if prop.private_area_m2 else "TOTAL"}


def _comparable_dict(c) -> dict:
    keys = ("id", "kind", "price", "rent", "area_m2", "source", "url", "price_type", "collected_at", "listing_date", "address", "neighborhood", "city",
            "state", "property_type", "bedrooms", "parking_spots", "condition", "condo_fee", "iptu", "area_basis", "distance_km", "listing_ref",
            "notes", "excluded", "exclusion_reason")
    return {k: getattr(c, k, None) for k in keys}


def _line(key: str, label: str, value: Decimal | None, status: str, origem: str, *, conservador: Decimal | None = None, base: Decimal | None = None,
          observacao: str = "", critico: bool = False, tratamento_base: str | None = None, tratamento_conservador: str | None = None, **extra) -> dict:
    """Linha de custo. Para item PENDENTE, cada cenário declara o tratamento: ``valor_base`` (reserva usada nos cenários base e
    otimista) e ``valor_conservador`` (reserva maior ou teto contratual). Sem valor declarado, o item fica FORA da soma e o
    cenário é marcado como incompleto: pendência nunca entra como zero silencioso."""
    known = value if status in (INFORMADO, ESTIMADO, NAO_APLICAVEL) else None
    cons = conservador if conservador is not None else known
    bas = base if base is not None else known
    line = {"chave": key, "descricao": label, "valor": _q(value), "status": status, "origem": origem,
            "valor_conservador": _q(cons), "valor_base": _q(bas), "observacao": observacao, "critico": critico,
            "tratamento_base": tratamento_base or ("valor do item" if bas is not None and status != PENDENTE else ("sem valor: fora da soma" if bas is None else "reserva")),
            "tratamento_conservador": tratamento_conservador or ("valor do item" if cons is not None and status != PENDENTE else ("sem valor: fora da soma" if cons is None else "reserva"))}
    line.update(extra)
    return line


def _manual_reserve(key: str, label: str, assumptions: dict, prefix: str, origin_key: str, missing_note: str, *, annual: bool = False) -> dict:
    """Custo sem valor real: reserva MANUAL por cenário (``<prefix>_base`` para base/otimista, ``<prefix>_conservador``), com origem
    declarada. O sistema não tem valor padrão para estes itens. Sem reserva, o item fica fora da soma (cenário incompleto). Sem reserva
    conservadora, o conservador usa a do base (nunca menos que o base)."""
    base, cons = _d(assumptions.get(f"{prefix}_base")), _d(assumptions.get(f"{prefix}_conservador"))
    if base is None and cons is None:
        return _line(key, label, None, PENDENTE, "não informado", observacao=missing_note + " Sem valor padrão do sistema: fica fora da soma.")
    origin = (assumptions.get(origin_key) or "").strip() or "reserva informada manualmente (origem não declarada)"
    unit = " por ano" if annual else ""
    cons_eff = cons if cons is not None else base
    return _line(key, label, None, PENDENTE, f"reserva manual: {origin}", base=base, conservador=cons_eff,
                 tratamento_base=(f"reserva manual de {_brl(base)}{unit} ({origin})" if base is not None else "sem reserva para o base: fora da soma"),
                 tratamento_conservador=(f"reserva manual de {_brl(cons_eff)}{unit} ({origin})"
                                         + ("" if cons is not None else "; sem reserva conservadora própria, usa a do base")),
                 observacao="Valor real não levantado: os cenários usam a reserva manual informada; o item continua PENDENTE.",
                 reserva_manual=True, origem_reserva=origin)


def _iptu_year(line: dict, conservative: bool) -> Decimal | None:
    if line.get("iptu_anual") is not None:
        return line["iptu_anual"]
    return line.get("iptu_anual_conservador" if conservative else "iptu_anual_base")


# ------------------------------------------------------------------ fonte única da exposição a débitos (v1.0.12)
# Condomínio e IPTU/tributos em atraso são lidos de UM lugar só, usado pela composição de custos (e, por ela, pelo veredito, pela
# inteligência de mercado e pela recomendação) e pelo checklist. Ordem da fonte do VALOR: dívida confirmada > dívida informada
# (cadastro legado, débito normalizado ou custo cadastrado) > estimativa condominial (provável no base, alto no conservador) >
# pendente. Consulta indisponível ou em validação nunca vira zero. Ordem da REGRA de responsabilidade: documento das condições
# da venda (trecho literal) > premissa ``condicoes_caixa`` > sem regra.
FONTE_CONFIRMADO, FONTE_INFORMADO, FONTE_ESTIMATIVA, FONTE_INDISPONIVEL, FONTE_PENDENTE = (
    "CONFIRMADO", "INFORMADO", "ESTIMATIVA", "INDISPONIVEL", "PENDENTE")
REGRA_EXCEDENTE = "COMPRADOR_ATE_LIMITE_VENDEDOR_EXCEDENTE"
REGRA_INTEGRAL_ACIMA = "COMPRADOR_ATE_LIMITE_VENDEDOR_INTEGRAL"
REGRA_COMPRADOR = "COMPRADOR_INTEGRAL"
REGRA_VENDEDOR = "VENDEDOR_INTEGRAL"
_DEBT_KINDS = {
    "condominio_atraso": {"tokens": ("CONDOM",), "codes": {"COTA_CONDOMINIAL", "MULTA_CONDOMINIAL", "JUROS_CONDOMINIAIS", "DESPESA_EXTRAORDINARIA"},
                          "cost_key": "condominio", "limit_key": "condominio_limite_pct_avaliacao", "tema": "CONDOMINIO", "default_rule": REGRA_EXCEDENTE,
                          "label": "condomínio"},
    "tributos_atraso": {"tokens": ("IPTU", "TRIBUT", "TAXA"), "codes": {"IPTU", "TAXA_MUNICIPAL", "DIVIDA_ATIVA_MUNICIPAL", "OUTRO_DEBITO_MUNICIPAL"},
                        "cost_key": "iptu", "limit_key": "tributos_limite_pct_avaliacao", "tema": "TRIBUTOS", "default_rule": REGRA_INTEGRAL_ACIMA,
                        "label": "IPTU/tributos"},
}
AVISO_ESTIMATIVA_CONDOMINIO = ("Estimativa calculada com base em informações documentais e premissas configuráveis. Não representa dívida "
                               "confirmada. Solicite declaração atualizada ao condomínio.")


def _rows(db, model, property_id: int) -> list:
    """Registros do imóvel; sessão simplificada de teste (sem ``scalars`` real) devolve lista vazia."""
    if db is None:
        return []
    try:
        from sqlalchemy import select
        rows = db.scalars(select(model).where(model.property_id == property_id).order_by(model.id)).all()
        return [r for r in rows if isinstance(r, model)]
    except Exception:
        return []


def caixa_rules(db, prop, assumptions: dict) -> dict[str, dict]:
    """Regra de responsabilidade do comprador por condomínio e por IPTU/tributos: documento > premissa > nenhuma."""
    assumptions = assumptions or {}
    out: dict[str, dict] = {key: {"tipo": None, "limite_pct": None, "comparador": None, "fonte": None, "origem": None, "trecho": None,
                                  "document_version_id": None, "chunk_id": None} for key in _DEBT_KINDS}
    sources = []
    if db is not None and prop is not None and getattr(prop, "id", None) is not None:
        try:
            from .sale_conditions import conditions_for_property
            sources = conditions_for_property(db, prop.id)
        except Exception:
            sources = []
    for key, spec in _DEBT_KINDS.items():
        for src in sources:
            clause = src.first(spec["tema"])
            if clause is None or clause.regra not in (REGRA_EXCEDENTE, REGRA_INTEGRAL_ACIMA, REGRA_COMPRADOR, REGRA_VENDEDOR):
                continue
            if clause.regra in (REGRA_EXCEDENTE, REGRA_INTEGRAL_ACIMA) and clause.limite_pct is None:
                continue
            out[key] = {"tipo": clause.regra, "limite_pct": clause.limite_pct, "comparador": clause.comparador, "fonte": "DOCUMENTO",
                        "origem": f"{src.source_label} (trecho literal)", "trecho": clause.excerpt, "document_version_id": src.document_version_id,
                        "chunk_id": clause.chunk_id}
            break
        if out[key]["tipo"] is None:
            caixa = assumptions.get("condicoes_caixa") or {}
            pct = _d(caixa.get(spec["limit_key"]))
            if pct is not None:
                out[key].update({"tipo": spec["default_rule"], "limite_pct": pct, "fonte": "PREMISSA",
                                 "origem": f"premissa do imóvel (condições informadas: {caixa.get('origem') or 'origem não declarada'})"})
    return out


def _buyer_share(debt: Decimal, rule: str | None, cap: Decimal | None) -> tuple[Decimal, Decimal]:
    """(parte do comprador, parte do vendedor/Caixa) para uma dívida conhecida."""
    if rule == REGRA_VENDEDOR:
        return ZERO, debt
    if rule == REGRA_COMPRADOR or cap is None:
        return debt, ZERO
    if rule == REGRA_EXCEDENTE:
        buyer = min(debt, cap)
        return buyer, debt - buyer
    buyer = debt if debt <= cap else ZERO      # REGRA_INTEGRAL_ACIMA; igualdade: comprador (premissa conservadora declarada)
    return buyer, debt - buyer


def debt_exposure(db, prop, assumptions: dict | None = None) -> dict[str, dict]:
    """Valor da dívida de condomínio e de IPTU/tributos em atraso, com a fonte, sem aplicar regra. Leitura apenas."""
    from . import models
    assumptions = assumptions or {}
    pid = getattr(prop, "id", None)
    normalized = _rows(db, models.PropertyDebt, pid) if pid is not None else []
    estimates = _rows(db, models.CondominiumEstimate, pid) if pid is not None else []
    costs_by_key: dict[str, Decimal] = {}
    for cost in getattr(prop, "costs", []) or []:
        k = canonical_cost_key(cost.category)
        costs_by_key[k] = costs_by_key.get(k, ZERO) + (_d(cost.amount) or ZERO)
    from .debts_service import dedupe_debts, is_real_debt, legacy_group
    legacy_all = [d for d in getattr(prop, "debts", []) or [] if str(d.status or "").upper() not in ("QUITADO", "CANCELADO", "PAGO")]
    # Débito legado com status ESTIMADO é estimativa, não dívida: nunca soma como valor informado.
    legacy_open = [d for d in legacy_all if str(d.status or "").upper() != "ESTIMADO"]
    legacy_estimated = [d for d in legacy_all if str(d.status or "").upper() == "ESTIMADO"]
    # Mesmo débito no legado e na Central (ou duas vezes): entra uma vez; o descartado fica em ``duplicidades`` (rastreável).
    kept_legacy, kept_norm, duplicates = dedupe_debts(legacy_open, [d for d in normalized if is_real_debt(d)])
    group_of = {"condominio_atraso": "CONDOMINIO", "tributos_atraso": "MUNICIPAL"}
    amount = lambda d: d.updated_amount if d.updated_amount is not None else d.original_amount  # noqa: E731
    out: dict[str, dict] = {}
    for key, spec in _DEBT_KINDS.items():
        group = group_of[key]
        # Cada débito legado pertence a um grupo só (condomínio tem precedência: "taxa condominial" não é tributo).
        legacy = [d for d in kept_legacy if legacy_group(d.category) == group]
        legacy_used = [d for d in legacy_all if legacy_group(d.category) == group]
        mine = [d for d in normalized if str(d.debt_type_code or "").upper() in spec["codes"] and d.status not in ("QUITADO", "CANCELADO")]
        real = [d for d in kept_norm if str(d.debt_type_code or "").upper() in spec["codes"]]
        unavailable = [d for d in mine if d.status in ("INDISPONIVEL", "EM_VALIDACAO")]
        estimated = [d for d in mine if (d.status == "ESTIMADO" or d.nature == "ESTIMATIVA_OPERACIONAL") and amount(d) is not None]
        estimated_legacy = [d for d in legacy_estimated if legacy_group(d.category) == group and d.amount is not None]
        dup_here = [x for x in duplicates if any(x["descartado"] == f"Debt #{getattr(d, 'id', None)}" for d in legacy_used)
                    or any(x["descartado"] == f"PropertyDebt #{getattr(d, 'id', None)}" for d in mine)]
        info: dict[str, Any] = {"chave": key, "valor": None, "fonte": FONTE_PENDENTE, "origem": "valor da dívida não informado", "registros": 0,
                                "estimativa": None, "indisponivel": bool(unavailable), "legado": legacy_used, "duplicidades": dup_here,
                                "componentes": [], "custo_ignorado": None}
        if legacy or real:
            total = sum((_d(d.amount) or ZERO for d in legacy), ZERO) + sum((_d(amount(d)) for d in real), ZERO)
            confirmed = all(str(d.status or "").upper() == "CONFIRMADO" for d in legacy) and all(d.status == "CONFIRMADO" for d in real)
            parts = (["dívida cadastrada"] if legacy else []) + (["débito da Central de Débitos"] if real else [])
            info.update({"valor": _q(total), "fonte": FONTE_CONFIRMADO if confirmed else FONTE_INFORMADO, "origem": " + ".join(parts),
                         "registros": len(legacy) + len(real),
                         "componentes": [{"origem": "Debt", "id": getattr(d, "id", None), "valor": _q(_d(d.amount)), "status": str(d.status or "")} for d in legacy]
                         + [{"origem": "PropertyDebt", "id": getattr(d, "id", None), "valor": _q(_d(amount(d))), "status": d.status} for d in real]})
            if spec["cost_key"] in costs_by_key:
                # Custo cadastrado do mesmo tipo não soma de novo à dívida (seria a mesma despesa); fica registrado.
                info["custo_ignorado"] = _q(costs_by_key[spec["cost_key"]])
        elif spec["cost_key"] in costs_by_key:
            info.update({"valor": _q(costs_by_key[spec["cost_key"]]), "fonte": FONTE_INFORMADO, "origem": "custo cadastrado", "registros": 1, "custo": True,
                         "componentes": [{"origem": "Cost", "id": None, "valor": _q(costs_by_key[spec["cost_key"]]), "status": "CADASTRADO"}]})
        elif unavailable:
            info.update({"fonte": FONTE_INDISPONIVEL, "origem": "consulta indisponível ou em validação (não é zero)", "registros": len(unavailable)})
        if info["valor"] is None:
            latest = max(estimates, key=lambda e: e.id) if (estimates and key == "condominio_atraso") else None
            if latest is not None and latest.scenario_provavel is not None:
                info["estimativa"] = {"id": latest.id, "base": _q(_d(latest.scenario_provavel)),
                                      "conservador": _q(_d(latest.scenario_conservador) or _d(latest.scenario_provavel)),
                                      "baixo": _q(_d(latest.scenario_otimista)), "confianca": latest.confidence,
                                      "origem": f"estimativa condominial nº {latest.id} (provável no base, alto no conservador)"}
            elif estimated or estimated_legacy:
                total = _q(sum((_d(amount(d)) for d in estimated), ZERO) + sum((_d(d.amount) for d in estimated_legacy), ZERO))
                where = " + ".join((["Central de Débitos"] if estimated else []) + (["cadastro de dívidas"] if estimated_legacy else []))
                info["estimativa"] = {"id": None, "base": total, "conservador": total, "baixo": None, "confianca": "BAIXA",
                                      "origem": f"estimativa cadastrada ({where})"}
            if info["estimativa"] is not None:
                info.update({"fonte": FONTE_ESTIMATIVA, "origem": info["estimativa"]["origem"]
                             + ("; consulta indisponível ou em validação" if unavailable else "")})
        out[key] = info
    return out


def acquisition_costs(prop, auction, premises: dict, assumptions: dict, sale_estimate: dict, db=None) -> dict:
    """Custos de aquisição e posse, por item, com status e origem. ``assumptions`` = ``Auction.financial_assumptions``."""
    acquisition = _d(auction.acquisition_value) if auction and auction.acquisition_value is not None else (_d(auction.bid_value) if auction else None)
    appraisal = _d(auction.appraisal_value) if auction else None
    area = _d(prop.private_area_m2) or _d(prop.area_m2)
    costs_by_key: dict[str, Decimal] = {}
    for cost in prop.costs:
        key = canonical_cost_key(cost.category)
        costs_by_key[key] = costs_by_key.get(key, ZERO) + (_d(cost.amount) or ZERO)
    debts_open = [d for d in prop.debts if str(d.status or "").upper() not in ("QUITADO", "CANCELADO", "PAGO")]
    used_debts: set[int] = set()
    lines: list[dict] = []
    lines.append(_line("aquisicao", "Preço de aquisição", acquisition, INFORMADO if acquisition is not None else PENDENTE, "cadastro do leilão/venda", critico=acquisition is None))
    consumed: set[str] = set()   # chaves de custo cadastrado já usadas em alguma linha (o resto vira linha própria: nada é omitido)
    commission = ZERO
    if auction is not None and auction.commission_fixed is not None:
        commission = _d(auction.commission_fixed)
        lines.append(_line("comissao", "Comissão do leiloeiro", commission, INFORMADO, "cadastro do leilão (valor fixo)"))
    elif auction is not None and auction.commission_percent is not None and acquisition is not None:
        commission = acquisition * _d(auction.commission_percent) / Decimal("100")
        lines.append(_line("comissao", "Comissão do leiloeiro", commission, INFORMADO,
                           "cadastro do leilão/venda (venda direta: sem leiloeiro)" if commission == ZERO else f"cadastro do leilão ({_pct(_d(auction.commission_percent) / Decimal('100'))})"))
    elif "comissao" in costs_by_key:
        lines.append(_line("comissao", "Comissão do leiloeiro", costs_by_key["comissao"], INFORMADO, "custo cadastrado"))
    else:
        lines.append(_line("comissao", "Comissão do leiloeiro", None, PENDENTE, "não informada", critico=True))
    consumed.add("comissao")   # com comissão no leilão, custo cadastrado de comissão não é somado de novo (sem dupla contagem)
    # ITBI: custo informado > alíquota declarada (com origem) > pendente. Base = maior entre aquisição e base mínima informada.
    itbi_rate = _d(assumptions.get("itbi_aliquota"))
    itbi_base_min = _d(assumptions.get("itbi_base_minima"))
    itbi_rate_pct = None
    consumed.update({"itbi", "registro", "reforma", "desocupacao", "condominio", "iptu"})
    municipality_id = municipality_id_for(db, prop)
    itbi_origin = assumptions.get("itbi_origem") or "alíquota informada nas premissas"
    if itbi_rate is None and "itbi" not in costs_by_key:
        itbi_rate, catalog_origin = catalog_value(db, "viabilidade.itbi_aliquota", municipality_id)
        itbi_origin = catalog_origin or itbi_origin
    if "itbi" in costs_by_key:
        lines.append(_line("itbi", "ITBI", costs_by_key["itbi"], INFORMADO, "custo cadastrado"))
    elif itbi_rate is not None and acquisition is not None:
        base = max(acquisition, itbi_base_min or ZERO)
        itbi_rate_pct = itbi_rate
        lines.append(_line("itbi", "ITBI", base * itbi_rate, ESTIMADO, itbi_origin,
                           observacao=f"Alíquota {_pct(itbi_rate)} sobre base de {_brl(base)} (maior entre aquisição e base mínima informada)."))
    else:
        lines.append(_line("itbi", "ITBI", None, PENDENTE, "não informado", observacao="Informe a alíquota municipal e a base (valor venal).", critico=True))
    for key, label, reserve_key in (("registro", "Escritura e registro", "viabilidade.reserva_registro_pct"), ("certidoes", "Certidões", "viabilidade.reserva_certidoes")):
        informed = costs_by_key.get(key) if key == "registro" else _d(assumptions.get("certidoes"))
        if informed is None and key == "registro" and assumptions.get("registro_estimado") not in (None, ""):
            lines.append(_line(key, label, _d(assumptions["registro_estimado"]), ESTIMADO, assumptions.get("registro_origem") or "premissa do imóvel"))
        elif informed is not None:
            lines.append(_line(key, label, informed, INFORMADO, "custo cadastrado" if key == "registro" else "premissa do imóvel"))
        else:
            reserve = premises[reserve_key]["valor"]
            amount = (acquisition * reserve) if key == "registro" and acquisition is not None else (reserve if key == "certidoes" else None)
            rule = (f"reserva de {_pct(reserve)} da aquisição" if key == "registro" else f"reserva de {_brl(reserve)}") + f" ({premises[reserve_key]['origem']})"
            lines.append(_line(key, label, None, PENDENTE, "não informado", conservador=amount, base=amount, tratamento_base=rule, tratamento_conservador=rule,
                               observacao=f"Valor real não informado; todos os cenários usam {rule}.", reserva_pct=reserve if key == "registro" else None))
    # Condomínio e tributos em atraso: fonte única (debt_exposure + caixa_rules). Valor: confirmado > informado > estimativa > pendente;
    # regra: documento das condições da venda > premissa > sem regra. A regra é aplicada DEPOIS do valor (inclusive da estimativa).
    exposure = debt_exposure(db, prop, assumptions)
    rules = caixa_rules(db, prop, assumptions)
    for key, label in (("condominio_atraso", "Condomínio em atraso"), ("tributos_atraso", "IPTU e demais tributos em atraso")):
        info, rule_info = exposure[key], rules[key]
        used_debts.update(id(d) for d in info.get("legado") or [])
        kind, limit_pct = rule_info["tipo"], rule_info["limite_pct"]
        cap = _q(appraisal * limit_pct) if (limit_pct is not None and appraisal is not None and kind in (REGRA_EXCEDENTE, REGRA_INTEGRAL_ACIMA)) else None
        who = "a Caixa" if rule_info["fonte"] == "PREMISSA" or "CAIXA" in str(rule_info.get("trecho") or "").upper() else "o vendedor"
        prefix = "Regra Caixa" if who == "a Caixa" else "Regra da venda"
        if kind == REGRA_EXCEDENTE and cap is not None:
            rule = f"{prefix}: comprador paga a dívida até {_pct(limit_pct)} da avaliação ({_brl(cap)}); {who} paga o excedente."
        elif kind == REGRA_INTEGRAL_ACIMA and cap is not None:
            rule = (f"{prefix}: se a dívida for menor que {_pct(limit_pct)} da avaliação ({_brl(cap)}), o comprador paga tudo; se for maior, "
                    f"{who} paga integralmente. {PREMISSA_IGUALDADE_IPTU}")
        elif kind == REGRA_COMPRADOR:
            rule = f"{prefix}: dívida integralmente por conta do comprador, sem limite."
        elif kind == REGRA_VENDEDOR:
            rule = f"{prefix}: dívida por conta de {who}."
        else:
            rule = None
        rule_origin = f" Fonte da regra: {rule_info['origem']}." if rule_info["origem"] else ""
        caixa_fields = {"divida_total": None, "responsabilidade_comprador": None, "assumido_caixa": None, "limite_responsabilidade": cap, "regra": rule,
                        "regra_tipo": kind, "regra_fonte": rule_info["fonte"], "regra_origem": rule_info["origem"], "regra_trecho": rule_info["trecho"],
                        "premissa_conservadora": PREMISSA_IGUALDADE_IPTU if (kind == REGRA_INTEGRAL_ACIMA and cap is not None) else None,
                        "fonte_valor": ("CUSTO" if info.get("custo") else "DIVIDA") if info["valor"] is not None else None,
                        "fonte_divida": info["fonte"], "origem_divida": info["origem"],
                        # Rastreabilidade (revisão PR #7): registros somados, duplicidades descartadas e custo não somado de novo.
                        "componentes": info.get("componentes") or [], "duplicidades": info.get("duplicidades") or [],
                        "custo_ignorado": info.get("custo_ignorado"), "consulta_indisponivel": bool(info.get("indisponivel"))}
        ressalvas = []
        if info.get("indisponivel"):
            ressalvas.append("Consulta indisponível ou em validação: o débito não foi apurado na fonte" + (
                "; o valor exibido é ESTIMATIVA, não dívida confirmada." if info["fonte"] == FONTE_ESTIMATIVA else "."))
        if info.get("duplicidades"):
            ressalvas.append(f"{len(info['duplicidades'])} registro(s) do mesmo débito em cadastros diferentes contado(s) uma vez só.")
        if info.get("custo_ignorado") is not None:
            ressalvas.append(f"Custo cadastrado de {_brl(info['custo_ignorado'])} do mesmo tipo não somado: já há dívida cadastrada.")
        caixa_fields["ressalvas"] = ressalvas
        if info["fonte"] == FONTE_ESTIMATIVA:
            caixa_fields["natureza_valor"] = "ESTIMATIVA"
        suffix = (" " + " ".join(ressalvas)) if ressalvas else ""
        debt = info["valor"]
        if debt is not None:
            buyer, seller = _buyer_share(debt, kind, cap)
            if rule is None:
                note = "Dívida cadastrada, sem regra de limitação informada: integralmente do comprador."
            else:
                note = rule + rule_origin + (" Dívida igual ao limite: aplicada a premissa conservadora." if (kind == REGRA_INTEGRAL_ACIMA and debt == cap) else "")
            caixa_fields.update({"divida_total": debt, "responsabilidade_comprador": buyer, "assumido_caixa": seller,
                                 "exposicao": {"divida_potencial": {"base": debt, "conservador": debt}, "divida_confirmada": debt if info["fonte"] == FONTE_CONFIRMADO else None,
                                               "responsabilidade_comprador": {"base": buyer, "conservador": buyer},
                                               "responsabilidade_caixa": {"base": seller, "conservador": seller}, "limite": cap,
                                               "valor_considerado": {"base": buyer, "conservador": buyer}}})
            origin = f"dívida confirmada ({info['origem']})" if info["fonte"] == FONTE_CONFIRMADO else info["origem"]
            lines.append(_line(key, label, buyer, INFORMADO, origin, observacao=note + suffix, **caixa_fields))
        elif info["fonte"] == FONTE_ESTIMATIVA and kind != REGRA_VENDEDOR:
            est = info["estimativa"]
            buyer_base, seller_base = _buyer_share(est["base"], kind, cap)
            buyer_cons, seller_cons = _buyer_share(est["conservador"], kind, cap)
            caixa_fields.update({"estimativa": est, "aviso_estimativa": AVISO_ESTIMATIVA_CONDOMINIO,
                                 "exposicao": {"divida_potencial": {"base": est["base"], "conservador": est["conservador"]}, "divida_confirmada": None,
                                               "responsabilidade_comprador": {"base": buyer_base, "conservador": buyer_cons},
                                               "responsabilidade_caixa": {"base": seller_base, "conservador": seller_cons}, "limite": cap,
                                               "valor_considerado": {"base": buyer_base, "conservador": buyer_cons}}})
            lines.append(_line(key, label, buyer_base, ESTIMADO, est["origem"], base=buyer_base, conservador=buyer_cons,
                               tratamento_base=f"estimativa provável ({_brl(est['base'])}) após a regra: {_brl(buyer_base)}",
                               tratamento_conservador=f"estimativa alta ({_brl(est['conservador'])}) após a regra: {_brl(buyer_cons)}",
                               observacao=f"ESTIMATIVA, não dívida confirmada. {AVISO_ESTIMATIVA_CONDOMINIO} "
                               + (rule + rule_origin if rule else "Sem regra de limitação: estimativa integral do comprador.") + suffix,
                               **caixa_fields))
        elif kind == REGRA_VENDEDOR:
            caixa_fields["exposicao"] = {"divida_potencial": None, "divida_confirmada": None, "responsabilidade_comprador": {"base": ZERO, "conservador": ZERO},
                                         "responsabilidade_caixa": None, "limite": None, "valor_considerado": {"base": ZERO, "conservador": ZERO}}
            lines.append(_line(key, label, ZERO, NAO_APLICAVEL, f"regra da venda ({rule_info['origem']})", observacao=rule, **caixa_fields))
        elif cap is not None:
            # Dívida desconhecida: o máximo que pode recair sobre o comprador é o limite (no IPTU, valor imediatamente abaixo dele).
            # Cenário base/otimista não têm estimativa honesta do valor: o item fica fora da soma e o cenário é marcado incompleto.
            unavailable = " Consulta indisponível ou em validação: não é zero." if info["fonte"] == FONTE_INDISPONIVEL else ""
            caixa_fields["exposicao"] = {"divida_potencial": None, "divida_confirmada": None, "responsabilidade_comprador": {"base": None, "conservador": cap},
                                         "responsabilidade_caixa": None, "limite": cap, "valor_considerado": {"base": None, "conservador": cap}}
            lines.append(_line(key, label, None, PENDENTE, info["origem"], conservador=cap,
                               tratamento_conservador=f"teto de responsabilidade do comprador ({_brl(cap)})",
                               tratamento_base="sem valor: fora da soma (cenário incompleto; veja o efeito do teto)",
                               observacao=f"Dívida desconhecida.{unavailable} {rule}{rule_origin} O assumido pelo vendedor só pode ser calculado com o valor da dívida.",
                               **caixa_fields))
        else:
            unavailable = " Consulta indisponível ou em validação: não é zero." if info["fonte"] == FONTE_INDISPONIVEL else ""
            caixa_fields["exposicao"] = {"divida_potencial": None, "divida_confirmada": None, "responsabilidade_comprador": None, "responsabilidade_caixa": None,
                                         "limite": None, "valor_considerado": {"base": None, "conservador": None}}
            lines.append(_line(key, label, None, PENDENTE, info["origem"] if info["fonte"] == FONTE_INDISPONIVEL else "não informado",
                               observacao=("Sem valor da dívida e sem regra de limitação: risco sem teto conhecido." if rule is None
                                           else f"Sem valor da dívida. {rule}{rule_origin}") + unavailable,
                               critico=True, **caixa_fields))
    # Reforma, regularização, desocupação.
    reforma = costs_by_key.get("reforma") if "reforma" in costs_by_key else _d(assumptions.get("reforma"))
    reserve_m2 = premises["viabilidade.reserva_reforma_m2"]["valor"]
    if reforma is not None:
        lines.append(_line("reforma", "Reforma", reforma, INFORMADO if "reforma" in costs_by_key else ESTIMADO, "custo cadastrado" if "reforma" in costs_by_key else "premissa do imóvel"))
    else:
        base_m2 = premises["viabilidade.reserva_reforma_m2_base"]["valor"]
        lines.append(_line("reforma", "Reforma", None, PENDENTE, "estado de conservação não vistoriado",
                           conservador=(reserve_m2 * area) if area else None, base=(base_m2 * area) if area else None,
                           tratamento_base=f"reserva de {_brl(base_m2)}/m² ({premises['viabilidade.reserva_reforma_m2_base']['origem']})",
                           tratamento_conservador=f"reserva de {_brl(reserve_m2)}/m² ({premises['viabilidade.reserva_reforma_m2']['origem']})",
                           observacao="Sem vistoria: base usa reparo leve; conservador, reforma mais ampla."))
    regularizacao = _d(assumptions.get("regularizacao"))
    if regularizacao is not None:
        lines.append(_line("regularizacao", "Regularização", regularizacao, ESTIMADO, assumptions.get("regularizacao_origem") or "premissa do imóvel"))
    else:
        line = _manual_reserve("regularizacao", "Regularização", assumptions, "regularizacao_reserva",
                               "regularizacao_reserva_origem", "Sem levantamento de pendências de regularização além da matrícula.")
        reserve, reserve_origin = catalog_value(db, "viabilidade.regularizacao_padrao", municipality_id)
        if not line.get("reserva_manual") and reserve is not None:
            rule = f"reserva de {_brl(reserve)} ({reserve_origin})"
            line = _line("regularizacao", "Regularização", None, PENDENTE, "não informado", base=reserve, conservador=reserve,
                         tratamento_base=rule, tratamento_conservador=rule,
                         observacao=f"Sem levantamento de regularização: todos os cenários usam a {rule}.")
        lines.append(line)
    occupancy = max(prop.occupancy_analyses, key=lambda o: o.id) if prop.occupancy_analyses else None
    if "desocupacao" in costs_by_key:
        lines.append(_line("desocupacao", "Desocupação", costs_by_key["desocupacao"], INFORMADO, "custo cadastrado"))
    elif occupancy is not None and occupancy.estimated_cost is not None:
        lines.append(_line("desocupacao", "Desocupação", _d(occupancy.estimated_cost), ESTIMADO, "análise de ocupação"))
    elif occupancy is not None and str(occupancy.status or "").upper() in ("DESOCUPADO", "LIVRE"):
        lines.append(_line("desocupacao", "Desocupação", ZERO, NAO_APLICAVEL, "análise de ocupação: desocupado"))
    elif occupancy is not None and str(occupancy.status or "").upper() in ("OCUPADO_CONFIRMADO", "OCUPADO_TERCEIROS"):
        # v1.0.12: ocupação confirmada pelo usuário sem custo estimado: a reserva entra em todos os cenários (não só no conservador).
        reserve = premises["viabilidade.reserva_desocupacao"]["valor"]
        rule = f"reserva de {_brl(reserve)} ({premises['viabilidade.reserva_desocupacao']['origem']})"
        lines.append(_line("desocupacao", "Desocupação", None, PENDENTE, "ocupação confirmada; custo de desocupação não estimado", base=reserve,
                           conservador=reserve, tratamento_base=rule, tratamento_conservador=rule,
                           observacao="Imóvel registrado como ocupado: todos os cenários usam a reserva até o custo real ser estimado."))
    else:
        reserve = premises["viabilidade.reserva_desocupacao"]["valor"]
        lines.append(_line("desocupacao", "Desocupação", None, PENDENTE, "ocupação não verificada", conservador=reserve,
                           tratamento_conservador=f"reserva de {_brl(reserve)} ({premises['viabilidade.reserva_desocupacao']['origem']})",
                           tratamento_base="sem valor: fora da soma (ocupação não verificada; veja o efeito da reserva)",
                           observacao="Ocupação não verificada: o conservador supõe imóvel ocupado; base e otimista ficam incompletos até a verificação."))
    # Custos e dívidas cadastrados que não pertencem a nenhuma linha acima entram como linhas próprias (antes eram omitidos).
    labels = {"custos_juridicos": "Custos jurídicos", "debitos": "Débitos cadastrados como custo", "carregamento": "Carregamento cadastrado como custo", "outros": "Outros custos"}
    for key in sorted(set(costs_by_key) - consumed):
        lines.append(_line(f"custo_{key}", labels.get(key, f"Custo cadastrado ({key})"), costs_by_key[key], INFORMADO, "custo cadastrado"))
    other_debts = [d for d in debts_open if id(d) not in used_debts]
    if other_debts:
        lines.append(_line("outras_dividas", "Outras dívidas cadastradas", sum((_d(d.amount) or ZERO for d in other_debts), ZERO), INFORMADO, "dívida cadastrada",
                           observacao=", ".join(sorted({str(d.category) for d in other_debts}))))
    # IPTU durante a posse: valor anual informado > pendente (o IPTU dos anúncios não é usado: não se sabe se é mensal ou anual).
    # Valor anual informado vale para todos os cenários; sem ele, reserva anual manual por cenário (com origem); sem ambos, PENDENTE.
    iptu_year = _d(assumptions.get("iptu_anual"))
    if iptu_year is not None:
        line = _line("iptu_posse", "IPTU durante a posse", None, ESTIMADO, assumptions.get("iptu_anual_origem") or "premissa do imóvel (IPTU anual)",
                     observacao="Proporcional ao prazo de cada cenário.")
        line.update({"iptu_anual": iptu_year, "iptu_anual_base": iptu_year, "iptu_anual_conservador": iptu_year})
    else:
        line = _manual_reserve("iptu_posse", "IPTU durante a posse", assumptions, "iptu_anual_reserva", "iptu_reserva_origem",
                               "Informe o IPTU anual (carnê ou certidão da Prefeitura) ou uma reserva anual com origem.", annual=True)
        catalog_iptu, catalog_iptu_origin = catalog_value(db, "iptu.valor_anual_padrao", municipality_id)
        if not line.get("reserva_manual") and catalog_iptu is not None:
            rule = f"reserva anual de {_brl(catalog_iptu)} ({catalog_iptu_origin})"
            line = _line("iptu_posse", "IPTU durante a posse", None, PENDENTE, "não informado", base=catalog_iptu, conservador=catalog_iptu,
                         tratamento_base=rule, tratamento_conservador=rule,
                         observacao="IPTU real não levantado: os cenários usam o IPTU anual padrão do catálogo, proporcional ao prazo.")
        # valor_base/valor_conservador aqui são ANUAIS; cada cenário aplica o proporcional ao prazo (_amount).
        line.update({"iptu_anual": None, "iptu_anual_base": line["valor_base"], "iptu_anual_conservador": line["valor_conservador"], "valores_anuais": True})
    lines.append(line)
    # Manutenção durante a posse: carregamento mensal informado > mediana do condomínio dos comparáveis (estimado) > custos mensais
    # padrão do catálogo > condomínio mensal padrão do catálogo > pendente.
    monthly = _d(assumptions.get("carregamento_mensal"))
    monthly_origin = "premissa do imóvel"
    if monthly is None:
        fees = [r for r in sale_estimate.get("_condo_fees", [])]
        if fees:
            monthly = mk.median(fees)
            monthly_origin = f"mediana do condomínio de {len(fees)} anúncio(s) comparável(is); IPTU não incluído"
    for key in ("viabilidade.custos_mensais_padrao", "condominio.valor_mensal_referencia"):
        if monthly is None:
            monthly, found_origin = catalog_value(db, key, municipality_id)
            monthly_origin = found_origin or monthly_origin
    return {"linhas": lines, "aquisicao": acquisition, "avaliacao": appraisal, "carregamento_mensal": monthly,
            "carregamento_origem": monthly_origin if monthly is not None else None, "itbi_aliquota": itbi_rate_pct, "itbi_base_minima": itbi_base_min,
            "registro_reserva_pct": premises["viabilidade.reserva_registro_pct"]["valor"]}


# Custo de aquisição dedutível no ganho de capital de pessoa física (regras da Receita Federal, IN SRF 84/2001): preço, comissão,
# ITBI, escritura/registro e benfeitorias (reforma com comprovante). Condomínio/IPTU da posse, dívidas em atraso, certidões,
# desocupação e regularização NÃO reduzem a base (estimativa prudente: mais imposto). Isenções (imóvel único até R$ 440 mil,
# reinvestimento em 180 dias) e o fator de redução por tempo de posse não são aplicados.
IR_DEDUCTIBLE = frozenset({"aquisicao", "comissao", "itbi", "registro", "reforma"})
FORMULA = ("investimento = soma dos itens incluídos; venda líquida = venda − corretagem; base do IR = venda líquida − custo de aquisição "
           "dedutível; IR = base × alíquota; resultado = venda líquida − IR − investimento; ROI = resultado ÷ investimento; "
           "margem de segurança = 1 − (venda de equilíbrio ÷ venda)")


def _amount(line: dict, conservative: bool, months: int) -> Decimal | None:
    if line["chave"] == "iptu_posse":
        year = _iptu_year(line, conservative)
        return year * Decimal(months) / Decimal("12") if year is not None else None
    return line["valor_conservador"] if conservative else line.get("valor_base")


def _value_kind(line: dict, amount: Decimal | None) -> str:
    """Natureza do valor usado no cenário, para a tela separar o que é confirmado do que é reserva, teto ou ausente."""
    if amount is None:
        return "FORA_DA_SOMA"
    if line["status"] == INFORMADO:
        return "CONFIRMADO"
    if line["status"] == NAO_APLICAVEL:
        return "NAO_APLICAVEL"
    if line["status"] == ESTIMADO:
        return "ESTIMADO"
    if line.get("limite_responsabilidade") is not None:
        return "TETO_CAIXA"
    return "RESERVA_MANUAL" if line.get("reserva_manual") else "RESERVA"


def _break_even(investment: Decimal, deductible: Decimal, c: Decimal, t: Decimal) -> Decimal | None:
    """Venda em que o resultado é zero: V(1−c) − t·max(V(1−c) − D, 0) = investimento."""
    if c >= ONE:
        return None
    if investment <= deductible:            # no equilíbrio não há ganho tributável
        return investment / (ONE - c)
    if t >= ONE:
        return None
    return (investment - t * deductible) / ((ONE - c) * (ONE - t))


def _scenario(name: str, value: Decimal | None, lines: list[dict], *, conservative: bool, months: int, monthly: Decimal | None,
              acquisition: Decimal | None, appraisal: Decimal | None, sale: SaleAssumptions, rent: Decimal | None, premises: dict,
              rent_indicative: bool = False) -> dict:
    """Cenário com composição completa e reprodutível: todos os valores são arredondados ao centavo ANTES de somar, então a
    tela fecha exatamente (soma dos itens = investimento; venda − corretagem − IR − investimento = resultado)."""
    value = _q(value)
    items: list[dict] = []
    pending: list[str] = []
    reserves: list[str] = []
    for line in lines:
        amount = _q(_amount(line, conservative, months))
        treatment = line.get("tratamento_conservador" if conservative else "tratamento_base") or ""
        if amount is None:
            basis = None
        elif line["status"] == PENDENTE:
            basis = treatment or "reserva"
            reserves.append(f"{line['descricao']}: {treatment}")
        else:
            basis = {INFORMADO: "valor confirmado", ESTIMADO: "estimativa", NAO_APLICAVEL: "não aplicável"}.get(line["status"], line["status"])
        items.append({"chave": line["chave"], "descricao": line["descricao"], "valor": amount, "status": line["status"], "incluido": amount is not None,
                      "base_valor": basis, "origem": line["origem"], "dedutivel_ir": line["chave"] in IR_DEDUCTIBLE,
                      "teto_conservador": _q(_amount(line, True, months)) if amount is None else None,
                      "reserva_manual": bool(line.get("reserva_manual")) and amount is not None,
                      "tipo_valor": _value_kind(line, amount)})
        if amount is None and line["status"] == PENDENTE:
            pending.append(line["descricao"])
    carrying = _q(monthly * Decimal(months)) if monthly is not None else None
    items.append({"chave": "manutencao_posse", "descricao": f"Condomínio durante a posse ({months} meses × {_brl(monthly)})" if monthly is not None else "Condomínio durante a posse",
                  "valor": carrying, "status": ESTIMADO if carrying is not None else PENDENTE, "incluido": carrying is not None,
                  "base_valor": "estimativa" if carrying is not None else None, "origem": "carregamento mensal", "dedutivel_ir": False,
                  "teto_conservador": None, "tipo_valor": "ESTIMADO" if carrying is not None else "FORA_DA_SOMA"})
    if carrying is None:
        pending.append("Condomínio durante a posse")
    investment = sum((i["valor"] for i in items if i["incluido"]), ZERO)
    deductible = sum((i["valor"] for i in items if i["incluido"] and i["dedutivel_ir"]), ZERO)
    # Efeito, sobre o resultado, dos itens fora da soma que têm teto/reserva conhecidos (não dedutíveis no IR: efeito 1 para 1;
    # dedutíveis reduzem também o IR). Mostra quanto o resultado pode cair quando a pendência for resolvida no pior caso.
    left_out = [i for i in items if not i["incluido"] and i["teto_conservador"] is not None]
    out = {"cenario": name, "valor_venda": value, "prazo_meses": months, "custos_aquisicao_posse": investment - (carrying or ZERO), "carregamento": carrying,
           "investimento_total": investment, "custos_pendentes_nao_incluidos": pending, "completo": not pending,
           "premissas": {"tratamento_pendencias": reserves + [f"{p}: sem valor, fora da soma" for p in pending],
                         "prazo_meses": months, "corretagem_venda": sale.corretagem_pct, "ir_ganho_capital": sale.tributo_pct}}
    c = sale.corretagem_pct or ZERO
    t = sale.tributo_pct or ZERO
    composition = {"itens": items, "investimento_total": investment, "despesas_financeiras": {"valor": ZERO, "observacao": "Compra à vista: financiamento e custo de oportunidade do capital não modelados."},
                   "formula": FORMULA}
    if value is None or investment <= ZERO:
        out.update({"resultado_liquido": None, "roi": None, "margem_seguranca": None, "desconto_sobre_mercado": None, "observacao": "Sem valor de venda estimado.",
                    "composicao": composition})
        return out
    brokerage = _q(value * c)
    net_sale = value - brokerage
    if sale.tax_base == TAX_BASE_VENDA:
        # Tributo sobre o valor de venda (premissa do usuário com base VENDA): não depende do custo de aquisição.
        tax_base = value
        tax = _q(value * t)
        break_even = investment / (ONE - c - t) if (ONE - c - t) > ZERO else None
    else:
        tax_base = max(net_sale - deductible, ZERO)
        tax = _q(tax_base * t)
        break_even = _break_even(investment, deductible, c, t)
    result = net_sale - tax - investment
    composition.update({
        "venda_bruta": value,
        "corretagem_venda": {"valor": brokerage, "percentual": c, "origem": premises["venda.corretagem_pct"]["origem"]},
        "venda_liquida": net_sale, "custo_aquisicao_dedutivel_ir": deductible, "base_ir": tax_base,
        "ir_ganho_capital": {"valor": tax, "aliquota": t, "origem": premises["venda.tributo_ganho_pct"]["origem"],
                             "observacao": "Sem isenções nem fator de redução; condomínio, IPTU, dívidas, certidões e desocupação não reduzem a base."},
        "resultado_liquido": result, "venda_equilibrio": _q(break_even),
        "conferencia": {"itens_somam_investimento": sum((i["valor"] for i in items if i["incluido"]), ZERO) == investment,
                        "resultado_reproduz": value - brokerage - tax - investment == result},
    })
    composition["itens_dedutiveis_ir"] = [{"descricao": i["descricao"], "valor": i["valor"]} for i in items if i["incluido"] and i["dedutivel_ir"]]
    composition["itens_nao_dedutiveis_ir"] = [{"descricao": i["descricao"], "valor": i["valor"]} for i in items if i["incluido"] and not i["dedutivel_ir"]]
    if left_out:
        extra = sum((i["teto_conservador"] for i in left_out), ZERO)
        extra_deductible = sum((i["teto_conservador"] for i in left_out if i["dedutivel_ir"]), ZERO)
        worse_tax = _q(max(net_sale - deductible - extra_deductible, ZERO) * t)
        line_by_key = {l["chave"]: l for l in lines}
        out["efeito_pendencias_no_teto"] = {
            "itens": [f"{i['descricao']}: {_brl(i['teto_conservador'])}" for i in left_out], "valor": extra,
            # Memória explícita: cada item somado, seu tipo e se reduz a base do IR; IR recalculado; itens sem teto conhecido.
            "detalhe": [{"chave": i["chave"], "descricao": i["descricao"], "valor": i["teto_conservador"], "dedutivel_ir": i["dedutivel_ir"],
                         "tipo": "TETO_CAIXA" if line_by_key.get(i["chave"], {}).get("limite_responsabilidade") is not None else "RESERVA",
                         "origem": line_by_key.get(i["chave"], {}).get("tratamento_conservador")} for i in left_out],
            "resultado_atual": result, "ir_atual": tax, "ir_se_no_teto": worse_tax, "ir_adicional": worse_tax - tax,
            "resultado_se_no_teto": net_sale - worse_tax - investment - extra,
            "conferencia": f"{_brl(result)} − {_brl(extra)} − IR adicional {_brl(worse_tax - tax)} = {_brl(net_sale - worse_tax - investment - extra)}",
            "sem_teto_conhecido": [i["descricao"] for i in items if not i["incluido"] and i["teto_conservador"] is None],
        }
    out.update({
        "corretagem_venda": brokerage, "tributo_venda": tax, "base_ir": tax_base, "venda_liquida": net_sale, "resultado_liquido": result,
        "roi": _q(result / investment, "0.0001"),
        "margem_seguranca": _q(ONE - break_even / value, "0.0001") if break_even is not None else None,
        "venda_equilibrio": _q(break_even),
        "desconto_sobre_mercado": _q(ONE - acquisition / value, "0.0001") if acquisition else None,
        "composicao": composition,
    })
    if rent is not None:
        iptu_line = next((l for l in lines if l["chave"] == "iptu_posse"), None)
        out["rentabilidade_aluguel"] = _rental(rent, items, monthly, _iptu_year(iptu_line, conservative) if iptu_line else None, premises, rent_indicative)
    return out


def _rental(rent: Decimal, items: list[dict], monthly: Decimal | None, iptu_year: Decimal | None, premises: dict, indicative: bool) -> dict:
    """Rentabilidade da tese de LOCAÇÃO (não da revenda). Base = investimento de aquisição e preparação, SEM o condomínio/IPTU do
    período de espera da revenda. Vacância explícita: o proprietário paga condomínio e IPTU nos meses vagos; no mês ocupado,
    o inquilino paga (contrato usual). Antes do IR sobre aluguel (carnê-leão), que depende da renda do proprietário."""
    occupancy = premises["aluguel.taxa_ocupacao"]["valor"]
    admin = premises["aluguel.taxa_administracao"]["valor"]
    base = sum((i["valor"] for i in items if i["incluido"] and i["chave"] not in ("manutencao_posse", "iptu_posse")), ZERO)
    vacant_months = Decimal("12") * (ONE - occupancy)
    gross_year = _q(rent * Decimal("12"))
    collected = _q(gross_year * occupancy)
    admin_cost = _q(collected * admin)
    vacancy_condo = _q((monthly or ZERO) * vacant_months)
    vacancy_iptu = _q(iptu_year * (ONE - occupancy)) if iptu_year is not None else None
    net = collected - admin_cost - vacancy_condo - (vacancy_iptu or ZERO)
    missing = [m for m, ok in (("condomínio mensal", monthly is not None), ("IPTU anual", iptu_year is not None)) if not ok]
    return {"aluguel_mensal": _q(rent), "aluguel_indicativo": indicative, "investimento_base": base,
            "receita_bruta_anual": gross_year, "receita_com_vacancia": collected, "taxa_administracao": admin_cost,
            "condominio_na_vacancia": vacancy_condo, "iptu_na_vacancia": vacancy_iptu, "resultado_anual_antes_ir": net,
            "bruta_anual": _q(gross_year / base, "0.0001") if base > ZERO else None,
            "liquida_anual": _q(net / base, "0.0001") if base > ZERO else None,
            "premissas": (f"ocupação {_pct(occupancy)} ({vacant_months.normalize()} mês(es) vago(s) por ano), administração {_pct(admin)} sobre o recebido, "
                          "condomínio e IPTU do proprietário só nos meses vagos; antes do IR sobre aluguel; seguro e manutenção não incluídos"),
            "completa": not missing and not indicative, "pendencias": missing + (["aluguel com base em menos de 3 comparáveis"] if indicative else [])}


def _lines_at(lines: list[dict], price: Decimal, costs: dict, commission_pct: Decimal | None) -> list[dict]:
    """Linhas de custo recalculadas para um preço de aquisição hipotético (custos proporcionais ao preço acompanham)."""
    out = []
    for line in lines:
        line = dict(line)
        if line["chave"] == "aquisicao":
            line["valor"] = line["valor_conservador"] = line["valor_base"] = price
        elif line["chave"] == "comissao" and commission_pct is not None:
            line["valor"] = line["valor_conservador"] = line["valor_base"] = price * commission_pct
        elif line["chave"] == "itbi" and costs["itbi_aliquota"] is not None:
            line["valor"] = line["valor_conservador"] = line["valor_base"] = max(price, costs["itbi_base_minima"] or ZERO) * costs["itbi_aliquota"]
        elif line["chave"] == "registro" and line["status"] == PENDENTE and line.get("reserva_pct") is not None:
            line["valor_conservador"] = line["valor_base"] = price * line["reserva_pct"]
        out.append(line)
    return out


def _solve_max_price(scen: dict, conservative: bool, roi_goal: Decimal, costs: dict, commission_pct: Decimal | None, common: dict, unknown: list[str],
                     goal_kind: str = GOAL_ROI_MINIMO) -> dict:
    """Maior preço de aquisição que atende a meta, calculado com a MESMA função do cenário (mesma composição, mesmo IR).
    Metas: ROI mínimo (resultado ÷ investimento), margem mínima (resultado ÷ venda) ou lucro mínimo (R$); ``roi_goal`` é o valor
    da meta. O indicador cai quando o preço sobe, então a busca binária converge ao centavo; comprando pelo teto, o cenário dá a meta."""
    value = scen["valor_venda"]
    base = {"cenario": scen["cenario"], "usa_reservas_conservadoras": conservative}
    if value is None:
        return {**base, "preco_maximo": None, "definitivo": False, "provisorio": False, "razao": "SEM_VALOR_DE_VENDA", "pendencias": []}
    kwargs = {k: v for k, v in common.items() if k not in ("lines", "acquisition")}

    def at_price(price: Decimal) -> tuple[Decimal | None, Decimal | None]:
        """(indicador da meta, ROI) comprando por ``price``."""
        s = _scenario(scen["cenario"], value, _lines_at(common["lines"], price, costs, commission_pct), conservative=conservative,
                      months=scen["prazo_meses"], acquisition=price, **kwargs)
        if s["resultado_liquido"] is None:
            return None, None
        roi_value = s["resultado_liquido"] / s["investimento_total"]
        if goal_kind == GOAL_LUCRO_MINIMO:
            return s["resultado_liquido"], roi_value
        if goal_kind == GOAL_MARGEM_MINIMA:
            return s["resultado_liquido"] / value, roi_value
        return roi_value, roi_value

    def meets(price: Decimal) -> bool:
        indicator = at_price(price)[0]
        return indicator is not None and indicator >= roi_goal

    low, high = Decimal("0.01"), value
    if not meets(low):
        return {**base, "preco_maximo": None, "definitivo": False, "provisorio": False, "razao": "META_INATINGIVEL", "meta_tipo": goal_kind,
                "pendencias": ["Meta financeira inatingível mesmo com preço próximo de zero (custos fixos e de venda altos demais)."]}
    if meets(high):
        low = high
    while high - low > Decimal("0.005"):
        mid = (low + high) / 2
        if meets(mid):
            low = mid
        else:
            high = mid
    price = low.quantize(Decimal("0.01"), rounding="ROUND_FLOOR")
    definitive = not unknown
    notes = [] if definitive else ["Preço máximo é ESTIMATIVA PROVISÓRIA: há custos sem valor (" + ", ".join(unknown) + "). O teto real tende a ser MENOR."]
    indicator, roi_at = at_price(price)
    return {**base, "preco_maximo": price, "definitivo": definitive, "provisorio": not definitive, "razao": "DEFINITIVO" if definitive else "PROVISORIO",
            "pendencias": notes, "meta_tipo": goal_kind, "roi_no_teto": _q(roi_at, "0.0001"),
            "indicador_no_teto": _q(indicator, "0.01" if goal_kind == GOAL_LUCRO_MINIMO else "0.0001")}


def _fill_base_with_ceiling(line: dict) -> dict:
    """Linha em que o item fora da soma do base recebe o teto/reserva conservador conhecido (IPTU: valor anual)."""
    if line["chave"] == "iptu_posse":
        if line.get("iptu_anual") is None and line.get("iptu_anual_base") is None and line.get("iptu_anual_conservador") is not None:
            return {**line, "iptu_anual_base": line["iptu_anual_conservador"]}
        return line
    if line.get("valor_base") is None and line.get("valor_conservador") is not None:
        return {**line, "valor_base": line["valor_conservador"]}
    return line


def _without(lines: list[dict], key: str) -> list[dict]:
    """Linhas com a reserva/teto de ``key`` removida (o item volta a ficar sem valor nos cenários)."""
    out = []
    for line in lines:
        if line["chave"] == key:
            line = {**line, "valor_base": None, "valor_conservador": None, "reserva_pct": None, "iptu_anual_base": None, "iptu_anual_conservador": None}
        out.append(line)
    return out


def _reserve_impacts(scen: dict, conservative: bool, roi_goal: Decimal, costs: dict, commission_pct: Decimal | None, common: dict,
                     max_price: Decimal | None, goal_kind: str = GOAL_ROI_MINIMO) -> list[dict]:
    """Quanto cada reserva/teto usado no lugar de um custo PENDENTE pesa no cenário: investimento, resultado, ROI e preço máximo.
    Calculado com a mesma função do cenário, retirando só aquela reserva (o resto da composição é idêntico)."""
    if scen["valor_venda"] is None or "composicao" not in scen:
        return []
    impacts = []
    for item in scen["composicao"]["itens"]:
        if item["status"] != PENDENTE or not item["incluido"]:
            continue
        alt_common = {**common, "lines": _without(common["lines"], item["chave"])}
        kwargs = {k: v for k, v in alt_common.items() if k != "lines"}
        alt = _scenario(scen["cenario"], scen["valor_venda"], alt_common["lines"], conservative=conservative, months=scen["prazo_meses"], **kwargs)
        alt_max = _solve_max_price(alt, conservative, roi_goal, costs, commission_pct, alt_common, [], goal_kind=goal_kind)["preco_maximo"]
        line = next((l for l in common["lines"] if l["chave"] == item["chave"]), {})
        impacts.append({
            "chave": item["chave"], "descricao": item["descricao"], "reserva": item["valor"], "base_valor": item["base_valor"],
            "tipo": "reserva manual" if line.get("reserva_manual") else ("teto Caixa" if line.get("limite_responsabilidade") is not None else "reserva do sistema"),
            "efeito_investimento": scen["investimento_total"] - alt["investimento_total"],
            "efeito_resultado": (scen["resultado_liquido"] - alt["resultado_liquido"]) if alt["resultado_liquido"] is not None else None,
            "efeito_roi": (scen["roi"] - alt["roi"]) if (scen.get("roi") is not None and alt.get("roi") is not None) else None,
            "efeito_preco_maximo": (max_price - alt_max) if (max_price is not None and alt_max is not None) else None,
        })
    return impacts


def _risk_snapshot(db, prop) -> dict:
    """Documentação e risco jurídico a partir do que a análise já registrou (sem nova análise, sem LLM)."""
    risks = [r for r in prop.risks if str(getattr(r, "status", "ATIVO") or "ATIVO").upper() not in ("INATIVO", "SUPERADO")]
    severities = sorted({str(r.severity or "").upper() for r in risks if r.severity})
    from .services import latest_execution
    execution = latest_execution(prop)
    doc_pending = []
    if execution is not None:
        doc_pending = [r.item.canonical_key for r in execution.results if r.applicable is not False and r.state in ("PENDENTE", "EM_ANALISE")
                       and r.item is not None and r.item.category in ("DOCUMENTAL", "JURIDICO")]
    has_registration_doc = any(str(d.document_type or "").upper() == "MATRICULA" for d in prop.documents)
    onus = None
    holder = None
    try:
        from .registry_chain import registry_for_property
        chain = registry_for_property(db, prop.id) if db is not None else None
        if chain is not None and not chain.is_empty():
            onus = chain.encumbrance_status()[0]
            holder = chain.holder_status
    except Exception:
        chain = None
    return {"riscos_ativos": len(risks), "severidades": severities, "pendencias_documentais": doc_pending, "matricula_anexada": has_registration_doc,
            "situacao_onus": onus, "titularidade": holder}


def consolidate(dims: dict) -> dict:
    """Conclusão consolidada. Precedência explícita:
    1) risco jurídico grave (ALTA/CRITICA) ou ônus existente → DESFAVORAVEL, qualquer que seja o desconto;
    2) preço acima do teto (dados de mercado com confiança ao menos MÉDIA) ou prejuízo no cenário base → DESFAVORAVEL;
    3) qualquer informação crítica ausente → INCONCLUSIVO (nunca FAVORÁVEL definitivo);
    4) demais casos → FAVORAVEL."""
    legal, market, costs, ret, liq, docs = dims["risco_juridico"], dims["mercado"], dims["custos"], dims["rentabilidade"], dims["liquidez"], dims["documentacao"]
    blockers: list[str] = []
    if set(legal.get("severidades") or []) & {"ALTA", "CRITICA"}:
        return {"resultado": DESFAVORAVEL, "motivos": ["Risco jurídico grave ativo: o desconto não compensa automaticamente."], "bloqueios": [], "ressalvas": []}
    if legal.get("situacao_onus") == "EXISTENTE":
        return {"resultado": DESFAVORAVEL, "motivos": ["Ônus ou gravame vigente identificado na matrícula."], "bloqueios": [], "ressalvas": []}
    market_ok = market.get("confianca") in (mk.CONF_ALTA, mk.CONF_MEDIA)
    if market_ok and ret.get("preco_acima_do_teto"):
        return {"resultado": DESFAVORAVEL, "motivos": ["Preço de aquisição acima do preço máximo pela meta de retorno."], "bloqueios": [], "ressalvas": []}
    if market_ok and ret.get("resultado_base") is not None and ret["resultado_base"] < ZERO:
        return {"resultado": DESFAVORAVEL, "motivos": ["Prejuízo no cenário base."], "bloqueios": [], "ressalvas": []}
    if not docs.get("matricula_anexada"):
        blockers.append("Matrícula não anexada.")
    if docs.get("pendencias_documentais"):
        blockers.append(f"{len(docs['pendencias_documentais'])} item(ns) documentais/jurídicos do checklist sem resposta.")
    if legal.get("situacao_onus") in (None, "INCONCLUSIVO"):
        blockers.append("Situação de ônus e gravames inconclusiva.")
    if not market_ok:
        blockers.append(f"Estimativa de mercado com confiança {market.get('confianca')}.")
    if costs.get("criticos_pendentes"):
        blockers.append("Custos críticos pendentes: " + ", ".join(costs["criticos_pendentes"]) + ".")
    if ret.get("preco_maximo_provisorio"):
        blockers.append("Preço máximo provisório (custos materiais pendentes).")
    if ret.get("preco_acima_do_teto") and not market_ok:
        blockers.append("Preço acima do teto calculado, mas com dados de mercado insuficientes para concluir.")
    if ret.get("preco_acima_do_teto_conservador") and not ret.get("preco_acima_do_teto"):
        blockers.append("Preço acima do teto do cenário conservador (abaixo do teto do cenário base).")
    if ret.get("resultado_base") is None:
        blockers.append("Resultado da revenda não calculado (sem valor de mercado estimado).")
    teto_pend, acq = ret.get("preco_maximo_base_com_pendencias_no_teto"), ret.get("aquisicao")
    if teto_pend is not None and acq is not None and acq > teto_pend:
        blockers.append(f"Com os itens fora da soma no teto, o preço máximo do cenário base cai para {_brl(teto_pend)}, abaixo do preço de "
                        f"aquisição ({_brl(acq)}): levantar as dívidas e a ocupação antes de decidir.")
    if ret.get("cenarios_incompletos"):
        blockers.append("Cenário(s) " + ", ".join(ret["cenarios_incompletos"]) + " incompleto(s): há custo sem valor fora da soma.")
    # Ressalvas: não bloqueiam a tese de revenda, mas aparecem na conclusão.
    caveats: list[str] = []
    if ret.get("aluguel_indicativo"):
        caveats.append("Aluguel apenas indicativo (menos de 3 comparáveis de locação): a tese de locação não está validada.")
    if market.get("somente_anunciados"):
        caveats.append("Amostra só com preços anunciados (não transacionados): desconto de negociação aplicado por premissa.")
    if ret.get("venda_preliminar"):
        caveats.append("Valor de venda do cenário base é ESTIMATIVA PRELIMINAR (avaliação × fator), sem comparáveis: confiança baixa.")
    if ret.get("margem_base") is not None and ret.get("margem_minima") is not None and ret["margem_base"] < ret["margem_minima"]:
        caveats.append(f"Margem líquida do cenário base ({_pct(_q(ret['margem_base'], '0.0001'))}) abaixo da margem mínima de referência "
                       f"({_pct(ret['margem_minima'])}).")
    if ret.get("margem_seguranca_base") is not None and ret.get("margem_seguranca_minima") is not None and ret["margem_seguranca_base"] < ret["margem_seguranca_minima"]:
        caveats.append(f"Margem de segurança do cenário base ({_pct(ret['margem_seguranca_base'])}) abaixo da mínima de referência "
                       f"({_pct(ret['margem_seguranca_minima'])}).")
    if liq.get("classificacao") in (mk.LIQ_BAIXA, mk.LIQ_INDETERMINADA):
        blockers.append(f"Liquidez {liq.get('classificacao')}.")
    if blockers:
        return {"resultado": INCONCLUSIVO, "motivos": ["Informações críticas ausentes impedem conclusão favorável."], "bloqueios": blockers, "ressalvas": caveats}
    return {"resultado": FAVORAVEL, "motivos": ["Documentação, risco, mercado, custos, rentabilidade e liquidez dentro dos critérios."], "bloqueios": [],
            "ressalvas": caveats}


def _sale_assumptions(assumptions: dict, premises: dict) -> SaleAssumptions:
    """Premissas de venda usadas pelos DOIS motores. Tributo com base VENDA só quando o usuário o informou assim; caso contrário,
    IR sobre o ganho (premissa do imóvel ou padrão declarado)."""
    if str(assumptions.get("tax_base") or "").upper() == TAX_BASE_VENDA and assumptions.get("tributo_pct") not in (None, ""):
        return SaleAssumptions(corretagem_pct=premises["venda.corretagem_pct"]["valor"], tributo_pct=_d(assumptions["tributo_pct"]), tax_base=TAX_BASE_VENDA)
    return SaleAssumptions(corretagem_pct=premises["venda.corretagem_pct"]["valor"], tributo_pct=premises["venda.tributo_ganho_pct"]["valor"], tax_base=TAX_BASE_GANHO)


def user_goal(assumptions: dict, premises: dict) -> dict:
    """Meta financeira usada pelo preço máximo nos DOIS motores: a do usuário (ROI, margem ou lucro mínimo) quando configurada.
    Sem meta do usuário, devolve o ROI padrão declarado com ``do_usuario=False``: a inteligência de mercado o mostra como referência
    identificada; o veredito não calcula preço máximo sem meta do usuário."""
    kind, value = assumptions.get("goal_kind"), _d(assumptions.get("goal_value"))
    if kind in SUPPORTED_GOALS and value is not None:
        label = {GOAL_ROI_MINIMO: f"ROI mínimo de {_pct(value)}", GOAL_MARGEM_MINIMA: f"Margem mínima de {_pct(value)}",
                 GOAL_LUCRO_MINIMO: f"Lucro mínimo de {_brl(value)}"}[kind]
        return {"tipo": kind, "valor": value, "descricao": label, "origem": "meta configurada pelo usuário", "do_usuario": True}
    default = premises["viabilidade.roi_minimo"]
    return {"tipo": GOAL_ROI_MINIMO, "valor": default["valor"], "descricao": f"ROI mínimo de {_pct(default['valor'])}",
            "origem": f"{default['origem']}; meta do investidor não configurada", "do_usuario": False}


def _inputs(db, prop) -> dict:
    """Entradas comuns da inteligência de mercado e do cálculo financeiro do veredito: premissas resolvidas, estimativas de mercado,
    composição de custos (uma só) e premissas de venda. Ponto único para os dois consumidores não divergirem."""
    from .services import current_auction
    auction = current_auction(prop)
    assumptions = (getattr(auction, "financial_assumptions", None) or {}) if auction else {}
    premises = resolve_premises(db, assumptions)
    subject = _subject(prop)
    comps = [_comparable_dict(c) for c in prop.comparables]
    discount = premises["mercado.desconto_negociacao"]["valor"]
    min_sim = premises["mercado.similaridade_minima"]["valor"]
    sale_est = mk.estimate(subject, comps, "VENDA", negotiation_discount=discount, min_similarity=min_sim)
    rent_est = mk.estimate(subject, comps, "ALUGUEL", negotiation_discount=discount, min_similarity=min_sim)
    used_ids = {r["id"] for r in sale_est["comparaveis"] + rent_est["comparaveis"] if r["usado"]}
    sale_est["_condo_fees"] = [_d(c["condo_fee"]) for c in comps if c["id"] in used_ids and c.get("condo_fee") not in (None, "")]
    costs = acquisition_costs(prop, auction, premises, assumptions, sale_est, db=db)
    sale_est.pop("_condo_fees", None)
    sale = _sale_assumptions(assumptions, premises)
    area = sale_est["area_referencia"]
    rent_value = rent_est["valor_estimado"] if rent_est["valor_estimado"] is not None else (
        mk.median([r["valor_m2_ajustado"] for r in rent_est["comparaveis"] if r["usado"]]) * area if rent_est["quantidade_usada"] and area else None)
    common = {"lines": costs["linhas"], "monthly": costs["carregamento_mensal"], "acquisition": costs["aquisicao"], "appraisal": costs["avaliacao"], "sale": sale,
              "rent": rent_value, "premises": premises, "rent_indicative": rent_est["valor_estimado"] is None and rent_value is not None}
    commission_pct = (_d(auction.commission_percent) / Decimal("100")) if (auction is not None and auction.commission_fixed is None
                                                                            and auction.commission_percent is not None) else None
    # Valor de venda do cenário BASE: premissa do usuário (quando informada) > estimativa dos comparáveis > estimativa preliminar
    # (avaliação × fator do catálogo, decisão 2.2) — esta só quando não há comparável usável, com selo próprio e confiança BAIXA.
    user_value = _d(assumptions.get("valor_venda_estimado"))
    preliminary = None
    if user_value is None and sale_est["valor_estimado"] is None and costs["avaliacao"]:
        factor = premises["viabilidade.fator_venda_avaliacao"]
        value = _q(costs["avaliacao"] * factor["valor"])
        preliminary = {"valor": value, "avaliacao": costs["avaliacao"], "fator": factor["valor"], "fator_origem": factor["origem"],
                       "selo": "Estimativa preliminar", "confianca": mk.CONF_BAIXA,
                       "observacao": "Sem comparáveis suficientes: valor de venda preliminar = avaliação do vendedor × fator. Informe o valor de venda "
                                     "em Financeiro > Premissas ou cadastre comparáveis para substituir.",
                       "formula": f"{_brl(costs['avaliacao'])} × {_pct(factor['valor'])} = {_brl(value)}"}
    if user_value is not None:
        base_value, base_origin = _q(user_value), "premissa do imóvel"
    elif sale_est["valor_estimado"] is not None:
        base_value = sale_est["valor_estimado"]
        base_origin = f"estimativa de mercado ({sale_est['quantidade_usada']} comparáveis, confiança {sale_est['confianca']})"
    elif preliminary is not None:
        base_value = preliminary["valor"]
        base_origin = f"{ORIGEM_PRELIMINAR}: {preliminary['formula']} ({preliminary['fator_origem']}); confiança BAIXA"
    else:
        base_value, base_origin = None, None
    return {"auction": auction, "assumptions": assumptions, "premises": premises, "subject": subject, "sale_est": sale_est, "rent_est": rent_est,
            "costs": costs, "sale": sale, "months": int(premises["venda.prazo_meses"]["valor"]), "common": common, "commission_pct": commission_pct,
            "base_value": base_value, "base_value_origin": base_origin, "venda_preliminar": preliminary}


def market_intelligence(db, prop) -> dict:
    """Visão consolidada de inteligência de mercado e viabilidade do imóvel (leitura; não grava nada)."""
    inp = _inputs(db, prop)
    auction, assumptions, premises, subject = inp["auction"], inp["assumptions"], inp["premises"], inp["subject"]
    sale_est, rent_est, costs, months, common = inp["sale_est"], inp["rent_est"], inp["costs"], inp["months"], inp["common"]
    acquisition, appraisal = costs["aquisicao"], costs["avaliacao"]
    liq = mk.liquidity(sale_est, rent_est, subject, acquisition=acquisition)
    area = sale_est["area_referencia"]
    stats = sale_est["estatisticas_m2"]
    n = sale_est["quantidade_usada"]

    def at(m2: Decimal | None) -> Decimal | None:
        return (m2 * area).quantize(Decimal("0.01")) if (m2 is not None and area) else None   # igual à faixa exibida

    low = stats["m2_ajustado_p25"] if n >= 4 else stats["m2_ajustado_min"]
    high = stats["m2_ajustado_p75"] if n >= 4 else stats["m2_ajustado_max"]
    rent_value = common["rent"]
    cons_f, opt_f = premises["cenario.prazo_conservador_fator"]["valor"], premises["cenario.prazo_otimista_fator"]["valor"]
    scenarios = [
        _scenario("CONSERVADOR", at(low), conservative=True, months=int((Decimal(months) * cons_f).to_integral_value()), **common),
        _scenario("BASE", inp["base_value"], conservative=False, months=months, **common),
        _scenario("OTIMISTA", at(high), conservative=False, months=max(1, int((Decimal(months) * opt_f).to_integral_value())), **common),
    ]
    scenarios[1]["valor_venda_origem"] = inp["base_value_origin"]
    base = scenarios[1]

    # Preço máximo: maior aquisição que entrega a META do usuário (ROI, margem ou lucro), com ITBI proporcional ao preço. Sem meta
    # configurada, a referência é o ROI padrão declarado, identificado como tal (o veredito não calcula preço máximo sem meta).
    goal = user_goal(assumptions, premises)
    roi_goal, goal_kind = goal["valor"], goal["tipo"]
    max_prices = {}
    pending_keys = [l["descricao"] for l in costs["linhas"] if l["status"] == PENDENTE]
    commission_pct = (_d(auction.commission_percent) / Decimal("100")) if (auction is not None and auction.commission_fixed is None
                                                                            and auction.commission_percent is not None) else None
    for scen in scenarios:
        conservative = scen["cenario"] == "CONSERVADOR"
        # Teto provisório quando o cenário tem item sem valor fora da soma (pendência nunca conta como zero).
        unknown = list(scen["custos_pendentes_nao_incluidos"])
        max_prices[scen["cenario"]] = _solve_max_price(scen, conservative, roi_goal, costs, commission_pct, common, unknown, goal_kind=goal_kind)
        if not conservative and scen.get("efeito_pendencias_no_teto"):
            # Mesmo cenário (venda e prazo), mas com os itens fora da soma no teto/reserva conhecido: mostra quanto o teto provisório cai.
            filled = [_fill_base_with_ceiling(l) for l in common["lines"]]
            filled_common = {**common, "lines": filled}
            kw = {k: v for k, v in filled_common.items() if k != "lines"}
            alt = _scenario(scen["cenario"], scen["valor_venda"], filled, conservative=False, months=scen["prazo_meses"], **kw)
            alt_max = _solve_max_price(alt, False, roi_goal, costs, commission_pct, filled_common, alt["custos_pendentes_nao_incluidos"], goal_kind=goal_kind)
            max_prices[scen["cenario"]]["com_pendencias_no_teto"] = {
                "preco_maximo": alt_max.get("preco_maximo"), "roi_no_teto": alt_max.get("roi_no_teto"), "indicador_no_teto": alt_max.get("indicador_no_teto"),
                "itens": [d["descricao"] for d in scen["efeito_pendencias_no_teto"]["detalhe"]],
                "sem_teto_conhecido": scen["efeito_pendencias_no_teto"]["sem_teto_conhecido"]}
        scen["impacto_reservas"] = _reserve_impacts(scen, conservative, roi_goal, costs, commission_pct, common, max_prices[scen["cenario"]].get("preco_maximo"),
                                                    goal_kind=goal_kind)
    recommended = max_prices.get("CONSERVADOR", {}).get("preco_maximo")
    base_max = max_prices.get("BASE", {}).get("preco_maximo")
    critical = [l["descricao"] for l in costs["linhas"] if l["critico"] and l["status"] == PENDENTE]
    dims = {
        "documentacao": {}, "risco_juridico": {}, "mercado": {"confianca": sale_est["confianca"], "comparaveis_venda": n, "comparaveis_aluguel": rent_est["quantidade_usada"],
                     "somente_anunciados": bool(n and sale_est["quantidade_anunciada"] == n)},
        "custos": {"criticos_pendentes": critical, "pendentes": pending_keys},
        "rentabilidade": {"roi_base": base.get("roi"), "resultado_base": base.get("resultado_liquido"),
                          "meta_roi": roi_goal if goal_kind == GOAL_ROI_MINIMO else None, "meta": goal,
                          "preco_maximo_recomendado": recommended, "preco_maximo_base": base_max,
                          "preco_acima_do_teto": bool(base_max is not None and acquisition is not None and acquisition > base_max),
                          "preco_acima_do_teto_conservador": bool(recommended is not None and acquisition is not None and acquisition > recommended),
                          "preco_maximo_provisorio": bool(max_prices.get("CONSERVADOR", {}).get("provisorio") or max_prices.get("BASE", {}).get("provisorio")),
                          "cenarios_incompletos": [s["cenario"] for s in scenarios if not s["completo"]],
                          "preco_maximo_base_com_pendencias_no_teto": (max_prices.get("BASE", {}).get("com_pendencias_no_teto") or {}).get("preco_maximo"),
                          "aquisicao": acquisition,
                          "aluguel_indicativo": common["rent_indicative"],
                          "margem_base": (base["resultado_liquido"] / base["valor_venda"]) if (base.get("resultado_liquido") is not None and base.get("valor_venda")) else None,
                          "margem_minima": premises["viabilidade.margem_minima"]["valor"],
                          "margem_seguranca_base": base.get("margem_seguranca"),
                          "margem_seguranca_minima": premises["viabilidade.margem_seguranca_minima"]["valor"],
                          "venda_preliminar": inp["venda_preliminar"] is not None},
        "liquidez": {"classificacao": liq["classificacao"], "confianca": liq["confianca"]},
    }
    snapshot = _risk_snapshot(db, prop)
    dims["documentacao"] = {"matricula_anexada": snapshot["matricula_anexada"], "pendencias_documentais": snapshot["pendencias_documentais"]}
    dims["risco_juridico"] = {"riscos_ativos": snapshot["riscos_ativos"], "severidades": snapshot["severidades"], "situacao_onus": snapshot["situacao_onus"],
                              "titularidade": snapshot["titularidade"]}
    conclusion = consolidate(dims)
    return {
        "property_id": prop.id, "data_calculo": date.today().isoformat(), "imovel": {**subject, "area": _q(_d(subject["area"]))},
        "venda": sale_est, "aluguel": rent_est, "liquidez": liq,
        "valores": {
            "valor_mercado_estimado": _q(sale_est["valor_estimado"]), "faixa_venda": sale_est["faixa"], "aluguel_estimado": _q(rent_value),
            "aluguel_indicativo": rent_est["valor_estimado"] is None and rent_value is not None, "faixa_aluguel": rent_est["faixa"],
            "preco_m2_anunciado_mediana": _q(stats["m2_anunciado_mediana"]), "preco_m2_estimado_mediana": _q(stats["m2_ajustado_mediana"]),
            "desconto_sobre_avaliacao": _q(ONE - acquisition / appraisal, "0.0001") if acquisition and appraisal else None,
            "desconto_sobre_mercado": base.get("desconto_sobre_mercado"),
            "observacao_descontos": "Desconto sobre a avaliação da Caixa ≠ desconto sobre o valor de mercado estimado a partir de comparáveis.",
            "venda_preliminar": inp["venda_preliminar"],
        },
        "custos": costs["linhas"], "carregamento_mensal": {"valor": _q(costs["carregamento_mensal"]), "origem": costs["carregamento_origem"]},
        "cenarios": scenarios,
        "preco_maximo": {"recomendado": recommended, "criterio": f"{goal['descricao']} no cenário conservador ({goal['origem']})",
                         "meta": goal, "por_cenario": max_prices, "provisorio": bool(max_prices.get("CONSERVADOR", {}).get("provisorio"))},
        "premissas": {k: {**v, "valor": str(v["valor"])} for k, v in premises.items()},
        "dimensoes": dims, "conclusao": conclusion,
        "fontes": sorted({(r["fonte"] or "", r["url"] or "", str(r["consultado_em"] or "")) for r in sale_est["comparaveis"] + rent_est["comparaveis"]}),
        "custo_ia_usd": 0,
    }


# ------------------------------------------------------------------ cálculo financeiro do veredito (mesma composição do cenário BASE)

# Natureza de cada valor no cálculo do veredito (o que é confirmado, estimado, premissa do usuário, reserva, pendente ou não aplicável).
NAT_CONFIRMADO, NAT_PREMISSA, NAT_ESTIMADO, NAT_RESERVA, NAT_PENDENTE, NAT_NAO_APLICAVEL = (
    "CONFIRMADO", "PREMISSA_USUARIO", "ESTIMADO", "RESERVA", "PENDENTE", "NAO_APLICAVEL")
# Status no vocabulário do motor financeiro (custos_status): INFORMADO, ESTIMADO, RESERVA, DESCONHECIDO (pendente), NAO_APLICAVEL.
_STATUS_FINANCEIRO = {NAT_CONFIRMADO: "INFORMADO", NAT_PREMISSA: "INFORMADO", NAT_ESTIMADO: "ESTIMADO", NAT_RESERVA: "RESERVA",
                      NAT_PENDENTE: "DESCONHECIDO", NAT_NAO_APLICAVEL: "NAO_APLICAVEL"}
# Itens da composição → chave do detalhamento legado (``custos``) do motor financeiro.
_CHAVE_LEGADA = {"aquisicao": "aquisicao", "comissao": "comissao", "itbi": "itbi", "registro": "registro", "certidoes": "outros",
                 "condominio_atraso": "condominio", "tributos_atraso": "iptu", "reforma": "reforma", "regularizacao": "outros",
                 "desocupacao": "desocupacao", "outras_dividas": "debitos", "iptu_posse": "carregamento", "manutencao_posse": "carregamento",
                 "custo_custos_juridicos": "custos_juridicos", "custo_debitos": "debitos", "custo_carregamento": "carregamento", "custo_outros": "outros"}
ORIGEM_USUARIO = "premissa do imóvel"


def _nature(item: dict, assumptions: dict) -> str:
    kind = item.get("tipo_valor")
    if kind == "FORA_DA_SOMA":
        return NAT_PENDENTE
    if kind == "NAO_APLICAVEL":
        return NAT_NAO_APLICAVEL
    if kind in ("RESERVA", "RESERVA_MANUAL", "TETO_CAIXA"):
        return NAT_RESERVA
    key = item["chave"]
    typed = {"certidoes": "certidoes", "registro": "registro_estimado", "reforma": "reforma", "regularizacao": "regularizacao",
             "iptu_posse": "iptu_anual", "manutencao_posse": "carregamento_mensal"}
    if key in typed and assumptions.get(typed[key]) not in (None, "") and (kind == "ESTIMADO" or key == "certidoes"):
        return NAT_PREMISSA   # valor digitado pelo usuário nas premissas
    return NAT_CONFIRMADO if kind == "CONFIRMADO" else NAT_ESTIMADO


def verdict_finance(db, prop) -> dict:
    """Cálculo financeiro do veredito com a MESMA composição, o MESMO IR e o MESMO preço máximo do cenário BASE da inteligência de
    mercado. Diferenças em relação ao cenário BASE exibido lá: a meta é a do usuário (nunca uma meta padrão), e tudo o que não foi
    confirmado pelo usuário (venda estimada, corretagem/IR/prazo padrão, reserva do sistema, custo sem valor) torna o cálculo
    PROVISÓRIO e aparece nas pendências. Custo sem valor fica fora da soma: nunca entra como zero."""
    inp = _inputs(db, prop)
    assumptions, premises, costs, common, sale = inp["assumptions"], inp["premises"], inp["costs"], inp["common"], inp["sale"]
    months, value = inp["months"], inp["base_value"]
    solve_common = {**common, "rent": None, "rent_indicative": False}
    scen = _scenario("BASE", value, common["lines"], conservative=False, months=months, monthly=common["monthly"], acquisition=common["acquisition"],
                     appraisal=common["appraisal"], sale=sale, rent=None, premises=premises)
    items = scen["composicao"]["itens"]
    lines_by_key = {l["chave"]: l for l in common["lines"]}
    pending: list[str] = []
    unknown: list[str] = []

    # Venda e premissas de saída: confirmadas pelo usuário ou padrão declarado (este torna o cálculo provisório).
    def user(key: str) -> bool:
        return premises[key]["origem"] == ORIGEM_USUARIO
    c_user = user("venda.corretagem_pct")
    t_user = sale.tax_base == TAX_BASE_VENDA or user("venda.tributo_ganho_pct")
    unknown_desc: list[str] = []

    def mark(code: str, description: str) -> None:
        unknown.append(code)
        unknown_desc.append(description)

    if value is None:
        pending.append("Valor de venda estimado ausente: resultado líquido, margem e ROI não calculados.")
    elif inp.get("venda_preliminar") is not None:
        mark("valor_venda", "valor de venda (estimativa preliminar: avaliação × fator, confiança baixa)")
        pending.append(f"Valor de venda não confirmado: o cálculo usa a ESTIMATIVA PRELIMINAR de {_brl(value)} ({inp['venda_preliminar']['formula']}), "
                       "sem comparáveis suficientes; confiança baixa. Informe o valor em Financeiro > Premissas ou cadastre comparáveis.")
    elif inp["base_value_origin"] != ORIGEM_USUARIO:
        mark("valor_venda", "valor de venda (estimativa de mercado não confirmada)")
        pending.append(f"Valor de venda não confirmado: o cálculo usa a estimativa de mercado de {_brl(value)} ({inp['base_value_origin']}). "
                       "Confirme ou ajuste em Financeiro > Premissas.")
    if not c_user:
        mark("corretagem_venda", "corretagem de venda (padrão não confirmado)")
        pending.append(f"Percentual de corretagem de venda não informado: o cálculo usa o padrão de {_pct(sale.corretagem_pct)} "
                       f"({premises['venda.corretagem_pct']['origem']}). Resultado e preço máximo ficam PROVISÓRIOS até a premissa ser informada.")
    if not t_user:
        mark("tributo_venda", "tributo na venda (padrão não confirmado)")
        pending.append(f"Percentual de tributo na venda não informado: o cálculo usa IR de {_pct(sale.tributo_pct)} sobre o ganho "
                       f"({premises['venda.tributo_ganho_pct']['origem']}). Resultado e preço máximo ficam PROVISÓRIOS até a premissa ser informada.")
    depends_on_months = any(i["chave"] in ("manutencao_posse", "iptu_posse") and i["incluido"] for i in items)
    if not user("venda.prazo_meses") and depends_on_months:
        mark("prazo_meses", "prazo da operação (padrão não confirmado)")
        pending.append(f"Prazo da operação não informado: o condomínio e o IPTU da posse usam o padrão de {months} meses "
                       f"({premises['venda.prazo_meses']['origem']}).")

    # Composição: natureza, status e origem de cada item; pendente fora da soma e reserva do sistema tornam o cálculo provisório.
    composition, breakdown, status, origin = [], {}, {}, {}
    for item in items:
        nature = _nature(item, assumptions)
        line = lines_by_key.get(item["chave"], {})
        composition.append({"chave": item["chave"], "descricao": item["descricao"], "valor": item["valor"], "incluido": item["incluido"],
                            "natureza": nature, "origem": item["origem"], "base_valor": item["base_valor"], "dedutivel_ir": item["dedutivel_ir"]})
        legacy = "debitos" if line.get("fonte_valor") == "DIVIDA" else _CHAVE_LEGADA.get(item["chave"], "outros")
        breakdown[legacy] = breakdown.get(legacy, ZERO) + (item["valor"] or ZERO)
        status[item["chave"]] = _STATUS_FINANCEIRO[nature]
        origin[item["chave"]] = item["origem"]
        code = "comissao_arrematacao" if item["chave"] == "comissao" else item["chave"]
        if line.get("fonte_divida") == FONTE_ESTIMATIVA and item["incluido"]:
            # Estimativa de dívida não é dívida confirmada: entra na soma, mas o cálculo continua provisório.
            mark(code, f"{item['descricao']} (estimativa, não é dívida confirmada)")
            pending.append(f"{item['descricao']}: valor estimado de {_brl(item['valor'])}, não é dívida confirmada; solicitar declaração atualizada "
                           "(cálculo provisório)." + (" Consulta indisponível ou em validação." if line.get("consulta_indisponivel") else ""))
        if nature == NAT_PENDENTE:
            mark(code, item["descricao"])
            label = item["descricao"] if item["descricao"][:2].isupper() else item["descricao"][0].lower() + item["descricao"][1:]   # sigla (ITBI, IPTU) intacta
            pending.append(f"Custo de {label} não informado: fora da soma, não é zero (cálculo provisório).")
        elif nature == NAT_RESERVA:
            if not line.get("reserva_manual"):
                mark(code, f"{item['descricao']} (reserva do sistema)")
            pending.append(f"{item['descricao']}: valor real não informado; o cálculo usa {item['base_valor']}.")
    investment = scen["investimento_total"]
    result = scen.get("resultado_liquido")
    goal = user_goal(assumptions, premises)
    goal_kind, goal_value = (goal["tipo"], goal["valor"]) if goal["do_usuario"] else (assumptions.get("goal_kind"), None)   # nunca meta padrão

    # Preço máximo: meta do usuário (sem meta, não há preço máximo), mesma função de cenário.
    meta = {"tipo": goal_kind, "valor": goal_value}
    detail = {"premissas_utilizadas": {"meta": meta, "valor_venda": value, "corretagem_pct": sale.corretagem_pct, "tributo_pct": sale.tributo_pct,
                                       "tax_base": sale.tax_base},
              "custos_desconhecidos": list(unknown), "custos_desconhecidos_descricao": list(unknown_desc)}
    max_price = None
    if value is None or goal_kind not in SUPPORTED_GOALS or goal_value is None:
        notes = []
        if value is None:
            notes.append("Valor de venda estimado (V) é essencial e não foi informado.")
        if goal_value is None:
            notes.append("Meta financeira (valor/percentual) é essencial e não foi informada.")
        detail.update({"preco_maximo": None, "viavel": False, "definitivo": False, "provisorio": False, "razao": "DADOS_ESSENCIAIS_AUSENTES", "pendencias": notes})
        pending.extend(notes)
        if goal_value is None:
            pending.append("Meta de preço máximo não configurada; preço máximo não calculado.")
    else:
        solved = _solve_max_price(scen, False, goal_value, costs, inp["commission_pct"], solve_common, unknown, goal_kind=goal_kind)
        max_price = solved["preco_maximo"]
        detail.update({"preco_maximo": max_price, "viavel": max_price is not None, "definitivo": bool(solved["definitivo"]),
                       "provisorio": bool(solved["provisorio"]), "razao": solved["razao"], "pendencias": solved["pendencias"],
                       "indicador_no_teto": solved.get("indicador_no_teto"), "roi_no_teto": solved.get("roi_no_teto")})
        if solved["razao"] == "META_INATINGIVEL":
            detail["mensagem"] = "Meta inatingível para o valor de venda e custos informados."
            pending.append(detail["mensagem"])
        pending.extend(solved["pendencias"])
    provisional = bool(result is not None and unknown)
    user_scenarios = [_user_scenario(sc, inp, value, months, solve_common, goal_kind if goal_value is not None else None, goal_value, unknown)
                      for sc in (assumptions.get("cenarios") or [])]
    brokerage, tax = scen.get("corretagem_venda"), scen.get("tributo_venda")
    exit_cost = (brokerage + tax) if (brokerage is not None and tax is not None) else None
    return {
        "motor": "viability.verdict_finance (mesma composição do cenário BASE da inteligência de mercado)",
        "valor_mercado": value, "valor_mercado_origem": inp["base_value_origin"], "valor_venda_preliminar": inp["venda_preliminar"],
        "custo_total": investment, "custos": breakdown, "custos_status": status, "custos_origem": origin,
        "composicao_custos": composition, "memoria_calculo": scen["composicao"],
        "custo_saida": exit_cost, "custo_saida_detalhe": {"corretagem_venda": brokerage, "tributos_venda": tax},
        "saida_status": {"corretagem_venda": "INFORMADO" if c_user else "ESTIMADO", "tributos_venda": "INFORMADO" if t_user else "ESTIMADO"},
        "premissas_origem": {"corretagem_pct": premises["venda.corretagem_pct"]["origem"],
                             "tributo_pct": ORIGEM_USUARIO if sale.tax_base == TAX_BASE_VENDA else premises["venda.tributo_ganho_pct"]["origem"],
                             "tax_base": sale.tax_base, "prazo_meses": premises["venda.prazo_meses"]["origem"],
                             "carregamento_mensal": costs["carregamento_origem"], "valor_venda": inp["base_value_origin"]},
        "carregamento_recorrente": scen.get("carregamento") or ZERO,
        "resultado_liquido": result,
        "margem_liquida": (result / value) if (result is not None and value) else None,
        "roi_operacao": scen.get("roi"),
        "break_even": scen.get("venda_equilibrio"),
        "break_even_detalhe": {"break_even": scen.get("venda_equilibrio"), "razao": "OK" if scen.get("venda_equilibrio") is not None else "INDEFINIDO",
                               "premissas": {"custo_total": investment, "corretagem_pct": sale.corretagem_pct, "tributo_pct": sale.tributo_pct,
                                             "tax_base": sale.tax_base, "custo_dedutivel_ir": scen["composicao"].get("custo_aquisicao_dedutivel_ir")}},
        "margem_absoluta": (value - investment) if value is not None else None,
        "margem_percentual": ((value - investment) / value) if value else None,
        "resultado_provisorio": provisional,
        "resultado_completo": bool(result is not None and not provisional),
        "custos_pendentes": [c["descricao"] for c in composition if c["natureza"] == NAT_PENDENTE],
        "custos_com_reserva": [c["descricao"] for c in composition if c["natureza"] == NAT_RESERVA],
        "preco_maximo": max_price, "preco_maximo_definitivo": bool(detail.get("definitivo")), "preco_maximo_provisorio": bool(detail.get("provisorio")),
        "preco_maximo_detalhe": detail,
        "pendencias": list(dict.fromkeys(pending)),
        "prazo_meses": months,
        "cenarios_usuario": user_scenarios,
    }


def _override(lines: list[dict], key: str, label: str, amount: Decimal) -> list[dict]:
    """Linhas com ``key`` substituída pelo valor do cenário do usuário (premissa do cenário; se não existia, entra como linha nova)."""
    new = _line(key, label, amount, ESTIMADO, "premissa do cenário do usuário")
    out = [new if l["chave"] == key else l for l in lines]
    return out if any(l["chave"] == key for l in lines) else out + [new]


def _user_scenario(sc: dict, inp: dict, base_value: Decimal | None, base_months: int, common: dict, goal_kind: str | None,
                   goal_value: Decimal | None, base_unknown: list[str]) -> dict:
    """Cenário informado pelo usuário (Financeiro > premissas ``cenarios``) calculado com a MESMA composição, o MESMO IR e o MESMO
    preço máximo do cenário BASE. Os parâmetros do usuário substituem só o que ele informou: venda, reforma, desocupação,
    carregamento (custo único do cenário, além do condomínio mensal da posse) e prazo. Ausência mantém o valor do BASE."""
    value = _q(_d(sc.get("valor_venda"))) if _d(sc.get("valor_venda")) is not None else base_value
    months = int(sc["prazo_meses"]) if sc.get("prazo_meses") not in (None, "") else base_months
    lines = list(common["lines"])
    for key, label in (("reforma", "Reforma"), ("desocupacao", "Desocupação"), ("custo_carregamento", "Carregamento do cenário")):
        field = "carregamento" if key == "custo_carregamento" else key
        if _d(sc.get(field)) is not None:
            lines = _override(lines, key, label, _d(sc[field]))
    sc_common = {**common, "lines": lines}
    kwargs = {k: v for k, v in sc_common.items() if k != "lines"}
    out = _scenario(sc.get("nome", "BASE"), value, lines, conservative=False, months=months, **kwargs)
    # Mesmas pendências do BASE, menos as que o cenário resolveu com valor próprio (reforma, desocupação).
    unknown = [u for u in base_unknown if not (u in ("reforma", "desocupacao") and _d(sc.get(u)) is not None)]
    unknown += [i["chave"] for i in out["composicao"]["itens"] if not i["incluido"] and i["chave"] not in unknown]
    max_price = None
    if goal_value is not None and value is not None:
        max_price = _solve_max_price(out, False, goal_value, inp["costs"], inp["commission_pct"], sc_common, unknown, goal_kind=goal_kind)["preco_maximo"]
    result = out.get("resultado_liquido")
    return {"cenario": sc.get("nome", "BASE"), "motor": "composição única (mesma do veredito e da inteligência de mercado)",
            "premissas": {"valor_venda": _d(sc.get("valor_venda")), "reforma": _d(sc.get("reforma")), "desocupacao": _d(sc.get("desocupacao")),
                          "carregamento": _d(sc.get("carregamento")), "prazo_meses": sc.get("prazo_meses"), "justificativa": sc.get("justificativa", "")},
            "custo_total": out["investimento_total"], "valor_mercado": value, "resultado_liquido": result,
            "resultado_provisorio": bool(result is not None and unknown), "margem_liquida": (result / value) if (result is not None and value) else None,
            "roi_operacao": out.get("roi"), "break_even": out.get("venda_equilibrio"), "preco_maximo": max_price,
            "pendencias": [f"{d} (fora da soma)" for d in out["custos_pendentes_nao_incluidos"]]}
