"""Testes do Workflow Engine (Ciclo 2 — Onda 1): motor PURO e determinístico.

Sem DB, sem I/O, sem LLM (G-2). Cobrem: vocabulário/versão do ruleset, matriz de
transições válidas/ inválidas (SPEC §4.4), gates de saída, hard stops e o invariante
inegociável (ADR-004): hard stop CONFIRMADO bloqueia F8->F9 mesmo com score alto;
HIPOTESE não bloqueia.
"""
from __future__ import annotations

from backend.app import workflow_rules as rules
from backend.app.workflow_engine import (
    HardStopSignal,
    OpportunityContext,
    can_transition,
    compute_hard_stops,
    evaluate_phase,
)


# --------------------------------------------------------------------------
# Ruleset: vocabulário e versão (B12-C)
# --------------------------------------------------------------------------

def test_ruleset_versao_e_14_fases():
    assert rules.WORKFLOW_RULESET_VERSION == "workflow-v1"
    assert len(rules.PHASES) == 14
    assert rules.PHASES[0] == "F0_INTAKE"
    assert rules.PHASES[-1] == "F13_ENCERRAMENTO"


def test_evaluate_phase_retorna_versao_do_ruleset():
    ctx = OpportunityContext(current_phase="F2_DOCUMENTOS", modality="JUDICIAL")
    ev = evaluate_phase(ctx)
    assert ev.ruleset_version == rules.WORKFLOW_RULESET_VERSION


# --------------------------------------------------------------------------
# Matriz de transições (B12-B) — SPEC §4.4
# --------------------------------------------------------------------------

def _ctx(phase, **kw):
    kw.setdefault("modality", "JUDICIAL")  # evita o hard stop de modalidade
    return OpportunityContext(current_phase=phase, **kw)


def test_avanco_valido_f0_para_f1_com_gate_satisfeito():
    ctx = _ctx("F0_INTAKE", satisfied_gates=frozenset({"F0_INTAKE"}))
    d = can_transition(ctx, "F1_TRIAGEM", "AVANCO")
    assert d.allowed is True and d.result == "PERMITIDA" and d.transition_type == "AVANCO"


def test_avanco_invalido_pula_fase():
    ctx = _ctx("F0_INTAKE", satisfied_gates=frozenset({"F0_INTAKE"}))
    d = can_transition(ctx, "F8_COMITE_DECISAO", "AVANCO")
    assert d.allowed is False and "fora da matriz" in d.reason


def test_avanco_bloqueado_sem_gate_satisfeito():
    ctx = _ctx("F2_DOCUMENTOS", phase_state="EM_ANDAMENTO")
    d = can_transition(ctx, "F3_JURIDICO_REGISTRAL", "AVANCO")
    assert d.allowed is False and "Gate de saída" in d.reason


def test_f2_avanca_para_fases_paralelas():
    ctx = _ctx("F2_DOCUMENTOS", satisfied_gates=frozenset({"F2_DOCUMENTOS"}))
    for alvo in ("F3_JURIDICO_REGISTRAL", "F4_FISCAL_OPERACIONAL", "F7_VIABILIDADE_FINANCEIRA"):
        assert can_transition(ctx, alvo, "AVANCO").allowed is True


def test_due_diligence_paralela_transita_entre_si_e_para_comite():
    ctx = _ctx("F3_JURIDICO_REGISTRAL", satisfied_gates=frozenset({"F3_JURIDICO_REGISTRAL"}))
    assert can_transition(ctx, "F4_FISCAL_OPERACIONAL", "AVANCO").allowed is True
    assert can_transition(ctx, "F8_COMITE_DECISAO", "AVANCO").allowed is True


def test_fase_terminal_nao_avanca():
    ctx = _ctx("F13_ENCERRAMENTO", satisfied_gates=frozenset({"F13_ENCERRAMENTO"}))
    assert can_transition(ctx, "F0_INTAKE", "AVANCO").allowed is False


# --------------------------------------------------------------------------
# Transições especiais: DESCARTE / PERDA / REABERTURA / RETROCESSO
# --------------------------------------------------------------------------

def test_descarte_permitido_em_qualquer_fase_nao_terminal():
    for fase in ("F0_INTAKE", "F3_JURIDICO_REGISTRAL", "F8_COMITE_DECISAO", "F9_LANCE_PAGAMENTO"):
        assert can_transition(_ctx(fase), fase, "DESCARTE").allowed is True


def test_descarte_nao_permitido_na_fase_terminal():
    assert can_transition(_ctx("F13_ENCERRAMENTO"), "F13_ENCERRAMENTO", "DESCARTE").allowed is False


def test_perda_so_a_partir_de_f9():
    assert can_transition(_ctx("F9_LANCE_PAGAMENTO"), "F9_LANCE_PAGAMENTO", "PERDA").allowed is True
    assert can_transition(_ctx("F8_COMITE_DECISAO"), "F8_COMITE_DECISAO", "PERDA").allowed is False


def test_retrocesso_exige_fase_anterior():
    ctx = _ctx("F7_VIABILIDADE_FINANCEIRA")
    assert can_transition(ctx, "F2_DOCUMENTOS", "RETROCESSO").allowed is True
    assert can_transition(ctx, "F8_COMITE_DECISAO", "RETROCESSO").allowed is False


def test_reabertura_para_fase_valida():
    ctx = _ctx("F8_COMITE_DECISAO")
    assert can_transition(ctx, "F3_JURIDICO_REGISTRAL", "REABERTURA").allowed is True
    assert can_transition(ctx, "FX_INEXISTENTE", "REABERTURA").allowed is False


# --------------------------------------------------------------------------
# Hard stops (B12-D / B12-E) — SPEC §6 / ADR-004
# --------------------------------------------------------------------------

def test_modalidade_indefinida_e_hard_stop_deterministico_em_f1():
    ctx = OpportunityContext(current_phase="F1_TRIAGEM", modality="INDEFINIDO")
    assert "MODALIDADE_INDEFINIDA" in compute_hard_stops(ctx)
    d = can_transition(ctx, "F2_DOCUMENTOS", "AVANCO")
    assert d.allowed is False and "MODALIDADE_INDEFINIDA" in d.active_hard_stops


def test_hard_stop_confirmado_bloqueia_f8_para_f9_mesmo_com_score_alto():
    # T-HS-1 / B16-A: score alto NÃO libera aprovação com hard stop CONFIRMADO.
    ctx = _ctx(
        "F8_COMITE_DECISAO",
        satisfied_gates=frozenset({"F8_COMITE_DECISAO"}),
        committee_decision="APROVADA",
        score_snapshot={"financeiro": 95, "global": 92},
        hard_stop_signals=(HardStopSignal("RISCO_JURIDICO_CRITICO", "CONFIRMADO"),),
    )
    d = can_transition(ctx, "F9_LANCE_PAGAMENTO", "AVANCO")
    assert d.allowed is False
    assert "RISCO_JURIDICO_CRITICO" in d.active_hard_stops


def test_hard_stop_hipotese_nao_bloqueia():
    # T-HS-2 / B12-E: hard stop em estado HIPOTESE (ex.: LLM) não bloqueia.
    ctx = _ctx(
        "F8_COMITE_DECISAO",
        satisfied_gates=frozenset({"F8_COMITE_DECISAO"}),
        committee_decision="APROVADA",
        hard_stop_signals=(HardStopSignal("RISCO_JURIDICO_CRITICO", "HIPOTESE"),),
    )
    d = can_transition(ctx, "F9_LANCE_PAGAMENTO", "AVANCO")
    assert d.allowed is True
    assert "RISCO_JURIDICO_CRITICO" not in d.active_hard_stops


def test_f8_para_f9_exige_decisao_humana_aprovada():
    base = dict(satisfied_gates=frozenset({"F8_COMITE_DECISAO"}))
    sem = can_transition(_ctx("F8_COMITE_DECISAO", **base), "F9_LANCE_PAGAMENTO", "AVANCO")
    assert sem.allowed is False and "APROVADA" in sem.reason
    com = can_transition(_ctx("F8_COMITE_DECISAO", committee_decision="APROVADA", **base), "F9_LANCE_PAGAMENTO", "AVANCO")
    assert com.allowed is True


def test_preco_acima_maximo_confirmado_bloqueia_comite():
    # T-HS-6 / B16-C: hard stop determinístico nasce CONFIRMADO e bloqueia.
    ctx = _ctx(
        "F8_COMITE_DECISAO",
        satisfied_gates=frozenset({"F8_COMITE_DECISAO"}),
        committee_decision="APROVADA",
        hard_stop_signals=(HardStopSignal("PRECO_ACIMA_MAXIMO", "CONFIRMADO"),),
    )
    assert can_transition(ctx, "F9_LANCE_PAGAMENTO", "AVANCO").allowed is False


def test_evaluate_phase_marca_bloqueada_quando_ha_hard_stop():
    ctx = _ctx(
        "F8_COMITE_DECISAO",
        satisfied_gates=frozenset({"F8_COMITE_DECISAO"}),
        hard_stop_signals=(HardStopSignal("RISCO_JURIDICO_CRITICO", "CONFIRMADO"),),
    )
    ev = evaluate_phase(ctx)
    assert ev.blocked is True and ev.phase_state == "BLOQUEADA"
    assert "RISCO_JURIDICO_CRITICO" in ev.active_hard_stops


def test_evaluate_phase_concluida_quando_gate_satisfeito_sem_hard_stop():
    ctx = _ctx("F2_DOCUMENTOS", satisfied_gates=frozenset({"F2_DOCUMENTOS"}))
    ev = evaluate_phase(ctx)
    assert ev.blocked is False and ev.gate_satisfied is True
    assert "F3_JURIDICO_REGISTRAL" in ev.forward_targets


def test_funcoes_sao_puras_sem_efeito():
    # B12-A: chamar repetidamente não muda o contexto (frozen) nem o resultado.
    ctx = _ctx("F2_DOCUMENTOS", satisfied_gates=frozenset({"F2_DOCUMENTOS"}))
    a = can_transition(ctx, "F3_JURIDICO_REGISTRAL", "AVANCO").to_dict()
    b = can_transition(ctx, "F3_JURIDICO_REGISTRAL", "AVANCO").to_dict()
    assert a == b
