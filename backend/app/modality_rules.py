"""Ruleset declarativo de MODALIDADES de aquisição (Onda 2 — F1).

Fonte única da verdade do vocabulário de modalidades e de como as regras variam por
modalidade, no mesmo espírito declarativo de ``workflow_rules.py``/``checklist.py``:
dados + funções puras, sem I/O e sem LLM. A classificação é determinística e só
confirma com evidência; sem evidência permanece ``INDEFINIDO`` (e o hard stop
``MODALIDADE_INDEFINIDA`` do workflow continua ativo).

Preservação: os 27 ``canonical_key`` do Checklist Mestre NÃO são alterados. A
aplicabilidade por modalidade é um METADADO aditivo (nunca renomeia/remove chave).
Compatibilidade com o legado: ``INDEFINIDO`` mantém os 27 itens aplicáveis (idêntico
ao comportamento atual), de modo que oportunidades legadas/sem modalidade não mudam.
"""
from __future__ import annotations

MODALITY_RULESET_VERSION = "modality-v1"

# --- Vocabulário canônico (SPEC/PLAN-WAVE-2 §2) -------------------------------
# LICITACAO é decisão de negócio em aberto (§8 do plano) e NÃO entra nesta onda.
MODALITY_EXTRAJUDICIAL_AF = "EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA"
MODALITY_EXTRAJUDICIAL_OUTRA = "EXTRAJUDICIAL_OUTRA_GARANTIA"
MODALITY_JUDICIAL = "JUDICIAL"
MODALITY_VENDA_DIRETA = "VENDA_DIRETA"
MODALITY_INDEFINIDO = "INDEFINIDO"

MODALITIES: tuple[str, ...] = (
    MODALITY_EXTRAJUDICIAL_AF,
    MODALITY_EXTRAJUDICIAL_OUTRA,
    MODALITY_JUDICIAL,
    MODALITY_VENDA_DIRETA,
    MODALITY_INDEFINIDO,
)

MODALITY_CATALOG: dict[str, dict[str, str]] = {
    MODALITY_EXTRAJUDICIAL_AF: {
        "name": "Extrajudicial — Alienação Fiduciária (Lei 9.514/97)",
        "description": "Execução extrajudicial com consolidação da propriedade e leilão do art. 27. Foco do produto.",
        "track": "EXTRAJUDICIAL",
        "status": "ATIVO",
    },
    MODALITY_EXTRAJUDICIAL_OUTRA: {
        "name": "Extrajudicial — Outra garantia",
        "description": "Outras execuções/vendas extrajudiciais com garantia diversa da alienação fiduciária.",
        "track": "EXTRAJUDICIAL",
        "status": "ATIVO",
    },
    MODALITY_JUDICIAL: {
        "name": "Judicial (CPC)",
        "description": "Arrematação em hasta pública judicial, regida pelo CPC. Rito e riscos próprios.",
        "track": "JUDICIAL",
        "status": "ATIVO",
    },
    MODALITY_VENDA_DIRETA: {
        "name": "Venda direta",
        "description": "Venda direta pelo credor/proprietário, sem leilão.",
        "track": "DIRETA",
        "status": "ATIVO",
    },
    MODALITY_INDEFINIDO: {
        "name": "Indefinida",
        "description": "Modalidade ainda não evidenciada (estado inicial da triagem).",
        "track": "TRIAGEM",
        "status": "ATIVO",
    },
}

# --- Aplicabilidade de checklist por modalidade — SPEC/MATRIZ-CHECKLIST-MODALIDADE
# Estados: APLICAVEL (padrão), CONDICIONAL, NAO_APLICAVEL. Só listamos as EXCEÇÕES;
# qualquer chave não listada para uma modalidade é APLICAVEL. INDEFINIDO = tudo
# aplicável (comportamento legado preservado). Os 27 keys permanecem intactos.
APPLICABILITY_APLICAVEL = "APLICAVEL"
APPLICABILITY_CONDICIONAL = "CONDICIONAL"
APPLICABILITY_NAO_APLICAVEL = "NAO_APLICAVEL"

# Itens específicos do rito EXTRAJUDICIAL de alienação fiduciária (Lei 9.514/97):
# não se aplicam ao judicial nem à venda direta.
_AF_ESPECIFICOS = (
    "INTIMACAO_PESSOAL", "INTIMACAO_EDITAL", "NOTIFICACAO_DOIS_LEILOES",
    "QUITACAO_80", "GARANTIA_DIVIDA_TERCEIRO", "CONSOLIDACAO_REGISTRADA",
    "LEILOES_NEGATIVOS_AVERBADOS", "PENHORA_INDISPONIBILIDADE",
)
# "Preço vil" (<50% da avaliação) é sinal do JUDICIAL; no extrajudicial é só um gatilho
# de atenção, não um piso legal (REVISAO-ANOTACOES-LEILAO §5).
_PRECO_VIL = "LANCE_MENOR_50_AVALIACAO"

# Mapa: modalidade -> {canonical_key -> estado de aplicabilidade} (apenas exceções).
CHECKLIST_APPLICABILITY: dict[str, dict[str, str]] = {
    MODALITY_EXTRAJUDICIAL_AF: {
        _PRECO_VIL: APPLICABILITY_CONDICIONAL,  # atenção, não piso legal
    },
    MODALITY_EXTRAJUDICIAL_OUTRA: {
        **{k: APPLICABILITY_CONDICIONAL for k in ("QUITACAO_80", "NOTIFICACAO_DOIS_LEILOES")},
        _PRECO_VIL: APPLICABILITY_CONDICIONAL,
    },
    MODALITY_JUDICIAL: {
        **{k: APPLICABILITY_NAO_APLICAVEL for k in _AF_ESPECIFICOS},
        _PRECO_VIL: APPLICABILITY_APLICAVEL,  # preço vil é relevante no judicial
    },
    MODALITY_VENDA_DIRETA: {
        **{k: APPLICABILITY_NAO_APLICAVEL for k in _AF_ESPECIFICOS},
        _PRECO_VIL: APPLICABILITY_NAO_APLICAVEL,
        "EDITAL_LIDO": APPLICABILITY_NAO_APLICAVEL,  # venda direta não tem edital
        "LEILOES_NEGATIVOS_AVERBADOS": APPLICABILITY_NAO_APLICAVEL,
    },
    MODALITY_INDEFINIDO: {},  # tudo aplicável (legado)
}

# --- Hard stops por modalidade (quais do catálogo do workflow fazem sentido) ---
# Alguns hard stops do workflow só se aplicam ao extrajudicial de AF. Em judicial/
# venda direta eles não devem bloquear (não há consolidação/intimação de mora).
AF_ONLY_HARD_STOPS = ("CONSOLIDACAO_NAO_REGISTRADA", "INTIMACAO_MORA_AUSENTE")

MODALITY_SUPPRESSED_HARD_STOPS: dict[str, tuple[str, ...]] = {
    MODALITY_JUDICIAL: AF_ONLY_HARD_STOPS,
    MODALITY_VENDA_DIRETA: AF_ONLY_HARD_STOPS,
    MODALITY_EXTRAJUDICIAL_OUTRA: (),      # garantia diversa: mantém (depende de evidência)
    MODALITY_EXTRAJUDICIAL_AF: (),
    MODALITY_INDEFINIDO: (),
}

# --- Documentos exigidos por modalidade (declaração; sem automação nesta onda) --
_DOCS_COMUNS = ("EDITAL", "MATRICULA")
MODALITY_REQUIRED_DOCS: dict[str, tuple[str, ...]] = {
    MODALITY_EXTRAJUDICIAL_AF: _DOCS_COMUNS + ("CONTRATO_ALIENACAO_FIDUCIARIA", "CONSOLIDACAO", "INTIMACAO_MORA"),
    MODALITY_EXTRAJUDICIAL_OUTRA: _DOCS_COMUNS + ("CONTRATO_GARANTIA",),
    MODALITY_JUDICIAL: _DOCS_COMUNS + ("AUTO_ARREMATACAO", "PROCESSO_JUDICIAL"),
    MODALITY_VENDA_DIRETA: ("MATRICULA", "PROPOSTA_VENDA"),
    MODALITY_INDEFINIDO: (),
}


# ---------------------------------------------------------------------------
# Helpers puros
# ---------------------------------------------------------------------------

def is_modality(code: str) -> bool:
    return code in MODALITIES


def normalize(code: str | None) -> str:
    c = str(code or "").strip().upper()
    return c if c in MODALITIES else MODALITY_INDEFINIDO


def checklist_applicability(modality: str, canonical_key: str) -> str:
    """Estado de aplicabilidade de um canonical_key sob a modalidade. Default APLICAVEL."""
    overrides = CHECKLIST_APPLICABILITY.get(normalize(modality), {})
    return overrides.get(canonical_key, APPLICABILITY_APLICAVEL)


def applicable_checklist_keys(modality: str, all_keys: tuple[str, ...]) -> tuple[str, ...]:
    """Subconjunto de ``all_keys`` cuja aplicabilidade NÃO é NAO_APLICAVEL para a
    modalidade. Preserva o catálogo (não remove chaves; apenas filtra aplicabilidade)."""
    mod = normalize(modality)
    return tuple(k for k in all_keys if checklist_applicability(mod, k) != APPLICABILITY_NAO_APLICAVEL)


def suppressed_hard_stops(modality: str) -> tuple[str, ...]:
    """Hard stops do catálogo do workflow que NÃO se aplicam à modalidade."""
    return MODALITY_SUPPRESSED_HARD_STOPS.get(normalize(modality), ())


def required_docs(modality: str) -> tuple[str, ...]:
    return MODALITY_REQUIRED_DOCS.get(normalize(modality), ())


# ---------------------------------------------------------------------------
# Classificação determinística (evidence-gated)
# ---------------------------------------------------------------------------

# Palavras-chave (normalizadas, sem acento) que indicam cada modalidade. Determinístico.
_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (MODALITY_EXTRAJUDICIAL_AF, ("ALIENACAO FIDUCIARIA", "9.514", "9514", "CONSOLIDACAO DA PROPRIEDADE", "ART. 27", "ARTIGO 27", "LEI 9.514")),
    (MODALITY_JUDICIAL, ("JUDICIAL", "HASTA PUBLICA", "CPC", "EXECUCAO FISCAL", "PENHORA", "PROCESSO N", "VARA ")),
    (MODALITY_VENDA_DIRETA, ("VENDA DIRETA", "VENDA ONLINE", "SEM LEILAO", "PROPOSTA DE COMPRA")),
    (MODALITY_EXTRAJUDICIAL_OUTRA, ("EXTRAJUDICIAL", "GARANTIA")),
)


def _strip_accents(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def classify_modality(*, signals_text: str | None, origin: str | None = None, has_evidence: bool = False) -> dict:
    """Propõe a modalidade a partir de sinais textuais objetivos (edital/origem).
    Determinístico, sem LLM. **Só confirma com evidência** (``has_evidence``); sem
    evidência, retorna a hipótese mas mantém ``modality=INDEFINIDO`` + necessidade de
    revisão manual. Retorna modalidade, grau de confiança, evidências e justificativa."""
    haystack = _strip_accents(f"{signals_text or ''} {origin or ''}").upper()
    matched: list[tuple[str, list[str]]] = []
    for modality, keywords in _SIGNALS:
        hits = [kw for kw in keywords if _strip_accents(kw).upper() in haystack]
        if hits:
            matched.append((modality, hits))

    if not matched:
        return {
            "modality": MODALITY_INDEFINIDO, "proposed": MODALITY_INDEFINIDO,
            "confidence": "BAIXA", "evidences": [], "needs_manual_review": True,
            "justification": "Nenhum sinal objetivo de modalidade encontrado.",
            "ruleset_version": MODALITY_RULESET_VERSION,
        }

    # Precedência: AF > JUDICIAL > VENDA_DIRETA > EXTRAJUDICIAL_OUTRA (ordem de _SIGNALS).
    proposed, hits = matched[0]
    multiple = len({m for m, _ in matched}) > 1
    confidence = "ALTA" if (has_evidence and not multiple) else ("MEDIA" if has_evidence else "BAIXA")
    confirmed = has_evidence and not multiple
    return {
        "modality": proposed if confirmed else MODALITY_INDEFINIDO,
        "proposed": proposed,
        "confidence": confidence,
        "evidences": hits,
        "needs_manual_review": not confirmed,
        "justification": (
            f"Sinais {hits} indicam {proposed}."
            + ("" if has_evidence else " Sem evidência vinculada: permanece INDEFINIDO até confirmação.")
            + (" Múltiplos sinais divergentes: requer revisão." if multiple else "")
        ),
        "ruleset_version": MODALITY_RULESET_VERSION,
    }
