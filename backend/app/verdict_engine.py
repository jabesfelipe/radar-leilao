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


# Grupos de fatores do veredito (v2). Não mudam a decisão: explicam o que a impede e como resolver cada pendência.
FATOR_IMPEDIMENTO = "impedimentos"
FATOR_INFORMACAO = "informacoes_essenciais"
FATOR_PREMISSA = "premissas_nao_configuradas"
FATOR_RISCO_CONFIANCA = "riscos_confianca"
FATOR_NAO_APLICAVEL = "nao_aplicaveis"
FATORES_ORDEM = (FATOR_IMPEDIMENTO, FATOR_INFORMACAO, FATOR_PREMISSA, FATOR_RISCO_CONFIANCA, FATOR_NAO_APLICAVEL)
FATORES_TITULO = {
    FATOR_IMPEDIMENTO: "Impedimentos jurídicos ou documentais",
    FATOR_INFORMACAO: "Informações essenciais ainda desconhecidas",
    FATOR_PREMISSA: "Premissas financeiras não configuradas",
    FATOR_RISCO_CONFIANCA: "Riscos que reduzem a confiança",
    FATOR_NAO_APLICAVEL: "Não aplicáveis à modalidade",
}
_ACAO_PREMISSA = "Informar em Financeiro > Premissas e salvar para recalcular."
_PREMISSA_TERMOS = ("valor de venda", "meta", "corretagem", "tributo", "prazo")


def _is_premise_text(text: str) -> bool:
    lowered = text.lower()
    if lowered.startswith(("custo", "cálculo provisório", "preço máximo é")):   # custos desconhecidos, não premissa
        return False
    return any(word in lowered for word in _PREMISSA_TERMOS)


def consolidate_factors(current_risks: list[Any], checklist_results: Iterable[Any], assessment: dict[str, Any], financial_pending: list[str]) -> dict[str, Any]:
    """Separa, sem perder nenhuma pendência, o que impede a recomendação, o que falta saber, o que falta configurar,
    o que só reduz a confiança e o que não se aplica. Cada fator traz a justificativa e a ação que o resolve."""
    from . import modality_rules
    groups: dict[str, list[dict[str, Any]]] = {key: [] for key in FATORES_ORDEM}
    # Risco gerado de um item do checklist (RiskEngine: risk_key "CHECKLIST_<chave>_<estado>") aparece uma vez só:
    # o fator do risco recebe a justificativa e a ação do item.
    risk_by_item: dict[str, dict[str, Any]] = {}
    for risk in current_risks:
        severity = _normalize(_value(risk, "severity"))
        target = FATOR_IMPEDIMENTO if severity in {"CRITICA", "ALTA"} else FATOR_RISCO_CONFIANCA
        entry = {"origem": "RISCO", "descricao": str(_value(risk, "description") or "Risco ativo"), "gravidade": severity or None,
                 "acao": "Resolver ou precificar o risco antes de decidir; validar com advogado." if target == FATOR_IMPEDIMENTO else "Avaliar e precificar o risco."}
        groups[target].append(entry)
        # RiskCandidate tem risk_key; o models.Risk persistido guarda em origin ("RiskEngine:ChecklistResult:<risk_key>").
        risk_key = str(_value(risk, "risk_key") or str(_value(risk, "origin") or "").rsplit(":", 1)[-1])
        if risk_key.startswith("CHECKLIST_"):
            for state_suffix in ("_RISCO_IDENTIFICADO", "_ATENCAO"):
                if risk_key.endswith(state_suffix):
                    risk_by_item[risk_key[len("CHECKLIST_"):-len(state_suffix)]] = entry
    for result in checklist_results:
        item = _value(result, "item")
        if item is None:
            continue
        key = _value(item, "canonical_key")
        purpose = modality_rules.ITEM_PURPOSE.get(key, {"grupo": modality_rules.GRUPO_DOCUMENTACAO, "acao": ""})
        state = _normalize(_value(result, "state"))
        entry = {"origem": "CHECKLIST", "chave": key, "descricao": _value(item, "question"), "estado": state, "grupo_item": purpose["grupo"],
                 "justificativa": (_value(result, "interpretation") or _value(result, "answer") or "").strip() or None, "acao": purpose["acao"]}
        if state in {"RISCO_IDENTIFICADO", "ATENCAO"} and key in risk_by_item:
            linked = risk_by_item[key]
            linked.update({"chave": key, "estado": state, "grupo_item": purpose["grupo"], "descricao": entry["descricao"],
                           "justificativa": " ".join(t for t in ((_value(result, "answer") or "").strip(), (_value(result, "interpretation") or "").strip()) if t) or None,
                           "acao": purpose["acao"] or linked["acao"]})
            continue
        if not _value(result, "applicable", True) or state == "NAO_APLICAVEL":
            groups[FATOR_NAO_APLICAVEL].append({**entry, "justificativa": (_value(result, "answer") or "").strip() or entry["justificativa"], "acao": None})
        elif state == "RISCO_IDENTIFICADO" and purpose["grupo"] in (modality_rules.GRUPO_SITUACAO_REGISTRAL, modality_rules.GRUPO_DOCUMENTACAO):
            groups[FATOR_IMPEDIMENTO].append(entry)
        elif state in {"PENDENTE", "EM_ANALISE"}:
            if purpose["grupo"] == modality_rules.GRUPO_FINANCEIRO_PREMISSAS:
                groups[FATOR_PREMISSA].append(entry)
            elif purpose["grupo"] in (modality_rules.GRUPO_PROCEDIMENTO_ORIGEM, modality_rules.GRUPO_PREFERENCIA):
                groups[FATOR_RISCO_CONFIANCA].append(entry)
            else:
                groups[FATOR_INFORMACAO].append(entry)
    # Pendências financeiras agrupadas por ASSUNTO (v1.0.12): o mesmo assunto (ex.: valor de venda) aparecia várias vezes, uma por
    # motor/mensagem. Fica um fator por assunto; as demais mensagens vão em ``detalhes`` (nenhuma é perdida).
    by_subject: dict[str, dict[str, Any]] = {}
    for text in _unique(list(assessment.get("faltantes") or []) + list(financial_pending)):
        subject = financial_subject(text)
        if subject in by_subject:
            entry = by_subject[subject]
            entry["detalhes"].append(text)
            entry["premissa"] = entry["premissa"] or _is_premise_text(text)
            continue
        by_subject[subject] = {"origem": "FINANCEIRO", "assunto": subject, "assunto_titulo": ASSUNTOS_FINANCEIROS.get(subject, subject),
                               "descricao": text, "detalhes": [], "premissa": _is_premise_text(text)}
    for entry in by_subject.values():
        # Premissa do investidor (venda, meta, corretagem, tributo, prazo) x dado desconhecido (custos, débitos, lance).
        premissa = entry.pop("premissa") or entry["assunto"] in _ASSUNTOS_PREMISSA
        entry["acao"] = _ACAO_PREMISSA if premissa else _ACAO_ASSUNTO.get(entry["assunto"], "Cadastrar o dado em Financeiro (custos, dívidas ou lance).")
        groups[FATOR_PREMISSA if premissa else FATOR_INFORMACAO].append(entry)
    return {"grupos": groups, "titulos": FATORES_TITULO, "contagem": {key: len(groups[key]) for key in FATORES_ORDEM}}


ASSUNTOS_FINANCEIROS = {"VALOR_VENDA": "Valor de venda", "META": "Meta financeira e preço máximo", "PREMISSAS_VENDA": "Premissas de venda",
                        "DEBITOS": "Débitos (condomínio e IPTU)", "OCUPACAO": "Ocupação e desocupação", "CUSTOS": "Custos da operação",
                        "JURIDICO": "Jurídico", "LANCE": "Lance pretendido"}
_ASSUNTOS_PREMISSA = {"VALOR_VENDA", "META", "PREMISSAS_VENDA"}
_ACAO_ASSUNTO = {"DEBITOS": "Solicitar declaração do condomínio e certidão de IPTU e cadastrar em Débitos.",
                 "OCUPACAO": "Verificar a ocupação e registrar em Ocupação.", "JURIDICO": "Validar com advogado."}


def financial_subject(text: str) -> str:
    """Assunto de uma pendência financeira, para agrupar mensagens repetidas de motores diferentes."""
    low = text.lower()
    if "lance pretendido" in low:
        return "LANCE"
    if low.startswith(("cálculo provisório", "preço máximo é")):
        return "CUSTOS"
    if "valor de venda" in low:
        return "VALOR_VENDA"
    if "meta" in low or "preço máximo não calculado" in low:
        return "META"
    if any(w in low for w in ("condomínio", "iptu", "tributos em atraso", "dívida", "débito")) and "posse" not in low:
        return "DEBITOS"
    if "ocupa" in low:
        return "OCUPACAO"
    if any(w in low for w in ("corretagem", "tributo na venda", "prazo da operação")):
        return "PREMISSAS_VENDA"
    if any(w in low for w in ("jurídic", "matrícula", "ônus")):
        return "JURIDICO"
    return "CUSTOS"


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
        checklist_results = list(checklist_results)   # percorrido duas vezes (pendências e fatores)
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
            "fatores": consolidate_factors(current_risks, checklist_results, assessment, financial_pending),
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
