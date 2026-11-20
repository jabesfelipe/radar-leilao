"""Riscos consolidados em linguagem simples (evolução da inteligência, v1.0.14).

Leitura pura, sem IA e sem gravar nada. Os riscos persistidos (``models.Risk``) continuam como estão: um registro por versão da
análise, com código técnico, origem do motor e id da evidência. Esta camada:

- consolida por risco (a mesma pergunta do checklist em várias versões vira um risco só, no estado mais recente) e guarda o
  histórico das versões só para auditoria interna;
- traduz o código técnico para título, significado, impacto, estimativa, evidência e "o que fazer", sem expor códigos de motor,
  números de versão nem ids de evidência;
- acrescenta as pendências essenciais do checklist (PENDENTE DE CONFIRMAÇÃO) e os itens verificados sem risco (NÃO IDENTIFICADO).

Situações: CONFIRMADO, POSSÍVEL, PENDENTE DE CONFIRMAÇÃO, RESOLVIDO, NÃO IDENTIFICADO.
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Iterable

SIT_CONFIRMADO, SIT_POSSIVEL, SIT_PENDENTE, SIT_RESOLVIDO, SIT_NAO_IDENTIFICADO = (
    "CONFIRMADO", "POSSIVEL", "PENDENTE_CONFIRMACAO", "RESOLVIDO", "NAO_IDENTIFICADO")
SITUACAO_LABELS = {SIT_CONFIRMADO: "Confirmado", SIT_POSSIVEL: "Possível", SIT_PENDENTE: "Pendente de confirmação",
                   SIT_RESOLVIDO: "Resolvido", SIT_NAO_IDENTIFICADO: "Não identificado"}

CATEGORIAS = ("Jurídico", "Ocupação e desocupação", "Financeiro", "Débitos", "Documentação", "Mercado", "Reforma", "Liquidez", "Operacional")
IMPACTO_FINANCEIRO, IMPACTO_PRAZO, IMPACTO_OPERACIONAL, IMPACTO_JURIDICO = "financeiro", "prazo", "operacional", "jurídico"

# Catálogo por chave canônica do checklist: categoria, título, o que significa, impactos, linha de custo da estimativa e o que fazer.
# ``essencial``: a pendência deste item impede uma recomendação segura (aparece como PENDENTE DE CONFIRMAÇÃO).
_C = dict
CATALOGO: dict[str, dict[str, Any]] = {
    "INTIMACAO_PESSOAL": _C(categoria="Jurídico", titulo="Intimação do devedor para pagar a dívida",
                            significado="Se o devedor não foi intimado pessoalmente para pagar a dívida, ele pode pedir a anulação do leilão.",
                            impactos=[IMPACTO_JURIDICO, IMPACTO_PRAZO], acoes=["Conferir na matrícula a averbação da intimação.",
                                                                            "Pedir ao leiloeiro a certidão de intimação."]),
    "INTIMACAO_EDITAL": _C(categoria="Jurídico", titulo="Intimação por edital",
                           significado="Quando o devedor não é encontrado, a intimação por edital precisa seguir a lei; falha abre espaço para "
                                       "questionamento.", impactos=[IMPACTO_JURIDICO], acoes=["Conferir se a intimação por edital consta na matrícula."]),
    "NOTIFICACAO_DOIS_LEILOES": _C(categoria="Jurídico", titulo="Aviso ao devedor das datas dos leilões",
                                   significado="A lei exige avisar o devedor das datas dos leilões; sem o aviso, o leilão pode ser questionado.",
                                   impactos=[IMPACTO_JURIDICO, IMPACTO_PRAZO], acoes=["Pedir ao leiloeiro o comprovante do aviso das datas."]),
    "QUITACAO_80": _C(categoria="Jurídico", titulo="Financiamento quase quitado",
                      significado="Contrato com grande parte paga aumenta a chance de o antigo dono contestar a perda do imóvel.",
                      impactos=[IMPACTO_JURIDICO, IMPACTO_PRAZO], acoes=["Conferir o valor da dívida e o valor do financiamento na matrícula."]),
    "GARANTIA_DIVIDA_TERCEIRO": _C(categoria="Jurídico", titulo="Imóvel residencial dado em garantia de dívida de outra pessoa",
                                   significado="Situação que costuma gerar ação judicial do antigo dono.", impactos=[IMPACTO_JURIDICO],
                                   acoes=["Ler o contrato registrado na matrícula para ver quem é o devedor."]),
    "LANCE_MENOR_50_AVALIACAO": _C(categoria="Jurídico", titulo="Lance abaixo de 50% da avaliação",
                                   significado="Venda muito abaixo da avaliação pode ser contestada como preço vil.", impactos=[IMPACTO_JURIDICO],
                                   acoes=["Comparar o lance com a avaliação do edital."]),
    "ACAO_QUESTIONAMENTO": _C(categoria="Jurídico", titulo="Ação judicial contra o leilão", essencial=True,
                              significado="Um processo questionando o leilão ou a execução pode anular a compra ou atrasar a posse.",
                              impactos=[IMPACTO_JURIDICO, IMPACTO_PRAZO, IMPACTO_FINANCEIRO],
                              acoes=["Pesquisar processos em nome do antigo proprietário no tribunal do estado.", "Consultar a Central Jurídica do imóvel."]),
    "LEILOES_NEGATIVOS_AVERBADOS": _C(categoria="Documentação", titulo="Leilões anteriores registrados na matrícula",
                                      significado="A matrícula deve registrar os leilões sem vencedor; a falta é uma falha documental.",
                                      impactos=[IMPACTO_JURIDICO], acoes=["Conferir na matrícula as averbações dos leilões."]),
    "CONSOLIDACAO_REGISTRADA": _C(categoria="Documentação", titulo="Propriedade consolidada em nome do banco", essencial=True,
                                  significado="Sem a consolidação registrada, o banco ainda não é dono e não pode vender.",
                                  impactos=[IMPACTO_JURIDICO], acoes=["Conferir na matrícula a averbação de consolidação da propriedade."]),
    "PENHORA_INDISPONIBILIDADE": _C(categoria="Jurídico", titulo="Penhora ou bloqueio na matrícula", essencial=True,
                                    significado="Penhora ou indisponibilidade pode impedir o registro da compra em seu nome.",
                                    impactos=[IMPACTO_JURIDICO, IMPACTO_PRAZO], acoes=["Ler os atos da matrícula e pedir certidão atualizada.",
                                                                                     "Verificar se o edital garante o cancelamento."]),
    "TERCEIRO_OCUPANTE": _C(categoria="Ocupação e desocupação", titulo="Imóvel ocupado", essencial=True, custo="desocupacao",
                            significado="Há alguém morando ou usando o imóvel. Você precisará negociar a saída ou entrar com ação de imissão "
                                        "na posse, o que gera custo e atraso para usar, alugar ou vender.",
                            impactos=[IMPACTO_FINANCEIRO, IMPACTO_PRAZO, IMPACTO_OPERACIONAL, IMPACTO_JURIDICO],
                            acoes=["Confirmar quem ocupa o imóvel (ex-proprietário, inquilino ou outra pessoa).",
                                   "Verificar se existe contrato de locação e se ele está registrado na matrícula.",
                                   "Verificar se há processo judicial sobre a posse.",
                                   "Estimar o prazo de desocupação (acordo ou ação de imissão na posse).",
                                   "Incluir no Financeiro os custos de advogado, acordo e o tempo sem uso do imóvel."]),
    "LOCACAO_REGISTRADA": _C(categoria="Ocupação e desocupação", titulo="Inquilino com contrato registrado", custo="desocupacao",
                             significado="Locação registrada na matrícula pode obrigar o novo dono a respeitar o contrato.",
                             impactos=[IMPACTO_PRAZO, IMPACTO_FINANCEIRO, IMPACTO_JURIDICO],
                             acoes=["Conferir na matrícula se há registro de locação.", "Pedir cópia do contrato ao ocupante ou ao banco."]),
    "EDITAL_LIDO": _C(categoria="Documentação", titulo="Edital lido por completo", essencial=True,
                      significado="O edital define regras de pagamento, débitos e desocupação; sem a leitura completa, pode haver custo oculto.",
                      impactos=[IMPACTO_FINANCEIRO, IMPACTO_JURIDICO], acoes=["Anexar o edital e as condições de venda e revisar cada cláusula."]),
    "EVICCAO": _C(categoria="Jurídico", titulo="Garantia do vendedor em caso de perda do imóvel",
                  significado="Se a compra for anulada na Justiça, define se o banco devolve o valor pago.", impactos=[IMPACTO_JURIDICO, IMPACTO_FINANCEIRO],
                  acoes=["Ler a cláusula de evicção no edital."]),
    "RESPONSABILIDADE_DEBITOS": _C(categoria="Débitos", titulo="Quem paga IPTU e condomínio atrasados", essencial=True, custo="condominio_atraso",
                                   significado="O edital diz se as dívidas de IPTU e condomínio ficam com você ou com o vendedor.",
                                   impactos=[IMPACTO_FINANCEIRO], acoes=["Ler a cláusula de débitos no edital.",
                                                                         "Consultar o IPTU na prefeitura e o condomínio com a administradora."]),
    "VAGA_MATRICULA": _C(categoria="Documentação", titulo="Vaga de garagem com matrícula própria",
                         significado="Vaga com matrícula separada precisa de registro próprio; vaga vinculada acompanha o apartamento.",
                         impactos=[IMPACTO_OPERACIONAL], acoes=["Conferir na matrícula se a vaga é vinculada ou autônoma."]),
    "ILIQUIDEZ": _C(categoria="Liquidez", titulo="Imóvel difícil de vender", significado="Pouca procura pode alongar o prazo de venda e reduzir o preço.",
                    impactos=[IMPACTO_PRAZO, IMPACTO_FINANCEIRO], acoes=["Pesquisar há quanto tempo imóveis parecidos estão anunciados."]),
    "CONDOMINIO_ALTO": _C(categoria="Financeiro", titulo="Condomínio mais caro que o de imóveis parecidos", custo="manutencao_posse",
                          significado="Condomínio alto aumenta o custo enquanto o imóvel não é vendido e reduz o interesse de compradores.",
                          impactos=[IMPACTO_FINANCEIRO], acoes=["Comparar a taxa com a de anúncios do mesmo prédio ou região."]),
    "COMPARAVEIS_SUFFICIENTES": _C(categoria="Mercado", titulo="Imóveis parecidos para comparar preço", essencial=True,
                                   significado="Sem 7 a 10 imóveis parecidos, o valor de venda e o aluguel não têm base confiável.",
                                   impactos=[IMPACTO_FINANCEIRO], acoes=["Cadastrar anúncios de venda e aluguel parecidos em Mercado."]),
    "REGIAO_SERVICOS": _C(categoria="Mercado", titulo="Região, segurança e serviços",
                          significado="Região mal servida reduz a procura e o preço.", impactos=[IMPACTO_PRAZO],
                          acoes=["Avaliar a vizinhança no mapa e visitar o local."]),
    "REFORMA_GRANDE": _C(categoria="Reforma", titulo="Necessidade de reforma grande", custo="reforma",
                         significado="Reforma grande aumenta o investimento e o prazo até vender ou alugar.", impactos=[IMPACTO_FINANCEIRO, IMPACTO_PRAZO],
                         acoes=["Ver fotos e laudo do edital; se possível, visitar.", "Informar o orçamento da reforma em Financeiro."]),
    "RETORNO_SELIC": _C(categoria="Financeiro", titulo="Retorno abaixo de aplicações seguras",
                        significado="Se o retorno esperado for menor que a Selic + 15% ao ano, o risco não compensa.", impactos=[IMPACTO_FINANCEIRO],
                        acoes=["Revisar o lance máximo e as premissas em Financeiro."]),
    "PRAZO_DOIS_ANOS": _C(categoria="Financeiro", titulo="Prazo longo até receber a venda",
                          significado="Prazo de dois anos ou mais reduz o retorno e aumenta o custo de manter o imóvel.", impactos=[IMPACTO_PRAZO, IMPACTO_FINANCEIRO],
                          acoes=["Revisar o prazo de venda nas premissas."]),
    "DISTANCIA_USUARIO": _C(categoria="Operacional", titulo="Imóvel longe de você",
                            significado="A distância dificulta visitas, reforma e acompanhamento.", impactos=[IMPACTO_OPERACIONAL],
                            acoes=["Prever um corretor ou representante local."]),
    "REFORMA_LIQUIDEZ": _C(categoria="Reforma", titulo="Reforma necessária para vender", custo="reforma",
                           significado="Sem obras, o imóvel pode ser difícil de vender pelo preço esperado.", impactos=[IMPACTO_FINANCEIRO, IMPACTO_PRAZO],
                           acoes=["Orçar a reforma mínima para venda."]),
    "CONDOMINIO_PORTARIA": _C(categoria="Operacional", titulo="Portaria para visitas sem corretor",
                              significado="Sem portaria, mostrar o imóvel sem corretor é mais difícil.", impactos=[IMPACTO_OPERACIONAL],
                              acoes=["Confirmar com o condomínio como funcionam as visitas."]),
    "ETICA_OCUPACAO": _C(categoria="Ocupação e desocupação", titulo="Imóvel ocupado por família",
                         significado="Desocupar um imóvel habitado por uma família exige negociação cuidadosa.", impactos=[IMPACTO_OPERACIONAL, IMPACTO_PRAZO],
                         acoes=["Decidir antes do lance se aceita negociar a saída de uma família."]),
}
# Categoria do motor (domínio) → categoria do investidor, para riscos sem chave do checklist.
_DOMINIO = {"juridico": "Jurídico", "desocupacao": "Ocupação e desocupação", "financeiro": "Financeiro", "documental": "Documentação",
            "mercado": "Mercado", "operacional": "Operacional", "debitos": "Débitos", "reforma": "Reforma", "liquidez": "Liquidez"}
_GRAVIDADE = {"BAIXA": "Baixa", "MEDIA": "Média", "ALTA": "Alta", "CRITICA": "Crítica"}
_KEY = re.compile(r"CHECKLIST_([A-Z0-9_]+?)_(RISCO_IDENTIFICADO|ATENCAO)\b")
_TECH = re.compile(r"\[[A-Z0-9_]+\]\s*|Checklist:\s*[A-Z0-9_]+:?\s*|Estado determin[ií]stico:\s*[A-Z_]+\.?|RiskEngine:\S+")


def _v(item: Any, key: str, default: Any = None) -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def risk_key(risk: Any) -> tuple[str, str | None]:
    """(chave de consolidação, estado do motor). Riscos do motor: chave canônica do checklist; demais: categoria + texto limpo."""
    text = f"{_v(risk, 'origin') or ''} {_v(risk, 'description') or ''}"
    match = _KEY.search(text)
    if match:
        return match.group(1), match.group(2)
    return f"{str(_v(risk, 'category') or '').lower()}:{plain_text(_v(risk, 'description'))[:120]}", None


def plain_text(value: Any) -> str:
    """Remove códigos técnicos de um texto legado (``[CHECKLIST_...]``, ``Checklist: CHAVE``, ``Estado determinístico``)."""
    text = str(value or "")
    out, count = _TECH.subn("", text)
    if not count:
        return text.strip()
    return re.sub(r"\s{2,}", " ", out).strip(" :-")


def _brl(value: Any) -> str | None:
    if value in (None, ""):
        return None
    q = Decimal(str(value)).quantize(Decimal("0.01"))
    return "R$ " + f"{q:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _estimate(key: str | None, cost_lines: Iterable[dict] | None) -> dict[str, Any]:
    spec = CATALOGO.get(key or "", {})
    line_key = spec.get("custo")
    line = next((l for l in cost_lines or [] if l.get("chave") == line_key), None) if line_key else None
    if line is None:
        return {"texto": "Sem estimativa de valor para este risco.", "valor_base": None, "valor_conservador": None, "tipo": "DESCONHECIDO"}
    base, cons, value = line.get("valor_base"), line.get("valor_conservador"), line.get("valor")
    status = str(line.get("status") or "")
    if value is not None and status in ("INFORMADO", "ESTIMADO"):
        texto = f"Valor considerado no Financeiro: {_brl(value)} ({line.get('origem')})."
        tipo = "DADO_MANUAL" if status == "INFORMADO" else "ESTIMATIVA"
    elif base is not None or cons is not None:
        faixa = _brl(base) if (base == cons or cons is None) else f"{_brl(base)} (base) a {_brl(cons)} (conservador)"
        texto = f"Reserva considerada no Financeiro: {faixa}. Valor real ainda não levantado."
        tipo = "ESTIMATIVA"
    else:
        texto = "Custo ainda sem valor: fica fora da soma do Financeiro (não é zero)."
        tipo = "DESCONHECIDO"
    return {"texto": texto, "valor_base": base if base is not None else value, "valor_conservador": cons if cons is not None else value, "tipo": tipo}


def _evidence(evidence: Any) -> dict[str, Any] | None:
    if evidence is None:
        return None
    from .privacy import redact_pii
    version = _v(evidence, "document_version")
    document = _v(version, "document") if version is not None else None
    name = _v(document, "name") if document is not None else None
    page = _v(evidence, "page")
    excerpt = redact_pii(str(_v(evidence, "source_excerpt") or _v(evidence, "fact") or ""), force=True)[:400] or None
    where = ", ".join(x for x in (name or ("Cadastro do imóvel" if version is None else "Documento"), f"página {page}" if page else None) if x)
    return {"documento": name, "pagina": page, "trecho": excerpt, "texto": where}


def _occupancy_confirmed(occupancy: Any) -> bool:
    status = str(_v(occupancy, "status") or "").upper()
    return "OCUPADO" in status and "DESOCUPADO" not in status and "CONFIRM" in status


def consolidate(risks: Iterable[Any], *, latest_version: int | None = None, checklist_results: Iterable[Any] = (),
                evidences: dict[int, Any] | None = None, cost_lines: Iterable[dict] | None = None, occupancy: Any = None) -> dict[str, Any]:
    """Consolida os riscos persistidos (todas as versões) + o checklist mais recente num quadro para o investidor."""
    evidences = evidences or {}
    cost_lines = list(cost_lines or [])
    groups: dict[str, list[Any]] = {}
    for risk in risks:
        if str(_v(risk, "status") or "ATIVO").upper() in ("INATIVO", "SUPERADO"):
            continue
        groups.setdefault(risk_key(risk)[0], []).append(risk)
    results = {}
    for result in checklist_results:
        item = _v(result, "item")
        if item is not None and _v(item, "canonical_key"):
            results[_v(item, "canonical_key")] = result
    versions = [int(_v(r, "analysis_version")) for g in groups.values() for r in g if _v(r, "analysis_version") is not None]
    latest = latest_version if latest_version is not None else (max(versions) if versions else None)

    items: list[dict[str, Any]] = []
    for key, rows in groups.items():
        rows = sorted(rows, key=lambda r: (_v(r, "analysis_version") or 0, _v(r, "id") or 0))
        last = rows[-1]
        _, state = risk_key(last)
        spec = CATALOGO.get(key, {})
        version = _v(last, "analysis_version")
        current = version is None or latest is None or version >= latest
        if not current:
            situacao = SIT_RESOLVIDO
        elif key in ("TERCEIRO_OCUPANTE", "ETICA_OCUPACAO") and _occupancy_confirmed(occupancy):
            situacao = SIT_CONFIRMADO
        elif state == "RISCO_IDENTIFICADO" or (state is None and str(_v(last, "severity") or "").upper() in ("ALTA", "CRITICA")):
            situacao = SIT_CONFIRMADO
        else:
            situacao = SIT_POSSIVEL
        category = spec.get("categoria") or _DOMINIO.get(str(_v(last, "category") or "").lower(), "Jurídico")
        result = results.get(key)
        detail = plain_text(_v(result, "interpretation") or _v(result, "answer")) if result is not None else ""
        items.append({
            "chave": key, "categoria": category, "titulo": spec.get("titulo") or plain_text(_v(last, "description")) or "Risco identificado",
            "o_que_significa": spec.get("significado") or plain_text(_v(last, "impact")) or plain_text(_v(last, "description")),
            "detalhe": detail or None,
            "situacao": situacao, "situacao_label": SITUACAO_LABELS[situacao],
            "gravidade": _v(last, "severity"), "gravidade_label": _GRAVIDADE.get(str(_v(last, "severity") or "").upper()),
            "impactos": spec.get("impactos") or [IMPACTO_JURIDICO],
            "estimativa": _estimate(key, cost_lines),
            "evidencia": _evidence(evidences.get(_v(last, "evidence_id"))) if _v(last, "evidence_id") is not None else None,
            "o_que_fazer": spec.get("acoes") or ["Revisar o documento de origem e registrar a conclusão no checklist."],
            "rastreabilidade": {"tipo": "FATO" if situacao == SIT_CONFIRMADO else "INFERENCIA",
                                "historico": [{"versao": _v(r, "analysis_version"), "risco_id": _v(r, "id"), "gravidade": _v(r, "severity"),
                                               "estado_motor": risk_key(r)[1], "evidencia_id": _v(r, "evidence_id")} for r in rows]},
        })
    seen = set(groups)
    for key, result in results.items():
        if key in seen or key not in CATALOGO or _v(result, "applicable", True) is False:
            continue
        spec = CATALOGO[key]
        state = str(_v(result, "state") or "").upper()
        if state in ("PENDENTE", "EM_ANALISE") and spec.get("essencial"):
            situacao = SIT_PENDENTE
        elif state == "NAO_IDENTIFICADO":
            situacao = SIT_NAO_IDENTIFICADO
        else:
            continue
        items.append({
            "chave": key, "categoria": spec["categoria"], "titulo": spec["titulo"], "o_que_significa": spec["significado"],
            "detalhe": plain_text(_v(result, "interpretation")) or None, "situacao": situacao, "situacao_label": SITUACAO_LABELS[situacao],
            "gravidade": None, "gravidade_label": None, "impactos": spec["impactos"],
            "estimativa": _estimate(key, cost_lines) if situacao == SIT_PENDENTE else {"texto": None, "valor_base": None, "valor_conservador": None,
                                                                                         "tipo": "FATO"},
            "evidencia": None, "o_que_fazer": spec["acoes"] if situacao == SIT_PENDENTE else [],
            "rastreabilidade": {"tipo": "DESCONHECIDO" if situacao == SIT_PENDENTE else "FATO", "historico": []},
        })
    order = {SIT_CONFIRMADO: 0, SIT_POSSIVEL: 1, SIT_PENDENTE: 2, SIT_RESOLVIDO: 3, SIT_NAO_IDENTIFICADO: 4}
    sev = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2, "BAIXA": 3}
    items.sort(key=lambda i: (order[i["situacao"]], sev.get(str(i["gravidade"] or "").upper(), 4), CATEGORIAS.index(i["categoria"])
                              if i["categoria"] in CATEGORIAS else 99, i["titulo"]))
    counts = {s: sum(1 for i in items if i["situacao"] == s) for s in order}
    principal = next((i for i in items if i["situacao"] in (SIT_CONFIRMADO, SIT_POSSIVEL)), None)
    return {"itens": items, "contagem": counts, "principal": principal["titulo"] if principal else None,
            "categorias": [c for c in CATEGORIAS if any(i["categoria"] == c for i in items)],
            "aviso": "Cada risco aparece uma vez, no estado mais recente. O histórico das análises fica guardado para auditoria."}


def for_property(db, prop, *, cost_lines: Iterable[dict] | None = None) -> dict[str, Any]:
    """Quadro consolidado do imóvel: riscos persistidos de todas as versões + checklist da última execução."""
    from sqlalchemy import select
    from . import models
    from .services import latest_execution
    # Referência = versão do veredito mais recente: riscos e veredito são recalculados juntos (análise completa ou incremental).
    latest_version = db.scalar(select(models.Verdict.analysis_version).where(models.Verdict.property_id == prop.id)
                               .order_by(models.Verdict.analysis_version.desc()))
    execution = latest_execution(prop)
    risks = list(prop.risks)
    ids = {r.evidence_id for r in risks if r.evidence_id is not None}
    evidences = {e.id: e for e in db.scalars(select(models.Evidence).where(models.Evidence.id.in_(ids))).all()} if ids else {}
    occupancy = max(prop.occupancy_analyses, key=lambda o: o.id) if prop.occupancy_analyses else None
    return consolidate(risks, latest_version=latest_version, checklist_results=execution.results if execution else [],
                       evidences=evidences, cost_lines=cost_lines, occupancy=occupancy)
