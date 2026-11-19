"""v1.0.12 — Fase C: linha do tempo da matrícula (dados fictícios)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.registry_chain import read_registry
from backend.app.registry_timeline import IDADE_NAO_DETERMINAVEL, build_timeline, timeline_for_property
from tests.test_checklist_evidencias import MATRICULA_LIMPA, _doc, _prop
from tests.test_v107_imovel7_regressao import COMPRADOR, MATRICULA_FICTICIA, _chunks
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)

HOJE = date(2026, 6, 1)


def _linha(texts=MATRICULA_FICTICIA):
    return build_timeline(read_registry(_chunks(texts), 77), {"document_id": 1, "document_version_id": 77, "nome": "matricula.txt"}, HOJE)


def _evento(tl, ato):
    return next(e for e in tl["eventos"] if e["ato"] == ato)


def test_eventos_com_data_tipo_e_trecho_na_ordem_dos_atos():
    tl = _linha()
    assert [e["ato"] for e in tl["eventos"]] == ["Abertura", "Av-1", "R-2", "R-3", "Av-4", "Av-5"]
    tipos = {e["ato"]: e["tipo"] for e in tl["eventos"]}
    assert tipos == {"Abertura": "ABERTURA", "Av-1": "AFETACAO", "R-2": "COMPRA_VENDA", "R-3": "ALIENACAO_FIDUCIARIA", "Av-4": "CONCLUSAO_OBRA",
                     "Av-5": "CONSOLIDACAO"}
    assert _evento(tl, "R-2")["data"] == "2001-02-01" and _evento(tl, "R-2")["data_texto"] == "01/02/2001"
    assert _evento(tl, "Av-1")["data"] is None                                   # "01/0 1" (OCR) não vira data
    for e in tl["eventos"]:
        assert e["trecho"] and e["documento"]["nome"] == "matricula.txt" and e["chunk_id"] is not None and e["fonte"]


def test_partes_com_papel_declarado_e_valor():
    tl = _linha()
    venda = _evento(tl, "R-2")
    papeis = {(p["papel"], p["nome"]) for p in venda["partes"]}
    assert ("VENDEDOR", "CONSTRUTORA FICTÍCIA ALFA LTDA") in papeis and ("COMPRADOR", COMPRADOR) in papeis
    comprador = next(p for p in venda["partes"] if p["papel"] == "COMPRADOR")
    assert comprador["tipo_pessoa"] == "FISICA" and comprador["como_identificado"]
    assert venda["valor"] == {"valor": Decimal("111111.11"), "texto": "R$ 111.111,11", "rotulo": "preço"}
    assert venda["construtora"] == "CONSTRUTORA FICTÍCIA ALFA LTDA"
    assert _evento(tl, "R-3")["valor"]["rotulo"] == "dívida"
    cons = _evento(tl, "Av-5")
    assert [(p["papel"], p["nome"]) for p in cons["partes"]] == [("CREDOR", "BANCO FICTÍCIO S.A.")]
    abertura = _evento(tl, "Abertura")
    assert abertura["partes"][0]["papel"] == "PROPRIETARIO_ANTERIOR"             # houve transmissão posterior registrada
    # Av-4 cita a construtora como FIADORA: papel "outros", nunca inferido como devedor
    assert all(p["papel"] != "DEVEDOR" for p in _evento(tl, "Av-4")["partes"])


def test_idade_so_pela_conclusao_de_obra():
    tl = _linha()
    assert tl["idade"]["anos"] == 24 and tl["idade"]["estimada"] and "Av-4" in tl["idade"]["texto"]
    sem_obra = _linha(MATRICULA_LIMPA)                                            # tem compra e venda, sem conclusão de obra
    assert sem_obra["idade"] == {"anos": None, "estimada": False, "base": None, "texto": IDADE_NAO_DETERMINAVEL}


def test_datas_chave_para_a_estimativa_condominial():
    tl = _linha()
    assert tl["datas_chave"] == {"aquisicao": {"data": "2001-02-01", "ato": "R-2"}, "consolidacao": {"data": "2003-04-03", "ato": "Av-5"}}


def test_cpf_nunca_aparece_no_nome():
    texto = ["Matrícula nº 1\nPROPRIETÁRIA: CONSTRUTORA EXEMPLO LTDA.\n",
             "R-1 - Matrícula nº 1 - COMPRA E VENDA. VENDEDORA: CONSTRUTORA EXEMPLO LTDA; COMPRADOR: FULANO FICTÍCIO CPF 529.982.247-25; "
             "pelo preço de R$ 10,00.\n"]
    nomes = [p["nome"] for e in _linha(texto)["eventos"] for p in e["partes"]]
    assert any(n.startswith("FULANO FICTÍCIO") for n in nomes)
    assert not any("529.982.247-25" in n or "52998224725" in n for n in nomes)


def test_sem_matricula_nao_inventa(db):
    prop = _prop(db)
    out = timeline_for_property(db, prop.id)
    assert out["disponivel"] is False and out["eventos"] == [] and out["idade"]["texto"] == IDADE_NAO_DETERMINAVEL


def test_api_linha_do_tempo(api):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    up = client.post(f"/api/imoveis/{pid}/documentos", data={"document_type": "MATRICULA"},
                     files={"file": ("matricula.txt", "\n".join(MATRICULA_FICTICIA).encode(), "text/plain")})
    assert up.status_code in (200, 201), up.text
    body = client.get(f"/api/imoveis/{pid}/matricula/linha-do-tempo").json()
    assert body["disponivel"] and [e["ato"] for e in body["eventos"]][:3] == ["Abertura", "Av-1", "R-2"]
    assert body["eventos"][2]["valor"]["valor"] in ("111111.11", 111111.11)
    assert body["idade"]["estimada"] is True
