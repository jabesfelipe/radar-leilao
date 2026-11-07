"""Ruleset declarativo do Workflow (Ciclo 2 — Onda 1, fundação B1).

Define, de forma **declarativa e versionada**, o vocabulário e as regras da máquina
de estados F0–F13: fases, estados de fase, tipos de transição, matriz de transições
válidas e catálogo de hard stops. Análogo a ``checklist.py``/``legal_catalog.py``.

Não contém lógica de avaliação (isso é do ``workflow_engine.py``, puro) nem efeitos
colaterais; é apenas dado. Base: ``SPEC-WORKFLOW-ENGINE.md`` (§2–§6, §10).

Versionamento (ADR-006): cada transição/decisão grava ``WORKFLOW_RULESET_VERSION``.
Mudança de regra = novo PR revisável; transições passadas não são reescritas.
"""
from __future__ import annotations

WORKFLOW_RULESET_VERSION = "workflow-v1"

# --- Fases (F0–F13) — SPEC §2 -------------------------------------------------
PHASES: tuple[str, ...] = (
    "F0_INTAKE",
    "F1_TRIAGEM",
    "F2_DOCUMENTOS",
    "F3_JURIDICO_REGISTRAL",
    "F4_FISCAL_OPERACIONAL",
    "F5_LOCALIZACAO_INSPECAO",
    "F6_OCUPACAO_POSSE",
    "F7_VIABILIDADE_FINANCEIRA",
    "F8_COMITE_DECISAO",
    "F9_LANCE_PAGAMENTO",
    "F10_TRANSFERENCIA_REGISTRO",
    "F11_POSSE_REGULARIZACAO",
    "F12_EXPLORACAO_SAIDA",
    "F13_ENCERRAMENTO",
)

# Fases de due diligence paralelizáveis (SPEC §2): entre si e convergem no comitê.
PARALLEL_PHASES: frozenset[str] = frozenset(
    {"F3_JURIDICO_REGISTRAL", "F4_FISCAL_OPERACIONAL", "F5_LOCALIZACAO_INSPECAO",
     "F6_OCUPACAO_POSSE", "F7_VIABILIDADE_FINANCEIRA"}
)

TERMINAL_PHASE = "F13_ENCERRAMENTO"

# --- Estados de fase — SPEC §3 ------------------------------------------------
PHASE_STATES: tuple[str, ...] = (
    "NAO_INICIADA",
    "EM_ANDAMENTO",
    "PENDENTE_EVIDENCIA",
    "EM_REVISAO",
    "CONCLUIDA",
    "CONCLUIDA_COM_RESSALVA",
    "BLOQUEADA",
    "NAO_APLICAVEL",
    "REABERTA",
)

# Estados a partir dos quais o gate de saída pode estar satisfeito (SPEC §4.1/§5).
PHASE_STATES_SATISFEITOS: frozenset[str] = frozenset({"CONCLUIDA", "CONCLUIDA_COM_RESSALVA", "NAO_APLICAVEL"})

# --- Tipos de transição — SPEC §4 --------------------------------------------
TRANSITION_TYPES: tuple[str, ...] = (
    "AVANCO",
    "RETROCESSO",
    "REABERTURA",
    "DESCARTE",
    "ENCERRAMENTO",
    "PERDA",
    "DECISAO",
)

# Resultado da avaliação de uma transição.
TRANSITION_RESULTS: tuple[str, ...] = ("PERMITIDA", "BLOQUEADA")

# Decisões humanas de comitê (F8) — SPEC §8.
DECISIONS: tuple[str, ...] = ("APROVADA", "REPROVADA", "ADIADA")

# Status de alto nível da Opportunity — SPEC-OPPORTUNITY-DOMAIN §4.
OPPORTUNITY_STATUSES: tuple[str, ...] = (
    "EM_PROSPECCAO",
    "EM_ANALISE",
    "EM_DECISAO",
    "APROVADA",
    "ADQUIRIDA",
    "ENCERRADA",
    "DESCARTADA",
    "PERDIDA",
)

# Transições especiais permitidas a partir de (quase) qualquer fase (SPEC §4.3/§4.4).
# DESCARTE é possível a qualquer momento (exige justificativa — validado no engine).
DESCARTE_ALLOWED_FROM: frozenset[str] = frozenset(set(PHASES) - {TERMINAL_PHASE})

# --- Matriz de AVANÇO (origem -> destinos válidos por avanço) — SPEC §4.4 ----
# Apenas transições do tipo AVANCO. DESCARTE/PERDA/REABERTURA/DECISAO são regras
# transversais tratadas no engine (não entram nesta matriz de avanço sequencial).
FORWARD_TRANSITIONS: dict[str, frozenset[str]] = {
    "F0_INTAKE": frozenset({"F1_TRIAGEM"}),
    "F1_TRIAGEM": frozenset({"F2_DOCUMENTOS"}),
    "F2_DOCUMENTOS": frozenset(PARALLEL_PHASES),
    # F3..F7 convergem no comitê e podem transitar entre si (due diligence paralela).
    "F3_JURIDICO_REGISTRAL": frozenset(PARALLEL_PHASES | {"F8_COMITE_DECISAO"}) - {"F3_JURIDICO_REGISTRAL"},
    "F4_FISCAL_OPERACIONAL": frozenset(PARALLEL_PHASES | {"F8_COMITE_DECISAO"}) - {"F4_FISCAL_OPERACIONAL"},
    "F5_LOCALIZACAO_INSPECAO": frozenset(PARALLEL_PHASES | {"F8_COMITE_DECISAO"}) - {"F5_LOCALIZACAO_INSPECAO"},
    "F6_OCUPACAO_POSSE": frozenset(PARALLEL_PHASES | {"F8_COMITE_DECISAO"}) - {"F6_OCUPACAO_POSSE"},
    "F7_VIABILIDADE_FINANCEIRA": frozenset(PARALLEL_PHASES | {"F8_COMITE_DECISAO"}) - {"F7_VIABILIDADE_FINANCEIRA"},
    "F8_COMITE_DECISAO": frozenset({"F9_LANCE_PAGAMENTO"}),
    "F9_LANCE_PAGAMENTO": frozenset({"F10_TRANSFERENCIA_REGISTRO"}),
    "F10_TRANSFERENCIA_REGISTRO": frozenset({"F11_POSSE_REGULARIZACAO"}),
    "F11_POSSE_REGULARIZACAO": frozenset({"F12_EXPLORACAO_SAIDA"}),
    "F12_EXPLORACAO_SAIDA": frozenset({"F13_ENCERRAMENTO"}),
    "F13_ENCERRAMENTO": frozenset(),  # terminal
}

# Fase(s) a partir das quais a transição de PERDA (não arrematou) é válida — SPEC §4.3.
PERDA_ALLOWED_FROM: frozenset[str] = frozenset({"F9_LANCE_PAGAMENTO"})

# --- Hard stops — SPEC §6 -----------------------------------------------------
# Catálogo declarativo: código -> fase onde bloqueia + descrição da origem (reuso).
# A DETECÇÃO (se está ativo) é feita pelo engine a partir do contexto; aqui só o
# catálogo e a fase de bloqueio. Hard stop ativo impede AVANÇO da fase indicada.
HARD_STOPS: dict[str, dict[str, str]] = {
    "MODALIDADE_INDEFINIDA": {
        "blocks_phase": "F1_TRIAGEM",
        "origin": "Opportunity.modality == INDEFINIDO (sem evidência de modalidade).",
    },
    "RISCO_JURIDICO_CRITICO": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "Risk(category=juridico, severity=CRITICA) ativo.",
    },
    "CONSOLIDACAO_NAO_REGISTRADA": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "Checklist CONSOLIDACAO_REGISTRADA != CONFIRMADO (alienação fiduciária).",
    },
    "INTIMACAO_MORA_AUSENTE": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "Checklist INTIMACAO_PESSOAL/INTIMACAO_EDITAL não confirmada.",
    },
    "MATRICULA_DIVERGENTE": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "DueDiligenceFront(MATRICULA): divergência edital × matrícula.",
    },
    "USUFRUTO_NAO_EXTINTO": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "Central Jurídica: usufruto não extinto (exige cancelamento).",
    },
    "ACAO_ANULATORIA_ATIVA": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "LegalProcess correlação ALTA + ação anulatória ativa.",
    },
    "PRECO_ACIMA_MAXIMO": {
        "blocks_phase": "F8_COMITE_DECISAO",
        "origin": "build_finance: lance > preço máximo aprovado.",
    },
}

# Eventos que invalidam avaliações anteriores (SPEC §7) -> fases reabertas.
# Reuso de DomainEvent; a invalidação apenas marca estado (sem LLM/nova análise).
INVALIDATION_EVENTS: dict[str, tuple[str, ...]] = {
    "EDITAL_ATUALIZADO": ("F1_TRIAGEM", "F2_DOCUMENTOS", "F3_JURIDICO_REGISTRAL", "F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
    "EDITAL_EXTRAIDO": ("F1_TRIAGEM", "F2_DOCUMENTOS", "F3_JURIDICO_REGISTRAL", "F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
    "MATRICULA_ATUALIZADA": ("F3_JURIDICO_REGISTRAL", "F8_COMITE_DECISAO"),
    "MATRICULA_EXTRAIDA": ("F3_JURIDICO_REGISTRAL", "F8_COMITE_DECISAO"),
    "PRECO_ALTERADO": ("F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
    "LEILAO_ATUALIZADO": ("F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
    "PROCESSO_VINCULADO": ("F3_JURIDICO_REGISTRAL", "F8_COMITE_DECISAO"),
    "CONSULTA_JUDICIAL_REALIZADA": ("F3_JURIDICO_REGISTRAL", "F8_COMITE_DECISAO"),
    "OCUPACAO_ATUALIZADA": ("F6_OCUPACAO_POSSE", "F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
    "DIVIDA_ADICIONADA": ("F4_FISCAL_OPERACIONAL", "F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
    "CUSTO_ADICIONADO": ("F4_FISCAL_OPERACIONAL", "F7_VIABILIDADE_FINANCEIRA", "F8_COMITE_DECISAO"),
}


def phase_index(phase: str) -> int:
    """Índice ordinal da fase (para comparar avanço/retrocesso). -1 se desconhecida."""
    try:
        return PHASES.index(phase)
    except ValueError:
        return -1


def is_phase(phase: str) -> bool:
    return phase in PHASES


def forward_targets(phase: str) -> frozenset[str]:
    """Destinos de AVANÇO válidos a partir de ``phase`` (vazio se terminal/desconhecida)."""
    return FORWARD_TRANSITIONS.get(phase, frozenset())


def hard_stops_for_phase(phase: str) -> tuple[str, ...]:
    """Códigos de hard stop que bloqueiam o AVANÇO da fase informada."""
    return tuple(code for code, meta in HARD_STOPS.items() if meta["blocks_phase"] == phase)
