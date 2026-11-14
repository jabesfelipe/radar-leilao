"""Validação de citações documentais e de valores extraídos (v1.0.4).

Tudo o que vem do LLM (chunk_id, página, trecho "literal", valor extraído) é ENTRADA NÃO CONFIÁVEL. Este módulo
decide, só com o conteúdo efetivamente extraído do documento, se uma citação sustenta a afirmação:

- ``FORTE``: o trecho informado aparece no documento e cobre os termos da afirmação;
- ``MODERADA``: o trecho aparece no documento e é relevante, mas cobre parte da afirmação (ou o trecho foi
  derivado do próprio documento porque o modelo não o informou);
- ``FRACA``: o documento citado não contém o suficiente para sustentar a afirmação;
- ``INVALIDA``: o trecho não aparece no documento, é texto do checklist/prompt, ou a afirmação traz valores
  que não estão no documento citado (ex.: número do snapshot financeiro atribuído ao edital).

Só FORTE e MODERADA podem ser apresentadas como prova documental (``STRENGTHS_PROVA``). A comparação normaliza
acentos, caixa, aspas, espaços e quebras de linha; não faz paráfrase nem aceita sinônimos.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

FORTE = "FORTE"
MODERADA = "MODERADA"
FRACA = "FRACA"
INVALIDA = "INVALIDA"
STRENGTHS = (FORTE, MODERADA, FRACA, INVALIDA)
STRENGTHS_PROVA = frozenset({FORTE, MODERADA})

ORIGEM_DOCUMENTO = "DOCUMENTO"
ORIGEM_CADASTRO = "CADASTRO"
ORIGEM_CALCULO = "CALCULO"
ORIGEM_PESQUISA_JUDICIAL = "PESQUISA_JUDICIAL"
ORIGEM_INFERENCIA = "INFERENCIA_IA"
ORIGEM_REGRA = "REGRA_DETERMINISTICA"
ORIGINS = (ORIGEM_DOCUMENTO, ORIGEM_CADASTRO, ORIGEM_CALCULO, ORIGEM_PESQUISA_JUDICIAL, ORIGEM_INFERENCIA, ORIGEM_REGRA)

MAX_EXCERPT = 600
_MESES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
# Palavras frequentes que não identificam um fato (evitam "cobertura" artificial).
_STOP = frozenset({
    "sobre", "entre", "quando", "possui", "possuem", "conforme", "segundo", "presente", "documento", "documentos",
    "informacao", "informacoes", "consta", "constam", "existe", "existem", "imovel", "imoveis", "valor", "valores",
    "trecho", "pelo", "pela", "pelos", "pelas", "deste", "desta", "esses", "essas", "estes", "estas", "outros",
    "outras", "ainda", "apenas", "sendo", "sera", "serao", "deve", "devem", "pode", "podem", "foram", "estao",
    "esta", "tambem", "mesmo", "mesma", "qualquer", "nenhum", "nenhuma", "todos", "todas", "relacao", "respeito",
})


def normalize(text: Any) -> str:
    """Minúsculas, sem acentos, sem aspas e com espaços/quebras de linha colapsados."""
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).lower()
    value = re.sub(r"[\"'`´«»“”‘’]", "", value)
    value = value.replace("º", "o").replace("ª", "a")
    return re.sub(r"\s+", " ", value).strip()


def _strip_edges(text: str) -> str:
    return text.strip(" .;:,-–—()[]")


def contains_phrase(text: str, phrase: str) -> bool:
    """``phrase`` aparece em ``text`` com fronteira de palavra (ambos já normalizados)."""
    if not phrase:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text) is not None


def excerpt_in_text(excerpt: Any, text: Any) -> bool:
    """O trecho informado é cópia literal (normalizada) do texto. Reticências separam partes que precisam
    aparecer em ordem; partes muito curtas (< 3 caracteres) não provam nada e são ignoradas."""
    norm_excerpt = _strip_edges(normalize(excerpt))
    if len(norm_excerpt) < 3:
        return False
    haystack = normalize(text)
    # Marcadores de mascaramento ([CPF], [EMAIL], [TELEFONE]...) entram no texto ENVIADO ao modelo (privacy.py); o
    # modelo os copia no trecho. Valem como lacuna, como as reticências: as partes ao redor precisam ser literais.
    parts = [_strip_edges(p) for p in re.split(r"\[\.\.\.\]|\.\.\.|…|\[[a-z_ ]{2,30}\]", norm_excerpt)]
    parts = [p for p in parts if len(p) >= 3]
    if not parts:
        return False
    position = 0
    for part in parts:
        index = haystack.find(part, position)
        if index < 0:
            return False
        position = index + len(part)
    return True


def _parse_number(token: str) -> Decimal | None:
    """Número em formato brasileiro ou simples ("240.000,00", "62,00", "9.514", "1500")."""
    token = token.strip(".,")
    if not token:
        return None
    try:
        if "," in token:
            inteiro, _, decimal_part = token.rpartition(",")
            return Decimal(inteiro.replace(".", "") + "." + decimal_part)
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", token):
            return Decimal(token.replace(".", ""))
        return Decimal(token)
    except InvalidOperation:
        return None


def numbers_in(text: Any, ignore_percent: bool = False) -> set[Decimal]:
    """Números com 2+ dígitos do texto (números de 1 dígito — "AV.3", "1 vaga" — não identificam um fato)."""
    found: set[Decimal] = set()
    norm_text = normalize(text)
    for match in re.finditer(r"\d[\d\.,]*", norm_text):
        raw = match.group(0)
        if ignore_percent and norm_text[match.end():match.end() + 2].lstrip().startswith("%"):
            continue
        if sum(ch.isdigit() for ch in raw) < 2:
            continue
        number = _parse_number(raw)
        if number is not None:
            found.add(number.normalize())
    return found


def key_terms(text: Any) -> set[str]:
    """Palavras significativas (5+ letras, fora da lista de palavras genéricas)."""
    return {w for w in re.findall(r"[a-z]{5,}", normalize(text)) if w not in _STOP}


def _coverage(terms: set[str], text: Any) -> float:
    if not terms:
        return 0.0
    haystack = normalize(text)
    return sum(1 for term in terms if term in haystack) / len(terms)


def best_window(statement: Any, content: Any, limit: int = 400) -> str:
    """Frase do PRÓPRIO documento que mais cobre a afirmação (trecho literal derivado da fonte, não do modelo)."""
    terms = key_terms(statement)
    numbers = numbers_in(statement)
    sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+|\n{1,}", str(content or "")) if s.strip()]
    best, best_score = "", 0
    for sentence in sentences:
        norm_sentence = normalize(sentence)
        score = sum(1 for term in terms if term in norm_sentence)
        score += len(numbers & numbers_in(sentence))
        if score > best_score:
            best, best_score = sentence, score
    return best[:limit] if best_score > 0 else ""


@dataclass(frozen=True)
class CitationAssessment:
    strength: str
    reason: str
    excerpt: str | None = None   # trecho LITERAL do documento (nunca texto do modelo que não esteja na fonte)

    @property
    def is_proof(self) -> bool:
        return self.strength in STRENGTHS_PROVA


def _is_forbidden(excerpt: str, forbidden: Iterable[str]) -> bool:
    norm_excerpt = _strip_edges(normalize(excerpt))
    if not norm_excerpt:
        return False
    for text in forbidden:
        norm_text = _strip_edges(normalize(text))
        if not norm_text:
            continue
        if norm_excerpt == norm_text or (len(norm_excerpt) >= 15 and norm_excerpt in norm_text):
            return True
    return False


def assess_citation(statement: Any, chunk_content: Any, excerpt: Any = None, forbidden: Iterable[str] = ()) -> CitationAssessment:
    """Força da citação de ``statement`` pelo chunk citado. ``forbidden``: textos que nunca são trecho de
    documento (perguntas do checklist, instruções do prompt)."""
    if not str(chunk_content or "").strip():
        return CitationAssessment(INVALIDA, "documento citado sem conteúdo extraído")
    informed = bool(excerpt and str(excerpt).strip())
    if informed:
        if _is_forbidden(str(excerpt), forbidden):
            return CitationAssessment(INVALIDA, "o trecho informado é texto do checklist/prompt, não do documento")
        if not excerpt_in_text(excerpt, chunk_content):
            return CitationAssessment(INVALIDA, "o trecho informado não aparece no documento citado")
        literal = str(excerpt).strip()[:MAX_EXCERPT]
    else:
        literal = best_window(statement, chunk_content)
    # Valores da afirmação precisam estar no documento citado (percentuais calculados pelo modelo não contam).
    missing = numbers_in(statement, ignore_percent=True) - numbers_in(chunk_content)
    if missing:
        sample = ", ".join(sorted(f"{n:f}" for n in missing)[:3])
        return CitationAssessment(INVALIDA, f"a afirmação traz valores que não estão no documento citado ({sample})")
    terms = key_terms(statement)
    cover_excerpt = _coverage(terms, literal) if literal else 0.0
    cover_chunk = _coverage(terms, chunk_content)
    if not literal:
        return CitationAssessment(FRACA, "nenhum trecho do documento citado sustenta a afirmação")
    if not terms:
        # Afirmação só com valores (todos presentes no documento): relevante, mas exige leitura humana.
        return CitationAssessment(MODERADA, "afirmação sem termos descritivos; valores conferidos no documento", literal)
    if informed and cover_excerpt >= 0.5:
        return CitationAssessment(FORTE, f"trecho literal cobre {cover_excerpt:.0%} dos termos da afirmação", literal)
    if cover_excerpt >= 0.25 or cover_chunk >= 0.5:
        reason = "trecho derivado do documento (o modelo não informou o trecho)" if not informed else f"trecho cobre {cover_excerpt:.0%} dos termos"
        return CitationAssessment(MODERADA, reason, literal)
    return CitationAssessment(FRACA, f"o documento citado cobre só {cover_chunk:.0%} dos termos da afirmação", literal)


# ---------------------------------------------------------------- valores extraídos (extração estruturada)

def value_variants(value: Any) -> list[str]:
    """Formas (normalizadas) em que um valor tipado pode aparecer escrito no documento."""
    if value is None:
        return []
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        d, m, y = value.day, value.month, value.year
        mes = _MESES[m - 1]
        return [f"{d:02d}/{m:02d}/{y}", f"{d}/{m}/{y}", f"{d:02d}/{m}/{y}", f"{d}/{m:02d}/{y}", value.isoformat(),
                f"{d:02d}.{m:02d}.{y}", f"{d:02d}-{m:02d}-{y}", f"{d} de {mes} de {y}", f"{d:02d} de {mes} de {y}",
                f"{d}o de {mes} de {y}"]
    if isinstance(value, (Decimal, int, float)) and not isinstance(value, bool):
        number = Decimal(str(value))
        inteiro = int(number)
        centavos = abs(number - inteiro).quantize(Decimal("0.01"))
        milhar = f"{inteiro:,}".replace(",", ".")
        cents = f"{int(centavos * 100):02d}"
        variants = [f"{milhar},{cents}", f"{inteiro},{cents}", f"{number:f}", str(inteiro) if centavos == 0 else f"{number:f}"]
        if centavos == 0:
            variants.append(milhar)
        return [normalize(v) for v in dict.fromkeys(variants)]
    return [normalize(value)]


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def value_in_text(value: Any, text: Any) -> bool:
    """O valor (em qualquer de suas grafias) aparece literalmente no texto."""
    haystack = normalize(text)
    if not haystack:
        return False
    if isinstance(value, (date, datetime, Decimal, int, float)) and not isinstance(value, bool):
        if any(contains_phrase(haystack, v) for v in value_variants(value)):
            return True
        if isinstance(value, (Decimal, int, float)):
            target = Decimal(str(value)).normalize()
            return target in numbers_in(text)
        return False
    norm_value = _strip_edges(normalize(value))
    if not norm_value:
        return False
    if contains_phrase(haystack, norm_value):
        return True
    # Identificadores numéricos ("99.901", "0001234-56.2020.5.02.0001"): compara a sequência de dígitos.
    if re.fullmatch(r"[\d\.\-/ ]+", norm_value) and len(_digits(norm_value)) >= 3:
        return any(_digits(token) == _digits(norm_value) for token in re.findall(r"\d[\d\.\-/]*\d", haystack))
    return False


def value_window(value: Any, content: Any, radius: int = 160) -> str:
    """Trecho literal do documento ao redor da primeira ocorrência do valor (para quando o modelo não informou)."""
    raw = str(content or "")
    lines = [line.strip() for line in re.split(r"\n+", raw) if line.strip()]
    for line in lines:
        if value_in_text(value, line):
            return line[: 2 * radius]
    return ""
