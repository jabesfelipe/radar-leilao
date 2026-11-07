"""Testes de isolamento entre oportunidades + compatibilidade legada (Ciclo 2 — Onda 1).

Usa PostgreSQL real (fixture ``db``; rollback ao final), SEM LLM e SEM tocar o
imóvel 633 real (fixtures sintéticas). Cobrem SPEC-OPPORTUNITY-ISOLATION (I1–I8) e
a MATRIZ-OPPORTUNITY-ID: opportunity_id NULLABLE nas 9 tabelas, NULL = legado,
numeração de versão por oportunidade, isolamento de histórico, preservação de
post_auctions.property_id UNIQUE e cascade de Property intocado.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app import models


def _property(db, titulo="Imóvel ISO"):
    prop = models.Property(title=titulo, address="Rua ISO", city="São Paulo", state="SP", area_m2=70, bedrooms=2)
    db.add(prop)
    db.flush()
    return prop


def _opportunity(db, prop, *, codigo, modality="JUDICIAL", is_legacy=False):
    opp = models.Opportunity(property_id=prop.id, codigo=codigo, modality=modality, is_legacy=is_legacy)
    db.add(opp)
    db.flush()
    return opp


# --------------------------------------------------------------------------
# Modelo básico (B11-A/B11-B) + 1:1 workflow
# --------------------------------------------------------------------------

def test_cria_opportunity_pertence_a_um_imovel(db):
    prop = _property(db)
    opp = _opportunity(db, prop, codigo="OPP-1")
    assert opp.id is not None
    assert opp.property_id == prop.id
    assert opp.status == "EM_PROSPECCAO" and opp.modality == "JUDICIAL" and opp.is_legacy is False


def test_workflow_1_para_1_unico_por_oportunidade(db):
    prop = _property(db)
    opp = _opportunity(db, prop, codigo="OPP-WF")
    db.add(models.OpportunityWorkflow(opportunity_id=opp.id, current_phase="F0_INTAKE"))
    db.flush()
    db.add(models.OpportunityWorkflow(opportunity_id=opp.id, current_phase="F1_TRIAGEM"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_property_1_para_n_opportunities(db):
    prop = _property(db)
    _opportunity(db, prop, codigo="OPP-A")
    _opportunity(db, prop, codigo="OPP-B")
    opps = db.scalars(select(models.Opportunity).where(models.Opportunity.property_id == prop.id)).all()
    assert len(opps) == 2


# --------------------------------------------------------------------------
# Isolamento de histórico (I2/I4 — T-ISO-1/3)
# --------------------------------------------------------------------------

def test_analises_nao_vazam_entre_oportunidades(db):
    prop = _property(db)
    opp_a = _opportunity(db, prop, codigo="OPP-A")
    opp_b = _opportunity(db, prop, codigo="OPP-B")
    db.add(models.Analysis(property_id=prop.id, opportunity_id=opp_a.id, version=1))
    db.add(models.Analysis(property_id=prop.id, opportunity_id=opp_b.id, version=1))
    db.flush()
    so_a = db.scalars(
        select(models.Analysis).where(
            models.Analysis.property_id == prop.id, models.Analysis.opportunity_id == opp_a.id
        )
    ).all()
    assert len(so_a) == 1 and so_a[0].opportunity_id == opp_a.id


def test_veredito_isolado_por_oportunidade(db):
    prop = _property(db)
    opp_a = _opportunity(db, prop, codigo="OPP-A")
    opp_b = _opportunity(db, prop, codigo="OPP-B")
    db.add(models.Verdict(property_id=prop.id, opportunity_id=opp_a.id, analysis_version=1, overall="FAVORAVEL", summary="A"))
    db.add(models.Verdict(property_id=prop.id, opportunity_id=opp_b.id, analysis_version=1, overall="INCONCLUSIVO", summary="B"))
    db.flush()
    v_b = db.scalars(select(models.Verdict).where(models.Verdict.opportunity_id == opp_b.id)).all()
    assert len(v_b) == 1 and v_b[0].overall == "INCONCLUSIVO"


# --------------------------------------------------------------------------
# Compatibilidade legada: opportunity_id NULL (I7 — T-ISO-7)
# --------------------------------------------------------------------------

def test_registro_legado_fica_com_opportunity_id_null(db):
    prop = _property(db, "Imóvel Legado")
    # Registro criado SEM contexto de oportunidade = legado (idêntico ao fluxo atual).
    db.add(models.Analysis(property_id=prop.id, version=1))
    db.flush()
    legado = db.scalars(
        select(models.Analysis).where(
            models.Analysis.property_id == prop.id, models.Analysis.opportunity_id.is_(None)
        )
    ).all()
    assert len(legado) == 1 and legado[0].opportunity_id is None


def test_criar_oportunidade_nova_nao_adota_registros_legados(db):
    prop = _property(db, "Imóvel Legado+Nova")
    db.add(models.Analysis(property_id=prop.id, version=1))  # legado
    db.flush()
    opp = _opportunity(db, prop, codigo="OPP-NOVA")
    db.add(models.Analysis(property_id=prop.id, opportunity_id=opp.id, version=1))  # nova
    db.flush()
    legado = db.scalars(
        select(models.Analysis).where(
            models.Analysis.property_id == prop.id, models.Analysis.opportunity_id.is_(None)
        )
    ).all()
    da_nova = db.scalars(
        select(models.Analysis).where(models.Analysis.opportunity_id == opp.id)
    ).all()
    assert len(legado) == 1 and legado[0].opportunity_id is None
    assert len(da_nova) == 1 and da_nova[0].opportunity_id == opp.id


# --------------------------------------------------------------------------
# Numeração de versão por oportunidade (I3 — T-ISO-2)
# --------------------------------------------------------------------------

def test_numeracao_de_versao_por_oportunidade(db):
    prop = _property(db)
    opp_a = _opportunity(db, prop, codigo="OPP-A")
    opp_b = _opportunity(db, prop, codigo="OPP-B")
    db.add_all([
        models.Analysis(property_id=prop.id, opportunity_id=opp_a.id, version=1),
        models.Analysis(property_id=prop.id, opportunity_id=opp_a.id, version=2),
    ])
    db.flush()
    # max(version) DENTRO de cada oportunidade, não global do imóvel.
    max_a = max(a.version for a in db.scalars(select(models.Analysis).where(models.Analysis.opportunity_id == opp_a.id)))
    max_b = [a.version for a in db.scalars(select(models.Analysis).where(models.Analysis.opportunity_id == opp_b.id))]
    assert max_a == 2 and max_b == []  # B começaria em version=1 (não 3)


# --------------------------------------------------------------------------
# post_auctions.property_id UNIQUE preservado (Gate 1, opção A)
# --------------------------------------------------------------------------

def test_post_auction_property_id_unique_preservado(db):
    prop = _property(db, "Imóvel Pós")
    opp = _opportunity(db, prop, codigo="OPP-POS")
    db.add(models.PostAuction(property_id=prop.id, opportunity_id=opp.id, status="EM_ANDAMENTO"))
    db.flush()
    db.add(models.PostAuction(property_id=prop.id, status="EM_ANDAMENTO"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --------------------------------------------------------------------------
# Isolamento ao descartar/apagar: cascade de Property intocado (I8 — T-ISO-8)
# --------------------------------------------------------------------------

def test_apagar_oportunidade_nao_afeta_registros_legados(db):
    prop = _property(db, "Imóvel Cascade")
    db.add(models.Analysis(property_id=prop.id, version=1))  # legado (opportunity_id NULL)
    db.flush()
    opp = _opportunity(db, prop, codigo="OPP-DEL")
    db.add(models.OpportunityWorkflow(opportunity_id=opp.id, current_phase="F0_INTAKE"))
    db.add(models.WorkflowTransition(
        opportunity_id=opp.id, from_phase=None, to_phase="F0_INTAKE",
        transition_type="AVANCO", result="PERMITIDA", phase_state="EM_ANDAMENTO",
    ))
    db.flush()
    db.delete(opp)  # apagar a oportunidade
    db.flush()
    # Análise legada permanece; imóvel permanece.
    legado = db.scalars(select(models.Analysis).where(models.Analysis.property_id == prop.id)).all()
    assert len(legado) == 1 and legado[0].opportunity_id is None
    assert db.get(models.Property, prop.id) is not None
    # Workflow/transições da oportunidade foram removidos junto (cascade da Opportunity).
    assert db.scalars(select(models.OpportunityWorkflow).where(models.OpportunityWorkflow.opportunity_id == opp.id)).all() == []


def test_workflow_transitions_isoladas_por_oportunidade(db):
    prop = _property(db)
    opp_a = _opportunity(db, prop, codigo="OPP-A")
    opp_b = _opportunity(db, prop, codigo="OPP-B")
    db.add_all([
        models.WorkflowTransition(opportunity_id=opp_a.id, to_phase="F1_TRIAGEM", transition_type="AVANCO", result="PERMITIDA", phase_state="EM_ANDAMENTO"),
        models.WorkflowTransition(opportunity_id=opp_a.id, to_phase="F2_DOCUMENTOS", transition_type="AVANCO", result="PERMITIDA", phase_state="EM_ANDAMENTO"),
        models.WorkflowTransition(opportunity_id=opp_b.id, to_phase="F1_TRIAGEM", transition_type="AVANCO", result="PERMITIDA", phase_state="EM_ANDAMENTO"),
    ])
    db.flush()
    t_a = db.scalars(select(models.WorkflowTransition).where(models.WorkflowTransition.opportunity_id == opp_a.id)).all()
    t_b = db.scalars(select(models.WorkflowTransition).where(models.WorkflowTransition.opportunity_id == opp_b.id)).all()
    assert len(t_a) == 2 and len(t_b) == 1
