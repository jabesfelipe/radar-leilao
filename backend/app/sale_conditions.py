"""Leitura determinística das CONDIÇÕES OFICIAIS DA VENDA (v1.0.11, evidencias-v1).

A matrícula e as condições da venda são fontes distintas. A matrícula diz o que está registrado no imóvel; as condições
(página oficial do imóvel/regras da venda direta, ou o edital, quando houver) dizem quem responde por condomínio,
IPTU/tributos e evicção, e como pode ser feito o pagamento. Este módulo só lê documentos anexados ao imóvel com o tipo
``CONDICOES_VENDA`` (ou ``EDITAL``) e devolve cada cláusula encontrada com o trecho literal e a sua localização.

Regras de segurança:

- Nenhuma cláusula é presumida. Sem documento, nada é devolvido; documento sem a cláusula devolve a cláusula ausente.
- A regra de limite é classificada pelo que o texto diz ("paga apenas o que exceder" x "assume integralmente acima do
  limite"); texto com limite mas sem a regra do excedente fica AMBIGUA (o checklist fica INCONCLUSIVO).
- Conhecer a regra não informa o valor do débito: quem usa o resultado deve dizer isso.

Funções puras sobre texto; ``conditions_for_property`` é o único ponto que consulta o banco (somente leitura).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from .registry_chain import _assemble, _locate, fold

DOC_CONDICOES = "CONDICOES_VENDA"
DOC_EDITAL = "EDITAL"

TEMA_CONDOMINIO = "CONDOMINIO"
TEMA_TRIBUTOS = "TRIBUTOS"
TEMA_EVICCAO = "EVICCAO"
TEMA_FGTS = "FGTS"
TEMA_PAGAMENTO = "PAGAMENTO"
# Informação do vendedor sobre a averbação dos leilões negativos (ex.: "Averbação dos leilões negativos: Em tratamento").
# É declaração do vendedor: não comprova a averbação, que só a matrícula atualizada mostra.
TEMA_LEILOES = "LEILOES_NEGATIVOS"
TEMAS = (TEMA_CONDOMINIO, TEMA_TRIBUTOS, TEMA_EVICCAO, TEMA_FGTS, TEMA_PAGAMENTO, TEMA_LEILOES)

# Regras de débito (condomínio, tributos).
REGRA_EXCEDENTE = "COMPRADOR_ATE_LIMITE_VENDEDOR_EXCEDENTE"     # comprador até o limite; vendedor paga só o que exceder
REGRA_INTEGRAL_ACIMA = "COMPRADOR_ATE_LIMITE_VENDEDOR_INTEGRAL"  # comprador se dentro do limite; acima dele o vendedor assume tudo
REGRA_COMPRADOR = "COMPRADOR_INTEGRAL"
REGRA_VENDEDOR = "VENDEDOR_INTEGRAL"
REGRA_AMBIGUA = "AMBIGUA"
# Evicção.
EVICCAO_RESPONDE = "RESPONDE"
EVICCAO_LIMITADA = "RESPONDE_COM_LIMITE"
EVICCAO_EXCLUIDA = "EXCLUIDA"
# FGTS.
FGTS_ACEITA = "ACEITA"
FGTS_NAO_ACEITA = "NAO_ACEITA"
MENCIONADO = "MENCIONADO"
# Situação da averbação dos leilões negativos segundo o vendedor.
LEILOES_EM_TRATAMENTO = "EM_TRATAMENTO"
LEILOES_AVERBADA = "AVERBADA_SEGUNDO_VENDEDOR"
LEILOES_NAO_AVERBADA = "NAO_AVERBADA_SEGUNDO_VENDEDOR"

_THEME_PATTERNS = {
    TEMA_CONDOMINIO: re.compile(r"\bCONDOMINI(O|AIS)\b"),
    TEMA_TRIBUTOS: re.compile(r"\bIPTU\b|\bTRIBUTOS?\b|IMPOSTO\s+PREDIAL"),
    TEMA_EVICCAO: re.compile(r"\bEVICCAO\b"),
    TEMA_FGTS: re.compile(r"\bFGTS\b"),
    TEMA_PAGAMENTO: re.compile(r"(FORMAS?|CONDICOES|MODALIDADES?)\s+DE\s+PAGAMENTO"),
    TEMA_LEILOES: re.compile(r"AVERBACAO\s+D[OA]S?\s+LEILOES\s+NEGATIVOS"),
}
# Cláusula de débito precisa falar de responsabilidade/limite (não basta citar "condomínio" na descrição do imóvel).
_DEBT_CONTEXT = re.compile(r"RESPONSAB|POR\s+CONTA|LIMITE|DEBITO|DESPESA|PAGAMENTO|QUITA|ARCA")
_PCT = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")
_EXCESS = re.compile(r"(VALOR|PARCELA|MONTANTE)\s+QUE\s+(EXCEDER|ULTRAPASSAR)|\bEXCEDENTE\b|\bDIFERENCA\b")
_INTEGRAL_ABOVE = re.compile(r"(ULTRAPASS|EXCED|SUPERIOR|ACIMA)[^.]{0,160}(INTEGRAL|TOTALIDADE|\bTOTAL\b)|(INTEGRAL|TOTALIDADE)[^.]{0,160}(ULTRAPASS|EXCED|SUPERIOR|ACIMA)")
_BUYER = re.compile(r"(SOB\s+(A\s+)?RESPONSABILIDADE|POR\s+CONTA|A\s+CARGO)\s+D[OA]S?\s+(COMPRADOR|ADQUIRENTE|ARREMATANTE|PROPONENTE)")
_SELLER = re.compile(r"(SOB\s+(A\s+)?RESPONSABILIDADE|POR\s+CONTA|A\s+CARGO)\s+D[AO]S?\s+(VENDEDOR|CAIXA|CREDOR|BANCO|COMITENTE)")
_UPTO = re.compile(r"ATE\s+O\s+LIMITE|ATE\s+\d|LIMITADA?\s+A\s+\d|NO\s+LIMITE\s+DE")
_BELOW = re.compile(r"INFERIOR(ES)?\s+A|ABAIXO\s+D|MENOR(ES)?\s+(QUE|DO\s+QUE)|NAO\s+(ULTRAPASS|EXCED|SUPER)")
_EVICCAO_NEG = re.compile(r"NAO\s+(SE\s+)?(RESPONSABILIZ|RESPONDE|GARANT)\w*[^.]{0,80}EVICCAO|EVICCAO[^.]{0,100}NAO\s+(SE\s+)?(RESPONSABILIZ|RESPONDE|GARANT)"
                          r"|EXIM\w*[^.]{0,100}EVICCAO|EVICCAO[^.]{0,100}EXIM|RENUNCI\w*[^.]{0,100}EVICCAO|EXCLU\w*[^.]{0,60}EVICCAO")
_EVICCAO_POS = re.compile(r"(RESPONDE|RESPONSABILIZ|GARANT)\w*[^.]{0,100}EVICCAO|EVICCAO[^.]{0,100}(RESPONDE|RESPONSABILIZ|GARANT)")
_EVICCAO_LIMIT = re.compile(r"LIMITAD|RESTRIT|RESTITUICAO|DEVOLUCAO\s+D[OEA]S?\s+(VALOR|PRECO|QUANTIA)|ATE\s+O\s+LIMITE|NO\s+LIMITE")
_FGTS_NO = re.compile(r"NAO\s+(SE\s+|SERA\s+|E\s+)?(ACEIT|PERMIT|ADMIT|POSSIVEL)\w*[^.]{0,80}FGTS|FGTS[^.]{0,60}NAO\s+(SERA\s+|E\s+)?(ACEIT|PERMITID|ADMITID|POSSIVEL)"
                      r"|VEDAD\w*[^.]{0,40}FGTS|NEM\s+(A\s+)?(UTILIZACAO|USO)\s+D[EO]\s+FGTS|SEM\s+(A\s+)?(UTILIZACAO|USO)\s+D[EO]\s+FGTS")
_FGTS_YES = re.compile(r"(ACEIT|PERMIT|ADMIT|UTILIZ|USO\s+D)\w*[^.]{0,60}FGTS|FGTS[^.]{0,60}(ACEIT|PERMIT|ADMIT|PODE\s+SER\s+UTILIZ)")


@dataclass
class Clause:
    tema: str
    regra: str
    excerpt: str
    start: int
    chunk_id: int | None
    page: int | None
    section: str | None
    limite_pct: Decimal | None = None      # fração (0.10 = 10%)
    comparador: str | None = None          # "ATE" (inclusive) | "ABAIXO_DE" (estrito) | None
    vendedor: str = "o vendedor"
    detalhes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"tema": self.tema, "regra": self.regra, "limite_pct": str(self.limite_pct) if self.limite_pct is not None else None,
                "comparador": self.comparador, "vendedor": self.vendedor, "detalhes": self.detalhes, "trecho": self.excerpt,
                "chunk_id": self.chunk_id, "pagina": self.page, "secao": self.section}


@dataclass
class SaleConditions:
    document_version_id: int | None
    document_id: int | None = None
    document_name: str | None = None
    document_type: str | None = None
    clauses: list[Clause] = field(default_factory=list)
    chunk_texts: dict[int, str] = field(default_factory=dict)

    def of(self, tema: str) -> list[Clause]:
        return [clause for clause in self.clauses if clause.tema == tema]

    def first(self, tema: str) -> Clause | None:
        found = self.of(tema)
        return found[0] if found else None

    @property
    def source_label(self) -> str:
        kind = "edital" if self.document_type == DOC_EDITAL else "condições da venda"
        return f"{kind} ('{self.document_name}')" if self.document_name else kind


def normalize_doc_type(value: str | None) -> str | None:
    """Tipo do documento para esta leitura: CONDICOES_VENDA (com variações de escrita) ou EDITAL; demais tipos: None."""
    raw = " ".join(fold(str(value or "")).replace("_", " ").replace("-", " ").split())
    if raw in ("CONDICOES VENDA", "CONDICOES DA VENDA", "CONDICOES DE VENDA", "CONDICOES OFICIAIS DA VENDA", "REGRAS DA VENDA"):
        return DOC_CONDICOES
    if raw == "EDITAL":
        return DOC_EDITAL
    return None


def _pct(text: str) -> Decimal | None:
    match = _PCT.search(text)
    if not match:
        return None
    try:
        value = Decimal(match.group(1).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return (value / Decimal("100")).quantize(Decimal("0.0001")) if 0 < value <= 100 else None


# Linha que abre outra cláusula: item numerado ("5. PAGAMENTO"), marcador de lista ou título com dois-pontos ("IPTU:").
_CLAUSE_START = re.compile(r"[ \t]*(\d{1,2}(\.\d{1,2})*[.)-]\s|[-•*]\s|[A-Z][A-Z /]{2,40}:)")


def _paragraph(folded: str, position: int) -> tuple[int, int]:
    """Parágrafo da cláusula: da linha da menção até a linha em branco, o início de outra cláusula ou 700 caracteres.

    A normalização do documento pode remover as linhas em branco; por isso a próxima linha numerada ou com título também
    encerra a cláusula (senão um percentual de outra cláusula, como a comissão, seria lido como limite)."""
    start = folded.rfind("\n", 0, position) + 1
    blank = folded.find("\n\n", position)
    end = min(blank if blank != -1 else len(folded), start + 700, len(folded))
    line_end = folded.find("\n", position)
    while line_end != -1 and line_end + 1 < end:
        if _CLAUSE_START.match(folded, line_end + 1):
            end = line_end
            break
        line_end = folded.find("\n", line_end + 1)
    # outra cláusula começando numa linha nova encerra esta
    for pattern in _THEME_PATTERNS.values():
        for match in pattern.finditer(folded, position + 1, end):
            line_start = folded.rfind("\n", 0, match.start()) + 1
            if line_start > start and not folded[line_start:match.start()].strip(" \t-•*0123456789.)"):
                end = min(end, line_start)
    return start, end


def _classify_debt(text: str) -> tuple[str, Decimal | None, str | None]:
    pct = _pct(text)
    comparator = "ABAIXO_DE" if _BELOW.search(text) else ("ATE" if _UPTO.search(text) else None)
    buyer, seller = bool(_BUYER.search(text)), bool(_SELLER.search(text))
    if pct is not None:
        if _EXCESS.search(text):
            return REGRA_EXCEDENTE, pct, comparator
        if _INTEGRAL_ABOVE.search(text):
            return REGRA_INTEGRAL_ACIMA, pct, comparator
        return REGRA_AMBIGUA, pct, comparator      # limite sem regra do que acontece acima dele
    if buyer and not seller:
        return REGRA_COMPRADOR, None, None
    if seller and not buyer:
        return REGRA_VENDEDOR, None, None
    return REGRA_AMBIGUA, None, comparator


def _classify_eviction(text: str) -> str:
    if _EVICCAO_NEG.search(text):
        return EVICCAO_EXCLUIDA
    if _EVICCAO_POS.search(text):
        return EVICCAO_LIMITADA if _EVICCAO_LIMIT.search(text) else EVICCAO_RESPONDE
    return REGRA_AMBIGUA


def _classify_fgts(text: str) -> str:
    if _FGTS_NO.search(text):
        return FGTS_NAO_ACEITA
    if _FGTS_YES.search(text):
        return FGTS_ACEITA
    return MENCIONADO


def _classify_auctions(text: str) -> tuple[str, str]:
    """(situação, valor literal) da linha "Averbação dos leilões negativos: <situação>"."""
    match = re.search(r"NEGATIVOS\s*[:\-]?\s*([^\n]{0,120})", text)
    value = (match.group(1) if match else "").strip(" .;")
    if re.search(r"EM\s+(TRATAMENTO|ANDAMENTO|PROVIDENCIA)|PENDENTE|AGUARDANDO", value):
        return LEILOES_EM_TRATAMENTO, value
    if re.search(r"\bNAO\b", value):
        return LEILOES_NAO_AVERBADA, value
    if re.search(r"AVERBAD|CONCLUID|REALIZAD|\bSIM\b", value):
        return LEILOES_AVERBADA, value
    return MENCIONADO, value


def read_conditions(chunks: Iterable[dict[str, Any]], document_version_id: int | None = None, *, document_name: str | None = None,
                    document_type: str | None = DOC_CONDICOES, document_id: int | None = None) -> SaleConditions:
    """Cláusulas encontradas no texto (``chunk_id``, ``content``, ``page``, ``section``), a primeira de cada tema."""
    chunks = list(chunks)
    original, segments = _assemble(chunks)
    folded = fold(original)
    result = SaleConditions(document_version_id, document_id, document_name, document_type,
                            chunk_texts={c["chunk_id"]: str(c.get("content") or "") for c in chunks if c.get("chunk_id") is not None})
    for tema, pattern in _THEME_PATTERNS.items():
        for match in pattern.finditer(folded):
            start, end = _paragraph(folded, match.start())
            text = folded[start:end]
            if tema in (TEMA_CONDOMINIO, TEMA_TRIBUTOS) and not _DEBT_CONTEXT.search(text):
                continue
            segment = _locate(segments, start)
            excerpt = re.sub(r"\s+", " ", original[start:end]).strip()[:600]
            seller = "a Caixa" if "CAIXA" in text else "o vendedor"
            if tema in (TEMA_CONDOMINIO, TEMA_TRIBUTOS):
                regra, pct, comparator = _classify_debt(text)
                clause = Clause(tema, regra, excerpt, start, segment.chunk_id if segment else None, segment.page if segment else None,
                                segment.section if segment else None, pct, comparator, seller)
            elif tema == TEMA_EVICCAO:
                clause = Clause(tema, _classify_eviction(text), excerpt, start, segment.chunk_id if segment else None, segment.page if segment else None,
                                segment.section if segment else None, vendedor=seller)
            elif tema == TEMA_LEILOES:
                situation, _ = _classify_auctions(folded[match.start():].split("\n", 1)[0])
                own_line = original[match.start():].split("\n", 1)[0]
                excerpt = re.sub(r"\s+", " ", own_line).strip()[:300] or excerpt
                literal = re.search(r"negativos\s*[:\-]?\s*(.{0,120})", own_line, re.IGNORECASE)
                clause = Clause(tema, situation, excerpt, start, segment.chunk_id if segment else None, segment.page if segment else None,
                                segment.section if segment else None, vendedor=seller,
                                detalhes=[literal.group(1).strip(" .;")] if literal and literal.group(1).strip(" .;") else [])
            elif tema == TEMA_FGTS:
                clause = Clause(tema, _classify_fgts(text), excerpt, start, segment.chunk_id if segment else None, segment.page if segment else None,
                                segment.section if segment else None, vendedor=seller)
            else:
                details = [label for word, label in (("A VISTA", "à vista"), ("FINANCIAMENTO", "financiamento"), ("PARCELAD", "parcelado"),
                                                     ("RECURSOS PROPRIOS", "recursos próprios")) if word in text]
                clause = Clause(tema, MENCIONADO, excerpt, start, segment.chunk_id if segment else None, segment.page if segment else None,
                                segment.section if segment else None, vendedor=seller, detalhes=details)
            result.clauses.append(clause)
            break
    result.clauses.sort(key=lambda clause: clause.start)
    return result


def conditions_for_property(db, property_id: int) -> list[SaleConditions]:
    """Condições lidas dos documentos do imóvel: CONDICOES_VENDA primeiro, depois EDITAL; última versão de cada documento.

    Sessões de teste simplificadas (sem ``scalars`` real) devolvem lista vazia: a leitura é complemento e nunca impede a
    análise."""
    from sqlalchemy import select
    from . import models
    try:
        documents = db.scalars(select(models.Document).where(models.Document.property_id == property_id).order_by(models.Document.id)).all()
    except (AttributeError, TypeError):
        return []
    found: list[SaleConditions] = []
    for document in documents:
        if not isinstance(document, models.Document):
            continue
        kind = normalize_doc_type(document.document_type)
        if kind is None:
            continue
        # Consulta direta (não a coleção ``document.versions``, que pode estar desatualizada na sessão logo após o upload).
        version = db.scalars(select(models.DocumentVersion).where(models.DocumentVersion.document_id == document.id)
                             .order_by(models.DocumentVersion.id.desc())).first()
        if version is None:
            continue
        rows = db.scalars(select(models.DocumentChunk).where(models.DocumentChunk.document_version_id == version.id)
                          .order_by(models.DocumentChunk.chunk_index, models.DocumentChunk.id)).all()
        chunks = [{"chunk_id": r.id, "content": r.content, "page": r.page, "section": r.section} for r in rows]
        if not chunks:
            continue
        found.append(read_conditions(chunks, version.id, document_name=document.name, document_type=kind, document_id=document.id))
    found.sort(key=lambda c: (0 if c.document_type == DOC_CONDICOES else 1, -(c.document_version_id or 0)))
    return found
