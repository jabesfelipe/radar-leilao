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
    ("INTIMACAO", "Intimação do devedor", r"INTIMAC"),
    ("INADIMPLENCIA", "Inadimplência / mora", r"INADIMPL|\bEM\s+MORA\b"),
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


_NORM_DATE_CONTEXT = re.compile(r"\b(LEI|DECRETO|PORTARIA|INSTRUCAO|RESOLUCAO|PROVIMENTO|CIRCULAR|MEDIDA\s+PROVISORIA|CODIGO)\b[^;\n]{0,50}?\bDE\s*$")


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
            # Data de lei/portaria citada no ato ("Lei nº 12.604, de 02/07/1999") não é a data do ato (revisão PR #8: com a data
            # do protocolo ilegível pelo OCR, a da lei era usada).
            if _NORM_DATE_CONTEXT.search(folded[max(start, match.start() - 70):match.start()]):
                continue
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


DATA_PROTOCOLO, DATA_DOCUMENTO, DATA_ATO, DATA_CITADA = "PROTOCOLO", "DOCUMENTO", "ATO", "CITADA"
DATA_TIPO_LABELS = {DATA_PROTOCOLO: "Data do protocolo", DATA_DOCUMENTO: "Data do documento apresentado (contrato, escritura, ofício)",
                    DATA_ATO: "Data do registro/averbação", DATA_CITADA: "Data citada no ato (tipo não identificado)"}
_CTX_PROTOCOLO = re.compile(r"PROTOCOL")
_CTX_DOCUMENTO = re.compile(r"INSTRUMENTO|CONTRATO|ESCRITURA|CEDULA|TITULO|DATAD[OA]|REQUERIMENTO|MANDADO|OFICIO|FORMAL|CARTA")
_CTX_ATO = re.compile(r"REGISTRAD|AVERBAD|REGISTRO|AVERBACAO|AVERBO|REGISTRO\s+EM")
_PROTOCOL_NUMBER = re.compile(r"PROTOCOL\w*\s*(?:N\s*[º°O.]*\s*|SOB\s+O\s+N\s*[º°O.]*\s*)?([0-9][0-9.]{2,})")
# Só contexto da PRÓPRIA certidão: "expedido em" solto (habite-se, alvará, carta) não é a emissão da certidão (validação do imóvel 7).
_CERT_CTX = re.compile(r"DATA\s*/\s*HORA|CERTIDAO[^\n]{0,80}?(?:EMITIDA|EXPEDIDA|GERADA|LAVRADA)\s+EM|CERTIFICO\s+E\s+DOU\s+FE[^\n]{0,120}?\bEM\b")


def _typed_dates(folded: str, original: str, start: int, end: int) -> list[dict[str, Any]]:
    """Todas as datas do ato com o TIPO deduzido do texto logo antes delas (evolução v1.0.14). Sem palavra que identifique o tipo,
    a data fica como CITADA: o sistema não troca data de protocolo por data do ato nem inventa data ausente."""
    found: list[tuple[int, int, date]] = []
    for pattern, ext in ((_DATE_NUM, False), (_DATE_EXT, True)):
        for match in pattern.finditer(folded, start, end):
            if _NORM_DATE_CONTEXT.search(folded[max(start, match.start() - 70):match.start()]):
                continue
            day, month, year = int(match.group(1)), (MESES[match.group(2)] if ext else int(match.group(2))), int(match.group(3))
            try:
                value = date(year, month, day)
            except ValueError:
                continue
            if 1800 <= year <= date.today().year + 1:
                found.append((match.start(), match.end(), value))
    found.sort()
    out: list[dict[str, Any]] = []
    previous_end = start
    for pos, stop, value in found:
        # Contexto = texto entre a data anterior e esta (no máximo 60 caracteres, na mesma linha); vale a palavra mais próxima.
        window = folded[max(previous_end, pos - 60):pos].rsplit("\n", 1)[-1]
        hits = [(m.end(), kind) for kind, rx in ((DATA_PROTOCOLO, _CTX_PROTOCOLO), (DATA_DOCUMENTO, _CTX_DOCUMENTO), (DATA_ATO, _CTX_ATO))
                for m in rx.finditer(window)]
        kind = max(hits)[1] if hits else DATA_CITADA
        out.append({"tipo": kind, "tipo_descricao": DATA_TIPO_LABELS[kind], "data": value.isoformat(),
                    "data_texto": re.sub(r"\s+", " ", original[pos:stop]).strip()})
        previous_end = stop
    return out


def _protocol(folded: str, start: int, end: int) -> str | None:
    match = _PROTOCOL_NUMBER.search(folded, start, end)
    return match.group(1).strip(".") if match else None


def certificate_issue(original: str) -> dict[str, Any]:
    """Data de emissão da certidão da matrícula, só quando o texto a identifica ("Data/hora", "emitida em", "expedida em").
    Sem isso: não localizada (a validade da matrícula vai até a data da certidão, que precisa ser conferida no documento)."""
    folded = fold(original or "")
    for ctx in _CERT_CTX.finditer(folded):
        window_end = min(len(folded), ctx.end() + 80)
        for pattern, ext in ((_DATE_NUM, False), (_DATE_EXT, True)):
            match = pattern.search(folded, ctx.end(), window_end)
            if match:
                day, month, year = int(match.group(1)), (MESES[match.group(2)] if ext else int(match.group(2))), int(match.group(3))
                try:
                    value = date(year, month, day)
                except ValueError:
                    continue
                return {"data": value.isoformat(), "data_texto": re.sub(r"\s+", " ", original[match.start():match.end()]).strip(),
                        "trecho": re.sub(r"\s+", " ", original[ctx.start():window_end]).strip(), "confianca": "MEDIA",
                        "texto": f"Certidão emitida em {value.strftime('%d/%m/%Y')} (lido no texto: \"{original[ctx.start():ctx.end()].strip()}\")."}
    return {"data": None, "data_texto": None, "trecho": None, "confianca": "BAIXA",
            "texto": "Data de emissão da certidão não localizada no texto lido. Confira no documento: a matrícula só vale até essa data."}


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
    if "CAIXA ECON" in fold(name):
        # OCR em colunas corta o nome ("CAIXA ECONÔMICA" / "...FEDERAL-CEF"): exibe a forma canônica da cadeia registral.
        name = canonical_party(name)
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


def _relocate_fiduciary_fragment(events: list[dict[str, Any]], spans: dict[str, tuple[int, int]], folded: str, original: str) -> None:
    """OCR em colunas (revisão PR #8, conferido no PDF): o trecho "FIADORA: ...; ALIENOU FIDUCIARIAMENTE ... em favor da ..." do
    registro da alienação apareceu no texto depois de outro ato. "Alienou fiduciariamente" só existe no ato da alienação: as partes
    desse trecho vão para o ato de alienação, com a origem declarada, e o ato onde o texto foi lido recebe um aviso."""
    af_event = next((e for e in events if e["tipo"] == "ALIENACAO_FIDUCIARIA"), None)
    if af_event is None:
        return
    for event in events:
        span = spans.get(event["ato"])
        if event is af_event or span is None or not _DEBTOR_BEFORE_AF.search(folded, *span):
            continue
        note = (f"; lido pelo OCR junto ao {event['ato']}, associado ao {af_event['ato']} pelo conteúdo (\"alienou fiduciariamente\" só aparece "
                "no registro da alienação)")
        moved = [p for p in event["partes"] if p["papel"] == "OUTROS"]
        event["partes"] = [p for p in event["partes"] if p not in moved]
        for party in moved:
            if not any(fold(p["nome"]) == fold(party["nome"]) and p["papel"] == party["papel"] for p in af_event["partes"]):
                af_event["partes"].append({**party, "como_identificado": party["como_identificado"] + note, "realocado_de": event["ato"]})
        favor = _FAVOR.search(folded, *span)
        if favor and not any(p["papel"] == "CREDOR" for p in af_event["partes"]):
            person = _person(original, favor.start(1), favor.end(1), "CREDOR", "texto: \"em favor de ...\"" + note)
            if person:
                af_event["partes"].append({**person, "realocado_de": event["ato"]})
        event["aviso_ocr"] = (f"Parte do texto lido junto a este ato (\"... alienou fiduciariamente ...\") pertence ao {af_event['ato']}: a página foi "
                              f"lida fora de ordem pelo OCR. As pessoas desse trecho foram associadas ao {af_event['ato']}.")


_PAPEL_SIMPLES = {"PROPRIETARIO_ANTERIOR": "Antigo proprietário", "VENDEDOR": "Vendedor", "COMPRADOR": "Comprador",
                  "DEVEDOR": "Devedor do financiamento", "CREDOR": "Banco credor"}


def _names(event: dict[str, Any], role: str) -> list[str]:
    return [p["nome"] for p in event.get("partes") or [] if p["papel"] == role]


def _brl(value: Any) -> str:
    number = Decimal(str(value))
    return "R$ " + f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _plain_language(event: dict[str, Any], events: list[dict[str, Any]], chain: RegistryChain) -> dict[str, Any]:
    """Título, explicação e envolvidos em linguagem simples (revisão PR #8). Só o que o ato registra: inadimplência, intimação
    ou notificação aparecem apenas quando o texto do ato as cita; o devedor da consolidação vem do registro da alienação."""
    from .registry_chain import INTIMACAO
    kind, ato = event["tipo"], event["ato"]
    one = lambda names, default: (names[0] if names else default)  # noqa: E731
    valor = f" pelo preço de {_brl(event['valor']['valor'])}" if event.get("valor") and event["valor"]["rotulo"] == "preço" else ""
    af = next((e for e in events if e["tipo"] == "ALIENACAO_FIDUCIARIA"), None)
    sale = next((e for e in events if e["tipo"] == "COMPRA_VENDA"), None)
    devedor = (_names(af, "DEVEDOR") or (_names(sale, "COMPRADOR") if sale else [])) if af else []
    envolvidos = []
    for p in event.get("partes") or []:
        if kind == "CONSOLIDACAO" and p["papel"] == "CREDOR":
            papel = "Novo proprietário (banco credor)"
        elif p["papel"] == "OUTROS":
            label = re.search(r"r[oó]tulo \"([^\"]+)\"", p.get("como_identificado") or "")
            papel = (label.group(1).strip(" :").capitalize() if label else "Pessoa citada") + (" (garantia pessoal; não é proprietária)"
                                                                                                 if label and "FIADOR" in fold(label.group(1)) else "")
        else:
            papel = _PAPEL_SIMPLES.get(p["papel"], p.get("papel_descricao") or p["papel"])
        envolvidos.append({"nome": p["nome"], "papel": papel})
    if kind == "ALIENACAO_FIDUCIARIA" and devedor and not _names(event, "DEVEDOR"):
        envolvidos.insert(0, {"nome": devedor[0], "papel": f"Devedor do financiamento (comprador do {sale['ato']}, no mesmo contrato)"})
    if kind == "ABERTURA":
        dono = one([p["nome"] for p in event.get("partes") or []], "proprietário não identificado")
        title, text = f"A matrícula foi aberta em nome de {dono}", f"Primeiro registro do imóvel: {dono} aparece como proprietária."
    elif kind in ("COMPRA_VENDA", "DOACAO", "ARREMATACAO"):
        comprador, vendedor = one(_names(event, "COMPRADOR"), "o comprador"), one(_names(event, "VENDEDOR"), "o proprietário anterior")
        title = f"{comprador} comprou o imóvel"
        text = f"{vendedor} vendeu o imóvel a {comprador}{valor}. A partir deste ato, {comprador} passou a ser o proprietário."
    elif kind == "ALIENACAO_FIDUCIARIA":
        credor = one(_names(event, "CREDOR"), chain.fiduciary.value if chain.fiduciary and chain.fiduciary.value else "o banco credor")
        quem = one(devedor, "o comprador")
        divida = f" de {_brl(event['valor']['valor'])}" if event.get("valor") else ""
        title = f"O imóvel foi dado em garantia de um financiamento com {credor}"
        text = (f"{quem} financiou a compra com {credor} e deu o imóvel em garantia (alienação fiduciária) da dívida{divida}. Enquanto a dívida "
                f"não é paga, {credor} tem a propriedade em garantia; se não for paga, pode consolidar o imóvel em seu nome.")
    elif kind == "CONSOLIDACAO":
        novo = one(_names(event, "CREDOR") or _names(event, "OUTROS"), chain.consolidation.value if chain.consolidation else "o credor")
        title = f"{novo} passou a ser proprietária do imóvel"
        intim = {f.value for f in chain.of(INTIMACAO) if f.act == ato}
        why = ("O cartório registrou a certidão de não pagamento após a intimação por edital: a dívida não foi paga no prazo e "
               if "NAO_PURGACAO" in intim and "EDITAL" in intim else
               ("O cartório registrou a certidão de não pagamento da dívida e " if "NAO_PURGACAO" in intim else "Conforme o registro, "))
        origem = (f" O ato não repete o nome do devedor: a dívida é a do financiamento registrado no {af['ato']}"
                  + (f", em nome de {devedor[0]}" if devedor else "") + ".") if af else ""
        text = f"{why}a propriedade foi consolidada em nome de {novo}.{origem}"
    elif kind == "CONCLUSAO_OBRA":
        title, text = "A obra do prédio foi concluída (habite-se)", "Averbação da conclusão da obra do empreendimento. Não muda quem é o proprietário."
    elif kind == "AFETACAO":
        title, text = "O imóvel foi vinculado ao regime do empreendimento", "Averbação administrativa da incorporação (afetação). Não muda quem é o proprietário."
    else:
        title, text = f"Outro ato registrado: {event['tipo_descricao']}", "Ato sem explicação automática: leia o trecho da matrícula."
    return {"titulo_simples": title, "ato_descricao": f"{ato} — {event['tipo_descricao']}", "explicacao": text, "envolvidos": envolvidos,
            "evidencia": {"ato": ato, "trecho": event.get("trecho"), "fonte": "matrícula anexada", "pagina": event.get("pagina"),
                          "confianca": "MEDIA" if any(p.get("realocado_de") for p in event.get("partes") or []) else "ALTA"}}


def most_recent_first(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordem de exibição: o ato mais recente primeiro. Usa o NÚMERO do ato (a numeração da matrícula é cronológica e não depende
    da data, que pode faltar ou vir errada do OCR); ato sem número fica logo depois do anterior a ele no texto; a abertura por último."""
    keyed, last = [], 0.0
    for index, event in enumerate(events):
        number = event.get("numero")
        key = float(number) if isinstance(number, int) else last + 0.5
        last = key
        keyed.append((key, index, event))
    return [e for _, _, e in sorted(keyed, key=lambda item: (item[0], item[1]), reverse=True)]


def build_timeline(chain: RegistryChain, document: dict[str, Any] | None = None, today: date | None = None) -> dict[str, Any]:
    """Linha do tempo a partir de uma cadeia já lida (função pura)."""
    today = today or date.today()
    original = chain.original or ""
    folded = fold(original)
    events: list[dict[str, Any]] = []
    spans: dict[str, tuple[int, int]] = {}
    first_act = chain.acts[0].start if chain.acts else len(folded)
    later_transfer = any(_kind(folded, a.start, a.end)[0] in TRANSMISSOES for a in chain.acts)
    owner = _OWNER.search(folded, 0, first_act)
    if owner:
        role = "PROPRIETARIO_ANTERIOR" if later_transfer else "OUTROS"
        person = _person(original, owner.start(1), owner.end(1), role, "rótulo \"PROPRIETÁRIA:\" na abertura da matrícula")
        builder = person["nome"] if person and _BUILDER.search(fold(person["nome"])) else None
        events.append({"ato": "Abertura", "numero": 0, "tipo": "ABERTURA", "tipo_descricao": "Abertura da matrícula", "data": None, "data_texto": None,
                       "data_tipo": None, "data_tipo_descricao": None, "datas": [], "protocolo": None,
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
        typed = _typed_dates(folded, original, act.start, act.end)
        first_typed = next((d for d in typed if when and d["data"] == when["data"]), None)
        events.append({"ato": act.label, "numero": act.number, "tipo": kind, "tipo_descricao": label,
                       "data": when["data"] if when else None, "data_texto": when["data_texto"] if when else None,
                       "data_tipo": first_typed["tipo"] if first_typed else None,
                       "data_tipo_descricao": first_typed["tipo_descricao"] if first_typed else None,
                       "datas": typed, "protocolo": _protocol(folded, act.start, act.end),
                       "partes": parties, "valor": _money(folded, original, act.start, act.end), "construtora": builder,
                       "conclusao_obra": kind == "CONCLUSAO_OBRA", "trecho": _excerpt(original, act.start, act.end), **_source(chain, act.start)})
        spans[act.label] = (act.start, act.end)
    _relocate_fiduciary_fragment(events, spans, folded, original)
    for event in events:
        event["documento"] = document
        event["fonte"] = "matrícula anexada (leitura determinística dos trechos armazenados)"
        event.update(_plain_language(event, events, chain))
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
    return {"eventos": events, "eventos_recentes_primeiro": most_recent_first(events), "idade": idade, "aviso_nomes": AVISO_NOMES,
            "datas_chave": {"aquisicao": {"data": acquisition["data"], "ato": acquisition["ato"]} if acquisition else None,
                            "consolidacao": {"data": cons["data"], "ato": cons["ato"]} if cons else None},
            "atos_lidos": [a.label for a in chain.acts], "certidao": certificate_issue(original),
            "aviso_datas": "Cada ato pode citar várias datas (protocolo, documento apresentado, registro). O tipo de cada data vem da palavra "
                           "que a antecede no texto; sem essa palavra, a data aparece como \"citada\". Nenhuma data é deduzida."}


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
                moved = party.get("realocado_de")
                add(name, kind, papel, event, "HISTORICO", "BAIXA" if odd else "MEDIA", how,
                    "Rótulo lido junto a um ato que não é contrato (texto de OCR pode estar fora de ordem): confirmar o ato no documento." if odd else
                    (f"O OCR leu este trecho junto ao {moved}; pelo conteúdo, pertence a este ato." if moved else None))
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
        text += (f" Existe divergência entre o cadastro e a matrícula: o titular informado no cadastro ({stored_holder}) não é o titular "
                 "atual pela sequência de atos (provável proprietário anterior). O cadastro não foi alterado.")
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
                                 "texto": TITULARIDADE_NAO_CONFIRMADA + ": sem matrícula com texto anexada.", "partes": [], "aviso": None},
                "eventos_recentes_primeiro": [],
                "situacao_atual": {"titular_atual": None, "titulo": TITULARIDADE_NAO_CONFIRMADA, "texto": "Sem matrícula com texto anexada ao imóvel.",
                                   "ato": None, "data": None, "confianca": "BAIXA", "atencao": []}}
    version = db.get(models.DocumentVersion, chain.document_version_id) if chain.document_version_id else None
    document = {"document_id": version.document_id if version else None, "document_version_id": chain.document_version_id,
                "nome": version.document.name if version is not None and version.document is not None else "matrícula"}
    out = build_timeline(chain, document, today)
    out["titularidade"] = titularity(chain, out)
    out["situacao_atual"] = current_situation(chain, out)
    out["pessoas"] = people(out)
    tit = out["titularidade"]
    out["situacao_atual"]["evidencia"] = tit.get("trecho")
    return {"property_id": property_id, "disponivel": True, **out}


def people(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    """Pessoas envolvidas na matrícula, uma linha por pessoa, com todos os papéis e atos (v1.0.14).

    "Perdeu o imóvel": devedor fiduciante de alienação seguida de consolidação em favor do credor. Construtora/incorporadora
    vêm do campo ``construtora`` dos atos. Nada é inferido além do que a titularidade e os atos já registram."""
    from .registry_chain import same_party
    rows: list[dict[str, Any]] = []
    events = timeline.get("eventos") or []
    consolidated = any(e.get("tipo") == "CONSOLIDACAO" for e in events)
    af_acts = [e.get("ato") for e in events if e.get("tipo") == "ALIENACAO_FIDUCIARIA"]
    last_af = af_acts[-1] if af_acts else None

    generic = {"CONSTRUTORA", "INCORPORADORA", "ENGENHARIA", "EMPREENDIMENTOS", "LTDA", "SERVICOS", "E", "S/A", "SA", "EIRELI", "ME"}

    def find(name: str) -> dict[str, Any] | None:
        f = fold(name)
        return next((r for r in rows if fold(r["nome"]) == f or same_party(r["nome"], name)
                     or (len(f) >= 8 and (f in fold(r["nome"]) or fold(r["nome"]) in f))), None)

    def add(name: str | None, kind: str | None, role: str, act: str | None, date_: str | None, current: bool) -> None:
        if not name:
            return
        words = [w for w in re.split(r"[\s/,.\-]+", fold(name)) if w]
        if words and all(w in generic for w in words):
            return          # só palavras genéricas ("INCORPORADORA/CONSTRUTORA"): rótulo lido como nome, não é pessoa
        existing = find(name)
        if existing is not None and len(name) > len(existing["nome"]) and role != "Construtora / incorporadora":
            existing["nome"] = name
        row = find(name)
        if row is None:
            row = {"nome": name, "tipo_pessoa": kind, "papeis": [], "atos": [], "atual": False, "perdeu_o_imovel": False, "primeira_data": date_}
            rows.append(row)
        if role not in row["papeis"]:
            row["papeis"].append(role)
        if act and act not in row["atos"]:
            row["atos"].append(act)
        row["atual"] = row["atual"] or current
        if "evedor" in role and consolidated and act is not None and act == last_af:
            row["perdeu_o_imovel"] = True
    for p in (timeline.get("titularidade") or {}).get("partes") or []:
        add(p["nome"], p.get("tipo_pessoa"), p["papel"], p.get("ato"), p.get("data"), p.get("status") == "ATUAL")
    for e in events:
        if e.get("construtora"):
            add(e["construtora"], "JURIDICA", "Construtora / incorporadora", e.get("ato"), e.get("data"), False)
    for r in rows:
        r["texto"] = (("Proprietário(a) atual. " if r["atual"] else "") + "; ".join(r["papeis"])
                      + (f" ({', '.join(r['atos'])})" if r["atos"] else "") + (". Perdeu o imóvel na consolidação." if r["perdeu_o_imovel"] else "."))
    rows.sort(key=lambda r: (not r["atual"], not r["perdeu_o_imovel"], r["nome"]))
    return rows


def _fmt(iso: str | None) -> str | None:
    return "/".join(reversed(iso.split("-"))) if iso else None


def current_situation(chain: RegistryChain, timeline: dict[str, Any]) -> dict[str, Any]:
    """Situação atual para o topo da tela (revisão PR #8): quem é o titular hoje, por qual ato e o que continua em aberto."""
    tit = timeline.get("titularidade") or {}
    holder, ato = tit.get("titular_atual"), tit.get("ato")
    event = next((e for e in timeline.get("eventos") or [] if e["ato"] == ato), None) if ato else None
    when = _fmt(event.get("data")) if event else None
    if holder and event and event["tipo"] == "CONSOLIDACAO":
        text = f"A propriedade foi consolidada em nome de {holder} no {ato}" + (f", em {when}." if when else " (data não identificada no texto).")
    elif holder:
        text = f"{holder} passou a ser proprietário pelo {ato}" + (f", em {when}." if when else " (data não identificada no texto).")
    else:
        text = "A sequência de atos lida não permite dizer quem é o proprietário hoje. Confira a matrícula atualizada."
    attention = []
    if chain.acts:
        situacao, justificativa = chain.encumbrance_status()
        attention.append(justificativa)
        readable, reason = chain.readable_for_absence()
        if not readable:
            attention.append(f"Leitura da matrícula incompleta: {reason}.")
    attention.append("A matrícula vale até a data da certidão: peça uma certidão atualizada antes de comprar.")
    return {"titular_atual": holder, "titulo": f"Titular atual: {holder}" if holder else TITULARIDADE_NAO_CONFIRMADA, "texto": text,
            "ato": ato, "data": event.get("data") if event else None, "confianca": tit.get("confianca") or "BAIXA", "atencao": attention}
