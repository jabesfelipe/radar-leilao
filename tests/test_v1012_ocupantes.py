"""v1.0.12 — Fase D: possíveis ocupantes (sugestão) e status/verificação da ocupação. Dados fictícios."""
from __future__ import annotations

from decimal import Decimal

from backend.app import models
from backend.app.occupancy_service import AVISO_POSSIVEIS_OCUPANTES, possible_occupants
from backend.app.viability import market_intelligence
from tests.test_checklist_evidencias import _analisar, _doc, _itens, _leilao, _prop
from tests.test_v107_imovel7_regressao import COMPRADOR, MATRICULA_FICTICIA
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)


def _com_matricula(db):
    prop = _prop(db)
    _leilao(db, prop)
    _doc(db, prop, "\n".join(MATRICULA_FICTICIA), "matricula.txt", "MATRICULA")
    db.flush()
    return prop


def test_possiveis_ocupantes_so_pessoas_fisicas_com_origem_e_aviso(db):
    prop = _com_matricula(db)
    out = possible_occupants(db, prop.id)
    assert out["aviso"] == AVISO_POSSIVEIS_OCUPANTES
    nomes = [p["nome"] for p in out["possiveis_ocupantes"]]
    assert nomes == [COMPRADOR]                                                    # construtora e banco (PJ) ficam fora
    origem = out["possiveis_ocupantes"][0]["origens"][0]
    assert origem["ato"] == "R-2" and origem["papel"] == "Comprador" and COMPRADOR in origem["trecho"] and origem["documento"] == "matricula.txt"


def test_possiveis_ocupantes_nao_respondem_o_checklist(db):
    prop = _com_matricula(db)
    itens = _itens(_analisar(db, prop)[0])
    assert itens["TERCEIRO_OCUPANTE"].state == "PENDENTE" and itens["ETICA_OCUPACAO"].state == "PENDENTE"


def test_status_confirmado_pelo_usuario_responde_11_e_27(db):
    prop = _com_matricula(db)
    db.add(models.OccupancyAnalysis(property_id=prop.id, status="OCUPADO_TERCEIROS"))
    db.flush()
    itens = _itens(_analisar(db, prop)[0])
    assert itens["TERCEIRO_OCUPANTE"].state == "ATENCAO" and "ocupado por terceiros" in itens["TERCEIRO_OCUPANTE"].answer
    vazio = _com_matricula(db)
    db.add(models.OccupancyAnalysis(property_id=vazio.id, status="NAO_VERIFICADO"))
    db.flush()
    assert _itens(_analisar(db, vazio)[0])["TERCEIRO_OCUPANTE"].state == "PENDENTE"


def test_ocupacao_confirmada_leva_a_reserva_a_todos_os_cenarios(db):
    prop = _prop(db)
    _leilao(db, prop)
    db.add(models.OccupancyAnalysis(property_id=prop.id, status="OCUPADO_CONFIRMADO"))
    db.flush(); db.expire(prop)
    linha = next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == "desocupacao")
    assert linha["valor_base"] == linha["valor_conservador"] == Decimal("5000.00")


def test_api_status_novo_com_verificacao_em_evidencia(api):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    r = client.post(f"/api/imoveis/{pid}/ocupacao", json={"status": "OCUPADO_CONFIRMADO", "verificacao": {
        "fonte": "vistoria no local", "data": "2026-05-10", "responsavel": "Analista Fictício", "observacao": "Moradores atenderam a porta."}})
    assert r.status_code < 300, r.text
    assert r.json()["evidence_id"] is not None
    atual = client.get(f"/api/imoveis/{pid}/ocupacao").json()["situacao_atual"]
    assert atual["status_label"] == "Ocupação confirmada"
    assert atual["verificacao"] == {"evidence_id": atual["evidence_id"], "fonte": "vistoria no local", "data": "10/05/2026",
                                    "responsavel": "Analista Fictício", "observacao": "Moradores atenderam a porta."}
    assert client.post(f"/api/imoveis/{pid}/ocupacao", json={"status": "INVALIDO"}).status_code == 422
    body = client.get(f"/api/imoveis/{pid}/ocupacao/possiveis-ocupantes").json()
    assert body["aviso"] == AVISO_POSSIVEIS_OCUPANTES and body["possiveis_ocupantes"] == [] and body["situacao_registrada"]["status"] == "OCUPADO_CONFIRMADO"
