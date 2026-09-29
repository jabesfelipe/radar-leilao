"""SignalEngine — detecção de sinais/evidências jurídicas (JUR-04).

Regras fundamentais (SPEC §35-36, §39):
- O mecanismo DETECTA EVIDÊNCIAS; não emite parecer nem decisão jurídica.
- Não transforma "movimentação contendo penhora" em "imóvel penhorado". Quando
  há evidência patrimonial (ex.: penhora), emite um sinal do tipo
  PROPERTY_<X>_EVIDENCE deixando claro que a confirmação de que a medida recai
  sobre um imóvel específico exige validação registral/documental.
- Homônimos: quando não há CPF/CNPJ suficiente para confirmar identidade, emite
  HOMONYM_POSSIBLE (evidência de possível homônimo, não confirmação).

Não persiste nada por si só (a persistência é do orquestrador/store) e não
depende de LLM/RAG.
"""
from __future__ import annotations

from ..enums import SignalCategory, SignalEvidenceType, SignalSeverity
from ..models import Process, SearchRequest, Signal
from .rules import SignalRule, default_signal_rules, normalize_text

# Sinais patrimoniais que podem sugerir constrição sobre bens; para eles emitimos
# TAMBÉM uma evidência explícita PROPERTY_<X>_EVIDENCE (SPEC §35).
_PROPERTY_EVIDENCE_FOR = {
    "PENHORA": "PROPERTY_PENHORA_EVIDENCE",
    "ARRESTO": "PROPERTY_ARRESTO_EVIDENCE",
    "INDISPONIBILIDADE": "PROPERTY_INDISPONIBILIDADE_EVIDENCE",
    "HIPOTECA": "PROPERTY_HIPOTECA_EVIDENCE",
}

_PROPERTY_EVIDENCE_TEXT = (
    "Foi identificada evidência processual relacionada a {termo}. A confirmação de "
    "que a medida recai sobre determinado imóvel exige validação registral e documental."
)

HOMONYM_SIGNAL_CODE = "HOMONYM_POSSIBLE"
HOMONYM_TEXT = (
    "Foi localizado processo com nome semelhante, mas não há evidência suficiente "
    "(CPF/CNPJ) para confirmar que pertence à pessoa pesquisada."
)


def _only_digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _names_match(searched: str, party_name: str) -> bool:
    """Compara nome pesquisado e nome da parte de forma robusta (caixa/acentos já
    normalizados por normalize_text). Considera correspondente quando os nomes são
    iguais ou quando o conjunto de tokens de um contém o do outro (ex.: nome
    parcial vs. nome completo). Não confirma identidade — é só correspondência de
    nome para fins de possível homônimo."""
    a = normalize_text(searched)
    b = normalize_text(party_name)
    if not a or not b:
        return False
    if a == b:
        return True
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        # Com um único token o risco de correspondência espúria é alto: exige
        # igualdade exata (já tratada acima).
        return False
    return tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a)


class SignalEngine:
    """Motor puro de sinais: recebe processos normalizados e devolve sinais.

    ``rules`` é injetável (facilita testes e versões alternativas); por padrão usa
    o catálogo versionado do arquivo.
    """

    def __init__(self, rules: list[SignalRule] | tuple[SignalRule, ...] | None = None) -> None:
        self._rules = tuple(rules) if rules is not None else default_signal_rules()

    def analyze_process(self, process: Process, request: SearchRequest | None = None) -> list[Signal]:
        signals: list[Signal] = []

        # 1) Sinais por correspondência de termos em movimentos, assuntos e classe.
        matched_codes: set[str] = set()
        for movement in process.movements:
            texto = movement.description or ""
            signals.extend(self._match(process, texto, SignalEvidenceType.MOVEMENT, movement.source_identifier, matched_codes))
        for subject in process.subjects:
            texto = subject.name or ""
            signals.extend(self._match(process, texto, SignalEvidenceType.SUBJECT, subject.source_identifier, matched_codes))
        if process.class_name:
            signals.extend(self._match(process, process.class_name, SignalEvidenceType.CLASS, None, matched_codes))

        # 2) Evidência processo×imóvel: para sinais patrimoniais, emite um sinal
        #    PROPERTY_<X>_EVIDENCE (evidência, nunca "imóvel penhorado").
        for signal in list(signals):
            prop_code = _PROPERTY_EVIDENCE_FOR.get(signal.signal_code)
            if prop_code is None:
                continue
            signals.append(
                Signal(
                    signal_code=prop_code,
                    category=SignalCategory.PATRIMONIAL,
                    severity=signal.severity,
                    confidence=round(max(0.0, signal.confidence - 0.1), 4),
                    evidence_text=_PROPERTY_EVIDENCE_TEXT.format(termo=signal.signal_code.lower()),
                    evidence_type=signal.evidence_type,
                    process_number=process.process_number,
                    tribunal=process.tribunal,
                    source_identifier=signal.source_identifier,
                    rule_version=signal.rule_version,
                )
            )

        # 3) Homônimo: se a pesquisa não tinha CPF/CNPJ e as partes do processo não
        #    trazem documento que confirme identidade, sinaliza possível homônimo.
        if self._is_possible_homonym(process, request):
            signals.append(
                Signal(
                    signal_code=HOMONYM_SIGNAL_CODE,
                    category=SignalCategory.IDENTIDADE,
                    severity=SignalSeverity.LOW,
                    confidence=0.5,
                    evidence_text=HOMONYM_TEXT,
                    evidence_type=SignalEvidenceType.PARTY,
                    process_number=process.process_number,
                    tribunal=process.tribunal,
                )
            )

        return signals

    def analyze(self, processes: list[Process], request: SearchRequest | None = None) -> list[Signal]:
        result: list[Signal] = []
        for process in processes:
            result.extend(self.analyze_process(process, request))
        return result

    # ------------------------------------------------------------------
    def _match(self, process: Process, texto: str, evidence_type: SignalEvidenceType, source_identifier: str | None, matched_codes: set[str]) -> list[Signal]:
        normalized = normalize_text(texto)
        if not normalized:
            return []
        found: list[Signal] = []
        for rule in self._rules:
            if not rule.matches(normalized):
                continue
            # Evita duplicar o MESMO signal_code para o mesmo processo.
            if rule.signal_code in matched_codes:
                continue
            matched_codes.add(rule.signal_code)
            found.append(
                Signal(
                    signal_code=rule.signal_code,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.base_confidence,
                    evidence_text=texto.strip(),
                    evidence_type=evidence_type,
                    process_number=process.process_number,
                    tribunal=process.tribunal,
                    source_identifier=source_identifier,
                    rule_version=rule.version,
                )
            )
        return found

    @staticmethod
    def _is_possible_homonym(process: Process, request: SearchRequest | None) -> bool:
        if request is None:
            return False
        pesquisou_documento = bool(_only_digits(request.cpf) or _only_digits(request.cnpj))
        pesquisou_nome = bool((request.name or "").strip())
        if pesquisou_documento or not pesquisou_nome:
            # Com documento não é homônimo por definição; sem nome não aplica.
            return False

        # Só avalia possível homônimo se houver uma PARTE cujo nome corresponde ao
        # nome pesquisado (comparação normalizada por caixa/acento). Sem parte
        # correspondente, não há homônimo a sinalizar.
        partes_correspondentes = [p for p in process.parties if _names_match(request.name, p.name)]
        if not partes_correspondentes:
            return False

        # É possível homônimo quando ALGUMA parte correspondente NÃO traz CPF/CNPJ
        # que confirme identidade. O documento é avaliado NA PRÓPRIA parte
        # correspondente — documento de partes não relacionadas não suprime o sinal.
        return any(not _only_digits(p.document) for p in partes_correspondentes)
