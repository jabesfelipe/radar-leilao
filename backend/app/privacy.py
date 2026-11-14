"""Minimização de dados pessoais antes de qualquer envio a provider externo (OpenAI) e nos logs.

Módulo folha (sem imports da aplicação no topo) para poder ser usado pelo gateway de LLM,
pelo filtro de logging e pelos agentes sem ciclos de importação.

O que faz (determinístico, sem IA):
- Mascara identificadores pessoais por padrão (CPF, RG, e-mail, telefone, dados bancários).
- Pseudonimiza as partes de processos que sejam pessoas físicas (``[PARTE ATIVA]``); empresas,
  bancos, condomínios e entes públicos permanecem, pois são necessários à análise jurídica.

O que NÃO faz (risco residual documentado em AUDITORIA-LLM.md): reconhecer NOMES de pessoas
escritos livremente dentro do texto de documentos (matrícula, edital). Isso exigiria NER e
não é confiável por regex. CNPJ não é mascarado (identifica credores/pessoas jurídicas).

Desligar apenas por decisão explícita: ``LLM_REDACT_PII=false``.
"""
from __future__ import annotations

import re
from typing import Any

# Ordem importa: padrões rotulados antes dos genéricos.
_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # CPF rotulado (aceita com ou sem pontuação): "CPF: 123.456.789-09", "CPF/MF nº 12345678909".
    (re.compile(r"(?i)\bcpf(?:/mf)?\s*(?:n[ºo.°]*\s*)?[:\-]?\s*\d[\d.\-/ ]{8,16}\d"), "[CPF]"),
    # CPF formatado em qualquer contexto.
    (re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)"), "[CPF]"),
    # RG / carteira de identidade rotulado.
    (re.compile(r"(?i)\b(?:rg|c\.?i\.?|carteira de identidade|identidade)\s*(?:n[ºo.°]*\s*)?[:\-]?\s*[\dxX][\dxX.\-]{5,14}"), "[RG]"),
    # E-mail.
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    # Telefone: com DDD entre parênteses, +55, ou rotulado (tel/fone/celular/whatsapp).
    (re.compile(r"(?i)\b(?:tel(?:efone)?|fone|celular|cel|whats(?:app)?)\.?\s*[:\-]?\s*[+\d()][\d()\-\s+]{7,18}\d"), "[TELEFONE]"),
    (re.compile(r"\(\d{2}\)\s?9?\d{4}[-\s]?\d{4}(?!\d)"), "[TELEFONE]"),
    (re.compile(r"\+55\s?\d{2}\s?9?\d{4}[-\s]?\d{4}(?!\d)"), "[TELEFONE]"),
    # Dados bancários rotulados (agência/conta).
    (re.compile(r"(?i)\b(?:ag[eê]ncia|ag\.|conta(?:\s+corrente|\s+poupan[cç]a)?|c/c)\s*(?:n[ºo.°]*\s*)?[:\-]?\s*\d[\d.\-]{2,14}\d"), "[DADO BANCÁRIO]"),
)

# Marcadores de pessoa jurídica / ente público: permanecem identificados.
_ENTITY_MARKERS = re.compile(
    r"(?i)\b(ltda|s\.?\s?a\.?|s/a|eireli|epp|me|banco|caixa|condom[ií]nio|associa[cç][aã]o|munic[ií]pio|"
    r"prefeitura|estado|uni[aã]o|fazenda|cooperativa|fundo|cia|companhia|empresa|institui[cç][aã]o|"
    r"cart[oó]rio|ofício|oficio|tribunal|minist[eé]rio|defensoria|procuradoria|incorporadora|construtora|"
    r"imobili[aá]ria|financeira|seguradora|leiloeiro|leil[oõ]es)\b"
)


import unicodedata
from dataclasses import dataclass, field

# Letras com variantes acentuadas: o casamento de nomes ignora acento e caixa.
_ACCENTS = {
    "a": "aàáâãäå", "e": "eèéêë", "i": "iìíîï", "o": "oòóôõö", "u": "uùúûü", "c": "cç", "n": "nñ",
}
_PARTICLES = {"da", "de", "do", "das", "dos", "e"}
_WORD = r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç'\-]+"
# Rótulos que, nos documentos, precedem o nome de uma PESSOA e dizem qual é o seu PAPEL jurídico.
_LABEL_ROLES: tuple[tuple[str, str], ...] = (
    (r"propriet[aá]ri[oa]s?", "PROPRIETARIO"), (r"titular(?:es)?", "TITULAR"), (r"fiduciante", "FIDUCIANTE"),
    (r"devedor(?:a|es)?", "DEVEDOR"), (r"executad[oa]s?", "EXECUTADO"), (r"r[ée]u", "REU"),
    (r"adquirente", "ADQUIRENTE"), (r"comprador(?:a|es)?", "COMPRADOR"), (r"vendedor(?:a|es)?", "VENDEDOR"),
    (r"outorgante", "OUTORGANTE"), (r"outorgad[oa]", "OUTORGADO"), (r"requerente", "REQUERENTE"),
    (r"inventariante", "INVENTARIANTE"), (r"usufrutu[aá]ri[oa]", "USUFRUTUARIO"), (r"c[oô]njuge", "CONJUGE"),
    (r"casad[oa] com", "CONJUGE"), (r"representad[oa] por", "REPRESENTANTE"), (r"advogad[oa]", "ADVOGADO"),
    (r"ocupante", "OCUPANTE"), (r"locat[aá]ri[oa]", "LOCATARIO"), (r"inquilin[oa]", "LOCATARIO"),
)
_LABELED_NAME = re.compile(
    r"(?i:\b(?P<label>" + "|".join(label for label, _ in _LABEL_ROLES) + r")\b)\s*[:\-–]?\s*"
    r"(?P<name>" + _WORD + r"(?:\s+(?:(?i:d[aeo]s?|e)\s+)?" + _WORD + r"){1,6})"
)


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _name_regex(name: str) -> re.Pattern[str]:
    """Regex que casa o nome ignorando caixa, acentos e variações de espaçamento."""
    parts: list[str] = []
    for token in name.split():
        chars = []
        for ch in token:
            base = _strip_accents(ch).lower()
            variants = _ACCENTS.get(base)
            chars.append(f"[{variants}{variants.upper()}]" if variants else re.escape(ch))
        parts.append("".join(chars))
    return re.compile(r"(?<![\wÀ-ÿ])" + r"\s+".join(parts) + r"(?![\wÀ-ÿ])", re.IGNORECASE)


def looks_like_entity(name: str) -> bool:
    return bool(_ENTITY_MARKERS.search(name or ""))


@dataclass
class NameAliaser:
    """Pseudonimização REVERSÍVEL (só localmente) de nomes de PESSOAS FÍSICAS conhecidos.

    O nome é trocado por um apelido que preserva o PAPEL jurídico (``[TITULAR]``, ``[PARTE PASSIVA 1]``,
    ``[PROPRIETARIO 2]``), de modo que a análise continua possível ("o titular constituiu alienação
    fiduciária…"). O mapa apelido→nome nunca sai do servidor: serve para restaurar as respostas do
    LLM antes de gravá-las no banco.

    LIMITES (documentados em AUDITORIA-LLM.md): só troca nomes **conhecidos** — os cadastrados no
    sistema (titular da matrícula, polos de processos, ocupantes) e os que aparecem logo após um
    rótulo jurídico ("Proprietário: …", "Executado: …"). Pessoas citadas sem rótulo e referências
    parciais ("o Sr. Silva") **não** são detectadas: não há reconhecimento de entidades (NER).
    """
    enabled: bool = True
    _entries: list[tuple[str, str, re.Pattern[str]]] = field(default_factory=list)  # (nome, apelido, regex)
    _counters: dict[str, int] = field(default_factory=dict)

    def _known(self, name: str) -> str | None:
        key = _strip_accents(name).lower()
        for existing, alias, _ in self._entries:
            if _strip_accents(existing).lower() == key:
                return alias
        return None

    def alias_for(self, name: str | None, role: str, *, numbered: bool = True) -> str | None:
        """Registra (se pessoa física) e devolve o apelido do nome; empresas/entes públicos voltam intactos."""
        if not name or not self.enabled:
            return name
        clean = " ".join(str(name).split())
        if len(clean) < 5 or looks_like_entity(clean):
            return redact_pii(clean)
        known = self._known(clean)
        if known:
            return known
        count = self._counters.get(role, 0) + 1
        self._counters[role] = count
        alias = f"[{role} {count}]" if numbered and (count > 1 or role not in {"TITULAR"}) else f"[{role}]"
        self._entries.append((clean, alias, _name_regex(clean)))
        self._entries.sort(key=lambda e: len(e[0]), reverse=True)  # nomes mais longos primeiro
        return alias

    def learn_from_text(self, text: str | None) -> int:
        """Detecta nomes logo após rótulos jurídicos e os registra com o papel do rótulo."""
        if not text or not self.enabled:
            return 0
        found = 0
        for match in _LABELED_NAME.finditer(text):
            label = match.group("label").lower()
            role = next((r for pattern, r in _LABEL_ROLES if re.fullmatch(pattern, label, re.IGNORECASE)), "PESSOA")
            name = match.group("name")
            # corta partículas penduradas no fim ("Fulano de Tal e")
            words = name.split()
            while words and words[-1].lower() in _PARTICLES:
                words.pop()
            if len(words) < 2:
                continue
            before = len(self._entries)
            self.alias_for(" ".join(words), role)
            found += len(self._entries) - before
        return found

    def apply(self, text: Any) -> Any:
        """Troca os nomes conhecidos pelos apelidos e aplica o mascaramento de identificadores."""
        if not isinstance(text, str) or not text or not self.enabled:
            return redact_pii(text) if isinstance(text, str) else text
        out = text
        for _, alias, regex in self._entries:
            out = regex.sub(alias, out)
        return redact_pii(out)

    def restore(self, text: Any) -> Any:
        """Troca os apelidos de volta pelos nomes (uso LOCAL, para gravar respostas do LLM no banco)."""
        if not isinstance(text, str) or not text or not self._entries:
            return text
        out = text
        for name, alias, _ in self._entries:
            out = out.replace(alias, name)
        return out

    def restore_obj(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.restore(value)
        if isinstance(value, list):
            return [self.restore_obj(v) for v in value]
        if isinstance(value, dict):
            return {k: self.restore_obj(v) for k, v in value.items()}
        return value

    @property
    def names(self) -> list[str]:
        return [name for name, _, _ in self._entries]


def pii_enabled() -> bool:
    from .config import settings
    return bool(getattr(settings, "llm_redact_pii", True))


def redact_pii(text: Any, *, force: bool = False) -> Any:
    """Mascara identificadores pessoais em ``text`` (não altera não-strings)."""
    if not isinstance(text, str) or not text:
        return text
    if not force and not pii_enabled():
        return text
    out = text
    for pattern, replacement in _PII_PATTERNS:
        out = pattern.sub(replacement, out)
    return _BARE_CPF.sub(lambda m: "[CPF]" if _valid_cpf(m.group(0)) else m.group(0), out)


# CPF só com dígitos e sem rótulo (v1.0.4): mascarado apenas se os dígitos verificadores forem válidos, para não
# atingir outros números de 11 dígitos (protocolos, matrícula, inscrição imobiliária) usados na análise.
_BARE_CPF = re.compile(r"(?<![\d/\-])(?<!\d\.)\d{11}(?![\d/\-])(?!\.\d)")


def _valid_cpf(digits: str) -> bool:
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    for size in (9, 10):
        total = sum(int(d) * w for d, w in zip(digits[:size], range(size + 1, 1, -1)))
        check = (total * 10) % 11 % 10
        if check != int(digits[size]):
            return False
    return True


def sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cópia das mensagens do chat com PII mascarada (o original não é alterado)."""
    safe: list[dict[str, Any]] = []
    for message in messages:
        content = message.get("content")
        safe.append({**message, "content": redact_pii(content)} if isinstance(content, str) else dict(message))
    return safe


def sanitize_texts(texts: list[str]) -> list[str]:
    return [redact_pii(t) for t in texts]


def minimize_party(name: str | None, role: str) -> str | None:
    """Pseudonimiza parte de processo que pareça pessoa física.

    ``role`` ex.: ``"PARTE ATIVA"``. Empresas/entes públicos (marcadores acima) são mantidos.
    """
    if not name:
        return name
    if not pii_enabled():
        return name
    if _ENTITY_MARKERS.search(name):
        return redact_pii(name)
    return f"[{role}]"
