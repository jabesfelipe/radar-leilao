"""Leitura determinística da cadeia registral da matrícula (v1.0.7).

Motivação (teste real do RESIDENCIAL AMERICA 5, imóvel 7 da VPS): os agentes leram a matrícula fora de ordem e
afirmaram que a incorporadora do cabeçalho era a titular, que não havia ônus apesar da alienação fiduciária
registrada e que a área total era a privativa. Este módulo lê o texto (OCR incluído) em ordem e separa:

- proprietário original (abertura da matrícula), proprietários intermediários e titular atual;
- alienação fiduciária, credor fiduciário, consolidação da propriedade, cancelamentos e baixas;
- ônus e gravames efetivamente encontrados;
- área total e área privativa.

Regras de segurança jurídica:

- O titular atual vem do ÚLTIMO ato de transmissão/consolidação, na ordem do texto. Sem esse ato legível, a
  titularidade fica INCONCLUSIVA.
- Consolidação em nome do credor NÃO equivale a baixa da alienação fiduciária nem a ausência de gravames.
- A situação de ônus nunca é declarada "inexistente" automaticamente: ausência no texto lido é INCONCLUSIVO.

Funções puras sobre texto; ``registry_for_property`` é o único ponto que consulta o banco. Nenhum dado é alterado
aqui: quem chama decide como registrar (sempre como evidência, nunca sobrescrevendo o cadastro).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

TITULARIDADE_DETERMINADA = "DETERMINADA"
INCONCLUSIVO = "INCONCLUSIVO"
ONUS_EXISTENTE = "EXISTENTE"

PESSOA_FISICA = "[pessoa física]"

# Fatos da cadeia.
PROPRIETARIO_ORIGINAL = "PROPRIETARIO_ORIGINAL"
TRANSMISSAO = "TRANSMISSAO"
ALIENACAO_FIDUCIARIA = "ALIENACAO_FIDUCIARIA"
CONSOLIDACAO = "CONSOLIDACAO"
CANCELAMENTO = "CANCELAMENTO"
ONUS = "ONUS"
AREA_PRIVATIVA = "AREA_PRIVATIVA"
AREA_TOTAL = "AREA_TOTAL"


def _fold_char(char: str) -> str:
    base = unicodedata.normalize("NFKD", char)
    return (base[0] if base else char).upper()


def fold(text: str) -> str:
    """Maiúsculas sem acento, preservando o comprimento (as posições valem para o texto original)."""
    return "".join(_fold_char(char) for char in text or "")


_ENTITY_HINTS = re.compile(
    r"\b(LTDA|S\.?\s?A\.?|S/A|EIRELI|CAIXA|BANCO|FEDERAL|EMPRESA|CONSTRUTORA|ENGENHARIA|INCORPORADORA|EMPREENDIMENTOS|"
    r"MUNICIPIO|PREFEITURA|ESTADO|UNIAO|FUNDO|COOPERATIVA|ASSOCIACAO|CONDOMINIO|COMPANHIA|CIA|INSTITUICAO|SECURITIZADORA)\b"
)


def _clean_name(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw or "").strip(" .,-;:—")
    return text[:160]


def canonical_party(name: str | None) -> str | None:
    """Nome exibível da parte: empresas/entes ficam com o nome; pessoa física vira um papel (minimização)."""
    if not name:
        return None
    clean = _clean_name(name)
    folded = fold(clean)
    if "CAIXA ECON" in folded:
        return "CAIXA ECONÔMICA FEDERAL"
    if _ENTITY_HINTS.search(folded):
        return clean
    return PESSOA_FISICA


def same_party(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    fa, fb = fold(canonical_party(a) or ""), fold(canonical_party(b) or "")
    if fa == fold(PESSOA_FISICA) or fb == fold(PESSOA_FISICA):
        return False
    core_a = re.sub(r"[^A-Z0-9 ]", "", fa).split()[:2]
    core_b = re.sub(r"[^A-Z0-9 ]", "", fb).split()[:2]
    return bool(core_a) and core_a == core_b


def parse_area(raw: str) -> Decimal | None:
    value = (raw or "").strip().rstrip(".,")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return number.quantize(Decimal("0.01")) if 0 < number < 100000 else None


@dataclass
class RegistryFact:
    kind: str
    value: str | None
    position: int
    chunk_id: int | None
    page: int | None
    section: str | None
    excerpt: str
    act: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"tipo": self.kind, "valor": self.value, "ato": self.act, "chunk_id": self.chunk_id, "pagina": self.page, "trecho": self.excerpt}


@dataclass
class RegistryChain:
    facts: list[RegistryFact] = field(default_factory=list)
    document_version_id: int | None = None
    chunk_texts: dict[int, str] = field(default_factory=dict)

    # ---- consultas -------------------------------------------------------
    def of(self, kind: str) -> list[RegistryFact]:
        return [fact for fact in self.facts if fact.kind == kind]

    @property
    def original_owner(self) -> RegistryFact | None:
        owners = self.of(PROPRIETARIO_ORIGINAL)
        return owners[0] if owners else None

    def ownership_events(self) -> list[RegistryFact]:
        return sorted(self.of(TRANSMISSAO) + self.of(CONSOLIDACAO), key=lambda fact: fact.position)

    @property
    def current_holder(self) -> RegistryFact | None:
        events = self.ownership_events()
        return events[-1] if events else None

    @property
    def holder_status(self) -> str:
        last = self.current_holder
        return TITULARIDADE_DETERMINADA if last is not None and last.value else INCONCLUSIVO

    @property
    def holder_name(self) -> str | None:
        return self.current_holder.value if self.holder_status == TITULARIDADE_DETERMINADA else None

    def intermediate_owners(self) -> list[str]:
        names = [fact.value or "não identificado" for fact in self.ownership_events()[:-1]]
        return names

    @property
    def fiduciary(self) -> RegistryFact | None:
        facts = self.of(ALIENACAO_FIDUCIARIA)
        return facts[-1] if facts else None

    @property
    def consolidation(self) -> RegistryFact | None:
        facts = self.of(CONSOLIDACAO)
        return facts[-1] if facts else None

    def fiduciary_cancelled(self) -> bool:
        af = self.fiduciary
        return bool(af) and any(c.position > af.position and c.value == ALIENACAO_FIDUCIARIA for c in self.of(CANCELAMENTO))

    def area(self, kind: str) -> Decimal | None:
        facts = self.of(kind)
        return parse_area(facts[0].value or "") if facts else None

    def encumbrance_status(self) -> tuple[str, str]:
        """(situação, justificativa). Nunca devolve "inexistente": o texto lido não prova a ausência de ônus."""
        onus = self.of(ONUS)
        cancels = self.of(CANCELAMENTO)
        af = self.fiduciary
        if onus:
            kinds = ", ".join(sorted({fact.value or "gravame" for fact in onus}))
            if cancels:
                return INCONCLUSIVO, f"Constam gravames ({kinds}) e também cancelamentos/baixas; confirme na matrícula quais seguem vigentes."
            return ONUS_EXISTENTE, f"Constam gravames na matrícula ({kinds}) sem cancelamento identificado no texto lido."
        if af is not None and not self.fiduciary_cancelled():
            if self.consolidation is not None and self.consolidation.position > af.position:
                return INCONCLUSIVO, ("Alienação fiduciária registrada" + (f" ({af.act})" if af.act else "") + " e propriedade consolidada em nome do credor"
                                      + (f" ({self.consolidation.act})" if self.consolidation.act else "") + "; não foi identificada averbação de cancelamento ou baixa. "
                                      "A consolidação não equivale a baixa nem prova ausência de outros gravames: confirmar com certidão de ônus atualizada.")
            return ONUS_EXISTENTE, "Alienação fiduciária registrada" + (f" ({af.act})" if af.act else "") + " sem cancelamento identificado no texto lido."
        return INCONCLUSIVO, "Nenhum ônus identificado no texto lido; a ausência no texto (inclusive OCR) não comprova a inexistência de ônus ou gravames."

    def is_empty(self) -> bool:
        return not self.facts

    def to_prompt_dict(self) -> dict[str, Any]:
        """Resumo para os agentes. Pessoas físicas aparecem como papel; trechos não são repetidos (o agente lê o RAG)."""
        situacao, justificativa = self.encumbrance_status()
        original = self.original_owner
        return {
            "proprietario_original": original.value if original else None,
            "proprietarios_intermediarios": self.intermediate_owners(),
            "titular_atual": self.holder_name,
            "titular_atual_situacao": self.holder_status,
            "titular_atual_ato": self.current_holder.act if self.current_holder else None,
            "alienacao_fiduciaria": ({"ato": self.fiduciary.act, "credor_fiduciario": self.fiduciary.value, "cancelada": self.fiduciary_cancelled()} if self.fiduciary else None),
            "consolidacao": ({"ato": self.consolidation.act, "em_nome_de": self.consolidation.value} if self.consolidation else None),
            "cancelamentos": [fact.act or "ato não identificado" for fact in self.of(CANCELAMENTO)],
            "onus_e_gravames": situacao,
            "onus_justificativa": justificativa,
            "area_total_m2": _as_float(self.area(AREA_TOTAL)),
            "area_privativa_m2": _as_float(self.area(AREA_PRIVATIVA)),
            "atos_em_ordem": [f"{fact.act or '?'} {fact.kind}" for fact in sorted(self.facts, key=lambda f: f.position) if fact.kind not in (AREA_TOTAL, AREA_PRIVATIVA)],
        }


def _as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


# ---------------------------------------------------------------------------
# Montagem do texto (com remoção da sobreposição entre trechos) e leitura
# ---------------------------------------------------------------------------

@dataclass
class _Segment:
    start: int
    end: int
    chunk_id: int | None
    page: int | None
    section: str | None


def _strip_overlap(previous: str, current: str) -> str:
    prev_lines = [line.strip() for line in previous.splitlines() if line.strip()]
    cur_lines = current.splitlines()
    stripped = [line.strip() for line in cur_lines]
    for size in range(min(6, len(prev_lines)), 0, -1):
        head = [line for line in stripped if line][:size]
        if head and head == prev_lines[-size:]:
            removed, index = 0, 0
            while index < len(cur_lines) and removed < size:
                if cur_lines[index].strip():
                    removed += 1
                index += 1
            return "\n".join(cur_lines[index:])
    return current


def _assemble(chunks: Iterable[dict[str, Any]]) -> tuple[str, list[_Segment]]:
    text_parts: list[str] = []
    segments: list[_Segment] = []
    cursor = 0
    previous = ""
    for chunk in chunks:
        content = str(chunk.get("content") or "")
        if not content.strip():
            continue
        piece = _strip_overlap(previous, content) if previous else content
        previous = content
        piece = piece + "\n"
        segments.append(_Segment(cursor, cursor + len(piece), chunk.get("chunk_id"), chunk.get("page"), chunk.get("section")))
        text_parts.append(piece)
        cursor += len(piece)
    return "".join(text_parts), segments


def _locate(segments: list[_Segment], position: int) -> _Segment | None:
    for segment in segments:
        if segment.start <= position < segment.end:
            return segment
    return segments[-1] if segments else None


_ACT = re.compile(r"\b(R|AV[A-Z]?)\s*[-.]?\s*([0-9LIS]{1,3})(?=\s*[-/])")


def _act_before(folded: str, position: int) -> str | None:
    window_start = max(0, position - 900)
    matches = list(_ACT.finditer(folded, window_start, position + 1))
    if not matches:
        return None
    kind, number = matches[-1].group(1), matches[-1].group(2)
    number = number.replace("L", "1").replace("I", "1").replace("S", "5")
    return f"{'R' if kind == 'R' else 'Av'}-{number}"


_ORIGINAL_OWNER = re.compile(r"PROPRIETARI[AO]S?\s*:\s*([^,;\n]{3,160})")
_SALE_HEADER = re.compile(r"-\s*(COMPRA\s+E\s+VENDA|DOACAO|PERMUTA|ARREMATACAO|ADJUDICACAO|DACAO\s+EM\s+PAGAMENTO|TRANSMISSAO)\b")
_BUYER = re.compile(r"\b(?:VENDEU|DOOU|TRANSMITIU|PERMUTOU|ADJUDICOU|ARREMATOU)\b[^\n]{0,40}?\b(?:AO|AOS|AS|A)\s+([^,;\n]{3,160})")
_AF_ACT = re.compile(r"ALIENOU\s+FIDUCIARIAMENTE|-\s*ALIENACAO\s+FIDUCIARIA\b")
_IN_FAVOR = re.compile(r"EM\s+FAVOR\s+D[AO]S?\s+([^,;\n]{3,160})")
_CONSOLIDATION = re.compile(r"CONSOLIDAD[AO]\s+A\s+PROPRIEDADE[\s\S]{0,240}?EM\s+NOME\s+D[AO]S?\s+(?:CREDORA?\s+)?([^,;\n]{3,160})")
_CONSOLIDATION_HEADER = re.compile(r"-\s*CONSOLIDACAO\s+D[AE]")
_CANCEL = re.compile(r"\b(CANCELAMENTO|CANCELAD[AO]S?|FICA\s+CANCELAD[AO]|BAIXA\s+D[AEO]S?)\b")
_ONUS = re.compile(r"\b(PENHORA|INDISPONIBILIDADE|HIPOTECA|ARRESTO|SEQUESTRO|USUFRUTO|INALIENABILIDADE|IMPENHORABILIDADE)\b")
_AREA_PRIV = re.compile(r"AREA\s+(?:PRIVATIVA(?:\s+REAL)?|UTIL|(?:CONSTRUIDA\s+)?DE\s+(?:UTILIZACAO|USO)\s+EXCLUSIV[AO])\s*(?:DE|:|=)?\s*([0-9]{1,5}(?:[.,][0-9]{1,4})?)\s*M")
_AREA_TOTAL = re.compile(r"AREA\s+(?:TOTAL(?:\s+CONSTRUIDA)?|(?:CORRESPONDENTE\s+OU\s+)?GLOBAL(?:\s+CONSTRUIDA)?|CONSTRUIDA\s+TOTAL)\s*(?:DE|:|=)?\s*([0-9]{1,5}(?:[.,][0-9]{1,4})?)\s*M")


def _excerpt(original: str, start: int, end: int) -> str:
    return re.sub(r"\s+", " ", original[max(0, start):min(len(original), end)]).strip()[:300]


def read_registry(chunks: Iterable[dict[str, Any]], document_version_id: int | None = None) -> RegistryChain:
    """Lê a cadeia registral a partir dos trechos (``chunk_id``, ``content``, ``page``, ``section``) em ordem."""
    chunks = list(chunks)
    original, segments = _assemble(chunks)
    folded = fold(original)
    chain = RegistryChain(document_version_id=document_version_id,
                          chunk_texts={chunk["chunk_id"]: str(chunk.get("content") or "") for chunk in chunks if chunk.get("chunk_id") is not None})

    def add(kind: str, value: str | None, start: int, end: int, act: str | None = None) -> None:
        segment = _locate(segments, start)
        for existing in chain.facts:   # mesmo fato lido duas vezes (sobreposição residual do OCR)
            if existing.kind == kind and existing.value == value and abs(existing.position - start) < 400:
                return
        chain.facts.append(RegistryFact(kind, value, start, segment.chunk_id if segment else None, segment.page if segment else None,
                                        segment.section if segment else None, _excerpt(original, start, end), act))

    owner = _ORIGINAL_OWNER.search(folded)
    if owner:
        add(PROPRIETARIO_ORIGINAL, canonical_party(original[owner.start(1):owner.end(1)]), owner.start(), owner.end())

    for header in _SALE_HEADER.finditer(folded):
        buyer = _BUYER.search(folded, header.end(), min(len(folded), header.end() + 1500))
        value = canonical_party(original[buyer.start(1):buyer.end(1)]) if buyer else None
        add(TRANSMISSAO, value, header.start(), (buyer.end() if buyer else header.end()) + 40, _act_before(folded, header.start()))

    for match in _AF_ACT.finditer(folded):
        creditor = None
        # credor: "em favor da ..." perto do ato; com OCR a menção pode vir deslocada (colunas lidas fora de ordem).
        window = (max(0, match.start() - 200), min(len(folded), match.end() + 3500))
        favor = _IN_FAVOR.search(folded, *window)
        if favor:
            creditor = canonical_party(original[favor.start(1):favor.end(1)])
        elif "CAIXA ECON" in folded[window[0]:window[1]]:
            creditor = "CAIXA ECONÔMICA FEDERAL"
        # O cabeçalho do ato ("R-3 ... - ALIENAÇÃO FIDUCIÁRIA") e o texto ("alienou fiduciariamente") descrevem o MESMO
        # registro: só há um novo fato quando o credor é outro (nova garantia) ou houve cancelamento entre eles.
        previous = [fact for fact in chain.facts if fact.kind == ALIENACAO_FIDUCIARIA]
        cancelled_between = previous and _CANCEL.search(folded, previous[-1].position, match.start())
        if previous and not cancelled_between and (previous[-1].value is None or creditor is None or previous[-1].value == creditor):
            previous[-1].value = previous[-1].value or creditor
            continue
        add(ALIENACAO_FIDUCIARIA, creditor, match.start(), match.end() + 160, _act_before(folded, match.start()))

    consolidations = list(_CONSOLIDATION.finditer(folded))
    for match in consolidations:
        add(CONSOLIDACAO, canonical_party(original[match.start(1):match.end(1)]), match.start(), match.end(), _act_before(folded, match.start()))
    if not consolidations:
        for match in _CONSOLIDATION_HEADER.finditer(folded):
            add(CONSOLIDACAO, None, match.start(), match.end() + 120, _act_before(folded, match.start()))

    for match in _CANCEL.finditer(folded):
        context = folded[match.start():match.start() + 400]
        target = ALIENACAO_FIDUCIARIA if "FIDUCIARI" in context else (_ONUS.search(context).group(1) if _ONUS.search(context) else None)
        add(CANCELAMENTO, target, match.start(), match.end() + 200, _act_before(folded, match.start()))

    for match in _ONUS.finditer(folded):
        before = folded[max(0, match.start() - 120):match.start()]
        if _CANCEL.search(before):
            continue   # "cancelamento da penhora": já registrado como cancelamento
        add(ONUS, match.group(1).lower(), match.start(), match.end() + 160, _act_before(folded, match.start()))

    for pattern, kind in ((_AREA_PRIV, AREA_PRIVATIVA), (_AREA_TOTAL, AREA_TOTAL)):
        match = pattern.search(folded)
        if match:
            add(kind, original[match.start(1):match.end(1)], match.start(), match.end() + 10)

    chain.facts.sort(key=lambda fact: fact.position)
    return chain


def conclusions(chain: RegistryChain, area_total: Any = None, area_private: Any = None) -> list[dict[str, Any]]:
    """Conclusões determinísticas a registrar como evidência, cada uma com o fato da matrícula que a sustenta.

    ``fact`` = RegistryFact de apoio (documento, trecho) ou None (conclusão sem trecho a citar, ex.: titularidade
    inconclusiva sem ato legível). Divergências entre cadastro e matrícula são registradas, nunca corrigidas aqui."""
    out: list[dict[str, Any]] = []
    original = chain.original_owner
    if original is not None:
        out.append({"category": "JURIDICO", "fact": original, "text": f"Proprietário original (abertura da matrícula): {original.value}."})
    events = chain.ownership_events()
    for event in events[:-1]:
        label = "Transmissão" if event.kind == TRANSMISSAO else "Consolidação"
        out.append({"category": "JURIDICO", "fact": event, "text": f"{label} registrada" + (f" ({event.act})" if event.act else "")
                    + f": proprietário intermediário {event.value or 'não identificado no texto'}."})
    if chain.holder_status == TITULARIDADE_DETERMINADA:
        last = chain.current_holder
        how = "consolidação da propriedade" if last.kind == CONSOLIDACAO else "último ato de transmissão"
        out.append({"category": "JURIDICO", "fact": last, "text": f"Titular atual pela sequência de atos da matrícula: {last.value} ({how}" + (f", {last.act}" if last.act else "") + ")."})
    else:
        out.append({"category": "JURIDICO", "fact": chain.current_holder or original,
                    "text": "Titularidade atual INCONCLUSIVA: a sequência de atos legível da matrícula não permite determinar o titular atual."})
    af = chain.fiduciary
    if af is not None:
        historic = chain.consolidation is not None and chain.consolidation.position > af.position
        out.append({"category": "JURIDICO", "fact": af, "text": "Alienação fiduciária registrada" + (f" ({af.act})" if af.act else "")
                    + (f"; credor fiduciário: {af.value}" if af.value else "; credor fiduciário não identificado no texto")
                    + ("; registro histórico anterior à consolidação, sem cancelamento averbado identificado." if historic else ".")})
    if chain.consolidation is not None and chain.consolidation is not chain.current_holder:
        cons = chain.consolidation
        out.append({"category": "JURIDICO", "fact": cons, "text": "Consolidação da propriedade" + (f" ({cons.act})" if cons.act else "") + (f" em nome de {cons.value}." if cons.value else ".")})
    for cancel in chain.of(CANCELAMENTO):
        out.append({"category": "JURIDICO", "fact": cancel, "text": "Cancelamento/baixa averbado" + (f" ({cancel.act})" if cancel.act else "") + (f" referente a {cancel.value.lower().replace('_', ' ')}." if cancel.value else ".")})
    for onus in chain.of(ONUS):
        out.append({"category": "JURIDICO", "fact": onus, "text": f"Gravame encontrado na matrícula: {onus.value}" + (f" ({onus.act})" if onus.act else "") + "."})
    situacao, justificativa = chain.encumbrance_status()
    out.append({"category": "JURIDICO", "fact": af or (chain.of(ONUS) or [None])[0],
                "text": f"Situação de ônus e gravames: {'EXISTENTES' if situacao == ONUS_EXISTENTE else 'INCONCLUSIVA'}. {justificativa}"})
    for kind, label, registered in ((AREA_TOTAL, "área total", area_total), (AREA_PRIVATIVA, "área privativa", area_private)):
        facts = chain.of(kind)
        if not facts:
            continue
        doc_value = parse_area(facts[0].value or "")
        cad_value = parse_area(str(registered)) if registered not in (None, "", 0) else None
        text = f"Matrícula: {label} de {_fmt(doc_value)} m²."
        if cad_value is not None and doc_value is not None and abs(cad_value - doc_value) > _TOLERANCE:
            text = (f"Divergência entre cadastro e matrícula na {label}: cadastro {_fmt(cad_value)} m², matrícula {_fmt(doc_value)} m². "
                    "O cadastro não foi alterado; confirmar a fonte correta.")
        elif cad_value is not None:
            text += " Confere com o cadastro."
        out.append({"category": "DOCUMENTAL", "fact": facts[0], "text": text})
    return out


def registry_for_property(db, property_id: int) -> RegistryChain | None:
    """Cadeia da matrícula mais recente do imóvel (última versão de documento MATRICULA com texto).

    Sessões de teste simplificadas (sem ``scalars`` real) devolvem ``None``: a leitura é um complemento e nunca
    impede a análise."""
    from sqlalchemy import select
    from . import models
    try:
        version = db.scalars(
            select(models.DocumentVersion)
            .join(models.Document, models.Document.id == models.DocumentVersion.document_id)
            .where(models.Document.property_id == property_id, models.Document.document_type == "MATRICULA")
            .order_by(models.DocumentVersion.id.desc())
        ).first()
    except (AttributeError, TypeError):
        return None
    if version is None or not isinstance(version, models.DocumentVersion):
        return None
    return registry_for_version(db, version.id)


def registry_for_version(db, document_version_id: int) -> RegistryChain | None:
    from sqlalchemy import select
    from . import models
    try:
        rows = db.scalars(
            select(models.DocumentChunk)
            .where(models.DocumentChunk.document_version_id == document_version_id)
            .order_by(models.DocumentChunk.chunk_index, models.DocumentChunk.id)
        ).all()
    except (AttributeError, TypeError):
        return None
    chunks = [{"chunk_id": row.id, "content": row.content, "page": row.page, "section": row.section} for row in rows if isinstance(row, models.DocumentChunk)]
    if not chunks:
        return None
    return read_registry(chunks, document_version_id)


# ---------------------------------------------------------------------------
# Revisão de afirmações dos agentes contra a cadeia e o cadastro
# ---------------------------------------------------------------------------

_NEGATIVE_ONUS = re.compile(
    r"(\b(NAO|NENHUM|NENHUMA|SEM|INEXIST\w*|AUSENCIA\s+DE)\b[^.]{0,50}\b(ONUS|GRAVAMES?|RESTRICO?E?S?|PENHORAS?|HIPOTECAS?)\b)"
    r"|LIVRE\s+(E\s+DESEMBARACAD\w+|DE\s+(ONUS|GRAVAMES?|QUAISQUER))"
)
_ABSENCE_OF_INFO = re.compile(r"\bINFORMAC|\bNAO\s+(FOI|FORAM)\s+(POSSIVEL|LOCALIZAD)|\bNAO\s+CONSTA\s+NO\s+CONTEXTO")
_CLAIM_PRIV = re.compile(r"AREA\s+(?:PRIVATIVA|UTIL|DE\s+(?:USO|UTILIZACAO)\s+EXCLUSIV[AO]|EXCLUSIVA)\D{0,25}?([0-9]{1,5}(?:[.,][0-9]{1,4})?)\s*M")
_CLAIM_TOTAL = re.compile(r"AREA\s+(?:TOTAL|GLOBAL|CONSTRUIDA\s+TOTAL)\D{0,25}?([0-9]{1,5}(?:[.,][0-9]{1,4})?)\s*M")
_HOLDER_CLAIM = re.compile(r"\b(TITULAR|PROPRIETARI[AO]\s+(ATUAL|DO\s+IMOVEL|E\s+)|PERTENCE\s+A|E\s+A\s+PROPRIETARIA|E\s+O\s+PROPRIETARIO)")
_HOLDER_QUALIFIER = re.compile(r"\b(ORIGINAL|ANTERIOR|ANTIG[AO]|VENDEU|VENDEDORA|INCORPORADORA|FIADORA|ADQUIRIU|ADQUIRENTE|ABERTURA|INICIAL|ERA\b|FOI\b)")
_TOLERANCE = Decimal("0.01")


@dataclass
class Review:
    """Resultado da revisão: ``None`` em ``statement`` = afirmação aceita como está."""
    statement: str | None = None
    rule: str | None = None
    rejected: str | None = None


def _fmt(value: Decimal | None) -> str:
    return f"{value:.2f}".replace(".", ",") if value is not None else "não informado"


def review_statement(statement: str, chain: RegistryChain | None, area_total: Any = None, area_private: Any = None) -> Review:
    """Confere uma afirmação de agente sobre ônus, áreas e titularidade.

    Devolve a afirmação substituta (registrada como inferência rejeitada, com a regra aplicada) quando a original
    afirma ausência de ônus, troca área total por privativa ou aponta como titular atual quem não é o titular pela
    sequência de atos da matrícula. A afirmação original é preservada em ``rejected`` para auditoria.
    """
    text = fold(statement or "")
    if not text.strip():
        return Review()

    if _NEGATIVE_ONUS.search(text) and not _ABSENCE_OF_INFO.search(text):
        situacao, justificativa = chain.encumbrance_status() if chain is not None else (INCONCLUSIVO, "Sem leitura da cadeia registral.")
        label = "EXISTENTES" if situacao == ONUS_EXISTENTE else "INCONCLUSIVA"
        return Review(f"Situação de ônus e gravames {label}: {justificativa}", "ONUS_SEM_PROVA_DE_AUSENCIA", statement)

    doc_priv = chain.area(AREA_PRIVATIVA) if chain is not None else None
    doc_total = chain.area(AREA_TOTAL) if chain is not None else None
    cad_priv = parse_area(str(area_private)) if area_private not in (None, "") else None
    cad_total = parse_area(str(area_total)) if area_total not in (None, "", 0) else None
    ref_priv, ref_total = doc_priv or cad_priv, doc_total or cad_total
    source = "a matrícula" if doc_priv or doc_total else "o cadastro"
    claim = _CLAIM_PRIV.search(text)
    if claim and ref_priv is not None:
        claimed = parse_area(claim.group(1))
        if claimed is not None and abs(claimed - ref_priv) > _TOLERANCE:
            swapped = ref_total is not None and abs(claimed - ref_total) <= _TOLERANCE
            reason = " (o valor informado é a área total)" if swapped else ""
            return Review(f"Divergência de área: o agente indicou área privativa de {_fmt(claimed)} m²{reason}; {source} indica área privativa de "
                          f"{_fmt(ref_priv)} m² e área total de {_fmt(ref_total)} m². Valor do agente não aceito.", "AREA_PRIVATIVA_DIVERGENTE", statement)
    claim = _CLAIM_TOTAL.search(text)
    if claim and ref_total is not None:
        claimed = parse_area(claim.group(1))
        if claimed is not None and abs(claimed - ref_total) > _TOLERANCE:
            swapped = ref_priv is not None and abs(claimed - ref_priv) <= _TOLERANCE
            reason = " (o valor informado é a área privativa)" if swapped else ""
            return Review(f"Divergência de área: o agente indicou área total de {_fmt(claimed)} m²{reason}; {source} indica área total de "
                          f"{_fmt(ref_total)} m² e área privativa de {_fmt(ref_priv)} m². Valor do agente não aceito.", "AREA_TOTAL_DIVERGENTE", statement)

    if chain is not None and _HOLDER_CLAIM.search(text) and not _HOLDER_QUALIFIER.search(text):
        holder = chain.holder_name
        named = [fact.value for fact in chain.facts if fact.kind in (PROPRIETARIO_ORIGINAL, TRANSMISSAO, CONSOLIDACAO) and fact.value and fact.value != PESSOA_FISICA]
        mentioned = [name for name in named if fold(name).split()[0] in text]
        if chain.holder_status == INCONCLUSIVO and mentioned:
            return Review("Titularidade atual INCONCLUSIVA: a sequência de atos legível da matrícula não permite determinar o titular atual.", "TITULARIDADE_INCONCLUSIVA", statement)
        if holder and mentioned and not any(same_party(name, holder) for name in mentioned):
            act = chain.current_holder.act if chain.current_holder else None
            original = chain.original_owner.value if chain.original_owner else None
            note = f" {original} consta como proprietária original (abertura da matrícula)." if original and any(same_party(original, name) for name in mentioned) else ""
            return Review(f"Titular atual pela sequência de atos da matrícula: {holder}" + (f" ({act})" if act else "") + "." + note, "TITULARIDADE_CRONOLOGICA", statement)
    return Review()
