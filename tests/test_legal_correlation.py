"""Testes unitários da correlação determinística imóvel × processo.

Regra fundamental coberta: nome igual NUNCA confirma identidade (homônimo).
"""
from backend.app.legal_correlation import (
    CORRELATION_HIGH,
    CORRELATION_LOW,
    CORRELATION_MEDIUM,
    CORRELATION_UNCONFIRMED,
    PropertyProfile,
    ProcessParty,
    ProcessProfile,
    correlate,
    names_match,
    parties_from_payload,
)


def _proc(parties, comarca=None, tribunal=None, uf=None):
    return ProcessProfile(parties=parties, comarca=comarca, tribunal=tribunal, uf=uf)


def test_cpf_coincide_resulta_alta():
    prop = PropertyProfile(owner_name="Maria Souza", owner_cpf="123.456.789-00")
    proc = _proc([ProcessParty(name="Maria Souza", cpf="12345678900", role="REU")])
    result = correlate(prop, proc)
    assert result.level == CORRELATION_HIGH
    assert "cpf" in result.criteria


def test_cnpj_coincide_resulta_alta():
    prop = PropertyProfile(owner_name="Imobiliária X", owner_cnpj="12.345.678/0001-99")
    proc = _proc([ProcessParty(name="Imobiliaria X Ltda", cnpj="12345678000199", role="REU")])
    result = correlate(prop, proc)
    assert result.level == CORRELATION_HIGH
    assert "cnpj" in result.criteria


def test_nome_mais_comarca_resulta_media():
    prop = PropertyProfile(owner_name="Joao da Silva", comarca="Curitiba", state="PR")
    proc = _proc([ProcessParty(name="Joao da Silva", role="REU")], comarca="Curitiba", uf="PR")
    result = correlate(prop, proc)
    assert result.level == CORRELATION_MEDIUM
    assert "nome" in result.criteria


def test_nome_mais_uf_resulta_media():
    prop = PropertyProfile(owner_name="Joao da Silva", state="PR")
    proc = _proc([ProcessParty(name="Joao da Silva", role="REU")], uf="PR")
    result = correlate(prop, proc)
    assert result.level == CORRELATION_MEDIUM


def test_apenas_nome_semelhante_resulta_baixa_homonimo():
    # Nome igual sem CPF/CNPJ e sem comarca/UF compatível → BAIXA (possível homônimo).
    prop = PropertyProfile(owner_name="Joao da Silva", comarca="Curitiba", state="PR")
    proc = _proc([ProcessParty(name="Joao da Silva", role="REU")], comarca="São Paulo", uf="SP")
    result = correlate(prop, proc)
    assert result.level == CORRELATION_LOW
    assert "homônimo" in result.reason.lower()


def test_dados_insuficientes_resulta_nao_confirmada():
    prop = PropertyProfile(owner_name="Maria Souza")
    proc = _proc([ProcessParty(name="Outro Nome Qualquer", role="REU")])
    result = correlate(prop, proc)
    assert result.level == CORRELATION_UNCONFIRMED


def test_sem_proprietario_conhecido_resulta_nao_confirmada():
    prop = PropertyProfile()
    proc = _proc([ProcessParty(name="Alguem", cpf="99999999999")])
    result = correlate(prop, proc)
    assert result.level == CORRELATION_UNCONFIRMED


def test_nome_igual_nunca_confirma_identidade():
    # Mesmo com nome idêntico, SEM identificador a correlação não é ALTA.
    prop = PropertyProfile(owner_name="Carlos Pereira", comarca="Londrina", state="PR")
    proc = _proc([ProcessParty(name="Carlos Pereira")], comarca="Londrina", uf="PR")
    result = correlate(prop, proc)
    assert result.level != CORRELATION_HIGH


def test_cpf_diferente_nao_eleva_para_alta():
    prop = PropertyProfile(owner_name="Maria Souza", owner_cpf="11111111111")
    proc = _proc([ProcessParty(name="Maria Souza", cpf="22222222222")], uf="PR", comarca="Curitiba")
    result = correlate(prop, proc)
    assert result.level != CORRELATION_HIGH


def test_names_match_tokens_parciais():
    assert names_match("Joao Silva", "Joao da Silva Santos") is True
    assert names_match("Maria", "Maria") is True
    # Um único token diferente não casa.
    assert names_match("Joao", "Pedro") is False
    # Acentos/caixa normalizados.
    assert names_match("JOÃO", "joao") is True


def test_parties_from_payload_mapeia_documentos():
    partes = parties_from_payload([
        {"name": "Fulano", "cpf": "12345678900", "role": "REU"},
        {"name": "Empresa", "document_cnpj": "12345678000199", "role": "AUTOR"},
    ])
    assert partes[0].cpf == "12345678900"
    assert partes[1].cnpj == "12345678000199"
    assert partes[1].role == "AUTOR"
