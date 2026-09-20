import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from backend.app import models, schemas
from backend.app.checklist import CHECKLIST_CONFIDENCES, CHECKLIST_MASTER, CHECKLIST_STATES, master_items
from backend.app.services import create_execution, ensure_checklist_master, checklist_item_snapshot, update_checklist_item, record_checklist_event, record_checklist_history


@pytest.fixture
def checklist_db(postgres_engine):
    if not {"checklist_items", "checklist_executions", "checklist_results", "entity_history", "domain_events"}.issubset(set(inspect(postgres_engine).get_table_names())):
        pytest.skip("Migrations do Checklist Mestre não aplicadas")
    columns = {column["name"] for column in inspect(postgres_engine).get_columns("checklist_items")}
    result_columns = {column["name"] for column in inspect(postgres_engine).get_columns("checklist_results")}
    if not {"description", "domain", "expected_evidence", "related_rules"}.issubset(columns) or not {"item_version", "previous_result_id", "applicable"}.issubset(result_columns):
        pytest.skip("Migration 0003 do Checklist Mestre não aplicada")
    from sqlalchemy.orm import Session
    session = Session(postgres_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_seed_tem_apenas_regras_presentes_e_e_idempotente(checklist_db):
    ensure_checklist_master(checklist_db)
    checklist_db.flush()
    first_count = len(checklist_db.query(models.ChecklistItem).all())
    ensure_checklist_master(checklist_db)
    checklist_db.flush()
    assert first_count == len(CHECKLIST_MASTER)
    assert first_count == len(checklist_db.query(models.ChecklistItem).all())


def test_seed_nao_sobrescreve_nem_reativa_regra(checklist_db):
    ensure_checklist_master(checklist_db)
    item = checklist_db.query(models.ChecklistItem).first()
    item.active = False
    item.question = "Alteração manual preservada"
    checklist_db.flush()
    ensure_checklist_master(checklist_db)
    checklist_db.flush()
    assert item.active is False
    assert item.question == "Alteração manual preservada"


def test_canonical_key_unica(checklist_db):
    item = models.ChecklistItem(canonical_key="RULE-TEST-UNICA", question="Regra de teste", domain=["CHECKLIST"])
    duplicate = models.ChecklistItem(canonical_key="RULE-TEST-UNICA", question="Duplicada", domain=["CHECKLIST"])
    checklist_db.add_all([item, duplicate])
    with pytest.raises(IntegrityError):
        checklist_db.flush()
    checklist_db.rollback()


def test_nova_execucao_cria_snapshot_sem_copiar_resposta(checklist_db):
    prop = models.Property(title="Imóvel Checklist", address="Rua Teste", city="São Paulo", state="SP")
    checklist_db.add(prop); checklist_db.flush()
    first = create_execution(checklist_db, prop, "TESTE", 1)
    first_result = first.results[0]
    first_result.state = "CONFIRMADO"
    first_result.answer = "Resposta anterior"
    checklist_db.flush()
    second = create_execution(checklist_db, prop, "TESTE", 2)
    second_result = next(result for result in second.results if result.checklist_item_id == first_result.checklist_item_id)
    assert second_result.state == "PENDENTE"
    assert second_result.answer == ""
    assert second_result.item_version == first_result.item.version
    assert second_result.previous_result_id == first_result.id


def test_regra_desativada_nao_entra_em_nova_execucao(checklist_db):
    prop = models.Property(title="Imóvel Ativação", address="Rua Teste", city="São Paulo", state="SP")
    checklist_db.add(prop); checklist_db.flush(); ensure_checklist_master(checklist_db)
    item = checklist_db.query(models.ChecklistItem).first()
    item.active = False; checklist_db.flush()
    execution = create_execution(checklist_db, prop, "TESTE", 1)
    assert item.id not in {result.checklist_item_id for result in execution.results}


def test_update_incrementa_versao_e_registra_snapshot(checklist_db):
    item = models.ChecklistItem(canonical_key="RULE-VERSAO", question="Original", domain=["CHECKLIST"], version=1)
    checklist_db.add(item); checklist_db.flush()
    before = checklist_item_snapshot(item)
    update_checklist_item(checklist_db, item, {"question": "Atualizada", "expected_evidence": ["EDITAL"]})
    assert item.version == 2
    assert item.question == "Atualizada"
    assert item.expected_evidence == ["EDITAL"]
    event = record_checklist_event(checklist_db, item, "CHECKLIST_ATUALIZADO", {"before": before, "after": checklist_item_snapshot(item)})
    record_checklist_history(checklist_db, item, "UPDATE", before, checklist_item_snapshot(item), event.id)
    history = checklist_db.query(models.EntityHistory).filter_by(entity_type="ChecklistItem", entity_id=item.id).all()
    assert history
    assert history[-1].before_data["version"] == 1
    assert history[-1].after_data["version"] == 2


def test_todos_os_estados_e_confiancas_sao_oficiais():
    for state in CHECKLIST_STATES:
        assert schemas.ChecklistUpdate(state=state).state == state
    for confidence in CHECKLIST_CONFIDENCES:
        assert schemas.ChecklistUpdate(state="PENDENTE", confidence=confidence).confidence == confidence
    with pytest.raises(ValueError):
        schemas.ChecklistUpdate(state="ESTADO_INVENTADO")


def test_evidencia_unica_e_multipla_sem_documento(checklist_db):
    prop = models.Property(title="Imóvel Evidência", address="Rua Evidência", city="São Paulo", state="SP")
    checklist_db.add(prop); checklist_db.flush()
    execution = create_execution(checklist_db, prop, "TESTE", 1)
    result = execution.results[0]
    evidence_one = models.Evidence(property_id=prop.id, fact="Evidência manual")
    evidence_two = models.Evidence(property_id=prop.id, fact="Evidência documental")
    checklist_db.add_all([evidence_one, evidence_two]); checklist_db.flush()
    checklist_db.add_all([models.ChecklistEvidence(checklist_result_id=result.id, evidence_id=evidence_one.id), models.ChecklistEvidence(checklist_result_id=result.id, evidence_id=evidence_two.id)])
    checklist_db.flush()
    assert {evidence.id for evidence in result.evidences} == {evidence_one.id, evidence_two.id}
    assert evidence_one.document_version_id is None
