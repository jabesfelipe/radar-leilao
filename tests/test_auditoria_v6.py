"""Auditoria da análise v6 (imóvel 7) — correções de extração, integração e apresentação. Dados fictícios.

A matrícula de teste reproduz o LAYOUT da matrícula real (OCR em colunas: a fiança e o "alienou fiduciariamente" aparecem
junto ao Av-4), com nomes, números e datas inventados.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app import debts_service, models, parameters as params
from backend.app.checklist_evidence import _quitacao_upper_bound
from backend.app.parameter_seeds import seed_parameters
from backend.app.privacy import redact_pii
from backend.app.registry_chain import VAGA, contract_terms, read_registry
from backend.app.registry_timeline import TITULARIDADE_NAO_CONFIRMADA, build_timeline, holder_summary, timeline_for_property, titularity
from backend.app.viability import debt_exposure, market_intelligence
from tests.test_checklist_evidencias import CONDICOES_FICTICIAS, _analisar, _doc, _itens, _leilao, _prop
from tests.test_v107_imovel7_regressao import COMPRADOR, MATRICULA_FICTICIA, _chunks
from tests.test_v2_venda_direta_integracao import _sem_chave, api  # noqa: F401 (fixtures)

CPF_OCR = "529.98t.247-25"   # CPF fictício com erro de OCR (letra no lugar de dígito)

# Mesma matrícula fictícia, com os trechos que a auditoria encontrou na real: vaga como direito de uso descrito ANTES da
# palavra "vaga", prazo e 1ª prestação no R-3 e CPF do comprador lido com erro de OCR.
MATRICULA_V6 = [
    MATRICULA_FICTICIA[0].replace(
        "fração ideal do solo.\n",
        "fração ideal do solo, direito de uso exclusivo de uma área descoberta de 12,0000m:?, referente a VAGA 01 de estacionamento, "
        "localizada no Térreo (Geral).\n"),
    MATRICULA_FICTICIA[1].replace("brasileiro, solteiro,", f"brasileiro, solteiro, portador do CPF/MF nº {CPF_OCR},")
                         .replace("constituiu RET.", "constituiu RET. FUNREJUS não incidente, conforme Lei nº 12.604, de 02/07/1999."),
    MATRICULA_FICTICIA[2].replace(
        "para garantia da dívida no valor de R$ 99.999,99.\n",
        "para garantia da dívida no valor de R$ 99.999,99, a ser reembolsada no PRAZO de 360 (trezentos e sessenta meses), com vencimento "
        "da primeira prestação em 01 de março de 2001.\n"),
    MATRICULA_FICTICIA[3],
]
CONSTRUTORA = "CONSTRUTORA FICTÍCIA ALFA LTDA"
CREDOR = "BANCO FICTÍCIO S.A"   # como a cadeia registral normaliza o nome (sem o ponto final)


def _chain(texts=MATRICULA_V6):
    return read_registry(_chunks(texts), 77)


def _timeline(chain):
    return build_timeline(chain, {"document_id": 1, "document_version_id": 77, "nome": "matricula.txt"}, date(2026, 6, 1))


def _imovel(db, matricula=MATRICULA_V6, city="Cidade Fictícia"):
    prop = _prop(db)
    prop.city = city
    _leilao(db, prop)
    _doc(db, prop, "\n".join(matricula), "matricula.txt", "MATRICULA")
    _doc(db, prop, CONDICOES_FICTICIAS, "condicoes.txt", "CONDICOES_VENDA")
    db.flush(); db.expire(prop)
    return prop


# =============================================================== titularidade histórica x atual

def test_titular_atual_e_o_da_consolidacao_e_a_construtora_fica_historica():
    chain = _chain()
    tit = titularity(chain, _timeline(chain))
    assert tit["titular_atual"] == CREDOR and tit["ato"] == "Av-5" and tit["situacao"] == "DETERMINADA" and tit["confianca"] == "ALTA"
    atuais = [p for p in tit["partes"] if p["status"] == "ATUAL"]
    assert atuais and all(p["nome"].startswith("BANCO FICTÍCIO") and p["ato"] == "Av-5" for p in atuais)
    construtora = [p for p in tit["partes"] if p["nome"] == CONSTRUTORA]
    assert construtora and all(p["status"] == "HISTORICO" for p in construtora)
    papeis = {p["papel"] for p in construtora}
    assert any(p.startswith("Proprietária(o) original") for p in papeis) and any(p.startswith("Vendedor") for p in papeis)
    fianca = next(p for p in construtora if p["papel"].startswith("Fiadora"))
    # OCR em colunas: a fiança foi lida junto ao Av-4, mas o trecho ("alienou fiduciariamente") é do R-3 (conferido no PDF real)
    assert "não é titular" in fianca["papel"] and fianca["ato"] == "R-3" and fianca["confianca"] == "MEDIA" and "Av-4" in fianca["observacao"]
    credor_r3 = next(p for p in tit["partes"] if p["papel"].startswith("Credor") and p["ato"] == "R-3")
    assert credor_r3["status"] == "HISTORICO" and credor_r3["trecho"]
    devedor = next(p for p in tit["partes"] if p["papel"].startswith("Devedor"))
    assert devedor["nome"] == COMPRADOR and devedor["ato"] == "R-3" and devedor["confianca"] == "MEDIA" and "inferido" in devedor["papel"]
    for p in tit["partes"]:
        assert p["papel"] and p["status"] in ("ATUAL", "HISTORICO") and p["confianca"] and (p["trecho"] or p["como_identificado"])


def test_sem_ato_de_transmissao_legivel_titularidade_nao_confirmada():
    chain = _chain([MATRICULA_V6[0]])                                              # só a abertura
    tit = titularity(chain, _timeline(chain))
    assert tit["titular_atual"] is None and tit["texto"].startswith(TITULARIDADE_NAO_CONFIRMADA)
    assert all(p["status"] == "HISTORICO" for p in tit["partes"])


def test_titular_gravado_no_cadastro_nao_prevalece_sobre_a_matricula(db):
    prop = _imovel(db)
    db.add(models.PropertyRegistration(property_id=prop.id, registration_number="99.999", holder=CONSTRUTORA)); db.flush()
    resumo = holder_summary(db, prop.id, CONSTRUTORA)
    assert resumo["titular_atual"] == CREDOR and resumo["divergencia_cadastro"] is True and "não é o titular atual" in resumo["texto"]
    from backend.app.services import _front_summary_matricula
    frente = _front_summary_matricula(db, prop)
    assert frente["titular"] == CREDOR and frente["titularidade"]["titular_cadastro"] == CONSTRUTORA
    assert timeline_for_property(db, prop.id)["titularidade"]["titular_atual"] == CREDOR


def test_api_matricula_traz_titularidade(api):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    client.post(f"/api/imoveis/{pid}/documentos", data={"document_type": "MATRICULA"},
                files={"file": ("matricula.txt", "\n".join(MATRICULA_V6).encode(), "text/plain")})
    client.post(f"/api/imoveis/{pid}/matricula", json={"registration_number": "99.999", "holder": CONSTRUTORA})
    body = client.get(f"/api/imoveis/{pid}/matricula").json()
    assert body["atual"]["holder"] == CONSTRUTORA                                  # cadastro preservado
    assert body["titularidade"]["titular_atual"] == CREDOR and body["titularidade"]["divergencia_cadastro"] is True
    linha = client.get(f"/api/imoveis/{pid}/matricula/linha-do-tempo").json()
    assert linha["titularidade"]["titular_atual"] == CREDOR


# =============================================================== linha do tempo para o investidor (revisão PR #8)

def _ev(tl, ato):
    return next(e for e in tl["eventos"] if e["ato"] == ato)


def test_historico_do_mais_recente_para_o_mais_antigo_pelo_numero_do_ato():
    tl = _timeline(_chain())
    assert [e["ato"] for e in tl["eventos"]] == ["Abertura", "Av-1", "R-2", "R-3", "Av-4", "Av-5"]        # contrato antigo preservado
    # R-2 e R-3 têm a mesma data: a ordem vem do número do ato, não da data nem da ordem do OCR
    assert [e["ato"] for e in tl["eventos_recentes_primeiro"]] == ["Av-5", "Av-4", "R-3", "R-2", "Av-1", "Abertura"]


def test_ordem_com_ato_sem_numero_e_datas_ausentes():
    from backend.app.registry_timeline import most_recent_first
    eventos = [{"ato": "Abertura", "numero": 0, "data": None}, {"ato": "R-2", "numero": 2, "data": "2001-01-01"},
               {"ato": "?", "numero": None, "data": None}, {"ato": "Av-3", "numero": 3, "data": None}]
    assert [e["ato"] for e in most_recent_first(eventos)] == ["Av-3", "?", "R-2", "Abertura"]


def test_data_de_lei_citada_no_ato_nao_vira_data_do_ato():
    av1 = _ev(_timeline(_chain()), "Av-1")
    assert av1["data"] is None and av1["data_texto"] is None and av1["titulo_simples"]   # protocolo ilegível: sem data, nunca a da lei


def test_titulo_explicacao_e_envolvidos_em_linguagem_simples():
    tl = _timeline(_chain())
    cons, af, venda, obra = _ev(tl, "Av-5"), _ev(tl, "R-3"), _ev(tl, "R-2"), _ev(tl, "Av-4")
    assert cons["titulo_simples"] == "BANCO FICTÍCIO S.A. passou a ser proprietária do imóvel" and cons["ato_descricao"].startswith("Av-5 — ")
    assert "certidão de não pagamento após a intimação por edital" in cons["explicacao"]           # o ato cita a certidão pós edital
    assert f"registrado no R-3, em nome de {COMPRADOR}" in cons["explicacao"]                       # Av-5 não repete o devedor
    assert ("Novo proprietário (banco credor)") in [p["papel"] for p in cons["envolvidos"]]
    assert af["titulo_simples"] == "O imóvel foi dado em garantia de um financiamento com BANCO FICTÍCIO S.A."
    assert af["envolvidos"][0]["nome"] == COMPRADOR and af["envolvidos"][0]["papel"].startswith("Devedor do financiamento")
    assert any(p["nome"] == CONSTRUTORA and "garantia pessoal" in p["papel"] for p in af["envolvidos"])
    assert venda["titulo_simples"] == f"{COMPRADOR} comprou o imóvel" and "pelo preço de R$ 111.111,11" in venda["explicacao"]
    assert {p["papel"] for p in venda["envolvidos"]} == {"Vendedor", "Comprador"}
    # trecho do R-3 lido junto ao Av-4: pessoas vão para o R-3 e o Av-4 avisa; não muda o proprietário
    assert obra["aviso_ocr"] and "R-3" in obra["aviso_ocr"] and obra["partes"] == [] and "Não muda" in obra["explicacao"]
    assert any(p.get("realocado_de") == "Av-4" for p in af["partes"])
    for e in tl["eventos"]:
        assert e["evidencia"]["ato"] == e["ato"] and e["evidencia"]["trecho"] == e["trecho"] and e["explicacao"]
    assert not any("inadimpl" in e["explicacao"].lower() for e in tl["eventos"])                 # nada além do que o texto registra


def test_nome_da_caixa_cortado_pelo_ocr_vira_a_forma_canonica():
    from backend.app.registry_timeline import _person
    for texto in ("CAIXA ECONÔMICA", "CAIXA ECONOMICA FEDERAL-CEF"):
        assert _person(texto, 0, len(texto), "CREDOR", "teste")["nome"] == "CAIXA ECONÔMICA FEDERAL"


def test_ato_desconhecido_sem_partes_nao_inventa():
    from backend.app.registry_timeline import _plain_language
    out = _plain_language({"ato": "Av-9", "tipo": "OUTRO", "tipo_descricao": "Outro ato", "partes": [], "valor": None, "trecho": "Av-9 - ..."},
                          [], _chain(MATRICULA_FICTICIA[:1]))
    assert out["titulo_simples"].startswith("Outro ato registrado") and out["envolvidos"] == [] and "leia o trecho" in out["explicacao"]


def test_situacao_atual_em_destaque(db):
    prop = _imovel(db)
    sit = timeline_for_property(db, prop.id)["situacao_atual"]
    assert sit["titulo"] == f"Titular atual: {CREDOR}" and sit["ato"] == "Av-5" and "no Av-5, em 03/04/2003" in sit["texto"]
    assert sit["atencao"] and any("certidão atualizada" in a for a in sit["atencao"])
    vazio = timeline_for_property(db, _prop(db).id)["situacao_atual"]
    assert vazio["titulo"] == TITULARIDADE_NAO_CONFIRMADA and vazio["titular_atual"] is None


# =============================================================== extração da matrícula

def test_vaga_descrita_como_direito_de_uso_antes_da_palavra_vaga_e_vinculada():
    vaga = _chain().of(VAGA)
    assert [f.value for f in vaga] == ["VINCULADA"] and "direito de uso" in vaga[0].excerpt.lower()
    assert [f.value for f in _chain(MATRICULA_FICTICIA).of(VAGA)] == []           # sem vaga descrita: nada inventado


def test_item_16_vaga_vinculada_e_item_04_com_teto_calculado(db):
    execution, _ = _analisar(db, _imovel(db))
    itens = _itens(execution)
    vaga = itens["VAGA_MATRICULA"]
    assert vaga.state == "CONFIRMADO" and vaga.answer.startswith("Não.") and "vinculada" in vaga.answer
    quitacao = itens["QUITACAO_80"]
    assert quitacao.state == "PENDENTE"                                            # teto calculado não é o percentual pago
    assert "26 de 360" in quitacao.interpretation and "7,2%" in quitacao.interpretation and "não o valor pago" in quitacao.interpretation


def test_prazo_e_primeira_prestacao_lidos_no_registro_da_alienacao():
    chain = _chain()
    terms = contract_terms(chain)
    assert terms["ato"] == "R-3" and terms["prazo_meses"] == 360 and terms["primeira_prestacao"] == "2001-03-01"
    texto = _quitacao_upper_bound(chain, chain.consolidation)
    assert texto.startswith("Limite teórico pela própria matrícula: o contrato tinha prazo de 360 meses (R-3")
    assert "Isso não significa que esse percentual foi pago" in texto
    assert contract_terms(_chain(MATRICULA_FICTICIA)) is None and _quitacao_upper_bound(_chain(MATRICULA_FICTICIA), None) == ""


# =============================================================== privacidade (OCR)

def test_cpf_rotulado_com_erro_de_ocr_e_mascarado():
    assert redact_pii(f"portador do CPF/MF nº {CPF_OCR}, residente", force=True) == "portador do CPF/MF nº [CPF], residente"
    assert redact_pii("CPF do proprietário", force=True) == "CPF do proprietário"   # palavra depois do rótulo não é número
    chain = _chain()
    tl = _timeline(chain)
    textos = [e["trecho"] for e in tl["eventos"]] + [p["trecho"] or "" for p in titularity(chain, tl)["partes"]]
    assert not any("529.98" in t for t in textos)


# =============================================================== reforma: premissa padrão visível

def test_reforma_sem_vistoria_usa_premissa_padrao_identificada(db):
    prop = _imovel(db)
    reforma = next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == "reforma")
    assert reforma["status"] == "PENDENTE" and reforma["valor_base"] == Decimal("5230.00") and reforma["valor_conservador"] == Decimal("13075.00")
    assert reforma["tratamento_base"].startswith("Reforma estimada: R$ 5.230,00") and "premissa padrão do Radar" in reforma["tratamento_base"]
    assert reforma["confianca"] == "BAIXA" and reforma["premissa_padrao"] is True and "ESTIMATIVA" in reforma["observacao"]
    execution, _ = _analisar(db, prop)
    item = _itens(execution)["REFORMA_GRANDE"]
    assert item.state == "PENDENTE" and "premissa padrão do Radar" in item.interpretation and "R$ 5.230,00" in item.interpretation


def test_reforma_informada_substitui_a_premissa_padrao(db):
    prop = _prop(db)
    _leilao(db, prop, {"reforma": "8000"})
    db.flush(); db.expire(prop)
    reforma = next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == "reforma")
    assert reforma["status"] == "ESTIMADO" and reforma["valor"] == Decimal("8000.00") and not reforma.get("premissa_padrao")


# =============================================================== condomínio: estimativa pela matrícula integrada

def test_sem_valor_mensal_a_linha_diz_o_periodo_e_o_que_falta(db):
    prop = _imovel(db)
    info = debt_exposure(db, prop)["condominio_atraso"]
    assert info["fonte"] == "PENDENTE" and info["valor"] is None and "valor mensal" in info["estimativa_indisponivel"]["motivo"]
    linha = next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == "condominio_atraso")
    assert linha["status"] == "PENDENTE" and linha["valor_base"] is None                    # pendente nunca vira zero
    assert "Estimativa condominial pela matrícula" in linha["observacao"] and "01/02/2001 (matrícula (R-2))" in linha["observacao"]
    assert linha["estimativa_condominial"]["possivel"] is False


def test_com_valor_mensal_do_admin_a_estimativa_entra_automatica_e_identificada(db):
    seed_parameters(db)
    param = db.query(models.Parameter).filter(models.Parameter.key == "condominio.valor_mensal_referencia", models.Parameter.scope == "GLOBAL").one()
    params.update_parameter(db, param, {"value": "300"}, actor="admin", justification="teste")
    db.flush()
    prop = _imovel(db)
    info = debt_exposure(db, prop)["condominio_atraso"]
    assert info["fonte"] == "ESTIMATIVA" and info["estimativa"]["automatica"] is True and "não registrada" in info["estimativa"]["origem"]
    assert info["valor"] is None                                                            # estimativa nunca é dívida
    intel = market_intelligence(db, prop)
    linha = next(l for l in intel["custos"] if l["chave"] == "condominio_atraso")
    # regra da venda aplicada DEPOIS da estimativa: comprador até 10% da avaliação (R$ 22.000,00)
    assert linha["status"] == "ESTIMADO" and linha["valor_base"] == min(info["estimativa"]["base"], Decimal("22000.00")) and linha["valor_base"] > 0
    assert "ESTIMATIVA" in linha["observacao"]
    assert db.query(models.CondominiumEstimate).filter_by(property_id=prop.id).count() == 0   # nada gravado


# =============================================================== IPTU: orientação na linha pendente

def test_iptu_pendente_aponta_a_consulta_assistida_do_municipio(db):
    debts_service.seed_all(db); db.flush()
    prop = _imovel(db, city="Fazenda Rio Grande")
    linha = next(l for l in market_intelligence(db, prop)["custos"] if l["chave"] == "tributos_atraso")
    assert linha["status"] == "PENDENTE" and linha["valor_base"] is None
    assert "consulta manual assistida" in linha["observacao"] and linha["orientacao_iptu"]["municipio"] == "Fazenda Rio Grande/PR"


def test_api_orientacao_iptu_informa_o_titular_pela_matricula(api):
    client, _ = api
    from tests.mercado_imovel7_dados import IMOVEL7
    from tests.test_v2_venda_direta_integracao import _json
    pid = client.post("/api/imoveis", json={k: _json(v) for k, v in IMOVEL7.items()}).json()["id"]
    client.post(f"/api/imoveis/{pid}/documentos", data={"document_type": "MATRICULA"},
                files={"file": ("matricula.txt", "\n".join(MATRICULA_V6).encode(), "text/plain")})
    body = client.get(f"/api/imoveis/{pid}/debitos/orientacao-iptu").json()
    assert body["titular_matricula"]["nome"] == CREDOR and "proprietário anterior" in body["titular_matricula"]["aviso"]
