"""Checklist Mestre por evidências (regra ``evidencias-v1``, v1.0.11).

Fonte única, no backend, da classificação dos itens a partir do que o Radar já tem:

- matrícula (cadeia registral, ``registry_chain``): itens 01 a 05, 07, 08, 10, 11 (cessão), 12 e 16;
- condições oficiais da venda ou edital (``sale_conditions``): itens 14 e 15;
- cadastro de ocupação, processos, localização, comparáveis e premissas: itens 07, 11, 17 a 27.

Regras (iguais para todos os itens):

1. Só toca item APLICÁVEL ainda em aberto (PENDENTE ou INCONCLUSIVO). Decisão do usuário ou de agente com citação válida
   prevalece; itens NAO_APLICAVEL pela modalidade nunca mudam.
2. Item jurídico/documental só é CONFIRMADO com trecho do documento (evidência DOCUMENTO). Cadastro, cálculo e premissas
   respondem itens de mercado, ocupação, financeiro e preferência, sempre com a origem declarada.
3. Ausência no texto nunca vira resposta negativa. "Sem restrição identificada" (estado NAO_IDENTIFICADO) só quando o
   documento certo foi examinado e lido em sequência; o limite da conclusão vai junto ("não é garantia de inexistência").
4. NAO_APLICAVEL por evidência só quando a condição de aplicabilidade comprovadamente não existe (ex.: venda direta cujo
   título não decorre de consolidação fiduciária, lida na matrícula).
5. Item que segue em aberto recebe justificativa própria: o que já se sabe, o que falta e onde buscar.

Toda resposta liga as evidências usadas (``ChecklistEvidence``) e registra a regra ``evidencias-v1:<chave>``.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import models, modality_rules

EVIDENCE_RULES_VERSION = "evidencias-v1"
OPEN_STATES = ("PENDENTE", "EM_ANALISE")
ORIGEM_NAO_LOCALIZADA = "NAO_LOCALIZADA"
# "Grande reforma" (item 21): referência de ANÁLISE, não regra jurídica. Premissa ``checklist.reforma_grande_pct``
# (premissa do imóvel > catálogo de parâmetros > padrão de 10% da aquisição; ver viability.DEFAULTS).
REFORMA_PREMISE_KEY = "checklist.reforma_grande_pct"


def _reforma_reference(r, intel: dict | None, assumptions: dict) -> tuple[Decimal, str]:
    """Limite de "grande reforma" e a sua origem, pela mesma resolução de premissas da inteligência de mercado."""
    premise = ((intel or {}).get("premissas") or {}).get(REFORMA_PREMISE_KEY)
    if premise is None:
        from .viability import resolve_premises
        premise = resolve_premises(r.db, assumptions).get(REFORMA_PREMISE_KEY)
    return Decimal(str(premise["valor"])), str(premise["origem"])


def _quitacao_upper_bound(chain, cons) -> str:
    """Item 04 (auditoria v6): limite SUPERIOR do que poderia estar quitado, pelo prazo e pela 1ª prestação lidos na matrícula.

    Conta as parcelas vencidas entre a 1ª prestação e a consolidação como se todas tivessem sido pagas (amortização linear);
    não é o percentual pago e não muda o estado do item. Sem prazo, 1ª prestação ou data da consolidação: texto vazio."""
    from datetime import date
    from .registry_chain import act_at, contract_terms, fold
    from .registry_timeline import _parse_date
    terms = contract_terms(chain)
    cons_act = act_at(chain, cons.position) if cons is not None else None
    when = _parse_date(fold(chain.original), chain.original, cons_act.start, cons_act.end) if cons_act is not None else None
    if not terms or not when or not terms["prazo_meses"]:
        return ""
    first, end = date.fromisoformat(terms["primeira_prestacao"]), date.fromisoformat(when["data"])
    if end < first:
        return ""
    due = (end.year - first.year) * 12 + (end.month - first.month) + (1 if end.day >= first.day else 0)
    due = max(0, min(due, terms["prazo_meses"]))
    share = Decimal(due) / Decimal(terms["prazo_meses"])
    return (f"Limite pela própria matrícula ({terms['ato']}: prazo de {terms['prazo_meses']} meses, 1ª prestação em {terms['primeira_prestacao_texto']}; "
            f"consolidação em {when['data_texto']}): venceram no máximo {due} de {terms['prazo_meses']} parcelas, então, mesmo com todas pagas, "
            f"o principal amortizado não passaria de cerca de {_pct(share.quantize(Decimal('0.001')))} (amortização linear; na Tabela Price, menos). "
            "É um teto calculado, não o valor pago; amortizações extraordinárias (ex.: FGTS) não aparecem na matrícula. ")
_BLOCKING_ONUS = ("penhora", "indisponibilidade", "arresto", "sequestro")
REGISTRY_KEYS = ("INTIMACAO_PESSOAL", "INTIMACAO_EDITAL", "NOTIFICACAO_DOIS_LEILOES", "QUITACAO_80", "GARANTIA_DIVIDA_TERCEIRO",
                 "ACAO_QUESTIONAMENTO", "LEILOES_NEGATIVOS_AVERBADOS", "CONSOLIDACAO_REGISTRADA", "PENHORA_INDISPONIBILIDADE",
                 "LOCACAO_REGISTRADA", "VAGA_MATRICULA")


def _brl(value: Any) -> str:
    number = Decimal(str(value))
    return "R$ " + f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: Decimal | None) -> str:
    if value is None:
        return "?"
    text = f"{(value * 100).normalize():f}".replace(".", ",")
    return f"{text}%"


class _Resolver:
    """Aplica as respostas numa execução do checklist, com as evidências e a regra de cada item."""

    def __init__(self, db, prop: models.Property, analysis: models.Analysis | None, execution: models.ChecklistExecution):
        self.db, self.prop, self.analysis, self.execution = db, prop, analysis, execution
        self.by_key = {r.item.canonical_key: r for r in execution.results if r.item is not None}
        self.modality = modality_rules.normalize_property_modality(getattr(prop, "modality", None))
        self.resolved: list[str] = []
        self.evidence_ids: list[int] = []

    # ---- estado -------------------------------------------------------------------------------------------------
    def open(self, key: str):
        result = self.by_key.get(key)
        if result is None or result.applicable is False or result.state not in OPEN_STATES:
            return None
        return result

    def _rule(self, key: str) -> str:
        return f"regra {EVIDENCE_RULES_VERSION}:{key}"

    def resolve(self, key: str, state: str, answer: str, basis: str, evidence_ids: list[int] | None = None, confidence: str = "MEDIA",
                not_applicable: bool = False) -> bool:
        result = self.open(key)
        if result is None:
            return False
        result.state = "NAO_APLICAVEL" if not_applicable else state
        if not_applicable:
            result.applicable = False
        result.answer = answer
        result.interpretation = f"{basis} ({self._rule(key)})"
        result.confidence = confidence
        if result.state not in OPEN_STATES:
            result.resolution_origin = "REGRA_DETERMINISTICA"
        for evidence_id in evidence_ids or []:
            self.link(result, evidence_id)
        self.resolved.append(key)
        return True

    def note(self, key: str, text: str, evidence_ids: list[int] | None = None) -> None:
        """Justificativa específica para item que continua PENDENTE (não muda o estado nem a origem)."""
        result = self.by_key.get(key)
        if result is None or result.applicable is False or result.state != "PENDENTE":
            return
        result.interpretation = f"Pendente: {text} ({self._rule(key)})"
        for evidence_id in evidence_ids or []:
            self.link(result, evidence_id)

    def link(self, result: models.ChecklistResult, evidence_id: int) -> None:
        if evidence_id is None or self.db.get(models.ChecklistEvidence, (result.id, evidence_id)) is not None:
            return
        self.db.add(models.ChecklistEvidence(checklist_result_id=result.id, evidence_id=evidence_id))
        self.db.flush()

    # ---- evidências ---------------------------------------------------------------------------------------------
    def _register(self, evidence: models.Evidence, relation: str) -> int:
        self.db.add(evidence); self.db.flush()
        if self.analysis is not None:
            self.db.add(models.EvidenceLink(evidence_id=evidence.id, target_type="Analysis", target_id=self.analysis.id, relation=relation))
        self.evidence_ids.append(evidence.id)
        return evidence.id

    def plain(self, origin: str, category: str, fact: str, agent: str, confidence: str = "MEDIA", document_version_id: int | None = None) -> int:
        """Evidência sem trecho de documento: cadastro, cálculo ou registro de "não localizado" no documento examinado."""
        evidence = models.Evidence(property_id=self.prop.id, document_version_id=document_version_id, chunk_id=None, category=category, fact=fact,
                                   confidence=confidence, page=None, section=None, source_excerpt=None, origin=origin, strength=None, agent=agent)
        return self._register(evidence, "MENCIONA" if origin == ORIGEM_NAO_LOCALIZADA else "SUSTENTA")

    def document(self, version_id: int, chunk_id: int | None, excerpt: str, fact: str, category: str, agent: str, chunk_text: str = "",
                 page: int | None = None, section: str | None = None) -> int | None:
        """Evidência com o trecho literal do documento (o texto da regra nunca substitui o trecho original)."""
        if chunk_id is None:
            return None
        from .citations import FORTE, MODERADA, excerpt_in_text
        from .evidence import normalize_documentary_evidence
        strength = FORTE if excerpt_in_text(excerpt, chunk_text) else MODERADA
        evidence = normalize_documentary_evidence(db=self.db, property_id=self.prop.id, document_version_id=version_id, chunk_id=chunk_id, category=category,
                                                  fact=fact, confidence="ALTA" if strength == FORTE else "MEDIA", page=page, section=section, source_excerpt=excerpt,
                                                  target_type="Analysis" if self.analysis is not None else None,
                                                  target_id=self.analysis.id if self.analysis is not None else None, origin="DOCUMENTO", strength=strength, agent=agent)
        self.evidence_ids.append(evidence.id)
        return evidence.id


# =================================================================================================================
# Matrícula (cadeia registral)
# =================================================================================================================

def resolve_registry_items(db, prop: models.Property, analysis, execution, chain, evidence_by_fact: dict[int, int],
                           created_evidence: list[int] | None = None) -> list[str]:
    """Itens que dependem da situação registral, a partir dos fatos da matrícula já registrados como evidência.

    ``evidence_by_fact`` liga cada fato lido (``id(fact)``) à evidência criada para ele em ``persist_registry_findings``;
    as evidências novas (registro de "não localizado") são acrescentadas a ``created_evidence``."""
    if execution is None or chain is None or chain.is_empty():
        return []
    from .registry_chain import (ACAO_JUDICIAL, CANCELAMENTO, CESSAO, GARANTIA, INTIMACAO, LEILAO, LOCACAO, NOTIFICACAO_LEILOES, ONUS,
                                 VAGA, VALOR_DIVIDA)
    r = _Resolver(db, prop, analysis, execution)
    version = db.get(models.DocumentVersion, chain.document_version_id) if chain.document_version_id else None
    doc_name = version.document.name if version is not None and version.document is not None else "matrícula"
    readable, reason = chain.readable_for_absence()
    acts = ", ".join(chain.act_labels()) or "nenhum ato reconhecido"
    examined = f"Matrícula examinada ('{doc_name}'; atos lidos: {acts})"
    vd = r.modality == modality_rules.MODALITY_VENDA_DIRETA
    af, cons = chain.fiduciary, chain.consolidation

    def ev(*facts) -> list[int]:
        return [evidence_by_fact[id(f)] for f in facts if f is not None and id(f) in evidence_by_fact]

    not_found_cache: dict[str, int] = {}

    def not_found(key: str, what: str) -> list[int]:
        if r.open(key) is None:
            return []   # item já decidido (usuário, agente ou regra): nada a registrar
        if key not in not_found_cache:
            not_found_cache[key] = r.plain(ORIGEM_NAO_LOCALIZADA, "JURIDICO", f"{examined}: {what}", "cadeia_registral",
                                           document_version_id=chain.document_version_id)
        return [not_found_cache[key]]

    def act(fact) -> str:
        return fact.act or "ato não identificado"

    # Venda direta cujo título NÃO decorre de consolidação fiduciária (matrícula lida, sem alienação nem consolidação):
    # os itens do procedimento de origem e dos leilões comprovadamente não se aplicam.
    title_not_fiduciary = vd and readable and af is None and cons is None
    if title_not_fiduciary:
        for key in ("INTIMACAO_PESSOAL", "INTIMACAO_EDITAL", "NOTIFICACAO_DOIS_LEILOES", "QUITACAO_80", "GARANTIA_DIVIDA_TERCEIRO", "LEILOES_NEGATIVOS_AVERBADOS"):
            r.resolve(key, "NAO_APLICAVEL", "Não aplicável: o título do vendedor não decorre de consolidação fiduciária.",
                      f"{examined}: não há registro de alienação fiduciária nem averbação de consolidação, condição que tornaria o item aplicável na venda direta.",
                      not_found(key, "sem alienação fiduciária e sem consolidação"), not_applicable=True)

    # ---- 01 e 02: intimação para purgar a mora ----------------------------------------------------------------------
    intim = {f.value: f for f in chain.of(INTIMACAO)}
    pessoal, edital, nao_purga = intim.get("PESSOAL"), intim.get("EDITAL"), intim.get("NAO_PURGACAO")
    cons_txt = f"A consolidação averbada ({act(cons)})" if cons is not None else "A matrícula"
    if pessoal is not None:
        r.resolve("INTIMACAO_PESSOAL", "CONFIRMADO", f"Sim. A matrícula menciona a intimação pessoal do devedor ({act(pessoal)}).",
                  "Fato lido na matrícula (trecho vinculado). A regularidade da intimação (prazo, pessoa intimada, endereço) está no procedimento do "
                  "cartório, não na matrícula.", ev(pessoal, cons))
        if edital is None:
            r.resolve("INTIMACAO_EDITAL", "NAO_APLICAVEL", "Não aplicável: a matrícula menciona intimação pessoal; o edital só cabe quando ela é negativa.",
                      f"Fato lido na matrícula ({act(pessoal)}).", ev(pessoal), not_applicable=True)
    if edital is not None:
        r.resolve("INTIMACAO_EDITAL", "CONFIRMADO", f"Sim. {cons_txt} cita a intimação por edital ({act(edital)}).",
                  "Fato lido na matrícula (trecho vinculado). A matrícula não comprova as publicações nem as tentativas de intimação pessoal que "
                  "justificam o edital (art. 26, § 4º, da Lei 9.514/97): solicitar ao cartório a cópia dos editais e a certidão das diligências.",
                  ev(edital, cons))
        if pessoal is None:
            r.resolve("INTIMACAO_PESSOAL", "EM_ANALISE", "",
                      f"INCONCLUSIVO: a intimação por edital citada na matrícula ({act(edital)}) indica que a intimação pessoal não se concretizou, "
                      "mas a matrícula não mostra as tentativas feitas. Solicitar ao Registro de Imóveis a certidão das diligências de intimação.",
                      ev(edital), confidence="BAIXA")
    if pessoal is None and edital is None:
        base = (f"{cons_txt} pressupõe a intimação do devedor sem purgação da mora (art. 26, § 7º, da Lei 9.514/97)"
                + (f" e a certidão de não pagamento ({act(nao_purga)})" if nao_purga is not None else "")
                + ", mas não informa como a intimação foi feita.") if cons is not None else "A matrícula examinada não registra consolidação nem intimação."
        r.note("INTIMACAO_PESSOAL", base + " Solicitar ao Registro de Imóveis a certidão das diligências de intimação.", ev(cons, nao_purga))
        r.note("INTIMACAO_EDITAL", base + " Se a intimação pessoal foi negativa, solicitar a cópia dos editais publicados.", ev(cons, nao_purga))

    # ---- 03: notificação das datas dos leilões ----------------------------------------------------------------------
    notif = chain.of(NOTIFICACAO_LEILOES)
    if notif:
        r.resolve("NOTIFICACAO_DOIS_LEILOES", "CONFIRMADO", f"Sim. A matrícula menciona a comunicação ao devedor das datas dos leilões ({act(notif[0])}).",
                  "Fato lido na matrícula (trecho vinculado). Conferir no comprovante se as duas datas foram comunicadas.", ev(notif[0]))
    else:
        r.note("NOTIFICACAO_DOIS_LEILOES", f"{examined}: não menciona a comunicação ao devedor das datas dos leilões, que normalmente não é averbada. "
               "Solicitar ao vendedor o comprovante (art. 27, § 2º-A, da Lei 9.514/97).")

    # ---- 04: percentual quitado -------------------------------------------------------------------------------------
    valor = chain.of(VALOR_DIVIDA)
    r.note("QUITACAO_80", (f"a matrícula registra a dívida garantida ({act(valor[0])}: {valor[0].value}), mas não os pagamentos feitos. "
                           if valor else "a matrícula não registra pagamentos do financiamento. ")
           + _quitacao_upper_bound(chain, cons)
           + "O percentual quitado só sai do extrato ou da planilha de evolução do contrato: solicitar ao vendedor.", ev(*valor[:1]))

    # ---- 05: garantia de dívida de terceiro -------------------------------------------------------------------------
    garantia = {f.value: f for f in chain.of(GARANTIA)}
    if garantia.get("TERCEIRO") is not None:
        g = garantia["TERCEIRO"]
        r.resolve("GARANTIA_DIVIDA_TERCEIRO", "ATENCAO", f"Sim, há indicação: o registro da alienação fiduciária ({act(g)}) menciona garantia de dívida de terceiro.",
                  "Fato lido na matrícula (trecho vinculado). Imóvel residencial de pessoa física dado em garantia de dívida de terceiro é mais sujeito a "
                  "questionamento pelo ex-devedor: conferir no contrato quem era o devedor e avaliar com advogado.", ev(g))
    elif garantia.get("PROPRIA") is not None:
        g = garantia["PROPRIA"]
        r.resolve("GARANTIA_DIVIDA_TERCEIRO", "NAO_IDENTIFICADO",
                  f"Não identificado. A alienação fiduciária ({act(g)}) foi constituída no contrato de compra e venda com mútuo: garante o financiamento "
                  "da própria aquisição, não dívida de terceiro.",
                  "Leitura do registro na matrícula (trecho vinculado). Confirmar no contrato se não havia devedor solidário ou interveniente garantidor.",
                  ev(g, af))
    else:
        r.note("GARANTIA_DIVIDA_TERCEIRO", (f"o registro da alienação fiduciária ({act(af)}) não indica de quem era a dívida garantida. " if af is not None
                                            else "a matrícula examinada não registra alienação fiduciária. ")
               + "Conferir no contrato registrado quem era o devedor.", ev(af))

    # ---- 07: ação averbada ------------------------------------------------------------------------------------------
    acoes = chain.of(ACAO_JUDICIAL)
    if acoes:
        r.resolve("ACAO_QUESTIONAMENTO", "RISCO_IDENTIFICADO", f"Sim. Consta na matrícula menção a ação judicial ({act(acoes[0])}).",
                  "Fato lido na matrícula (trecho vinculado). Identificar o processo e verificar se questiona a execução ou a venda; avaliar com advogado.",
                  ev(*acoes))
    else:
        r.note("ACAO_QUESTIONAMENTO", f"{examined}: nenhuma ação averbada ou citação identificada. Ações não averbadas não aparecem na matrícula: "
               "pesquisar certidões dos distribuidores (Justiça Estadual e Federal) em nome do ex-devedor e do vendedor.",
               not_found("ACAO_QUESTIONAMENTO", "nenhuma averbação de ação, citação ou protesto contra alienação identificada") if readable else None)

    # ---- 08: leilões negativos --------------------------------------------------------------------------------------
    leiloes = chain.of(LEILAO)
    negativos_av = [f for f in leiloes if f.value == "NEGATIVO" and (f.act or "").startswith("Av")]

    def seller_auction_info() -> tuple[str, list[int]]:
        """Informação do vendedor (condições da venda) sobre a averbação dos leilões negativos: complementa a matrícula, não a substitui."""
        if r.open("LEILOES_NEGATIVOS_AVERBADOS") is None:
            return "", []
        from .sale_conditions import TEMA_LEILOES, conditions_for_property
        for src in conditions_for_property(db, prop.id):
            clause = src.first(TEMA_LEILOES)
            if clause is None:
                continue
            literal = clause.detalhes[0] if clause.detalhes else clause.excerpt
            evidence_id = r.document(src.document_version_id, clause.chunk_id, clause.excerpt,
                                     f"Informação do vendedor ({src.source_label}): averbação dos leilões negativos \"{literal}\".", "CONDICOES_VENDA",
                                     "condicoes_venda", src.chunk_texts.get(clause.chunk_id, ""), clause.page, clause.section)
            text = (f" Informação do vendedor nas {src.source_label}: \"Averbação dos leilões negativos: {literal}\". É declaração do vendedor: "
                    "não comprova a averbação, que precisa ser confirmada na matrícula atualizada (Registro de Imóveis).")
            return text, [evidence_id] if evidence_id else []
        return "", []

    if negativos_av:
        r.resolve("LEILOES_NEGATIVOS_AVERBADOS", "CONFIRMADO", "Sim. Leilões negativos averbados (" + ", ".join(act(f) for f in negativos_av) + ").",
                  "Fato lido na matrícula (trecho vinculado).", ev(*negativos_av), confidence="ALTA")
    elif leiloes:
        f = leiloes[0]
        what = {"NEGATIVO": "menciona leilões negativos fora de uma averbação própria", "QUITACAO": "averba termo de quitação/extinção da dívida",
                "MENCAO": "menciona leilão sem indicar o resultado"}[f.value or "MENCAO"]
        seller_text, seller_ids = seller_auction_info()
        r.resolve("LEILOES_NEGATIVOS_AVERBADOS", "EM_ANALISE", "",
                  f"INCONCLUSIVO: a matrícula {what} ({act(f)}), sem comprovar a averbação dos dois leilões negativos. Conferir o trecho e a matrícula atualizada."
                  + seller_text, ev(*leiloes) + seller_ids, confidence="BAIXA")
    elif cons is not None:
        seller_text, seller_ids = seller_auction_info()
        r.resolve("LEILOES_NEGATIVOS_AVERBADOS", "EM_ANALISE", "",
                  f"INCONCLUSIVO: {examined} registra a consolidação ({act(cons)}) e nenhuma averbação de leilões negativos"
                  + ("" if readable else f" ({reason})") + ". Isso não prova que os leilões não ocorreram, nem que a averbação seja exigida: a "
                  "exigência para registrar a compra varia entre cartórios. Conferir na matrícula atualizada e confirmar com o Registro de Imóveis."
                  + seller_text,
                  ev(cons) + seller_ids + not_found("LEILOES_NEGATIVOS_AVERBADOS", "nenhuma averbação de leilões negativos ou termo de quitação"),
                  confidence="BAIXA")
    elif not title_not_fiduciary:
        r.note("LEILOES_NEGATIVOS_AVERBADOS", f"{examined}: sem consolidação nem leilões identificados" + ("" if readable else f" ({reason})")
               + ". Anexar a matrícula atualizada (inteiro teor).")

    # ---- 10: penhora, indisponibilidade, arresto, sequestro ---------------------------------------------------------
    blocking = [f for f in chain.of(ONUS) if str(f.value or "").lower() in _BLOCKING_ONUS]
    cancels = chain.of(CANCELAMENTO)

    def cancelled(f) -> bool:
        return any(c.position > f.position and (c.value is None or str(c.value).lower() == str(f.value).lower()) for c in cancels)

    active = [f for f in blocking if not cancelled(f)]
    if active:
        kinds = ", ".join(sorted({f"{f.value} ({act(f)})" for f in active}))
        r.resolve("PENHORA_INDISPONIBILIDADE", "RISCO_IDENTIFICADO", f"Sim. Consta na matrícula: {kinds}.",
                  "Lido da cadeia registral (trecho vinculado). Confirmar na certidão de ônus atualizada se segue vigente, o processo e o credor; "
                  "restrição vigente pode impedir ou condicionar o registro da compra.", ev(*active))
    elif blocking:
        kinds = ", ".join(sorted({f"{f.value} ({act(f)})" for f in blocking}))
        r.resolve("PENHORA_INDISPONIBILIDADE", "EM_ANALISE", "",
                  f"INCONCLUSIVO: constam {kinds} e cancelamento/baixa averbado depois; confirmar na certidão de ônus atualizada que nenhuma restrição segue vigente.",
                  ev(*blocking, *cancels), confidence="BAIXA")
    elif readable:
        r.resolve("PENHORA_INDISPONIBILIDADE", "NAO_IDENTIFICADO",
                  "Sem restrição identificada. Nenhum registro ou averbação de penhora, indisponibilidade, arresto ou sequestro na matrícula examinada.",
                  f"{examined}: {reason}. Resultado limitado à cópia lida, cuja data não foi verificada: não é garantia de inexistência. Antes da compra, "
                  "solicitar certidão de ônus reais atualizada e consultar a CNIB em nome do vendedor e do ex-devedor.",
                  not_found("PENHORA_INDISPONIBILIDADE", "nenhum registro de penhora, indisponibilidade, arresto ou sequestro"))
    else:
        r.resolve("PENHORA_INDISPONIBILIDADE", "EM_ANALISE", "",
                  f"INCONCLUSIVO: {examined}, mas {reason}; a ausência de penhora ou indisponibilidade no texto não pode ser afirmada. "
                  "Anexar matrícula legível e atualizada ou a certidão de ônus.",
                  not_found("PENHORA_INDISPONIBILIDADE", f"leitura incompleta ({reason})"), confidence="BAIXA")

    # ---- 11 (parte registral): cessão de direitos -------------------------------------------------------------------
    cessao = chain.of(CESSAO)
    if cessao:
        r.resolve("TERCEIRO_OCUPANTE", "ATENCAO", f"Sim, há indicação: cessão de direitos registrada na matrícula ({act(cessao[0])}).",
                  "Fato lido na matrícula (trecho vinculado). Identificar o cessionário e se ele ocupa o imóvel; a ocupação ainda deve ser verificada por vistoria.",
                  ev(*cessao))

    # ---- 12: locação registrada -------------------------------------------------------------------------------------
    locacao = chain.of(LOCACAO)
    if locacao:
        r.resolve("LOCACAO_REGISTRADA", "RISCO_IDENTIFICADO", f"Sim. Consta locação registrada ou averbada na matrícula ({act(locacao[0])}).",
                  "Fato lido na matrícula (trecho vinculado). Contrato com cláusula de vigência registrado obriga o comprador a respeitá-lo (Lei 8.245/91, "
                  "art. 8º): conferir prazo e valor.", ev(*locacao))
    elif readable:
        r.resolve("LOCACAO_REGISTRADA", "NAO_IDENTIFICADO", "Sem restrição identificada. Nenhum contrato de locação registrado ou averbado na matrícula examinada.",
                  f"{examined}: {reason}. Locação não registrada não aparece na matrícula: a ocupação continua a ser verificada no item 11.",
                  not_found("LOCACAO_REGISTRADA", "nenhum registro ou averbação de locação"))
    else:
        r.note("LOCACAO_REGISTRADA", f"{examined}, mas {reason}: não é possível afirmar a ausência de locação registrada.")

    # ---- 16: vaga de garagem ----------------------------------------------------------------------------------------
    vagas = chain.of(VAGA)
    spots = getattr(prop, "parking_spots", None)
    if vagas and vagas[0].value == "PROPRIA":
        r.resolve("VAGA_MATRICULA", "CONFIRMADO", "Sim. A matrícula descreve a vaga como unidade com matrícula própria.",
                  "Fato lido na matrícula (trecho vinculado). Conferir a matrícula da vaga (ônus próprios).", ev(vagas[0]))
    elif vagas and vagas[0].value == "VINCULADA":
        r.resolve("VAGA_MATRICULA", "CONFIRMADO", "Não. A matrícula descreve a vaga como vinculada à unidade ou de uso, sem matrícula própria.",
                  "Fato lido na matrícula (trecho vinculado). A vaga acompanha o apartamento e não pode ser vendida separadamente.", ev(vagas[0]))
    elif vagas:
        r.resolve("VAGA_MATRICULA", "EM_ANALISE", "", "INCONCLUSIVO: a matrícula menciona vaga de garagem sem dizer se tem matrícula própria. "
                  "Conferir na convenção do condomínio.", ev(vagas[0]), confidence="BAIXA")
    elif readable and spots == 0:
        r.resolve("VAGA_MATRICULA", "NAO_APLICAVEL", "Não aplicável: o cadastro informa 0 vaga e a matrícula examinada não descreve vaga.",
                  f"{examined} e cadastro do imóvel (vagas: 0).", not_found("VAGA_MATRICULA", "nenhuma vaga de garagem descrita"), not_applicable=True)
    elif readable and spots:
        r.resolve("VAGA_MATRICULA", "EM_ANALISE", "",
                  f"INCONCLUSIVO: o cadastro informa {spots} vaga(s), mas a matrícula examinada não descreve vaga: pode ser de uso comum ou ter matrícula "
                  "separada. Conferir na convenção do condomínio ou pedir a matrícula da vaga.", not_found("VAGA_MATRICULA", "nenhuma vaga de garagem descrita"),
                  confidence="BAIXA")
    else:
        r.note("VAGA_MATRICULA", f"{examined}: não descreve vaga" + ("" if readable else f" ({reason})")
               + "; o cadastro não informa o número de vagas. Conferir na convenção do condomínio.")

    if created_evidence is not None:
        created_evidence.extend(r.evidence_ids)
    if r.resolved:
        db.flush()
    return r.resolved


# =================================================================================================================
# Demais fontes: condições da venda, ocupação, processos, localização, mercado, premissas
# =================================================================================================================

def resolve_checklist_evidence(db, prop: models.Property, analysis, execution, registry=None) -> list[int]:
    """Itens respondidos pelas condições da venda e pelos demais módulos do Radar; justificativa própria para os que seguem
    pendentes. Chamado na análise depois da matrícula e dos dados cadastrados. Devolve as evidências criadas."""
    if execution is None:
        return []
    r = _Resolver(db, prop, analysis, execution)
    _sale_condition_items(r)
    _occupancy_items(r, registry)
    _process_items(r)
    _location_items(r)
    _market_and_finance_items(r)
    _registry_absent_notes(r, registry)
    if r.resolved or r.evidence_ids:
        db.flush()
    return r.evidence_ids


def _sale_condition_items(r: _Resolver) -> None:
    from .sale_conditions import (EVICCAO_EXCLUIDA, EVICCAO_LIMITADA, EVICCAO_RESPONDE, REGRA_AMBIGUA, REGRA_COMPRADOR, REGRA_EXCEDENTE,
                                  REGRA_INTEGRAL_ACIMA, REGRA_VENDEDOR, TEMA_CONDOMINIO, TEMA_EVICCAO, TEMA_FGTS, TEMA_PAGAMENTO, TEMA_TRIBUTOS,
                                  conditions_for_property)
    sources = conditions_for_property(r.db, r.prop.id)
    if not sources:
        missing = ("Sem edital nem condições oficiais da venda anexadas. Na venda direta não há edital: anexar a página oficial do imóvel ou o "
                   "documento de regras da venda com o tipo CONDICOES_VENDA.") if r.modality == modality_rules.MODALITY_VENDA_DIRETA else \
                  "Sem edital nem condições oficiais da venda anexadas: anexar o edital (tipo EDITAL) ou as condições da venda (tipo CONDICOES_VENDA)."
        r.note("EVICCAO", missing)
        r.note("RESPONSABILIDADE_DEBITOS", missing + " Os valores dos débitos dependem de declaração do condomínio e certidão de IPTU.")
        return
    src = sources[0]
    doc = f"Documento examinado: {src.source_label}."

    def clause_evidence(clause, fact: str) -> list[int]:
        evidence_id = r.document(src.document_version_id, clause.chunk_id, clause.excerpt, fact, "CONDICOES_VENDA", "condicoes_venda",
                                 src.chunk_texts.get(clause.chunk_id, ""), clause.page, clause.section)
        return [evidence_id] if evidence_id else []

    def not_found(what: str) -> list[int]:
        return [r.plain(ORIGEM_NAO_LOCALIZADA, "CONDICOES_VENDA", f"{doc} {what}", "condicoes_venda", document_version_id=src.document_version_id)]

    # Outras obrigações lidas (FGTS, pagamento): registradas como evidência da análise, sem item próprio no checklist.
    for tema, label in ((TEMA_FGTS, "Uso do FGTS"), (TEMA_PAGAMENTO, "Condições de pagamento")):
        clause = src.first(tema)
        if clause is not None:
            detail = {"ACEITA": "aceito", "NAO_ACEITA": "não aceito"}.get(clause.regra, "mencionado") if tema == TEMA_FGTS else (
                ", ".join(clause.detalhes) or "mencionadas")
            clause_evidence(clause, f"{label} ({src.source_label}): {detail}.")

    # ---- 14: evicção ------------------------------------------------------------------------------------------------
    ev_clause = src.first(TEMA_EVICCAO)
    if r.open("EVICCAO") is None:
        pass
    elif ev_clause is None:
        r.resolve("EVICCAO", "EM_ANALISE", "", f"INCONCLUSIVO: {doc} O documento não trata de evicção. Sem cláusula, vale a regra legal (Código Civil, "
                  "arts. 447 a 457), mas a venda pode ter regras próprias: conferir o documento completo ou perguntar ao vendedor.",
                  not_found("Nenhuma cláusula sobre evicção."), confidence="BAIXA")
    elif ev_clause.regra == EVICCAO_EXCLUIDA:
        r.resolve("EVICCAO", "RISCO_IDENTIFICADO", "Não. As condições da venda excluem ou afastam a responsabilidade do vendedor pela evicção.",
                  f"Regra oficial da venda (trecho vinculado). {doc} Exclusão expressa é permitida (Código Civil, art. 448): o comprador assume o risco de "
                  "perder o imóvel por decisão judicial sem garantia do vendedor. Avaliar com advogado.",
                  clause_evidence(ev_clause, "Cláusula de evicção: exclusão de responsabilidade do vendedor."))
    elif ev_clause.regra in (EVICCAO_RESPONDE, EVICCAO_LIMITADA):
        limited = ev_clause.regra == EVICCAO_LIMITADA
        r.resolve("EVICCAO", "CONFIRMADO", ("Sim, com limitação: " if limited else "Sim. ") + f"as condições da venda preveem a responsabilidade de "
                  f"{ev_clause.vendedor} pela evicção" + (" nos limites do trecho citado." if limited else "."),
                  f"Regra oficial da venda (trecho vinculado). {doc}" + (" Ler o limite (ex.: restituição do valor pago) no trecho." if limited else ""),
                  clause_evidence(ev_clause, "Cláusula de evicção: responsabilidade do vendedor" + (" com limite." if limited else ".")))
    else:
        r.resolve("EVICCAO", "EM_ANALISE", "", f"INCONCLUSIVO: {doc} O documento cita evicção, mas o texto não permite dizer se o vendedor responde por "
                  "ela. Ler o trecho vinculado e confirmar com o vendedor.", clause_evidence(ev_clause, "Cláusula sobre evicção (redação ambígua)."), confidence="BAIXA")

    # ---- 15: débitos de condomínio e IPTU ---------------------------------------------------------------------------
    if r.open("RESPONSABILIDADE_DEBITOS") is None:
        return
    from .services import current_auction
    auction = current_auction(r.prop)
    appraisal = Decimal(str(auction.appraisal_value)) if auction is not None and auction.appraisal_value not in (None, 0) else None

    def describe(clause, tema_label: str) -> str | None:
        if clause.regra == REGRA_EXCEDENTE:
            text = (f"comprador responde {'até' if clause.comparador != 'ABAIXO_DE' else 'abaixo de'} {_pct(clause.limite_pct)} do valor de avaliação; "
                    f"{clause.vendedor} paga só o que exceder esse limite")
        elif clause.regra == REGRA_INTEGRAL_ACIMA:
            text = (f"comprador responde se o débito ficar {'abaixo de' if clause.comparador == 'ABAIXO_DE' else 'até'} {_pct(clause.limite_pct)} do valor "
                    f"de avaliação; acima do limite, {clause.vendedor} assume o débito integralmente")
        elif clause.regra == REGRA_COMPRADOR:
            text = "por conta do comprador, sem limite indicado"
        elif clause.regra == REGRA_VENDEDOR:
            text = f"por conta de {clause.vendedor}"
        else:
            return None
        if clause.limite_pct is not None and appraisal is not None:
            text += f" (limite de {_brl(appraisal * clause.limite_pct)} sobre a avaliação de {_brl(appraisal)})"
        return f"{tema_label}: {text}"

    cond, trib = src.first(TEMA_CONDOMINIO), src.first(TEMA_TRIBUTOS)
    # Mesma fonte de valores da composição de custos (viability.debt_exposure): confirmado > informado > estimativa > pendente.
    from .viability import FONTE_ESTIMATIVA, FONTE_INDISPONIVEL, debt_exposure
    exposure = debt_exposure(r.db, r.prop, (auction.financial_assumptions or {}) if auction is not None else {})
    known, others = [], []
    for label, key in (("condomínio", "condominio_atraso"), ("IPTU/tributos", "tributos_atraso")):
        info = exposure[key]
        if info["valor"] not in (None, 0):
            known.append(f"{label} {_brl(info['valor'])} ({info['origem']})")
        elif info["fonte"] == FONTE_ESTIMATIVA:
            others.append(f"{label}: estimativa de {_brl(info['estimativa']['base'])} (provável) a {_brl(info['estimativa']['conservador'])} (alto), "
                          "não é dívida confirmada")
        elif info["fonte"] == FONTE_INDISPONIVEL:
            others.append(f"{label}: consulta indisponível ou em validação (não é zero)")
    debt_text = ("Débitos cadastrados: " + "; ".join(known) + "." if known else
                 "Valores dos débitos não informados: conhecer a regra não informa a dívida. Solicitar declaração de débitos do condomínio e certidão de débitos de IPTU.")
    if others:
        debt_text += " " + "; ".join(others) + "."
    debt_ids = [r.plain("CADASTRO", "FINANCEIRO", "Débitos cadastrados no imóvel: " + "; ".join(known) + ".", "cadastro")] if known else []
    parts, ids, ambiguous, missing = [], [], [], []
    for clause, label, tema in ((cond, "Condomínio", "condomínio"), (trib, "IPTU/tributos", "IPTU/tributos")):
        if clause is None:
            missing.append(tema)
            continue
        text = describe(clause, label)
        ids += clause_evidence(clause, f"Regra de {tema} ({src.source_label}): " + (text.split(': ', 1)[1] if text else "redação ambígua") + ".")
        (parts if text else ambiguous).append(text or tema)
    if parts and not ambiguous and not missing:
        r.resolve("RESPONSABILIDADE_DEBITOS", "CONFIRMADO", ". ".join(parts) + ". " + debt_text,
                  f"Regras oficiais da venda (trechos vinculados). {doc} A regra define quem paga; o valor efetivo dos débitos é outra informação e entra "
                  "no custo da operação.", ids + debt_ids)
    elif parts or ambiguous:
        problems = ([f"redação sem a regra do que acontece acima do limite ({', '.join(ambiguous)})"] if ambiguous else []) + \
                   ([f"sem regra para {', '.join(missing)}"] if missing else [])
        r.resolve("RESPONSABILIDADE_DEBITOS", "EM_ANALISE", "", "INCONCLUSIVO: " + (". ".join(parts) + ". " if parts else "") + f"{doc} Problema: "
                  + "; ".join(problems) + ". " + debt_text, ids + debt_ids + (not_found("Sem regra para " + ", ".join(missing) + ".") if missing else []),
                  confidence="BAIXA")
    else:
        r.resolve("RESPONSABILIDADE_DEBITOS", "EM_ANALISE", "", f"INCONCLUSIVO: {doc} O documento não trata de débitos de condomínio nem de IPTU. "
                  + debt_text, not_found("Nenhuma regra de responsabilidade por condomínio ou IPTU."), confidence="BAIXA")


def _latest(items):
    items = [i for i in items or [] if i is not None]
    return max(items, key=lambda i: i.id or 0) if items else None


def _occupancy_items(r: _Resolver, registry) -> None:
    if r.open("TERCEIRO_OCUPANTE") is None and r.open("ETICA_OCUPACAO") is None:
        return
    occ = _latest(r.prop.occupancy_analyses)
    status = str(occ.status or "").upper() if occ is not None else ""
    cessao_txt = ""
    if registry is not None and not registry.is_empty():
        from .registry_chain import CESSAO
        cessao_txt = "" if registry.of(CESSAO) else " Cessão de posição contratual: não consta na matrícula examinada."
    # Só o registro de ocupação feito pelo usuário responde 11 e 27; "possíveis ocupantes" dos documentos são sugestão e não entram.
    from .occupancy_service import OCCUPIED_STATUSES, STATUS_LABELS, VACANT_STATUSES
    if status in OCCUPIED_STATUSES or status in VACANT_STATUSES:
        label = STATUS_LABELS.get(status, status).lower()
        detail = "; ".join(t for t in ((f"perfil: {occ.occupant_profile}" if occ.occupant_profile else ""),
                                       (f"custo estimado de desocupação {_brl(occ.estimated_cost)}" if occ.estimated_cost not in (None, 0) else ""),
                                       (f"prazo estimado {occ.estimated_months} meses" if occ.estimated_months else "")) if t)
        fact = f"Cadastro de ocupação: {status.lower() if status in ('OCUPADO', 'DESOCUPADO') else label}" + (f" ({detail})" if detail else "") + "."
        ids = [r.plain("CADASTRO", "DESOCUPACAO", fact, "cadastro_ocupacao", "MEDIA" if occ.evidence_id else "BAIXA")]
        if occ.evidence_id:
            ids.append(occ.evidence_id)
        conf = "MEDIA" if occ.evidence_id else "BAIXA"
        if status in OCCUPIED_STATUSES:
            how = {"OCUPADO_TERCEIROS": "ocupado por terceiros", "OCUPADO_CONFIRMADO": "ocupado (ocupação confirmada)"}.get(status, "ocupado")
            r.resolve("TERCEIRO_OCUPANTE", "ATENCAO", f"Sim. Imóvel registrado como {how}" + (f" ({detail})." if detail else "."),
                      "Informação do cadastro de ocupação (fornecida pelo usuário" + (", com evidência vinculada" if occ.evidence_id else ", sem documento") + ")."
                      + cessao_txt + " Planejar a desocupação (custo e prazo) antes de decidir.", ids, confidence=conf)
            r.note("ETICA_OCUPACAO", "imóvel registrado como ocupado" + (f" ({occ.occupant_profile})" if occ.occupant_profile else "")
                   + ": decisão pessoal do investidor sobre comprar imóvel ocupado.", ids)
        else:
            r.resolve("TERCEIRO_OCUPANTE", "NAO_IDENTIFICADO", "Sem restrição identificada. Imóvel registrado como desocupado.",
                      "Informação do cadastro de ocupação (fornecida pelo usuário" + (", com evidência vinculada" if occ.evidence_id else ", sem documento") + ")."
                      + cessao_txt + " Confirmar por vistoria perto da compra: a ocupação pode mudar.", ids, confidence=conf)
            r.resolve("ETICA_OCUPACAO", "NAO_APLICAVEL", "Não aplicável: imóvel registrado como desocupado.",
                      "Informação do cadastro de ocupação. Reavaliar se a ocupação mudar.", ids, confidence=conf, not_applicable=True)
    else:
        r.note("TERCEIRO_OCUPANTE", "ocupação não verificada (cadastro de ocupação ausente ou desconhecido)." + cessao_txt
               + " Verificar por vistoria, com vizinhos e com a portaria ou o síndico, e registrar em Ocupação.")
        r.note("ETICA_OCUPACAO", "depende da ocupação (item 11), ainda não verificada. Decisão pessoal do investidor.")


def _process_items(r: _Resolver) -> None:
    processes = [p for p in r.prop.processes if str(p.correlation_level or "").upper() != "NAO_CONFIRMADA"]
    if not processes or r.open("ACAO_QUESTIONAMENTO") is None:
        return
    numbers = ", ".join(p.number for p in processes[:5])
    fact = f"{len(processes)} processo(s) vinculado(s) ao imóvel no cadastro: {numbers}."
    ids = [r.plain("CADASTRO", "JURIDICO", fact, "cadastro_processos")] + [p.evidence_id for p in processes if p.evidence_id]
    r.resolve("ACAO_QUESTIONAMENTO", "EM_ANALISE", "", f"INCONCLUSIVO: {fact} Verificar se algum questiona a execução, o leilão ou a venda "
              "(objeto, partes e fase); a existência do processo não basta para concluir.", ids, confidence="BAIXA")


def _location_items(r: _Resolver) -> None:
    if r.open("REGIAO_SERVICOS") is None:
        return
    location = r.db.query(models.PropertyLocation).filter(models.PropertyLocation.property_id == r.prop.id).first()
    ratings = dict((location.location_checklist or {}) if location is not None else {})
    services = ("acesso_viario", "transporte_publico", "comercio_servicos", "escolas_saude", "infraestrutura_entorno")
    rated = {k: str(ratings.get(k)).upper() for k in services if str(ratings.get(k) or "").upper() in ("BOM", "REGULAR", "RUIM")}
    vizinhanca = str(ratings.get("vizinhanca") or "").upper()
    if len(rated) < 3:
        r.note("REGIAO_SERVICOS", f"{len(rated)} de {len(services)} critérios de serviços e acesso avaliados no checklist de localização (mínimo 3). "
               "Registrar a avaliação em Localização (transporte, comércio, escolas e saúde, acesso, vizinhança).")
        return
    when = f" em {location.inspected_at:%d/%m/%Y}" if getattr(location, "inspected_at", None) else ""
    summary = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in rated.items()) + (f"; vizinhança: {vizinhanca}" if vizinhanca else "")
    ids = [r.plain("CADASTRO", "MERCADO", f"Checklist de localização registrado{when}: {summary}.", "cadastro_localizacao")]
    bad = [k.replace("_", " ") for k, v in rated.items() if v == "RUIM"] + (["vizinhança"] if vizinhanca == "RUIM" else [])
    if bad:
        r.resolve("REGIAO_SERVICOS", "ATENCAO", "Não totalmente: avaliado(s) como RUIM: " + ", ".join(bad) + ".",
                  "Avaliação do entorno registrada pelo usuário (checklist de localização).", ids)
    elif vizinhanca in ("BOM", "REGULAR"):
        r.resolve("REGIAO_SERVICOS", "CONFIRMADO", "Sim, pela avaliação registrada: serviços, acesso e vizinhança sem critério RUIM.",
                  "Avaliação do entorno registrada pelo usuário (checklist de localização); segurança avaliada pela vizinhança aparente.", ids)
    else:
        r.resolve("REGIAO_SERVICOS", "EM_ANALISE", "", "INCONCLUSIVO: serviços e acesso sem critério RUIM, mas a vizinhança (segurança aparente) não foi "
                  "avaliada. Completar o checklist de localização.", ids, confidence="BAIXA")


def _market_and_finance_items(r: _Resolver) -> None:
    from . import market as mk
    from .services import current_auction
    intel = None
    try:
        from .viability import market_intelligence
        intel = market_intelligence(r.db, r.prop)
    except Exception:   # complemento: falha no cálculo de mercado nunca impede a análise
        intel = None
    comps = [c for c in r.prop.comparables if not c.excluded]
    vendas = sum(1 for c in comps if str(c.kind or "").upper() == "VENDA")
    alugueis = sum(1 for c in comps if str(c.kind or "").upper() == "ALUGUEL")

    # ---- 17: liquidez -----------------------------------------------------------------------------------------------
    liq = (intel or {}).get("liquidez") or {}
    classe = liq.get("classificacao")
    reasons = " ".join(liq.get("justificativa") or [])
    conf = {"ALTA": "ALTA", "MEDIA": "MEDIA"}.get(str(liq.get("confianca") or "").upper(), "BAIXA")
    if r.open("ILIQUIDEZ") is None:
        pass
    elif classe in (mk.LIQ_ALTA, mk.LIQ_MEDIA, mk.LIQ_BAIXA):
        fact = f"Liquidez estimada {classe} (confiança {liq.get('confianca')}): {reasons} {liq.get('prazo_observacao') or ''}".strip()
        ids = [r.plain("CALCULO", "MERCADO", fact, "inteligencia_mercado", conf)]
        if classe == mk.LIQ_BAIXA:
            r.resolve("ILIQUIDEZ", "ATENCAO", f"Sim, há indício: liquidez estimada BAIXA. {reasons}", "Cálculo da inteligência de mercado sobre os "
                      "comparáveis cadastrados; sem tempo de venda observado.", ids, confidence=conf)
        else:
            r.resolve("ILIQUIDEZ", "NAO_IDENTIFICADO", f"Sem restrição identificada: liquidez estimada {classe}. {reasons}",
                      "Cálculo da inteligência de mercado sobre os comparáveis cadastrados. O prazo de venda não foi medido (sem datas de anúncio e "
                      "fechamento).", ids, confidence=conf)
    else:
        r.note("ILIQUIDEZ", "sem comparáveis de venda utilizáveis, a liquidez não foi estimada. Cadastrar comparáveis de venda semelhantes.")

    # ---- 18: condomínio x similares ---------------------------------------------------------------------------------
    fees = sorted(Decimal(str(c.condo_fee)) for c in comps if c.condo_fee not in (None, 0))
    if fees:
        median = fees[len(fees) // 2] if len(fees) % 2 else (fees[len(fees) // 2 - 1] + fees[len(fees) // 2]) / 2
        r.note("CONDOMINIO_ALTO", f"o condomínio do próprio imóvel não está cadastrado; mediana do condomínio de {len(fees)} comparável(is): {_brl(median)}. "
               "Informar o valor do condomínio (boleto ou síndico) para comparar.")
    else:
        r.note("CONDOMINIO_ALTO", "nem o condomínio do imóvel nem o dos comparáveis estão cadastrados. Informar o valor do condomínio do imóvel e dos similares.")

    # ---- 19: comparáveis suficientes (a resposta positiva é a regra de dados cadastrados) ----------------------------
    r.note("COMPARAVEIS_SUFFICIENTES", f"{vendas} comparável(is) de venda e {alugueis} de aluguel cadastrados (excluídos não contam); o item pede 7 a 10 de "
           "cada. Poucos cadastrados não provam que não existam: cadastrar mais.")

    # ---- 21 e 25: reforma -------------------------------------------------------------------------------------------
    auction = current_auction(r.prop)
    assumptions = (auction.financial_assumptions or {}) if auction is not None else {}
    reforma = assumptions.get("reforma")
    acquisition = None
    if auction is not None:
        acquisition = auction.acquisition_value if auction.acquisition_value not in (None, 0) else (auction.bid_value if auction.bid_value not in (None, 0) else None)
    if r.open("REFORMA_GRANDE") is None:
        pass
    elif reforma not in (None, ""):
        value = Decimal(str(reforma))
        limite, limite_origem = _reforma_reference(r, intel, assumptions)
        fact = f"Premissa de reforma informada pelo usuário: {_brl(value)}" + (f" sobre aquisição de {_brl(acquisition)}" if acquisition else "") + "."
        ids = [r.plain("CADASTRO", "FINANCEIRO", fact, "premissas")]
        reference = (f"Referência de análise usada: grande reforma a partir de {_pct(limite)} do preço de aquisição ({limite_origem}). É premissa de "
                     "análise, não regra jurídica: ajuste em Financeiro > Premissas se o seu critério for outro. Valor de reforma do usuário, sem vistoria.")
        if value == 0:
            r.resolve("REFORMA_GRANDE", "NAO_IDENTIFICADO", "Sem restrição identificada: o usuário informou reforma de R$ 0,00.",
                      "Premissa do usuário, sem vistoria registrada.", ids, confidence="BAIXA")
        elif acquisition:
            ratio = value / Decimal(str(acquisition))
            text = f"reforma estimada de {_brl(value)} = {_pct(ratio.quantize(Decimal('0.001')))} do preço de aquisição (referência de análise: {_pct(limite)})"
            if ratio >= limite:
                r.resolve("REFORMA_GRANDE", "ATENCAO", f"Sim, pela referência adotada: {text}.", reference, ids, confidence="BAIXA")
            else:
                r.resolve("REFORMA_GRANDE", "NAO_IDENTIFICADO", f"Sem restrição identificada pela referência adotada: {text}.", reference, ids,
                          confidence="BAIXA")
        else:
            r.note("REFORMA_GRANDE", f"reforma estimada de {_brl(value)} informada, mas sem preço de aquisição para medir o porte. Cadastrar o valor da compra.", ids)
    else:
        # Auditoria v6: o financeiro usa a premissa padrão de reforma; o item diz qual é, sem tratá-la como resposta (não é vistoria).
        from .viability import resolve_premises
        premises = resolve_premises(r.db, assumptions)
        area = r.prop.private_area_m2 or r.prop.area_m2
        per_m2 = (premises.get("viabilidade.reserva_reforma_m2_base") or {}).get("valor")
        default = (f" O cálculo financeiro usa a premissa padrão do Radar: reforma estimada de {_brl(Decimal(str(per_m2)) * Decimal(str(area)))} "
                   f"({_brl(per_m2)}/m² × {str(area).replace('.', ',')} m²; confiança baixa, ajustável nas premissas). A premissa não diz se o imóvel "
                   "precisa de grandes obras." if per_m2 is not None and area not in (None, 0) else "")
        r.note("REFORMA_GRANDE", "sem vistoria nem estimativa de reforma nas premissas." + default + " Vistoriar o imóvel ou informar a estimativa com fonte.")
    r.note("REFORMA_LIQUIDEZ", "sem vistoria registrada" + (f"; liquidez estimada {classe}" if classe else "")
           + ". Vistoriar o imóvel e avaliar se obras aumentariam a procura na revenda.")

    # ---- 22: retorno x Selic + 15% a.a. -----------------------------------------------------------------------------
    base = next((s for s in (intel or {}).get("cenarios", []) if s.get("cenario") == "BASE"), None)
    roi, months = (base or {}).get("roi"), (base or {}).get("prazo_meses")
    if roi is not None and months:
        annual = (Decimal(1) + Decimal(str(roi))) ** (Decimal(12) / Decimal(months)) - 1 if Decimal(str(roi)) > -1 else None
        r.note("RETORNO_SELIC", f"ROI do cenário base de {_pct(Decimal(str(roi)).quantize(Decimal('0.001')))} em {months} meses"
               + (f" (cerca de {_pct(annual.quantize(Decimal('0.001')))} ao ano)" if annual is not None else "")
               + ". A taxa Selic de referência não está cadastrada no Radar: comparar com a Selic vigente + 15% a.a.")
    else:
        r.note("RETORNO_SELIC", "retorno não calculado (faltam valor de venda ou comparáveis). Configurar as premissas financeiras; a Selic de referência "
               "não está cadastrada no Radar.")

    # ---- 23, 24, 26: premissa e preferência -------------------------------------------------------------------------
    prazo = ((intel or {}).get("premissas") or {}).get("venda.prazo_meses") or {}
    r.note("PRAZO_DOIS_ANOS", "prazo da operação não informado nas premissas" + (f" (referência usada no cálculo: {prazo.get('valor')} meses, {prazo.get('origem')})"
                                                                                  if prazo.get("valor") else "") + ". Informar o prazo em Financeiro > Premissas.")
    r.note("DISTANCIA_USUARIO", f"decisão do investidor. O Radar não registra o endereço do investidor; imóvel em {r.prop.city}/{r.prop.state}.")
    r.note("CONDOMINIO_PORTARIA", "o Radar não tem informação sobre portaria do condomínio. Verificar na visita ou com a administradora.")


def _registry_absent_notes(r: _Resolver, registry) -> None:
    if registry is not None and not registry.is_empty():
        return
    has_doc = any(str(d.document_type or "").upper() == "MATRICULA" for d in r.prop.documents)
    text = ("matrícula anexada, mas o texto lido não permitiu reconhecer os atos registrais (OCR ilegível ou documento incompleto). Anexar cópia legível "
            "e atualizada (inteiro teor).") if has_doc else "matrícula não anexada. Anexar a matrícula atualizada (inteiro teor) do imóvel."
    for key in REGISTRY_KEYS:
        purpose = modality_rules.ITEM_PURPOSE.get(key, {})
        r.note(key, f"{text} Fonte necessária: {purpose.get('fonte', 'matrícula')}.")
