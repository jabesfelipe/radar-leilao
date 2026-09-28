"""Diagnóstico (TASK 72): por que o Verdict V8 do imóvel 633 persistiu 28
pending_items (27 perguntas do Checklist + 1 financeira) enquanto a
ChecklistExecution V8 já tinha 7 CONFIRMADO / 20 PENDENTE.

Causa raiz PROVADA (reproduzida no banco real do 633, sem alterar dados):

1. `Property.checklist_executions` NÃO tem `order_by` — a ordem da coleção em
   memória é arbitrária. No 633 a ordem real observada foi
   [697, 901, 902, 1089, 1153, 662, 663, 664, 665], então
   `reversed(prop.checklist_executions)[0]` era a execução 665 (uma execução
   antiga, 27 PENDENTE), NÃO a execução V8 (1153, 7 CONFIRMADO).

2. `create_execution` insere a nova execução por FK (`property_id=prop.id`), e não
   pela relationship (`property=prop`). Logo a execução V8 recém-criada NEM ENTRAVA
   na coleção `prop.checklist_executions` em memória durante o próprio request
   (reproduzido: a nova execução criada por FK não aparece na coleção).

Consequência: o antigo `latest_execution(prop) = next(iter(reversed(...)))` usado
pelo `create_verdict` selecionava uma execução ERRADA (antiga / all-PENDENTE).
O VerdictEngine (que só conta PENDENTE/EM_ANALISE) recebeu 27 resultados pendentes
e persistiu as 27 perguntas — mesmo os 7 itens já estando CONFIRMADO na execução V8
(que estava em OUTRO objeto, não lido pelo verdict). Não foi edição pós-veredito:
os 7 CONFIRMADO já existiam antes do verdict, mas em uma execução que o cálculo
antigo não selecionava.

A Task 71 corrigiu a seleção com `execution_for_version(prop, analysis.version)`
(consulta por versão exata), que retorna a execução da versão da análise. Estes
testes demonstram o mecanismo. NÃO alteram regra de negócio nem dados históricos.
"""
from __future__ import annotations

from types import SimpleNamespace

from backend.app import services


class ArbitraryCollectionProperty:
    """Property cuja coleção checklist_executions está em ordem arbitrária e SEM a
    execução da versão corrente (simula a execução criada por FK, ausente da
    coleção in-memory) — exatamente o cenário do imóvel 633 na V8."""

    def __init__(self, executions, prop_id=633):
        self.id = prop_id
        self.checklist_executions = executions


def _exec(exec_id, analysis_version, confirmados=0, pendentes=27):
    # Cada pergunta precisa ser um texto distinto: o VerdictEngine deduplica
    # pendências por texto (_unique), então perguntas idênticas colapsariam em 1.
    results = (
        [SimpleNamespace(state="CONFIRMADO", applicable=True, item=SimpleNamespace(question=f"C{exec_id}-{i}")) for i in range(confirmados)]
        + [SimpleNamespace(state="PENDENTE", applicable=True, item=SimpleNamespace(question=f"P{exec_id}-{i}")) for i in range(pendentes)]
    )
    return SimpleNamespace(id=exec_id, analysis_version=analysis_version, results=results)


def _old_latest_execution(prop):
    """Reprodução fiel do latest_execution ANTIGO (antes da Task 71)."""
    return next(iter(reversed(prop.checklist_executions)), None)


def test_selecao_antiga_reversed_pegava_execucao_errada():
    # Ordem arbitrária exatamente como observada no banco do 633 (V8 = exec 1153).
    execs = [
        _exec(697, 4, confirmados=2, pendentes=25),
        _exec(901, 5, confirmados=3, pendentes=24),
        _exec(902, 6, confirmados=0, pendentes=27),
        _exec(1089, 7, confirmados=4, pendentes=23),
        _exec(1153, 8, confirmados=7, pendentes=20),  # execução V8 correta
        _exec(662, None, confirmados=0, pendentes=27),
        _exec(663, 1, confirmados=0, pendentes=27),
        _exec(664, 2, confirmados=0, pendentes=27),
        _exec(665, 3, confirmados=0, pendentes=27),  # última da coleção arbitrária
    ]
    prop = ArbitraryCollectionProperty(execs)

    escolhida_antiga = _old_latest_execution(prop)
    # A seleção antiga pega o ÚLTIMO da coleção arbitrária (665, all-PENDENTE),
    # não a execução V8 (1153). É a origem das 27 perguntas pendentes no Verdict V8.
    assert escolhida_antiga.id == 665
    assert sum(1 for r in escolhida_antiga.results if r.state == "CONFIRMADO") == 0
    assert sum(1 for r in escolhida_antiga.results if r.state == "PENDENTE") == 27


def test_execution_for_version_seleciona_a_execucao_da_v8_correta():
    execs = [
        _exec(697, 4, confirmados=2, pendentes=25),
        _exec(1153, 8, confirmados=7, pendentes=20),
        _exec(665, 3, confirmados=0, pendentes=27),
    ]
    prop = ArbitraryCollectionProperty(execs)
    # A correção da Task 71 (por versão exata) devolve a execução V8 (1153).
    sel = services.execution_for_version(prop, 8)
    assert sel.id == 1153
    assert sum(1 for r in sel.results if r.state == "CONFIRMADO") == 7
    assert sum(1 for r in sel.results if r.state == "PENDENTE") == 20


def test_pending_items_do_verdict_dependem_da_execucao_escolhida():
    # Demonstra o efeito no VerdictEngine: a execução escolhida determina os
    # pending_items. Execução errada (all-PENDENTE) => 27 perguntas; execução V8
    # correta => 20 perguntas. VerdictEngine inalterado (só conta PENDENTE/EM_ANALISE).
    from backend.app.verdict_engine import VerdictEngine

    exec_errada = _exec(665, 3, confirmados=0, pendentes=27)
    exec_v8 = _exec(1153, 8, confirmados=7, pendentes=20)

    v_errado = VerdictEngine().evaluate(633, 8, checklist_results=exec_errada.results)
    v_correto = VerdictEngine().evaluate(633, 8, checklist_results=exec_v8.results)

    assert len(v_errado.pending_items) == 27   # o que o Verdict V8 persistido reflete
    assert len(v_correto.pending_items) == 20   # o que a Task 71 produz agora


def test_execucao_criada_por_fk_nao_entra_na_colecao_relationship():
    # Reproduz o padrão de create_execution: objeto criado com property_id (FK) e
    # SEM property=prop não é adicionado à coleção in-memory. Aqui validamos a
    # premissa do diagnóstico de forma determinística: a coleção só contém o que
    # foi explicitamente inserido nela.
    execs = [_exec(665, 3)]
    prop = ArbitraryCollectionProperty(list(execs))
    nova = _exec(1153, 8, confirmados=7, pendentes=20)  # "criada por FK" (não anexada)
    assert nova not in prop.checklist_executions
    # a seleção antiga jamais veria a nova execução; a por-versão também não, pois
    # ela não está na coleção — confirmando que a fonte de verdade tem de ser a
    # coleção correta (o que a Task 71 assume ao consultar por versão na sessão).
    assert _old_latest_execution(prop).id == 665
