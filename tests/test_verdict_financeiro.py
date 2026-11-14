"""Veredito orientado à decisão do investidor: "vale a pena arrematar por este lance?".

O veredito passa a considerar o motor financeiro DETERMINÍSTICO (preço máximo, lance, resultado,
margem, ROI). Nenhum LLM decide o resultado financeiro. Caso de referência: caso-01 sintético
(e2e/fixtures/caso-01): lance R$ 240.000, preço máximo R$ 136.266, prejuízo R$ 26.550, margem -7,9%.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings
from backend.app.finance import MaxPriceGoal, SaleAssumptions, calculate_financial
from backend.app.services import is_unavailability_notice, serialize
from backend.app.verdict_engine import FIN_INDETERMINADO, FIN_INVIAVEL, FIN_VIAVEL, VerdictEngine, assess_financial

FIXTURES = Path(__file__).resolve().parent.parent / "e2e" / "fixtures" / "caso-01"


def fin(lance=240000, *, venda=335000, meta=("MARGEM_MINIMA", "0.20"), itbi=True, corretagem="0.06", tributo="0.15"):
    """Financeiro do caso-01 calculado pelo motor REAL (calculate_financial)."""
    costs = [{"category": "Registro", "amount": Decimal("4000")}, {"category": "Reforma", "amount": Decimal("25000")}]
    if itbi:
        costs.append({"category": "ITBI", "amount": Decimal("11850")})
    return serialize(calculate_financial(
        bid=Decimal(str(lance)), appraisal=Decimal("400000"), costs=costs,
        debts=[{"amount": Decimal("21600"), "status": "PENDENTE"}, {"amount": Decimal("4800"), "status": "PENDENTE"}],
        occupancy={"estimated_cost": Decimal("15000")}, area=Decimal("62"), commission_percent=Decimal("5"),
        market_value=Decimal(str(venda)) if venda is not None else None, monthly_carrying=Decimal("900"), holding_months=8,
        sale=SaleAssumptions(corretagem_pct=Decimal(corretagem) if corretagem else None, tributo_pct=Decimal(tributo) if tributo else None),
        goal=MaxPriceGoal(kind=meta[0], value=Decimal(meta[1])) if meta else None,
    ))


def risk(severity, category="JURIDICO", risk_id=1, evidence_id=10):
    return SimpleNamespace(id=risk_id, severity=severity, evidence_id=evidence_id, status="ATIVO", category=category, description=f"Risco {severity}")


def pendente(question="Houve intimação pessoal?", category="JURIDICO"):
    return SimpleNamespace(state="PENDENTE", applicable=True, item=SimpleNamespace(question=question, category=category))


def decisao(result):
    return result.financial["decisao"]


# ---------------------------------------------------------------- caso de referência

def test_caso01_motor_financeiro_bate_com_o_gabarito_escrito_antes():
    gabarito = json.loads((FIXTURES / "gabarito.json").read_text(encoding="utf-8"))["resposta_esperada"]
    f = fin()
    assert round(f["preco_maximo"]) == gabarito["preco_maximo_referencia_brl"]
    assert round(f["resultado_liquido"]) == gabarito["resultado_no_lance_minimo_brl"]
    assert round(f["custo_total"]) == gabarito["custo_total_no_lance_minimo_brl"]


def test_caso01_e_inviavel_e_o_veredito_manda_nao_arrematar_com_justificativa():
    a = assess_financial(fin())
    assert a["status"] == FIN_INVIAVEL
    texto = " ".join(a["motivos"])
    assert "prejuízo de R$ 26.550" in texto and "acima do preço máximo de R$ 136.266" in texto and "-7,9%" in texto and "20,0%" in texto
    # Mesmo com pendências documentais, sem evidência e SEM leitura automática: a perda é financeira e certa.
    r = VerdictEngine().evaluate(1, 1, checklist_results=[pendente()], financial=fin(), automated_analysis_available=False)
    assert r.overall == "DESFAVORAVEL"
    rec = decisao(r)["recomendacao"]
    assert rec["codigo"] == "NAO_ARREMATAR" and round(rec["lance_maximo"]) == 136266 and rec["lance_pretendido"] == 240000
    assert rec["texto"].startswith("NÃO ARREMATAR") and "R$ 136.266" in rec["texto"]
    assert r.summary.startswith("NÃO ARREMATAR")
    tipos = {f["tipo"] for f in decisao(r)["fundamentos"]}
    assert {"INVIABILIDADE_FINANCEIRA", "PENDENCIA_DOCUMENTAL", "ANALISE_AUTOMATICA_INDISPONIVEL"} <= tipos
    assert "RISCO_JURIDICO" not in tipos     # nenhum risco jurídico foi inventado


# ---------------------------------------------------------------- quatro estados

def test_favoravel_exige_viabilidade_financeira_completa_evidencia_e_nenhuma_pendencia():
    f = fin(120000)
    assert assess_financial(f)["status"] == FIN_VIAVEL
    r = VerdictEngine().evaluate(1, 1, evidence_ids=[5], financial=f, automated_analysis_available=True)
    assert r.overall == "FAVORAVEL"
    rec = decisao(r)["recomendacao"]
    assert rec["codigo"] == "ARREMATAR_ATE_PRECO_MAXIMO" and "R$ 136.266" in rec["texto"]


def test_atencao_quando_ha_risco_nao_critico_mesmo_com_lance_viavel():
    r = VerdictEngine().evaluate(1, 1, risks=[risk("ALTA", category="DESOCUPACAO")], evidence_ids=[5], financial=fin(120000))
    assert r.overall == "ATENCAO"
    assert decisao(r)["recomendacao"]["codigo"] == "ARREMATAR_SOMENTE_APOS_RESOLVER_RISCOS"
    assert any(f["tipo"] == "RISCO_OPERACIONAL" for f in decisao(r)["fundamentos"])


def test_desfavoravel_por_risco_critico_mesmo_com_financeiro_viavel():
    r = VerdictEngine().evaluate(1, 1, risks=[risk("CRITICA")], evidence_ids=[5], financial=fin(120000))
    assert r.overall == "DESFAVORAVEL" and decisao(r)["recomendacao"]["codigo"] == "NAO_ARREMATAR"
    assert any(f["tipo"] == "RISCO_JURIDICO" and f["gravidade"] == "CRITICA" for f in decisao(r)["fundamentos"])


def test_inviabilidade_financeira_prevalece_sobre_risco_nao_critico():
    r = VerdictEngine().evaluate(1, 1, risks=[risk("MEDIA")], evidence_ids=[5], financial=fin())
    assert r.overall == "DESFAVORAVEL"


def test_ausencia_de_ia_nao_vira_inviabilidade_financeira():
    # Lance viável + leitura automática indisponível + checklist pendente => INCONCLUSIVO (nunca DESFAVORÁVEL).
    r = VerdictEngine().evaluate(1, 1, checklist_results=[pendente()], financial=fin(120000), automated_analysis_available=False)
    assert r.overall == "INCONCLUSIVO"
    assert decisao(r)["recomendacao"]["codigo"] == "COMPLETAR_ANALISE"
    assert not any(f["tipo"] == "INVIABILIDADE_FINANCEIRA" for f in decisao(r)["fundamentos"])


# ---------------------------------------------------------------- dados ausentes: INCONCLUSIVO, nada inventado

def test_sem_valor_de_venda_e_indeterminado_e_inconclusivo():
    f = fin(240000, venda=None)
    a = assess_financial(f)
    assert a["status"] == FIN_INDETERMINADO and f["preco_maximo"] is None
    assert any("Valor de venda" in x for x in a["faltantes"])
    assert VerdictEngine().evaluate(1, 1, evidence_ids=[5], financial=f).overall == "INCONCLUSIVO"


def test_sem_meta_e_sem_prejuizo_e_indeterminado():
    a = assess_financial(fin(120000, meta=None))
    assert a["status"] == FIN_INDETERMINADO and any("Meta financeira" in x for x in a["faltantes"])


def test_sem_lance_e_indeterminado():
    a = assess_financial(fin(0))
    assert a["status"] == FIN_INDETERMINADO and any("Lance pretendido" in x for x in a["faltantes"])


def test_calculo_provisorio_com_prejuizo_ainda_e_inviavel():
    # ITBI desconhecido entra como zero: o resultado real só pode ser PIOR, então o prejuízo é conclusivo.
    f = fin(240000, itbi=False)
    assert f["resultado_provisorio"] is True and f["resultado_liquido"] < 0
    assert assess_financial(f)["status"] == FIN_INVIAVEL


def test_calculo_provisorio_positivo_nao_e_favoravel():
    f = fin(120000, itbi=False)
    a = assess_financial(f)
    assert a["status"] == FIN_INDETERMINADO and any("provisório" in x.lower() for x in a["faltantes"])
    assert VerdictEngine().evaluate(1, 1, evidence_ids=[5], financial=f).overall == "INCONCLUSIVO"


def test_financeiro_ausente_nunca_e_favoravel():
    assert VerdictEngine().evaluate(1, 1, evidence_ids=[5]).overall == "INCONCLUSIVO"


# ---------------------------------------------------------------- aviso de indisponibilidade não é evidência

def test_aviso_de_agente_que_nao_rodou_nao_e_evidencia():
    aviso = {"kind": "ausencia", "statement": "LLM não configurada; análise deste domínio aguarda OPENAI_API_KEY", "chunk_ids": []}
    assert is_unavailability_notice({"agent": "juridico", "llm_used": False}, aviso) is True
    assert is_unavailability_notice({"agent": "juridico", "llm_used": True}, aviso) is False           # agente rodou: ausência é achado
    assert is_unavailability_notice({"agent": "juridico"}, aviso) is False                              # legado: não descarta
    assert is_unavailability_notice({"agent": "juridico", "llm_used": False}, {**aviso, "chunk_ids": [3]}) is False


# ---------------------------------------------------------------- integração (API + PostgreSQL reais, sem chave)

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


@pytest.fixture
def client(postgres_engine, monkeypatch, tmp_path):
    if TestClient is None:
        pytest.skip("fastapi.testclient indisponível")
    from backend.app.database import get_db
    from backend.app.main import app
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _cadastrar_caso01(c, lance=240000):
    ins = json.loads((FIXTURES / "insumos.json").read_text(encoding="utf-8"))
    pid = c.post("/api/imoveis", json=ins["imovel"]).json()["id"]
    assert c.post(f"/api/imoveis/{pid}/leilao", json={**ins["leilao"], "bid_value": lance}).status_code < 300
    assert c.post(f"/api/imoveis/{pid}/matricula", json=ins["matricula"]).status_code < 300
    assert c.post(f"/api/imoveis/{pid}/ocupacao", json=ins["ocupacao"]).status_code < 300
    for cost in ins["custos"]:
        assert c.post(f"/api/imoveis/{pid}/custos", json=cost).status_code < 300
    for debt in ins["dividas"]:
        assert c.post(f"/api/imoveis/{pid}/dividas", json=debt).status_code < 300
    for comp in ins["comparaveis"]:
        assert c.post(f"/api/imoveis/{pid}/comparaveis", json=comp).status_code < 300
    assert c.put(f"/api/imoveis/{pid}/financeiro/premissas", json=ins["premissas_financeiras"]).status_code < 300
    for nome, tipo in (("matricula.txt", "MATRICULA"), ("edital.txt", "EDITAL")):
        r = c.post(f"/api/imoveis/{pid}/documentos", files={"file": (nome, (FIXTURES / nome).read_bytes(), "text/plain")}, data={"document_type": tipo})
        assert r.status_code < 300, r.text
    return pid


def test_api_caso01_sem_ia_recomenda_nao_arrematar(client):
    c, session = client
    pid = _cadastrar_caso01(c)
    r = c.post(f"/api/imoveis/{pid}/analisar", json={})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["status"] == "falha" and corpo["status_detalhe"]["codigo"] == "IA_INDISPONIVEL"   # IA ausente informada
    assert corpo["veredito"] == "DESFAVORAVEL"                                                        # decisão é financeira
    rec = corpo["financeiro"]["decisao"]["recomendacao"]
    assert rec["codigo"] == "NAO_ARREMATAR" and round(rec["lance_maximo"]) == 136266
    # Avisos "LLM não configurada" não viram evidência.
    assert corpo["evidencias"] == []
    evs = session.query(models.Evidence).filter(models.Evidence.property_id == pid).all()
    assert not any("não configurada" in (e.fact or "") for e in evs)
    # Pendência resolvida pelos dados: 2º leilão = 60% da avaliação.
    detalhe = c.get(f"/api/imoveis/{pid}").json()
    itens = {i["canonical_key"]: i for i in detalhe["checklist"]}
    assert itens["LANCE_MENOR_50_AVALIACAO"]["state"] == "NAO_IDENTIFICADO" and "60,0%" in itens["LANCE_MENOR_50_AVALIACAO"]["answer"]
    assert itens["PRAZO_DOIS_ANOS"]["state"] == "NAO_IDENTIFICADO"
    assert itens["INTIMACAO_PESSOAL"]["state"] == "PENDENTE"            # o que depende de documento não é inventado
    assert detalhe["veredito"]["overall"] == "DESFAVORAVEL" and detalhe["veredito"]["summary"].startswith("NÃO ARREMATAR")


def test_api_lance_viavel_sem_ia_fica_inconclusivo_e_nao_desfavoravel(client):
    c, _ = client
    pid = _cadastrar_caso01(c, lance=120000)
    corpo = c.post(f"/api/imoveis/{pid}/analisar", json={}).json()
    assert corpo["veredito"] == "INCONCLUSIVO"
    decisao_api = corpo["financeiro"]["decisao"]
    assert decisao_api["avaliacao_financeira"]["status"] == "VIAVEL"
    assert decisao_api["recomendacao"]["codigo"] == "COMPLETAR_ANALISE"
    assert any(f["tipo"] == "ANALISE_AUTOMATICA_INDISPONIVEL" for f in decisao_api["fundamentos"])


def test_visao_de_evidencias_traz_trecho_literal_e_mascara_dados_pessoais(client):
    c, session = client
    from backend.app.main import verdict_evidences_view
    pid = _cadastrar_caso01(c)
    chunk = (session.query(models.DocumentChunk).join(models.DocumentVersion).join(models.Document)
             .filter(models.Document.property_id == pid, models.DocumentChunk.content.contains("111.222.333-96")).first())
    assert chunk is not None
    ev = models.Evidence(property_id=pid, document_version_id=chunk.document_version_id, chunk_id=chunk.id, category="DOCUMENTAL",
                         fact="Proprietário com CPF 111.222.333-96 na R.1", confidence="MEDIA")
    session.add(ev); session.flush()
    view = verdict_evidences_view(session, [ev.id])[0]
    assert view["documento"] == "matricula.txt" and view["tem_trecho_documento"] is True
    assert "R.1/99.901" in view["source_excerpt"]                     # trecho literal do documento
    assert "111.222.333-96" not in view["source_excerpt"] and "111.222.333-96" not in view["fact"]
    assert "[CPF]" in view["source_excerpt"]


def _evidencia_com_cpf(session, pid):
    chunk = (session.query(models.DocumentChunk).join(models.DocumentVersion).join(models.Document)
             .filter(models.Document.property_id == pid, models.DocumentChunk.content.contains("111.222.333-96")).first())
    ev = models.Evidence(property_id=pid, document_version_id=chunk.document_version_id, chunk_id=chunk.id, category="DOCUMENTAL",
                         fact="Proprietário CPF 111.222.333-96, e-mail fulano@example.com", page=1, section="R.1",
                         source_excerpt=chunk.content, confidence="MEDIA")
    session.add(ev); session.flush()
    return ev, chunk


def test_api_de_evidencias_mascara_dados_pessoais_sem_perder_rastreabilidade(client):
    c, session = client
    pid = _cadastrar_caso01(c)
    ev, chunk = _evidencia_com_cpf(session, pid)
    lista = c.get(f"/api/imoveis/{pid}/evidencias")
    assert lista.status_code == 200
    item = next(e for e in lista.json() if e["id"] == ev.id)
    assert "111.222.333-96" not in lista.text and "fulano@example.com" not in lista.text
    assert "[CPF]" in item["fact"] and "[EMAIL]" in item["fact"] and "R.1/99.901" in item["source_excerpt"]
    assert (item["document_version_id"], item["chunk_id"], item["page"], item["section"]) == (chunk.document_version_id, chunk.id, 1, "R.1")
    detalhe = c.get(f"/api/imoveis/{pid}/evidencias/{ev.id}")
    assert detalhe.status_code == 200 and "111.222.333-96" not in detalhe.text
    assert "R.1/99.901" in detalhe.json()["chunk"]["content"] and "embedding" not in detalhe.json()["chunk"]
    imovel = c.get(f"/api/imoveis/{pid}")
    assert "111.222.333-96" not in json.dumps(imovel.json()["evidencias"], ensure_ascii=False)
    session.refresh(ev)
    assert "111.222.333-96" in ev.fact            # só a resposta é mascarada; o registro original não muda


def test_diagnostico_da_analise_tem_rastreabilidade_e_nao_vaza_dados(client):
    c, session = client
    from backend.app.diagnostics import build_diagnostic, to_markdown
    pid = _cadastrar_caso01(c)
    assert c.post(f"/api/imoveis/{pid}/analisar", json={}).status_code == 200
    analysis_id = c.get(f"/api/imoveis/{pid}/historico").json()["analises"][0]["id"]
    d = build_diagnostic(session, analysis_id)
    assert d["analise"]["id"] == analysis_id and d["analise"]["imovel_id"] == pid
    assert d["analise"]["status_codigo"] == "IA_INDISPONIVEL"
    assert {r["agente"] for r in d["agentes"]} == {"documental", "juridico", "financeiro", "mercado", "checklist"}
    assert all(r["status"] == "SEM_CHAVE" and r["custo_usd"] in (None, 0.0) for r in d["agentes"])
    assert d["veredito"]["overall"] == "DESFAVORAVEL" and d["veredito"]["recomendacao"]["codigo"] == "NAO_ARREMATAR"
    assert d["veredito"]["avaliacao_financeira"] == "INVIAVEL" and d["veredito"]["motivos_financeiros"]
    assert {x["documento"] for x in d["documentos"]} == {"matricula.txt", "edital.txt"}
    assert all(x.get("do_mesmo_imovel", True) for x in d["rag_referencias"])
    texto = json.dumps(d, ensure_ascii=False) + to_markdown(d)
    assert "111.222.333-96" not in texto and "Carlos Eduardo Teste Silva" not in texto and "sk-" not in texto
    assert "NAO_ARREMATAR" in to_markdown(d)
