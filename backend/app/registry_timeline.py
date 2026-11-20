"""Linha do tempo da matrícula (v1.0.12, Fase C).

Leitura determinística, sem IA, sobre os trechos JÁ armazenados da última matrícula do imóvel (``registry_chain``): não
reprocessa o documento nem grava nada. Cada evento corresponde a um ato reconhecido no início de linha (R-n / Av-n) e traz
data, tipo, partes com o papel declarado no texto, valor, construtora, conclusão de obra e o trecho de origem.

Regras:

- Papel só quando o texto o declara (rótulo "VENDEDORA:", verbo "vendeu a", "em favor de", "em nome da credora"). Nada é
  inferido de posição ou de ausência.
- Nomes de pessoas físicas aparecem só para usuário autenticado (a API exige autenticação) e sem CPF/RG (``redact_pii``).
- Idade do imóvel só a partir de averbação de conclusão de obra / habite-se, como estimativa. Nunca a partir da primeira compra.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .registry_chain import PESSOA_FISICA, RegistryChain, _locate, canonical_party, fold

IDADE_NAO_DETERMINAVEL = "Idade não determinável pela matrícula."
AVISO_NOMES = ("Nomes lidos na matrícula, exibidos só para usuários autenticados, sem CPF ou outros documentos. Não use em exportações "
               "públicas.")

MESES = {"JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9,
         "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12}
_DATE_NUM = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b")
_DATE_EXT = re.compile(r"\b(\d{1,2})(?:º|O)?\s+DE\s+(" + "|".join(MESES) + r")\s+DE\s+(\d{4})\b")

TIPOS: tuple[tuple[str, str, re.Pattern[str]], ...] = tuple((k, d, re.compile(p)) for k, d, p in (
    ("CONSOLIDACAO", "Consolidação da propriedade", r"CONSOLIDA"),
    ("CONCLUSAO_OBRA", "Conclusão de obra / habite-se",
     r"CONCLUSAO\s+D[AE]\s+(OBRA|CONSTRUCAO)|HABITE[\s-]*SE|CARTA\s+DE\s+HABITACAO|AVERBACAO\s+D[AE]\s+CONSTRUCAO|CONSTRUCAO\s+CONCLUIDA"),
    ("CANCELAMENTO", "Cancelamento", r"CANCELAMENTO|\bCANCELAD"),
    ("ALIENACAO_FIDUCIARIA", "Alienação fiduciária", r"ALIENACAO\s+FIDUCIARIA|ALIENOU\s+FIDUCIARIAMENTE"),
    ("COMPRA_VENDA", "Compra e venda", r"COMPRA\s+E\s+VENDA|\bVENDEU\b"),
    ("DOACAO", "Doação", r"\bDOACAO\b|\bDOOU\b"),
    ("ARREMATACAO", "Arrematação / adjudicação", r"ARREMATACAO|ADJUDICACAO"),
    ("LEILAO", "Leilões", r"\bLEIL(AO|OES)\b"),
    ("PENHORA", "Penhora", r"\bPENHORA\b"),
    ("INDISPONIBILIDADE", "Indisponibilidade", r"INDISPONIBILIDADE"),
    ("HIPOTECA", "Hipoteca", r"\bHIPOTECA\b"),
    ("AFETACAO", "Patrimônio de afetação", r"AFETACAO"),
    ("INCORPORACAO", "Incorporação imobiliária", r"INCORPORACAO"),
    ("INSTITUICAO_CONDOMINIO", "Instituição de condomínio", r"INSTITUICAO\s+D[EO]\s+CONDOMINIO|ESPECIFICACAO\s+D[EO]\s+CONDOMINIO"),
    ("CESSAO", "Cessão de direitos", r"CESSAO\s+(E\s+TRANSFERENCIA\s+)?(DE\s+)?(DIREITOS|POSICAO)"),
    ("LOCACAO", "Locação", r"\bLOCACAO\b"),
))
TRANSMISSOES = {"COMPRA_VENDA", "DOACAO", "ARREMATACAO", "CONSOLIDACAO"}

PAPEIS = {"PROPRIETARIO_ANTERIOR": "Proprietário anterior", "COMPRADOR": "Comprador", "VENDEDOR": "Vendedor", "DEVEDOR": "Devedor",
          "CREDOR": "Credor", "OUTROS": "Outros"}
_LABELED = re.compile(
    r"\b(VENDEDOR[AE]?S?|TRANSMITENTES?|OUTORGANTES?(?:\s+VENDEDOR[AE]?S?)?|COMPRADOR[AE]?S?|ADQUIRENTES?|OUTORGAD[OA]S?(?:\s+COMPRADOR[AE]?S?)?"
    r"|DEVEDOR[AE]?S?(?:\s+FIDUCIANTES?)?|FIDUCIANTES?|CREDOR[AE]?S?(?:\s+FIDUCIARI[OA]S?)?|FIDUCIARI[OA]S?|INTERVENIENTES?(?:\s+\w+)?"
    r"|FIADOR[AE]?S?|CONSTRUTORA|INCORPORADORA)\s*:\s*([^;\n]{3,160})")
_SELL = re.compile(r"\bVENDEU\b")
_BUY_AFTER = re.compile(r"\bVENDEU\b[^\n]{0,40}?\b(?:AO|AOS|AS|A)\s+([^,;\n]{3,160})")
_FAVOR = re.compile(r"EM\s+FAVOR\s+D[AO]S?\s+([^,;\n]{3,160})")
_IN_NAME = re.compile(r"EM\s+NOME\s+D[AO]S?\s+(CREDORA?\s+|FIDUCIARIA\s+)?([^,;\n]{3,160})")
_DEBTOR_BEFORE_AF = re.compile(r"ALIENOU\s+FIDUCIARIAMENTE")
_OWNER = re.compile(r"PROPRIETARI[AO]S?\s*:\s*([^,;\n]{3,160})")
_MONEY = re.compile(r"R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})")
_BUILDER = re.compile(r"\b(CONSTRUTORA|INCORPORADORA|ENGENHARIA|EMPREENDIMENTOS)\b")
_QUALIFIED = re.compile(r",?\s*J[AÁ]\s+QUALIFICAD[OA]S?\s*,?\s*$", re.IGNORECASE)


def _role(label: str) -> str:
    folded = fold(label)
    if folded.startswith(("VENDEDOR", "TRANSMITENTE")) or folded.startswith("OUTORGANTE"):
        return "VENDEDOR"
    if folded.startswith(("COMPRADOR", "ADQUIRENTE", "OUTORGAD")):
        return "COMPRADOR"
    if folded.startswith(("DEVEDOR", "FIDUCIANTE")):
        return "DEVEDOR"
    if folded.startswith(("CREDOR", "FIDUCIARI")):
        return "CREDOR"
    return "OUTROS"


def _parse_date(folded: str, original: str, start: int, end: int) -> dict[str, Any] | None:
    """Primeira data válida do ato (normalmente a do protocolo/título), com o texto literal."""
    found = []
    for pattern, ext in ((_DATE_NUM, False), (_DATE_EXT, True)):
        for match in pattern.finditer(folded, start, end):
            day, month, year = int(match.group(1)), (MESES[match.group(2)] if ext else int(match.group(2))), int(match.group(3))
            try:
                value = date(year, month, day)
            except ValueError:
                continue
            if 1800 <= year <= date.today().year + 1:
                found.append((match.start(), value, original[match.start():match.end()]))
    if not found:
        return None
    position, value, literal = min(found)
    return {"data": value.isoformat(), "data_texto": re.sub(r"\s+", " ", literal).strip()}


def _person(original: str, start: int, end: int, role: str, how: str) -> dict[str, Any] | None:
    from .privacy import redact_pii
    raw = re.sub(r"\s+", " ", original[start:end]).strip(" ,-;:—")
    raw = _QUALIFIED.sub("", raw).strip(" ,-;:—")
    # Só o nome: qualificação (nacionalidade, estado civil, profissão, documentos) vem depois da primeira vírgula.
    raw = raw.split(",", 1)[0].strip(" -;:—")
    if len(raw) < 3:
        return None
    name = redact_pii(raw[:160], force=True)
    pessoa = "FISICA" if canonical_party(name) == PESSOA_FISICA else "JURIDICA"
    return {"papel": role, "papel_descricao": PAPEIS[role], "nome": name, "tipo_pessoa": pessoa, "como_identificado": how}


def _seller_before(folded: str, original: str, act_start: int, sell_pos: int) -> dict[str, Any] | None:
    """Vendedor declarado antes de "vendeu": o trecho entre a última vírgula/ponto anterior e o verbo (sem "já qualificada")."""
    window_start = max(act_start, sell_pos - 220)
    chunk = folded[window_start:sell_pos]
    chunk_clean = _QUALIFIED.sub("", chunk.rstrip())
    cut = max(chunk_clean.rfind(","), chunk_clean.rfind("."), chunk_clean.rfind(" - "))
    start = window_start + (cut + 1 if cut >= 0 else 0)
    end = window_start + len(chunk_clean)
    if end - start < 3:
        return None
    return _person(original, start, end, "VENDEDOR", "texto: \"... vendeu a ...\"")


def _parties(folded: str, original: str, start: int, end: int, kind: str) -> list[dict[str, Any]]:
    parties: list[dict[str, Any]] = []
    for match in _LABELED.finditer(folded, start, end):
        role = _role(match.group(1))
        person = _person(original, match.start(2), match.end(2), role, f"rótulo \"{original[match.start(1):match.end(1)].strip()}\"")
        if person:
            parties.append(person)
    sell = _SELL.search(folded, start, end)
    if sell and not any(p["papel"] == "VENDEDOR" for p in parties):
        seller = _seller_before(folded, original, start, sell.start())
        if seller:
            parties.append(seller)
    buy = _BUY_AFTER.search(folded, start, end)
    if buy and not any(p["papel"] == "COMPRADOR" for p in parties):
        person = _person(original, buy.start(1), buy.end(1), "COMPRADOR", "texto: \"vendeu a ...\"")
        if person:
            parties.append(person)
    if kind == "ALIENACAO_FIDUCIARIA":
        favor = _FAVOR.search(folded, start, end)
        if favor and not any(p["papel"] == "CREDOR" for p in parties):
            person = _person(original, favor.start(1), favor.end(1), "CREDOR", "texto: \"em favor de ...\"")
            if person:
                parties.append(person)
        af = _DEBTOR_BEFORE_AF.search(folded, start, end)
        if af and not any(p["papel"] == "DEVEDOR" for p in parties):
            seller_like = _seller_before(folded, original, start, af.start())
            if seller_like:
                parties.append({**seller_like, "papel": "DEVEDOR", "papel_descricao": PAPEIS["DEVEDOR"], "como_identificado": "texto: \"... alienou fiduciariamente\""})
    if kind == "CONSOLIDACAO":
        named = _IN_NAME.search(folded, start, end)
        if named:
            role = "CREDOR" if named.group(1) else "OUTROS"
            person = _person(original, named.start(2), named.end(2), role, "texto: \"em nome da credora ...\"" if role == "CREDOR" else "texto: \"em nome de ...\"")
            if person:
                parties.append(person)
    unique, seen = [], set()
    for p in parties:
        key = (p["papel"], fold(p["nome"]))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _money(folded: str, original: str, start: int, end: int) -> dict[str, Any] | None:
    match = _MONEY.search(folded, start, end)
    if not match:
        return None
    context = folded[max(start, match.start() - 60):match.start()]
    label = "preço" if "PRECO" in context else ("dívida" if "DIVIDA" in context else ("valor" if "VALOR" in context else "valor citado"))
    try:
        value = Decimal(match.group(1).replace(".", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return {"valor": value, "texto": original[match.start():match.end()], "rotulo": label}


def _title(folded: str, start: int, end: int) -> str:
    """Título do ato: o que vem depois do último " - " do cabeçalho, até o primeiro ponto final depois de letra
    ("R-2 - Matrícula nº 1 - Protocolo ... - COMPRA E VENDA." → "COMPRA E VENDA")."""
    window = folded[start:min(end, start + 300)]
    stop = re.search(r"[A-Z]\.(\s|$)", window)
    head = window[:stop.start() + 1] if stop else window
    cut = head.rfind(" - ")
    return head[cut + 3:] if cut >= 0 else head


def _kind(folded: str, start: int, end: int) -> tuple[str, str]:
    head = folded[start:min(end, start + 260)]
    for scope in (_title(folded, start, end), head, folded[start:end]):
        for key, label, pattern in TIPOS:
            if pattern.search(scope):
                return key, label
    return "OUTRO", "Outro ato"


def _source(chain: RegistryChain, position: int) -> dict[str, Any]:
    segment = _locate(chain.segments, position) if chain.segments else None
    return {"chunk_id": segment.chunk_id if segment else None, "pagina": segment.page if segment else None, "secao": segment.section if segment else None}


def _excerpt(original: str, start: int, end: int, size: int = 500) -> str:
    """Trecho literal do ato com CPF, RG, e-mail, telefone e dados bancários mascarados (o resto do texto fica intacto)."""
    from .privacy import redact_pii
    return redact_pii(re.sub(r"\s+", " ", original[start:min(end, start + size)]).strip(), force=True)


def build_timeline(chain: RegistryChain, document: dict[str, Any] | None = None, today: date | None = None) -> dict[str, Any]:
    """Linha do tempo a partir de uma cadeia já lida (função pura)."""
    today = today or date.today()
    original = chain.original or ""
    folded = fold(original)
    events: list[dict[str, Any]] = []
    first_act = chain.acts[0].start if chain.acts else len(folded)
    later_transfer = any(_kind(folded, a.start, a.end)[0] in TRANSMISSOES for a in chain.acts)
    owner = _OWNER.search(folded, 0, first_act)
    if owner:
        role = "PROPRIETARIO_ANTERIOR" if later_transfer else "OUTROS"
        person = _person(original, owner.start(1), owner.end(1), role, "rótulo \"PROPRIETÁRIA:\" na abertura da matrícula")
        builder = person["nome"] if person and _BUILDER.search(fold(person["nome"])) else None
        events.append({"ato": "Abertura", "numero": 0, "tipo": "ABERTURA", "tipo_descricao": "Abertura da matrícula", "data": None, "data_texto": None,
                       "partes": [person] if person else [], "valor": None, "construtora": builder, "conclusao_obra": False,
                       "trecho": _excerpt(original, owner.start(), owner.end() + 120), **_source(chain, owner.start())})
    for act in chain.acts:
        kind, label = _kind(folded, act.start, act.end)
        when = _parse_date(folded, original, act.start, act.end)
        parties = _parties(folded, original, act.start, act.end, kind)
        builder_match = _BUILDER.search(folded, act.start, act.end)
        builder = next((p["nome"] for p in parties if _BUILDER.search(fold(p["nome"]))), None)
        if builder is None and builder_match:
            line_end = folded.find("\n", builder_match.start())
            stop = min(x for x in (folded.find(",", builder_match.start()), line_end if line_end != -1 else act.end, act.end) if x != -1)
            builder = re.sub(r"\s+", " ", original[builder_match.start():stop]).strip(" .,;:") or None
        events.append({"ato": act.label, "numero": act.number, "tipo": kind, "tipo_descricao": label,
                       "data": when["data"] if when else None, "data_texto": when["data_texto"] if when else None,
                       "partes": parties, "valor": _money(folded, original, act.start, act.end), "construtora": builder,
                       "conclusao_obra": kind == "CONCLUSAO_OBRA", "trecho": _excerpt(original, act.start, act.end), **_source(chain, act.start)})
    for event in events:
        event["documento"] = document
        event["fonte"] = "matrícula anexada (leitura determinística dos trechos armazenados)"
    obra = [e for e in events if e["conclusao_obra"] and e["data"]]
    if obra:
        first = obra[0]
        built = date.fromisoformat(first["data"])
        years = today.year - built.year - ((today.month, today.day) < (built.month, built.day))
        idade = {"anos": years, "estimada": True, "base": f"{first['ato']} ({first['tipo_descricao']}), data citada no ato: {first['data_texto']}",
                 "texto": f"Idade estimada de {years} ano(s), a partir da averbação de conclusão de obra ({first['ato']}, {first['data_texto']}). "
                          "A data é a do ato registral; o habite-se pode ser anterior."}
    else:
        idade = {"anos": None, "estimada": False, "base": None, "texto": IDADE_NAO_DETERMINAVEL}
    transfers = [e for e in events if e["tipo"] in ("COMPRA_VENDA", "DOACAO", "ARREMATACAO") and e["data"]]
    consolidations = [e for e in events if e["tipo"] == "CONSOLIDACAO" and e["data"]]
    cons = consolidations[-1] if consolidations else None
    acquisition = None
    if transfers:
        before = [e for e in transfers if cons is None or e["data"] <= cons["data"]]
        acquisition = (before or transfers)[-1]
    return {"eventos": events, "idade": idade, "aviso_nomes": AVISO_NOMES,
            "datas_chave": {"aquisicao": {"data": acquisition["data"], "ato": acquisition["ato"]} if acquisition else None,
                            "consolidacao": {"data": cons["data"], "ato": cons["ato"]} if cons else None},
            "atos_lidos": [a.label for a in chain.acts]}


TITULARIDADE_NAO_CONFIRMADA = "Titularidade atual não confirmada"
_PAPEL_TITULARIDADE = {"PROPRIETARIO_ANTERIOR": "Proprietária(o) original (abertura da matrícula)", "VENDEDOR": "Vendedor(a): transmitiu o imóvel",
                       "COMPRADOR": "Adquirente (compra e venda)", "DEVEDOR": "Devedor(a) fiduciante", "CREDOR": "Credor(a) fiduciário(a)"}
_NON_CONTRACT_ACTS = {"CONCLUSAO_OBRA", "AFETACAO", "ABERTURA"}


def titularity(chain: RegistryChain, timeline: dict[str, Any]) -> dict[str, Any]:
    """Quem aparece na matrícula e em que papel, separando o titular ATUAL dos históricos (auditoria v6).

    Titular atual = último ato de transmissão ou consolidação (``registry_chain``), com o trecho; sem esse ato legível,
    "Titularidade atual não confirmada". Um nome lido na matrícula nunca vira titular só por aparecer no texto: o papel vem
    do rótulo ou da frase do ato. Papel inferido (ex.: devedor fiduciante = adquirente que deu o imóvel em garantia no mesmo
    contrato) é marcado e tem confiança menor."""
    from .privacy import redact_pii
    from .registry_chain import CONSOLIDACAO, GARANTIA, TITULARIDADE_DETERMINADA, same_party
    events = timeline.get("eventos") or []
    current = chain.current_holder if chain.holder_status == TITULARIDADE_DETERMINADA else None
    rows: list[dict[str, Any]] = []

    def add(name, kind, role, event, status, confidence, how, note=None, excerpt=None):
        if not name:
            return
        if any(r["papel"] == role and (fold(r["nome"]) == fold(name) or same_party(r["nome"], name)) for r in rows):
            return
        rows.append({"nome": name, "tipo_pessoa": kind, "papel": role, "ato": event.get("ato") if event else None,
                     "data": event.get("data") if event else None, "fonte": (event.get("documento") or {}).get("nome") if event else None,
                     "trecho": redact_pii(excerpt or (event.get("trecho") if event else None) or "", force=True) or None, "status": status, "confianca": confidence,
                     "como_identificado": how, "observacao": note})

    def is_current(name, event) -> bool:
        return current is not None and event.get("ato") == current.act and same_party(name, current.value)

    af_after = {f.act for f in chain.of(GARANTIA) if f.value == "PROPRIA"}
    for event in events:
        for party in event.get("partes") or []:
            name, kind, role, how = party["nome"], party.get("tipo_pessoa"), party["papel"], party.get("como_identificado")
            if event.get("tipo") == "CONSOLIDACAO" and role == "CREDOR":
                add(name, kind, "Proprietário(a) após a consolidação (credor fiduciário)", event,
                    "ATUAL" if is_current(name, event) else "HISTORICO", "ALTA", how)
            elif role == "OUTROS" and event.get("tipo") == "ABERTURA":
                # Proprietária na abertura sem transmissão posterior legível: pode ou não ser a titular hoje.
                add(name, kind, "Proprietária(o) na abertura da matrícula (titularidade atual não confirmada)", event, "HISTORICO", "MEDIA", how)
            elif role == "OUTROS":
                label = re.search(r"r[oó]tulo \"([^\"]+)\"", how or "")
                papel = (label.group(1).strip(" :").capitalize() if label else "Pessoa citada") + ": não é titular"
                odd = event.get("tipo") in _NON_CONTRACT_ACTS
                add(name, kind, papel, event, "HISTORICO", "BAIXA" if odd else "MEDIA", how,
                    "Rótulo lido junto a um ato que não é contrato (texto de OCR pode estar fora de ordem): confirmar o ato no documento." if odd else None)
            else:
                add(name, kind, _PAPEL_TITULARIDADE.get(role, party.get("papel_descricao") or role), event,
                    "ATUAL" if is_current(name, event) else "HISTORICO", "ALTA" if role in ("PROPRIETARIO_ANTERIOR", "VENDEDOR", "COMPRADOR") else "MEDIA", how)
                if role == "COMPRADOR" and af_after:
                    nxt = next((e for e in events if e.get("tipo") == "ALIENACAO_FIDUCIARIA" and e.get("ato") in af_after), None)
                    if nxt is not None and not any(p["papel"] == "DEVEDOR" for p in nxt.get("partes") or []):
                        add(name, kind, "Devedor(a) fiduciante (inferido)", nxt, "HISTORICO", "MEDIA",
                            f"adquirente do {event.get('ato')} que deu o imóvel em garantia no mesmo contrato ({nxt.get('ato')})",
                            "Papel inferido: a alienação fiduciária foi constituída no contrato de compra e venda com mútuo.")
    af = chain.fiduciary
    if af is not None and af.value:
        event = next((e for e in events if e.get("ato") == af.act), None)
        add(af.value, "JURIDICA", _PAPEL_TITULARIDADE["CREDOR"], event or {"ato": af.act}, "HISTORICO", "ALTA",
            "texto: \"em favor de ...\" (cadeia registral)", excerpt=af.excerpt)
    if current is not None:
        event = next((e for e in events if e.get("ato") == current.act), None) or {"ato": current.act}
        papel = "Proprietário(a) após a consolidação (credor fiduciário)" if current.kind == CONSOLIDACAO else "Titular pelo último ato de transmissão"
        add(current.value, "JURIDICA" if current.value and "[" not in current.value else "FISICA", papel, event, "ATUAL", "ALTA",
            "último ato de transmissão ou consolidação da matrícula", excerpt=current.excerpt)
        how = "consolidação da propriedade" if current.kind == CONSOLIDACAO else "último ato de transmissão"
        text = f"Titular atual pela matrícula: {current.value} ({how}, {current.act})."
    else:
        text = TITULARIDADE_NAO_CONFIRMADA + ": a sequência de atos legível não permite determinar o titular atual."
    return {"situacao": chain.holder_status, "titular_atual": current.value if current else None, "ato": current.act if current else None,
            "trecho": redact_pii(current.excerpt, force=True) if current else None, "confianca": "ALTA" if current else "BAIXA", "texto": text, "partes": rows,
            "aviso": "Proprietários anteriores, vendedores, devedores e fiadores são históricos: só o último ato de transmissão ou consolidação "
                     "define o titular atual, e a matrícula vale até a data da certidão."}


def holder_summary(db, property_id: int, stored_holder: str | None) -> dict[str, Any]:
    """Titular para exibição (auditoria v6): o da cadeia registral prevalece sobre o campo gravado no cadastro da matrícula.

    O cadastro (``PropertyRegistration.holder``) pode ter sido extraído antes da leitura por atos ou digitado; nunca é
    alterado aqui. Divergência vira aviso; sem ato legível de transmissão/consolidação, "Titularidade atual não confirmada"."""
    from .registry_chain import TITULARIDADE_DETERMINADA, registry_for_property, same_party
    chain = registry_for_property(db, property_id)
    current = chain.current_holder if chain is not None and chain.holder_status == TITULARIDADE_DETERMINADA else None
    holder = current.value if current is not None else None
    divergent = bool(stored_holder and holder and not same_party(stored_holder, holder) and fold(stored_holder) != fold(holder))
    if holder:
        text = f"Titular atual pela matrícula: {holder} ({current.act})."
    else:
        text = TITULARIDADE_NAO_CONFIRMADA + "."
    if divergent:
        text += (f" O titular gravado no cadastro da matrícula ({stored_holder}) não é o titular atual pela sequência de atos: "
                 "provável proprietário anterior. O cadastro não foi alterado.")
    return {"titular_atual": holder, "ato": current.act if current else None, "situacao": "DETERMINADA" if holder else "INCONCLUSIVO",
            "titular_cadastro": stored_holder, "divergencia_cadastro": divergent, "texto": text}


def timeline_for_property(db, property_id: int, today: date | None = None) -> dict[str, Any]:
    """Linha do tempo da matrícula mais recente do imóvel (somente leitura, sem reprocessar o documento)."""
    from . import models
    from .registry_chain import registry_for_property
    chain = registry_for_property(db, property_id)
    if chain is None or not chain.acts and not chain.original:
        return {"property_id": property_id, "disponivel": False, "motivo": "Sem matrícula com texto anexada ao imóvel.", "eventos": [],
                "idade": {"anos": None, "estimada": False, "base": None, "texto": IDADE_NAO_DETERMINAVEL}, "datas_chave": {}, "atos_lidos": [],
                "titularidade": {"situacao": "INCONCLUSIVO", "titular_atual": None, "ato": None, "trecho": None, "confianca": "BAIXA",
                                 "texto": TITULARIDADE_NAO_CONFIRMADA + ": sem matrícula com texto anexada.", "partes": [], "aviso": None}}
    version = db.get(models.DocumentVersion, chain.document_version_id) if chain.document_version_id else None
    document = {"document_id": version.document_id if version else None, "document_version_id": chain.document_version_id,
                "nome": version.document.name if version is not None and version.document is not None else "matrícula"}
    out = build_timeline(chain, document, today)
    out["titularidade"] = titularity(chain, out)
    return {"property_id": property_id, "disponivel": True, **out}
