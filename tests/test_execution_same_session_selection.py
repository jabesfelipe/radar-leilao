"""TASK 73 — Garantir seleção da ChecklistExecution recém-criada no mesmo
request/sessão.

Reproduz o cenário real (com banco real, via fixture ``db``, sem LLM e sem
análise real; a fixture faz rollback ao final, nada é persistido):

    Property
       ↓  (relationship checklist_executions é CARREGADA antes)
    create_execution()  ->  nova ChecklistExecution Vn (inserida por FK property_id)
       ↓
    create_verdict()  ->  execution_for_version(prop, Vn, db=db)
       ↓
    deve encontrar EXATAMENTE Vn

Causa: create_execution insere por property_id (FK) e NÃO anexa a nova execução à
coleção prop.checklist_executions. Se a coleção já foi carregada antes, a Session
mantém a lista em memória sem re-consultar, então a execução recém-criada não
aparece nela. A correção da Task 73 faz execution_for_version consultar o banco
(fonte de verdade) quando recebe `db`.

Estes testes NÃO executam LLM, NÃO fazem análise real e NÃO geram V9.
"""
from __future__ import annotations

from backend.app import models, services


def _nova_property(db):
    prop = models.Property(title="Imóvel T73", address="Rua T73", city="São Paulo", state="SP", area_m2=70, bedrooms=2)
    db.add(prop)
    db.flush()
    return prop


def test_execution_for_version_com_db_encontra_execucao_recem_criada(db):
    prop = _nova_property(db)

    # 1) FORÇA o carregamento da relationship ANTES de criar a nova execução.
    #    Aqui está vazia; o ponto é que a Session passa a ter a coleção materializada.
    _ = list(prop.checklist_executions)
    assert _ == []

    # 2) create_execution insere a execução da versão 8 por FK (property_id).
    execution = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version=8)
    assert execution.analysis_version == 8

    # 3) A coleção em memória continua desatualizada: a nova execução NÃO entrou nela
    #    (é o bug de origem — reproduzido de forma determinística).
    assert execution not in prop.checklist_executions

    # 4) Com db (fonte de verdade), a seleção por versão encontra EXATAMENTE a Vn.
    encontrada = services.execution_for_version(prop, 8, db=db)
    assert encontrada is not None
    assert encontrada.id == execution.id
    assert encontrada.analysis_version == 8


def test_caminho_em_memoria_sem_db_ficava_stale(db):
    """Demonstra por que a correção era necessária: SEM db, a seleção usa a
    relationship carregada e NÃO enxerga a execução recém-criada por FK."""
    prop = _nova_property(db)
    _ = list(prop.checklist_executions)  # carrega a coleção (vazia) antes

    execution = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis_version=8)

    # Sem db: cai no caminho da relationship, que está stale -> não acha a Vn e
    # devolve o fallback (latest_execution sobre a coleção vazia = None).
    em_memoria = services.execution_for_version(prop, 8, db=None)
    assert em_memoria is None or em_memoria.id != execution.id

    # Com db: encontra corretamente.
    com_db = services.execution_for_version(prop, 8, db=db)
    assert com_db.id == execution.id


def test_create_verdict_usa_a_execucao_da_versao_corrente(db):
    """Reproduz o fluxo create_execution -> create_verdict na MESMA sessão e
    confirma que o veredito é calculado sobre a execução da versão corrente."""
    prop = _nova_property(db)
    _ = list(prop.checklist_executions)  # relationship carregada antes

    analysis = services.create_analysis(db, prop, "checklist", ["checklist"], [], "T73", [])
    execution = services.create_execution(db, prop, "REANALISE_INCREMENTAL", analysis.version)

    # Confirma 2 itens da execução corrente para diferenciar contagem de pendências.
    confirmados = 0
    for result in execution.results:
        if confirmados >= 2:
            break
        if result.applicable:
            result.state = "CONFIRMADO"
            confirmados += 1
    db.flush()
    assert confirmados == 2

    total_aplicaveis = sum(1 for r in execution.results if r.applicable)
    checklist_pendentes = total_aplicaveis - confirmados

    verdict = services.create_verdict(db, prop, analysis)

    # As pendências do veredito vêm da execução da versão corrente (a recém-criada),
    # não de uma execução antiga/errada. Todas as perguntas do master são distintas,
    # então não há deduplicação colapsando a contagem. O build_finance adiciona
    # exatamente 1 pendência financeira canônica (preço máximo não definido na SPEC).
    FINANCEIRA = 1
    assert len(verdict.pending_items) == checklist_pendentes + FINANCEIRA
    assert verdict.analysis_version == analysis.version
