"""Checklist por prioridade (v1.0.14): P0 bloqueadores, P1 riscos críticos, P2 riscos importantes, P3 complementares.

Leitura pura sobre a última execução do checklist. Não muda estado, resposta nem regra de nenhum item: só ordena, explica
em linguagem simples (catálogo de riscos) e diz o que verificar, a próxima ação e quem costuma resolver.
"""
from __future__ import annotations

from typing import Any

from .checklist import RESULT_LABELS, checklist_outcome, RESULTADO_PENDENTE, RESULTADO_INCONCLUSIVO, RESULTADO_RISCO
from .risk_presenter import CATALOGO

P0, P1, P2, P3 = "P0", "P1", "P2", "P3"
PRIORITY_LABELS = {P0: "P0 — Bloqueador", P1: "P1 — Risco crítico", P2: "P2 — Risco importante", P3: "P3 — Verificação complementar"}
PRIORITY_TEXT = {P0: "Sem esta informação não há decisão segura.", P1: "Problema jurídico, de ocupação, financeiro ou documental relevante.",
                 P2: "Investigação que melhora a decisão.", P3: "Verificação menos crítica."}
PRIORIDADE: dict[str, str] = {
    "CONSOLIDACAO_REGISTRADA": P0, "EDITAL_LIDO": P0, "RESPONSABILIDADE_DEBITOS": P0, "ACAO_QUESTIONAMENTO": P0,
    "PENHORA_INDISPONIBILIDADE": P0, "COMPARAVEIS_SUFFICIENTES": P0,
    "TERCEIRO_OCUPANTE": P1, "LOCACAO_REGISTRADA": P1, "INTIMACAO_PESSOAL": P1, "NOTIFICACAO_DOIS_LEILOES": P1, "EVICCAO": P1,
    "REFORMA_GRANDE": P1,
    "QUITACAO_80": P2, "INTIMACAO_EDITAL": P2, "GARANTIA_DIVIDA_TERCEIRO": P2, "LANCE_MENOR_50_AVALIACAO": P2, "ILIQUIDEZ": P2,
    "CONDOMINIO_ALTO": P2, "RETORNO_SELIC": P2, "PRAZO_DOIS_ANOS": P2, "LEILOES_NEGATIVOS_AVERBADOS": P2, "REFORMA_LIQUIDEZ": P2,
    "VAGA_MATRICULA": P3, "REGIAO_SERVICOS": P3, "DISTANCIA_USUARIO": P3, "CONDOMINIO_PORTARIA": P3, "ETICA_OCUPACAO": P3,
}
_RESPONSAVEL = {"Jurídico": "Advogado", "Ocupação": "Advogado e investidor", "Desocupação": "Advogado e investidor", "Documentação": "Investidor ou despachante",
                "Débitos": "Investidor", "Financeiro": "Investidor", "Mercado": "Investidor ou corretor", "Reforma": "Investidor ou engenheiro",
                "Liquidez": "Investidor ou corretor", "Operacional": "Investidor"}
_OPEN = (RESULTADO_PENDENTE, RESULTADO_INCONCLUSIVO, RESULTADO_RISCO)


def _v(obj: Any, key: str, default: Any = None) -> Any:
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _evidence(result: Any) -> dict[str, Any] | None:
    for ev in _v(result, "evidences", []) or []:
        version = _v(ev, "document_version")
        doc = _v(version, "document") if version is not None else None
        name, page = (_v(doc, "name") if doc is not None else None), _v(ev, "page")
        return {"documento": name, "pagina": page, "texto": ", ".join(x for x in (name or "Cadastro do imóvel", f"página {page}" if page else None) if x)}
    return None


def prioritized(results: list[Any]) -> dict[str, Any]:
    items = []
    for result in results:
        item = _v(result, "item")
        key = _v(item, "canonical_key")
        if not key:
            continue
        spec = CATALOGO.get(key, {})
        priority = PRIORIDADE.get(key, P3)
        outcome = checklist_outcome(_v(result, "state"), _v(result, "applicable", True))
        category = spec.get("categoria", "Operacional")
        items.append({
            "chave": key, "nome": spec.get("titulo") or _v(item, "question"), "explicacao": spec.get("significado"),
            "prioridade": priority, "prioridade_label": PRIORITY_LABELS[priority], "categoria": category,
            "status": outcome, "status_label": RESULT_LABELS.get(outcome, outcome), "aberto": outcome in _OPEN,
            "impacto": spec.get("impactos") or [], "evidencia": _evidence(result),
            "fonte": {"DOCUMENTO": "documento analisado", "REGRA_DETERMINISTICA": "dados cadastrados"}.get(str(_v(result, "resolution_origin") or ""),
                                                                                                      "ainda sem fonte" if outcome in _OPEN else "análise"),
            "o_que_verificar": _v(item, "question"), "resposta": _v(result, "answer") or None,
            "proxima_acao": (spec.get("acoes") or ["Revisar o item e registrar a conclusão."])[0] if outcome in _OPEN else None,
            "responsavel": _RESPONSAVEL.get(category, "Investidor"),
        })
    order = {P0: 0, P1: 1, P2: 2, P3: 3}
    items.sort(key=lambda i: (not i["aberto"], order[i["prioridade"]], i["status"] != RESULTADO_RISCO, i["nome"] or ""))
    open_by = {p: sum(1 for i in items if i["aberto"] and i["prioridade"] == p) for p in order}
    blockers = [i for i in items if i["aberto"] and i["prioridade"] == P0]
    return {"itens": items, "abertos_por_prioridade": open_by, "bloqueadores_abertos": [i["nome"] for i in blockers],
            "prioridades": [{"codigo": p, "label": PRIORITY_LABELS[p], "texto": PRIORITY_TEXT[p]} for p in order]}


def for_property(prop: Any) -> dict[str, Any]:
    from .services import latest_execution
    execution = latest_execution(prop)
    return {"property_id": _v(prop, "id"), **prioritized(list(execution.results) if execution else [])}
