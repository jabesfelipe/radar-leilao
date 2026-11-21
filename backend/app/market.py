from __future__ import annotations

from decimal import Decimal
import unicodedata
from typing import Any, Iterable

ZERO = Decimal("0")

# Amostra mínima recomendada pelo método (checklist: "7 a 10 imóveis similares").
MIN_SAMPLE = 7
# Acima deste coeficiente de variação a amostra é considerada dispersa/heterogênea.
HIGH_DISPERSION_CV = Decimal("0.30")


def decimal(value: Any | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def normalize_kind(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().upper()


def median(values: Iterable[Decimal]) -> Decimal | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _coefficient_of_variation(values: list[Decimal]) -> Decimal | None:
    """Coeficiente de variação (desvio padrão / média). Mede dispersão relativa
    da amostra. Requer >= 2 valores e média > 0."""
    if len(values) < 2:
        return None
    mean = sum(values, ZERO) / Decimal(len(values))
    if mean == ZERO:
        return None
    var = sum(((v - mean) ** 2 for v in values), ZERO) / Decimal(len(values))
    # raiz quadrada via Decimal
    std = var.sqrt()
    return std / mean


def _quality(values: list[Decimal], *, min_sample: int, high_dispersion_cv: Decimal = HIGH_DISPERSION_CV) -> dict[str, Any]:
    """Sinaliza a qualidade da amostra (SPEC/auditoria Task 2): amostra
    insuficiente e dispersão elevada. NÃO afirma verificação externa nem inventa
    dados — apenas descreve o que a amostra cadastrada permite.

    ``min_sample`` e ``high_dispersion_cv`` são PARAMETRIZÁVEIS (catálogo central,
    Etapa D): o default mantém o valor histórico, preservando compatibilidade."""
    n = len(values)
    cv = _coefficient_of_variation(values)
    avisos: list[str] = []
    if n == 0:
        avisos.append("Sem comparáveis cadastrados: não há base para estimativa de mercado.")
    elif n < min_sample:
        avisos.append(f"Amostra insuficiente ({n} < {min_sample} recomendados): estimativa apenas indicativa, não conclusiva.")
    if cv is not None and cv > high_dispersion_cv:
        avisos.append("Dispersão elevada entre os comparáveis: possível heterogeneidade (área, localização, conservação ou preços discrepantes).")
    return {
        "quantidade": n,
        "amostra_suficiente": n >= min_sample,
        "coeficiente_variacao": cv,
        "dispersao_elevada": bool(cv is not None and cv > high_dispersion_cv),
        "avaliacao_definitiva": False,  # média/mediana NUNCA é avaliação definitiva de mercado
        "avisos": avisos,
    }


def summarize_sale(comparables: list[dict], *, min_sample: int = MIN_SAMPLE, high_dispersion_cv: Decimal = HIGH_DISPERSION_CV) -> dict:
    rows = [(decimal(item.get("price")), decimal(item.get("area_m2"))) for item in comparables if normalize_kind(item.get("kind", "VENDA")) == "VENDA"]
    prices = [price for price, _ in rows if price is not None]
    price_per_m2 = [price / area for price, area in rows if price is not None and area is not None and area > ZERO]
    return {
        "quantidade": len(prices),
        "preco_medio": sum(prices, ZERO) / Decimal(len(prices)) if prices else None,
        "preco_mediano": median(prices),
        "preco_m2_medio": sum(price_per_m2, ZERO) / Decimal(len(price_per_m2)) if price_per_m2 else None,
        "preco_m2_mediano": median(price_per_m2),
        "quantidade_com_area": len(price_per_m2),
        "qualidade": _quality(prices, min_sample=min_sample, high_dispersion_cv=high_dispersion_cv),
    }


def summarize_rent(comparables: list[dict], *, min_sample: int = MIN_SAMPLE, high_dispersion_cv: Decimal = HIGH_DISPERSION_CV) -> dict:
    rows = [(decimal(item.get("rent")), decimal(item.get("area_m2"))) for item in comparables if normalize_kind(item.get("kind")) == "ALUGUEL"]
    rents = [rent for rent, _ in rows if rent is not None]
    rent_per_m2 = [rent / area for rent, area in rows if rent is not None and area is not None and area > ZERO]
    return {
        "quantidade": len(rents),
        "aluguel_medio": sum(rents, ZERO) / Decimal(len(rents)) if rents else None,
        "aluguel_mediano": median(rents),
        "aluguel_m2_medio": sum(rent_per_m2, ZERO) / Decimal(len(rent_per_m2)) if rent_per_m2 else None,
        "aluguel_m2_mediano": median(rent_per_m2),
        "quantidade_com_area": len(rent_per_m2),
        "qualidade": _quality(rents, min_sample=min_sample, high_dispersion_cv=high_dispersion_cv),
    }


def _sources(comparables: list[dict]) -> list[dict]:
    """Preserva a rastreabilidade da origem/URL de cada comparável quando disponível
    (sem inventar). Datas são incluídas quando o item as fornecer."""
    fontes: list[dict] = []
    for item in comparables:
        origem = item.get("source")
        url = item.get("url")
        if origem or url:
            fontes.append({
                "kind": normalize_kind(item.get("kind", "VENDA")),
                "source": origem,
                "url": url,
                "data": item.get("date") or item.get("data"),
            })
    return fontes


# ===========================================================================
# v1.0.8 — Inteligência de mercado (estimativa com rastreabilidade)
# ---------------------------------------------------------------------------
# Regras: nada é inventado. Anúncio (preço pedido) é ANUNCIADO e nunca é tratado como venda: entra na estimativa com
# um desconto de negociação PARAMETRIZADO e declarado. Poucos comparáveis reduzem a confiança e, abaixo de 3, não há
# valor pontual (só faixa indicativa). Distância só é usada quando medida (o sistema não estima coordenadas).
# ===========================================================================

PRICE_ANUNCIADO = "ANUNCIADO"
PRICE_TRANSACIONADO = "TRANSACIONADO"
CONF_ALTA, CONF_MEDIA, CONF_BAIXA, CONF_SEM_DADOS = "ALTA", "MEDIA", "BAIXA", "SEM_DADOS"
LIQ_ALTA, LIQ_MEDIA, LIQ_BAIXA, LIQ_INDETERMINADA = "ALTA", "MEDIA", "BAIXA", "INDETERMINADA"

DEFAULT_NEGOTIATION_DISCOUNT = Decimal("0.10")   # anúncio → negociado (premissa configurável, não fato)
DEFAULT_MIN_SIMILARITY = Decimal("0.50")
OUTLIER_IQR_FACTOR = Decimal("1.5")
MIN_POINT_ESTIMATE = 3                           # abaixo disso: só faixa indicativa

_SIMILARITY_WEIGHTS = {"cidade": Decimal("0.25"), "bairro": Decimal("0.15"), "tipo": Decimal("0.15"), "quartos": Decimal("0.15"),
                       "area": Decimal("0.20"), "vagas": Decimal("0.05"), "distancia": Decimal("0.05")}


def _fold(value: Any) -> str:
    return " ".join(normalize_kind(value).replace("-", " ").split())


def _type_key(value: Any) -> str:
    text = _fold(value)
    if text.startswith("APART") or text.startswith("APTO"):
        return "APARTAMENTO"
    if "CASA" in text or "SOBRADO" in text:
        return "CASA"
    return text


def similarity(subject: dict, comp: dict) -> dict:
    """Grau de similaridade (0–1) do comparável com o imóvel analisado, com os critérios usados.

    Atributo ausente em qualquer dos lados vale 0,5 (neutro) e é listado em ``nao_informados``: a falta de dado não
    vira semelhança nem diferença. Distância só pesa quando foi medida."""
    parts: dict[str, Decimal] = {}
    missing: list[str] = []

    def put(name: str, value: Decimal | None) -> None:
        if value is None:
            missing.append(name)
            parts[name] = Decimal("0.5")
        else:
            parts[name] = value

    sc, cc = _fold(subject.get("city")), _fold(comp.get("city"))
    put("cidade", (Decimal("1") if sc == cc else ZERO) if sc and cc else None)
    sb, cb = _fold(subject.get("neighborhood")), _fold(comp.get("neighborhood"))
    put("bairro", (Decimal("1") if sb == cb else Decimal("0.4")) if sb and cb else None)
    st, ct = _type_key(subject.get("property_type")), _type_key(comp.get("property_type"))
    put("tipo", (Decimal("1") if st == ct else ZERO) if st and ct else None)
    sq, cq = subject.get("bedrooms"), comp.get("bedrooms")
    put("quartos", ({0: Decimal("1"), 1: Decimal("0.5")}.get(abs(int(sq) - int(cq)), ZERO)) if sq is not None and cq is not None else None)
    sa, ca = decimal(subject.get("area")), decimal(comp.get("area_m2"))
    if sa and ca and sa > ZERO and ca > ZERO:
        ratio = min(sa, ca) / max(sa, ca)
        area_score = max(ZERO, Decimal("1") - (Decimal("1") - ratio) * Decimal("2.5"))
        if str(comp.get("area_basis") or "").upper() == "TOTAL":
            area_score = area_score * Decimal("0.8")   # área total comparada com área privativa: menos comparável
        put("area", area_score)
    else:
        put("area", None)
    sv, cv = subject.get("parking_spots"), comp.get("parking_spots")
    put("vagas", (Decimal("1") if int(sv) == int(cv) else Decimal("0.5")) if sv is not None and cv is not None else None)
    dist = decimal(comp.get("distance_km"))
    if dist is not None:
        put("distancia", Decimal("1") if dist <= 1 else Decimal("0.7") if dist <= 3 else Decimal("0.4") if dist <= 5 else Decimal("0.1"))
    weights = {k: w for k, w in _SIMILARITY_WEIGHTS.items() if k in parts}
    score = sum((parts[k] * w for k, w in weights.items()), ZERO) / sum(weights.values(), ZERO)
    return {"grau": score.quantize(Decimal("0.01")), "criterios": {k: v.quantize(Decimal("0.01")) for k, v in parts.items()}, "nao_informados": missing,
            "fora_do_municipio": bool(sc and cc and sc != cc)}


def percentile(values: list[Decimal], fraction: Decimal) -> Decimal | None:
    """Percentil com interpolação linear (fraction em 0–1)."""
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    pos = (Decimal(len(ordered) - 1)) * fraction
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - Decimal(low))


def outlier_bounds(values: list[Decimal], factor: Decimal = OUTLIER_IQR_FACTOR) -> tuple[Decimal, Decimal] | None:
    """Limites de Tukey (Q1 − k·IQR, Q3 + k·IQR). Com menos de 4 valores não há como identificar discrepantes."""
    if len(values) < 4:
        return None
    q1, q3 = percentile(values, Decimal("0.25")), percentile(values, Decimal("0.75"))
    iqr = q3 - q1
    return q1 - factor * iqr, q3 + factor * iqr


def _value_of(comp: dict, kind: str) -> Decimal | None:
    value = decimal(comp.get("rent") if kind == "ALUGUEL" else comp.get("price"))
    return value if value is not None and value > ZERO else None


def _is_duplicate(a: dict, b: dict, kind: str) -> bool:
    """Mesmo imóvel anunciado por corretores diferentes: mesmo valor (diferença de até R$ 1 ou 0,1%), área até 1,5 m²
    de diferença e mesmo bairro (ou bairro não informado em um deles). Na coleta real (imóvel 7) as repetições tinham
    valor idêntico; tolerância maior juntaria unidades diferentes do mesmo prédio."""
    va, vb = _value_of(a, kind), _value_of(b, kind)
    if va is None or vb is None or abs(va - vb) > max(Decimal("1"), max(va, vb) * Decimal("0.001")):
        return False
    aa, ab = decimal(a.get("area_m2")) or ZERO, decimal(b.get("area_m2")) or ZERO
    if aa > ZERO and ab > ZERO and abs(aa - ab) > Decimal("1.5"):
        return False
    na, nb = _fold(a.get("neighborhood")), _fold(b.get("neighborhood"))
    return not (na and nb and na != nb)


def estimate(subject: dict, comparables: list[dict], kind: str = "VENDA", *, negotiation_discount: Decimal = DEFAULT_NEGOTIATION_DISCOUNT,
             min_similarity: Decimal = DEFAULT_MIN_SIMILARITY, min_sample: int = MIN_SAMPLE) -> dict:
    """Estimativa de valor (VENDA) ou aluguel mensal (ALUGUEL) a partir dos comparáveis, com memória de cálculo.

    Etapas, todas registradas em ``comparaveis`` (usado/excluído e motivo): excluídos manualmente → duplicatas →
    sem valor → similaridade abaixo do mínimo → sem área (fora do R$/m²) → discrepantes (Tukey). O R$/m² anunciado é
    convertido em "provável negociado" com ``negotiation_discount``; transacionados entram sem desconto."""
    kind = "ALUGUEL" if normalize_kind(kind) == "ALUGUEL" else "VENDA"
    area = decimal(subject.get("area"))
    rows: list[dict] = []
    kept: list[dict] = []
    for comp in comparables:
        if normalize_kind(comp.get("kind", "VENDA")) != kind:
            continue
        sim = similarity(subject, comp)
        row = {"id": comp.get("id"), "valor": _value_of(comp, kind), "area_m2": decimal(comp.get("area_m2")), "tipo_preco": (comp.get("price_type") or PRICE_ANUNCIADO),
               "similaridade": sim["grau"], "criterios": sim["criterios"], "nao_informados": sim["nao_informados"], "usado": False, "motivo": None,
               "fonte": comp.get("source"), "url": comp.get("url"), "consultado_em": comp.get("collected_at"), "bairro": comp.get("neighborhood"),
               "endereco": comp.get("address"), "area_base": comp.get("area_basis"), "distancia_km": decimal(comp.get("distance_km"))}
        rows.append(row)
        if comp.get("excluded"):
            row["motivo"] = "Excluído no cadastro: " + (comp.get("exclusion_reason") or "sem motivo informado")
            continue
        if row["valor"] is None:
            row["motivo"] = "Sem valor informado"
            continue
        dup = next((k for k in kept if _is_duplicate(k["_comp"], comp, kind)), None)
        if dup is not None:
            row["motivo"] = f"Provável duplicata do comparável {dup['row']['id']} (mesmo valor, área e bairro)"
            continue
        if sim["fora_do_municipio"]:
            row["motivo"] = "Fora do município do imóvel"
            continue
        if sim["grau"] < min_similarity:
            row["motivo"] = f"Similaridade {sim['grau']} abaixo do mínimo {min_similarity}"
            continue
        kept.append({"_comp": comp, "row": row})

    with_area = [k for k in kept if k["row"]["area_m2"] and k["row"]["area_m2"] > ZERO]
    for k in kept:
        if k not in with_area:
            k["row"]["motivo"] = "Sem área: não entra no cálculo por m²"
    m2 = {id(k): k["row"]["valor"] / k["row"]["area_m2"] for k in with_area}
    bounds = outlier_bounds(list(m2.values()))
    used = []
    for k in with_area:
        value = m2[id(k)]
        if bounds and not (bounds[0] <= value <= bounds[1]):
            k["row"]["motivo"] = f"Valor discrepante: R$ {value:.2f}/m² fora de [{bounds[0]:.2f}; {bounds[1]:.2f}]"
            continue
        factor = Decimal("1") - negotiation_discount if str(k["row"]["tipo_preco"]).upper() != PRICE_TRANSACIONADO else Decimal("1")
        k["row"].update({"usado": True, "valor_m2": value.quantize(Decimal("0.01")), "valor_m2_ajustado": (value * factor).quantize(Decimal("0.01"))})
        used.append(k["row"])
    for row in rows:
        if "valor_m2" not in row and row["valor"] is not None and row["area_m2"]:
            row["valor_m2"] = (row["valor"] / row["area_m2"]).quantize(Decimal("0.01"))

    n = len(used)
    asked = [r["valor_m2"] for r in used]
    adjusted = [r["valor_m2_ajustado"] for r in used]
    cv = _coefficient_of_variation(adjusted)
    n_anunciado = sum(1 for r in used if str(r["tipo_preco"]).upper() != PRICE_TRANSACIONADO)
    if n == 0:
        confidence = CONF_SEM_DADOS
    elif n >= min_sample and cv is not None and cv <= Decimal("0.20") and n_anunciado < n:
        # ALTA exige ao menos um negócio fechado na amostra: só anúncios (preço pedido) limitam a confiança a MÉDIA.
        confidence = CONF_ALTA
    elif n >= 4 and (cv is None or cv <= HIGH_DISPERSION_CV):
        confidence = CONF_MEDIA
    else:
        confidence = CONF_BAIXA
    stats = {
        "m2_anunciado_mediana": median(asked), "m2_anunciado_media": (sum(asked, ZERO) / Decimal(n)) if n else None,
        "m2_ajustado_mediana": median(adjusted), "m2_ajustado_media": (sum(adjusted, ZERO) / Decimal(n)) if n else None,
        "m2_ajustado_p25": percentile(adjusted, Decimal("0.25")), "m2_ajustado_p75": percentile(adjusted, Decimal("0.75")),
        "m2_ajustado_min": min(adjusted) if adjusted else None, "m2_ajustado_max": max(adjusted) if adjusted else None,
        "coeficiente_variacao": cv,
    }
    low_m2 = stats["m2_ajustado_p25"] if n >= 4 else stats["m2_ajustado_min"]
    high_m2 = stats["m2_ajustado_p75"] if n >= 4 else stats["m2_ajustado_max"]
    avisos: list[str] = []
    if n == 0:
        avisos.append("Nenhum comparável utilizável: sem base para estimativa.")
    elif n < MIN_POINT_ESTIMATE:
        avisos.append(f"Apenas {n} comparável(is) utilizável(is): só faixa indicativa, sem valor pontual.")
    elif n < min_sample:
        avisos.append(f"Amostra pequena ({n} < {min_sample} recomendados): estimativa de baixa precisão.")
    if cv is not None and cv > HIGH_DISPERSION_CV:
        avisos.append("Dispersão elevada entre os comparáveis.")
    if n_anunciado:
        avisos.append(f"{n_anunciado} de {n} valores são de ANÚNCIO (preço pedido), não de negócio fechado; aplicado desconto de negociação de "
                      f"{negotiation_discount * 100:.0f}% (premissa configurável).")
    if area is None or area <= ZERO:
        avisos.append("Área do imóvel analisado ausente: sem conversão de R$/m² em valor.")
    # Limitações da amostra usada (explicitadas para quem lê a estimativa; não alteram o cálculo).
    limitacoes: list[str] = []
    basis = [str(r.get("area_base") or "").upper() for r in used]
    n_total = sum(1 for b in basis if b == "TOTAL")
    n_unknown = sum(1 for b in basis if b not in ("PRIVATIVA", "UTIL", "ÚTIL", "TOTAL"))
    if n_total:
        limitacoes.append(f"{n_total} de {n} comparável(is) informam ÁREA TOTAL (inclui áreas comuns/vaga): R$/m² tende a ficar MENOR que o "
                          "da área privativa, o que puxa a estimativa para baixo. Similaridade de área reduzida em 20% nesses casos.")
    if n_unknown:
        limitacoes.append(f"{n_unknown} de {n} comparável(is) sem base de área declarada no anúncio (privativa ou total): R$/m² com incerteza de base.")
    if n and n_anunciado == n:
        limitacoes.append("Nenhum negócio fechado (ITBI, cartório ou corretor) na amostra: só preço pedido; confiança limitada a MÉDIA.")
    if n and not any(r.get("distancia_km") is not None for r in used):
        limitacoes.append("Distância até o imóvel não medida em nenhum comparável: localização avaliada só por bairro/município.")
    no_bed = sum(1 for r in used if "quartos" in (r.get("nao_informados") or []))
    if no_bed:
        limitacoes.append(f"{no_bed} comparável(is) sem número de quartos no anúncio (critério neutro).")
    if n:
        limitacoes.append("Estado de conservação dos comparáveis e do imóvel não vistoriado: o valor supõe padrão equivalente.")
    has_area = area is not None and area > ZERO
    cents = Decimal("0.01")
    point = (stats["m2_ajustado_mediana"] * area).quantize(cents) if (has_area and n >= MIN_POINT_ESTIMATE) else None
    return {
        "tipo": kind, "quantidade_usada": n, "quantidade_total": len(rows), "quantidade_anunciada": n_anunciado,
        "confianca": confidence, "valor_estimado": point,
        "faixa": {"min": (low_m2 * area).quantize(cents), "max": (high_m2 * area).quantize(cents)} if (has_area and n) else None,
        "faixa_criterio": "P25–P75" if n >= 4 else ("mín–máx" if n else None),
        "area_referencia": area, "estatisticas_m2": stats, "desconto_negociacao": negotiation_discount,
        "similaridade_minima": min_similarity, "similaridade_media": (sum((r["similaridade"] for r in used), ZERO) / Decimal(n)).quantize(Decimal("0.01")) if n else None,
        "limites_discrepancia": {"min": bounds[0], "max": bounds[1]} if bounds else None,
        "comparaveis": rows, "avisos": avisos, "limitacoes": limitacoes, "indicativa": n < MIN_POINT_ESTIMATE,
        "qualidade_amostra": sample_quality(n, cv, min_sample=min_sample),
    }


AMOSTRA_INSUFICIENTE, AMOSTRA_BAIXA, AMOSTRA_MEDIA, AMOSTRA_ALTA = "INSUFICIENTE", "BAIXA", "MEDIA", "ALTA"
AMOSTRA_LABELS = {AMOSTRA_INSUFICIENTE: "Amostra insuficiente", AMOSTRA_BAIXA: "Amostra baixa", AMOSTRA_MEDIA: "Amostra média",
                  AMOSTRA_ALTA: "Amostra alta"}


def sample_quality(n: int, cv: Decimal | None = None, *, min_sample: int = MIN_SAMPLE) -> dict:
    """Qualidade da amostra de comparáveis usados (v1.0.14): INSUFICIENTE (< 3, sem valor pontual), BAIXA (3 até abaixo do mínimo do
    método), MEDIA (mínimo atingido com dispersão alta) e ALTA (mínimo atingido e dispersão controlada)."""
    if n < MIN_POINT_ESTIMATE:
        level = AMOSTRA_INSUFICIENTE
        text = (f"{n} comparável(is) utilizável(is): abaixo de {MIN_POINT_ESTIMATE}, não há valor de mercado confiável. "
                "Cadastre mais imóveis parecidos.")
    elif n < min_sample:
        level = AMOSTRA_BAIXA
        text = f"{n} comparáveis utilizáveis: abaixo dos {min_sample} recomendados pelo método; estimativa de baixa precisão."
    elif cv is not None and cv > HIGH_DISPERSION_CV:
        level = AMOSTRA_MEDIA
        text = f"{n} comparáveis, mas com preços por m² muito diferentes entre si (dispersão alta)."
    else:
        level = AMOSTRA_ALTA
        text = f"{n} comparáveis com preços por m² próximos entre si."
    return {"nivel": level, "label": AMOSTRA_LABELS[level], "quantidade": n, "minimo_recomendado": min_sample, "texto": text}


def liquidity(sale: dict, rent: dict, subject: dict, *, acquisition: Decimal | None = None) -> dict:
    """Liquidez estimada da revenda, com justificativa e confiança. Prazo de venda só com dados de tempo de venda
    (anúncio e fechamento); o sistema não presume prazo."""
    n = sale.get("quantidade_usada") or 0
    reasons: list[str] = []
    if n == 0:
        return {"classificacao": LIQ_INDETERMINADA, "pontuacao": None, "confianca": CONF_SEM_DADOS, "prazo_estimado_meses": None,
                "justificativa": ["Sem comparáveis de venda utilizáveis: liquidez não avaliada."],
                "prazo_observacao": "Sem dados de tempo de venda (data do anúncio e do fechamento)."}
    points = Decimal("0")
    if n >= MIN_SAMPLE:
        points += 2; reasons.append(f"Oferta comparável ampla ({n} anúncios semelhantes no município).")
    elif n >= 4:
        points += 1; reasons.append(f"Oferta comparável moderada ({n} anúncios semelhantes).")
    else:
        reasons.append(f"Pouca oferta comparável identificada ({n}).")
    cv = (sale.get("estatisticas_m2") or {}).get("coeficiente_variacao")
    if cv is not None and cv <= Decimal("0.20"):
        points += 1; reasons.append("Preços por m² homogêneos (mercado com referência clara).")
    tipo, quartos, area = _type_key(subject.get("property_type")), subject.get("bedrooms"), decimal(subject.get("area"))
    if tipo == "APARTAMENTO" and quartos is not None and 1 <= int(quartos) <= 3 and area is not None and Decimal("30") <= area <= Decimal("80"):
        points += 1; reasons.append("Tipologia de maior procura (apartamento compacto de 1 a 3 quartos).")
    if subject.get("parking_spots"):
        points += Decimal("0.5"); reasons.append("Possui vaga de garagem.")
    if (rent.get("quantidade_usada") or 0) >= 1:
        points += Decimal("0.5"); reasons.append("Há demanda de locação observada para a tipologia.")
    market = sale.get("valor_estimado")
    if acquisition is not None and market:
        ratio = decimal(acquisition) / market
        reasons.append(f"Preço de aquisição equivale a {ratio * 100:.0f}% do valor estimado: margem para revender abaixo do mercado, se necessário.")
    classification = LIQ_ALTA if points >= 4 else LIQ_MEDIA if points >= Decimal("2.5") else LIQ_BAIXA
    if classification == LIQ_ALTA and not sale.get("quantidade_usada", 0) > sale.get("quantidade_anunciada", 0):
        # Só anúncios: muita oferta é referência de preço, mas também concorrência na revenda; sem negócios fechados ou
        # tempo de venda, a liquidez não é classificada como ALTA.
        classification = LIQ_MEDIA
        reasons.append("Sem negócios fechados nem tempo de venda observados: classificação limitada a MÉDIA (muita oferta também é concorrência na revenda).")
    confidence = sale.get("confianca") if sale.get("confianca") != CONF_ALTA else CONF_MEDIA   # sem tempo de venda real, no máximo MÉDIA
    return {"classificacao": classification, "pontuacao": points, "confianca": confidence, "prazo_estimado_meses": None, "justificativa": reasons,
            "prazo_observacao": "Sem dados de tempo de venda (data do anúncio e do fechamento): prazo não estimado."}


def calculate_market(comparables: list[dict] | None, *, min_sample: int = MIN_SAMPLE, high_dispersion_cv: Decimal = HIGH_DISPERSION_CV) -> dict:
    """Consolida exclusivamente comparáveis já cadastrados, sem scoring ou valuation
    automático. Sinaliza a qualidade da amostra (suficiência, dispersão) e preserva
    a origem/data quando disponível. A média/mediana NÃO é avaliação definitiva de
    mercado — isso é explicitado em ``qualidade`` (SPEC/auditoria Task 2).

    ``min_sample``/``high_dispersion_cv`` são parametrizáveis (Etapa D): o router
    resolve pelo catálogo central e injeta; os defaults preservam o valor histórico."""
    rows = comparables or []
    return {
        "venda": summarize_sale(rows, min_sample=min_sample, high_dispersion_cv=high_dispersion_cv),
        "aluguel": summarize_rent(rows, min_sample=min_sample, high_dispersion_cv=high_dispersion_cv),
        "fontes": _sources(rows),
        "observacao": "Estimativa baseada apenas em comparáveis cadastrados manualmente; não há verificação externa.",
        "parametros": {"amostra_minima": min_sample, "cv_dispersao_alta": str(high_dispersion_cv)},
    }
