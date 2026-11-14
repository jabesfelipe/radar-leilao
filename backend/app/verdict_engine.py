from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable
import unicodedata


VERDICT_STATES = ("FAVORAVEL", "ATENCAO", "DESFAVORAVEL", "INCONCLUSIVO")

# Situação financeira da operação NO LANCE PRETENDIDO (motor determinístico, sem IA).
FIN_VIAVEL = "VIAVEL"
FIN_INVIAVEL = "INVIAVEL"
FIN_INDETERMINADO = "INDETERMINADO"

# Tipos de fundamento do veredito: o investidor precisa saber POR QUE, e de que natureza.
F_RISCO_JURIDICO = "RISCO_JURIDICO"
F_RISCO_OPERACIONAL = "RISCO_OPERACIONAL"
F_INVIABILIDADE_FINANCEIRA = "INVIABILIDADE_FINANCEIRA"
F_PENDENCIA_DOCUMENTAL = "PENDENCIA_DOCUMENTAL"
F_PENDENCIA_FINANCEIRA = "PENDENCIA_FINANCEIRA"
F_ANALISE_AUTOMATICA_INDISPONIVEL = "ANALISE_AUTOMATICA_INDISPONIVEL"
F_VIABILIDADE_FINANCEIRA = "VIABILIDADE_FINANCEIRA"

_LEGAL_RISK_CATEGORIES = {"JURIDICO", "DOCUMENTAL"}


@dataclass(frozen=True)
class VerdictDecision:
    property_id: int
    analysis_version: int
    overall: str
    summary: str
    what_is_known: str
    what_is_unknown: str
    pending_items: list[str]
    financial: dict[str, Any]
    risk_ids: list[int]
    evidence_ids: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize(value: Any) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().upper()


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def brl(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "não informado"
    text = f"{abs(number):,.0f}".replace(",", ".")
    return f"-R$ {text}" if number < 0 else f"R$ {text}"


def pct(value: Any) -> str:
    number = _num(value)
    return "não calculada" if number is None else f"{number * 100:.1f}%".replace(".", ",")


def assess_financial(financial: dict[str, Any] | None) -> dict[str, Any]:
    """Avalia, de forma determinística, se a operação atende aos critérios financeiros NO LANCE pretendido.

    Entrada: o resultado de ``finance.calculate_financial`` (já serializado). Nada é inventado: sem
    lance, valor de venda ou meta, o resultado é INDETERMINADO com a lista do que falta.

    Regras de INVIABILIDADE (valem mesmo quando o cálculo é PROVISÓRIO): custos desconhecidos entram
    como zero na simulação parcial, o que só MELHORA o resultado e SUPERESTIMA o preço máximo. Logo, se
    a operação já é ruim com esses custos zerados, ela é ruim de verdade:
      - resultado líquido projetado negativo (prejuízo);
      - lance pretendido acima do preço máximo calculado para a meta;
      - meta configurada (margem, ROI ou lucro mínimo) não atingida no lance;
      - meta inatingível para o valor de venda e os custos informados.
    VIÁVEL exige cálculo COMPLETO (sem custos materiais desconhecidos), preço máximo DEFINITIVO, meta
    configurada e atendida, e lance dentro do preço máximo.
    """
    fin = dict(financial or {})
    lance = _num(fin.get("valor_aquisicao"))
    preco_maximo = _num(fin.get("preco_maximo"))
    definitivo = bool(fin.get("preco_maximo_definitivo"))
    resultado = _num(fin.get("resultado_liquido"))
    margem = _num(fin.get("margem_liquida"))
    roi = _num(fin.get("roi_operacao"))
    completo = bool(fin.get("resultado_completo"))
    detalhe = fin.get("preco_maximo_detalhe") or {}
    meta = (detalhe.get("premissas_utilizadas") or {}).get("meta") or {}
    meta_tipo = meta.get("tipo")
    meta_valor = _num(meta.get("valor"))
    razao = detalhe.get("razao")
    venda = _num(fin.get("valor_mercado"))
    metricas = {
        "lance": lance, "preco_maximo": preco_maximo, "preco_maximo_definitivo": definitivo,
        "resultado_liquido": resultado, "margem_liquida": margem, "roi_operacao": roi,
        "custo_total": _num(fin.get("custo_total")), "valor_venda": venda, "break_even": _num(fin.get("break_even")),
        "meta": {"tipo": meta_tipo, "valor": meta_valor} if meta_tipo else None,
        "calculo_completo": completo,
    }

    faltantes: list[str] = []
    if lance is None or lance <= 0:
        faltantes.append("Lance pretendido (valor de arrematação) não informado.")
    if venda is None:
        faltantes.append("Valor de venda estimado não informado.")
    if not meta_tipo:
        faltantes.append("Meta financeira (margem, ROI ou lucro mínimo) não configurada.")
    if lance is None or lance <= 0:
        # Sem lance o resultado é calculado sobre zero: nada pode ser concluído.
        return {"status": FIN_INDETERMINADO, "motivos": [], "faltantes": faltantes, "metricas": metricas}

    motivos: list[str] = []
    if resultado is not None and resultado < 0:
        motivos.append(f"Resultado projetado negativo: prejuízo de {brl(-resultado)} no lance de {brl(lance)} (margem {pct(margem)}).")
    if preco_maximo is not None and lance > preco_maximo:
        excesso = (lance / preco_maximo - 1) if preco_maximo > 0 else None
        texto = f"Lance de {brl(lance)} acima do preço máximo de {brl(preco_maximo)}"
        if excesso is not None:
            texto += f" ({pct(excesso)} acima)"
        motivos.append(texto + ".")
    if razao == "META_INATINGIVEL":
        motivos.append("Meta financeira inatingível com o valor de venda e os custos informados.")
    if meta_tipo == "MARGEM_MINIMA" and meta_valor is not None and margem is not None and margem < meta_valor:
        motivos.append(f"Margem líquida de {pct(margem)} abaixo da mínima de {pct(meta_valor)}.")
    elif meta_tipo == "ROI_MINIMO" and meta_valor is not None and roi is not None and roi < meta_valor:
        motivos.append(f"ROI da operação de {pct(roi)} abaixo do mínimo de {pct(meta_valor)}.")
    elif meta_tipo == "LUCRO_MINIMO" and meta_valor is not None and resultado is not None and resultado < meta_valor:
        motivos.append(f"Lucro projetado de {brl(resultado)} abaixo do mínimo de {brl(meta_valor)}.")
    if motivos:
        return {"status": FIN_INVIAVEL, "motivos": _unique(motivos), "faltantes": faltantes, "metricas": metricas}

    if not completo:
        desconhecidos = detalhe.get("custos_desconhecidos") or []
        faltantes.append("Cálculo provisório: há custos materiais desconhecidos" + (f" ({', '.join(desconhecidos)})" if desconhecidos else "") + ".")
    if preco_maximo is None and meta_tipo:
        faltantes.append("Preço máximo não calculado.")
    elif preco_maximo is not None and not definitivo:
        faltantes.append("Preço máximo é estimativa provisória.")
    if faltantes:
        return {"status": FIN_INDETERMINADO, "motivos": [], "faltantes": _unique(faltantes), "metricas": metricas}
    return {
        "status": FIN_VIAVEL,
        "motivos": [f"Lance de {brl(lance)} dentro do preço máximo de {brl(preco_maximo)}; resultado projetado {brl(resultado)} (margem {pct(margem)}, ROI {pct(roi)})."],
        "faltantes": [], "metricas": metricas,
    }


class VerdictEngine:
    """Motor puro que decide o estado a partir de resultados já persistidos (determinístico)."""

    def evaluate(
        self,
        property_id: int,
        analysis_version: int,
        risks: Iterable[Any] = (),
        checklist_results: Iterable[Any] = (),
        pending_items: Iterable[str] = (),
        evidence_ids: Iterable[int] = (),
        financial: dict[str, Any] | None = None,
        automated_analysis_available: bool | None = None,
    ) -> VerdictDecision:
        current_risks = [risk for risk in risks if _normalize(_value(risk, "status", "ATIVO")) not in {"INATIVO", "SUPERADO"}]
        risk_ids = _unique(_value(risk, "id") for risk in current_risks if _value(risk, "id") is not None)
        risk_evidence_ids = [
            _value(risk, "evidence_id")
            for risk in current_risks
            if _value(risk, "evidence_id") is not None
        ]
        checklist_pending_results = [
            result for result in checklist_results
            if _value(result, "applicable", True) and _normalize(_value(result, "state")) in {"PENDENTE", "EM_ANALISE"} and _value(result, "item") is not None
        ]
        checklist_pending = [_value(_value(result, "item"), "question") for result in checklist_pending_results]
        finance = dict(financial or {})
        financial_pending = [item for item in list(finance.get("pendencias", []) or []) if item]
        pending = _unique([item for item in list(checklist_pending) + list(pending_items) + financial_pending if item])
        all_evidence_ids = _unique(list(evidence_ids) + risk_evidence_ids)
        severities = {_normalize(_value(risk, "severity")) for risk in current_risks}
        assessment = assess_financial(finance) if finance else {"status": FIN_INDETERMINADO, "motivos": [], "faltantes": ["Cálculo financeiro não disponível."], "metricas": {}}

        # ---- Fundamentos, separados por natureza ----
        fundamentos: list[dict[str, Any]] = []
        for risk in current_risks:
            categoria = _normalize(_value(risk, "category"))
            tipo = F_RISCO_JURIDICO if categoria in _LEGAL_RISK_CATEGORIES or not categoria else F_RISCO_OPERACIONAL
            fundamentos.append({"tipo": tipo, "gravidade": _normalize(_value(risk, "severity")) or None, "descricao": str(_value(risk, "description") or "Risco ativo")})
        if assessment["status"] == FIN_INVIAVEL:
            fundamentos += [{"tipo": F_INVIABILIDADE_FINANCEIRA, "descricao": motivo} for motivo in assessment["motivos"]]
        elif assessment["status"] == FIN_VIAVEL:
            fundamentos += [{"tipo": F_VIABILIDADE_FINANCEIRA, "descricao": motivo} for motivo in assessment["motivos"]]
        fundamentos += [{"tipo": F_PENDENCIA_FINANCEIRA, "descricao": item} for item in _unique(assessment["faltantes"] + financial_pending)]
        for result in checklist_pending_results:
            item = _value(result, "item")
            fundamentos.append({"tipo": F_PENDENCIA_DOCUMENTAL, "categoria": _value(item, "category"), "descricao": _value(item, "question")})
        if automated_analysis_available is False:
            fundamentos.append({"tipo": F_ANALISE_AUTOMATICA_INDISPONIVEL, "descricao": "A leitura automática dos documentos não foi executada nesta análise; riscos jurídicos e documentais NÃO foram avaliados por ela."})

        # ---- Decisão (precedência explícita) ----
        financeiro_inviavel = assessment["status"] == FIN_INVIAVEL
        if "CRITICA" in severities:
            overall = "DESFAVORAVEL"
        elif financeiro_inviavel:
            overall = "DESFAVORAVEL"
        elif severities:
            overall = "ATENCAO"
        elif pending:
            overall = "INCONCLUSIVO"
        elif not all_evidence_ids:
            overall = "INCONCLUSIVO"
        elif assessment["status"] != FIN_VIAVEL:
            overall = "INCONCLUSIVO"
        else:
            overall = "FAVORAVEL"

        metricas = assessment.get("metricas") or {}
        lance_maximo = metricas.get("preco_maximo")
        if overall == "DESFAVORAVEL" and financeiro_inviavel:
            codigo = "NAO_ARREMATAR"
            texto = "NÃO ARREMATAR por este lance. " + " ".join(assessment["motivos"])
            if lance_maximo is not None and lance_maximo > 0:
                texto += f" Só reavaliar com lance de até {brl(lance_maximo)}" + ("" if metricas.get("preco_maximo_definitivo") else " (estimativa provisória)") + "."
            if "CRITICA" in severities:
                texto += " Há também risco crítico ativo."
        elif overall == "DESFAVORAVEL":
            codigo = "NAO_ARREMATAR"
            texto = "NÃO ARREMATAR: há risco crítico ativo que inviabiliza a operação, independentemente do preço."
        elif overall == "ATENCAO":
            codigo = "ARREMATAR_SOMENTE_APOS_RESOLVER_RISCOS"
            texto = f"ATENÇÃO: {len(current_risks)} risco(s) ativo(s) precisam ser resolvidos ou precificados antes de arrematar."
            if assessment["status"] == FIN_VIAVEL and lance_maximo is not None:
                texto += f" Financeiramente, o lance está dentro do preço máximo de {brl(lance_maximo)}."
        elif overall == "FAVORAVEL":
            codigo = "ARREMATAR_ATE_PRECO_MAXIMO"
            texto = f"FAVORÁVEL: arrematar até {brl(lance_maximo)}. " + " ".join(assessment["motivos"])
        else:
            codigo = "COMPLETAR_ANALISE"
            texto = "INCONCLUSIVO: ainda não é possível recomendar a arrematação."
            if assessment["status"] != FIN_VIAVEL:
                texto += " Faltam dados financeiros essenciais."
            if checklist_pending:
                texto += f" {len(checklist_pending)} item(ns) do checklist sem confirmação."
            if automated_analysis_available is False:
                texto += " A leitura automática dos documentos não foi executada."

        recomendacao = {"codigo": codigo, "texto": texto.strip(), "lance_maximo": lance_maximo,
                        "lance_maximo_definitivo": bool(metricas.get("preco_maximo_definitivo")), "lance_pretendido": metricas.get("lance")}
        finance["decisao"] = {
            "recomendacao": recomendacao,
            "avaliacao_financeira": assessment,
            "fundamentos": fundamentos,
            "analise_automatica_disponivel": automated_analysis_available,
        }

        known_parts = []
        if assessment["status"] in (FIN_VIAVEL, FIN_INVIAVEL):
            known_parts.append("Financeiro (cálculo determinístico): " + " ".join(assessment["motivos"]))
        if current_risks:
            known_parts.append(f"{len(current_risks)} risco(s) ativo(s) com base no checklist.")
        if all_evidence_ids:
            known_parts.append("Evidências e resultados determinísticos registrados na análise.")
        known = " ".join(known_parts) if known_parts else "Nenhuma evidência suficiente foi registrada na análise."
        unknown = "; ".join(pending) if pending else ""
        summary = f"{recomendacao['texto']} (Veredito determinístico da Analysis V{analysis_version}: {overall}.)"
        return VerdictDecision(
            property_id=property_id,
            analysis_version=analysis_version,
            overall=overall,
            summary=summary,
            what_is_known=known,
            what_is_unknown=unknown,
            pending_items=pending,
            financial=finance,
            risk_ids=[int(value) for value in risk_ids],
            evidence_ids=[int(value) for value in all_evidence_ids],
        )
