"""JUR-04 — testes do Motor de Sinais Jurídicos (SignalEngine)."""
from __future__ import annotations

from judicial_api.enums import (
    JusticeType,
    SignalCategory,
    SignalEvidenceType,
    SignalSeverity,
)
from judicial_api.models import Movement, Party, Process, SearchRequest, Subject
from judicial_api.signals import SignalEngine, load_signal_rules
from judicial_api.signals.rules import SignalRule, normalize_text


def _process(**kw):
    base = dict(process_number="0000001-11.2020.8.16.0001", tribunal="TJPR", justice_type=JusticeType.STATE)
    base.update(kw)
    return Process(**base)


# ---------------------------------------------------------------------------
# Detecção por termos
# ---------------------------------------------------------------------------

def test_detecta_penhora_em_movimento():
    proc = _process(movements=[Movement(description="Determinada a PENHORA de bens do executado", source_identifier="m1")])
    signals = SignalEngine().analyze_process(proc)
    codes = {s.signal_code for s in signals}
    assert "PENHORA" in codes
    penhora = next(s for s in signals if s.signal_code == "PENHORA")
    assert penhora.category == SignalCategory.PATRIMONIAL
    assert penhora.severity == SignalSeverity.HIGH
    assert penhora.evidence_type == SignalEvidenceType.MOVEMENT
    assert penhora.source_identifier == "m1"
    assert 0.0 <= penhora.confidence <= 1.0


def test_detecta_por_assunto_e_classe():
    proc = _process(
        subjects=[Subject(name="Execução Fiscal", source_identifier="a1")],
        class_name="Usucapião Extraordinária",
    )
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc)}
    assert "EXECUCAO_FISCAL" in codes
    assert "USUCAPIAO" in codes


def test_normalizacao_ignora_acentos_e_caixa():
    assert normalize_text("EXECUÇÃO Fiscal") == "execucao fiscal"
    proc = _process(movements=[Movement(description="RECUPERAÇÃO JUDICIAL deferida")])
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc)}
    assert "RECUPERACAO_JUDICIAL" in codes


def test_sem_correspondencia_nao_gera_sinal():
    proc = _process(movements=[Movement(description="Conclusos para despacho")])
    assert SignalEngine().analyze_process(proc) == []


def test_nao_duplica_mesmo_codigo_no_mesmo_processo():
    proc = _process(movements=[
        Movement(description="penhora realizada"),
        Movement(description="nova penhora determinada"),
    ])
    penhoras = [s for s in SignalEngine().analyze_process(proc) if s.signal_code == "PENHORA"]
    assert len(penhoras) == 1


# ---------------------------------------------------------------------------
# Distinção processo × imóvel (evidência, nunca "imóvel penhorado")
# ---------------------------------------------------------------------------

def test_penhora_gera_evidencia_de_imovel_sem_afirmar():
    proc = _process(movements=[Movement(description="Penhora sobre imóvel")])
    signals = SignalEngine().analyze_process(proc)
    codes = {s.signal_code for s in signals}
    assert "PROPERTY_PENHORA_EVIDENCE" in codes
    ev = next(s for s in signals if s.signal_code == "PROPERTY_PENHORA_EVIDENCE")
    # é EVIDÊNCIA: menciona necessidade de validação registral, não afirma constrição
    assert "evidência processual" in ev.evidence_text
    assert "validação registral" in ev.evidence_text
    # nenhum sinal afirma que o imóvel está penhorado
    for s in signals:
        assert "está penhorado" not in s.evidence_text.lower()


def test_sinal_nao_patrimonial_nao_gera_property_evidence():
    proc = _process(subjects=[Subject(name="Inventário")])
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc)}
    assert "INVENTARIO" in codes
    assert not any(c.startswith("PROPERTY_") for c in codes)


# ---------------------------------------------------------------------------
# Homônimos
# ---------------------------------------------------------------------------

def test_homonimo_quando_pesquisa_por_nome_sem_documento():
    proc = _process(parties=[Party(name="JOÃO DA SILVA")])  # parte sem documento
    req = SearchRequest(name="João da Silva")  # sem cpf/cnpj
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" in codes


def test_sem_homonimo_quando_pesquisa_por_cpf():
    proc = _process(parties=[Party(name="JOÃO DA SILVA")])
    req = SearchRequest(name="João da Silva", cpf="12345678900")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" not in codes


def test_sem_homonimo_quando_parte_tem_documento():
    proc = _process(parties=[Party(name="JOÃO DA SILVA", document="12345678900", document_type="CPF")])
    req = SearchRequest(name="João da Silva")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" not in codes


def test_sem_request_nao_avalia_homonimo():
    proc = _process(parties=[Party(name="JOÃO DA SILVA")])
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc)}
    assert "HOMONYM_POSSIBLE" not in codes


# ---------------------------------------------------------------------------
# Homônimos — correspondência de nome por parte (correção de falsos positivos)
# ---------------------------------------------------------------------------

def test_homonimo_nome_correspondente_sem_documento():
    proc = _process(parties=[Party(name="MARIA SOUZA LIMA")])
    req = SearchRequest(name="Maria Souza Lima")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" in codes


def test_sem_homonimo_quando_nome_nao_corresponde():
    # Nenhuma parte tem nome parecido com o pesquisado, mesmo sem documento.
    proc = _process(parties=[Party(name="EMPRESA XPTO LTDA")])
    req = SearchRequest(name="João da Silva")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" not in codes


def test_homonimo_avalia_documento_na_parte_correspondente_nao_em_outras():
    # A parte correspondente (mesmo nome) NÃO tem documento; outra parte tem.
    # O documento da parte não relacionada não pode suprimir o sinal.
    proc = _process(parties=[
        Party(name="JOÃO DA SILVA"),  # correspondente, sem documento
        Party(name="BANCO CREDOR S.A.", document="11222333000181", document_type="CNPJ"),  # não relacionada
    ])
    req = SearchRequest(name="João da Silva")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" in codes


def test_sem_homonimo_quando_parte_correspondente_tem_documento():
    proc = _process(parties=[
        Party(name="JOÃO DA SILVA", document="12345678900", document_type="CPF"),
        Party(name="OUTRA PESSOA QUALQUER"),  # sem documento, mas não corresponde
    ])
    req = SearchRequest(name="João da Silva")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" not in codes


def test_homonimo_ignora_acentuacao_e_caixa_na_correspondencia():
    proc = _process(parties=[Party(name="joao da silva")])   # sem acento, minúsculo
    req = SearchRequest(name="JOÃO DA SÍLVA")                  # com acento, maiúsculo
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" in codes


def test_homonimo_nome_parcial_corresponde_a_nome_completo():
    # Nome pesquisado é subconjunto do nome completo da parte (tokens) => corresponde.
    proc = _process(parties=[Party(name="João Carlos da Silva")])
    req = SearchRequest(name="João da Silva")
    codes = {s.signal_code for s in SignalEngine().analyze_process(proc, req)}
    assert "HOMONYM_POSSIBLE" in codes


def test_evidencia_de_homonimo_nao_afirma_identidade():
    proc = _process(parties=[Party(name="JOÃO DA SILVA")])
    req = SearchRequest(name="João da Silva")
    sinal = next(s for s in SignalEngine().analyze_process(proc, req) if s.signal_code == "HOMONYM_POSSIBLE")
    texto = sinal.evidence_text.lower()
    # é EVIDÊNCIA de POSSÍVEL homônimo, não confirmação de identidade/homonímia
    assert "nome semelhante" in texto
    assert "não há evidência suficiente" in texto
    assert "confirmado" not in texto


# ---------------------------------------------------------------------------
# Regras versionadas
# ---------------------------------------------------------------------------

def test_regras_sao_versionadas_e_propagam_versao_no_sinal():
    proc = _process(movements=[Movement(description="penhora")])
    penhora = next(s for s in SignalEngine().analyze_process(proc) if s.signal_code == "PENHORA")
    assert penhora.rule_version >= 1


def test_engine_aceita_regras_injetadas():
    regra = SignalRule(
        signal_code="TESTE", name="Teste", category=SignalCategory.PATRIMONIAL,
        severity=SignalSeverity.LOW, base_confidence=0.9, terms=(normalize_text("termo especial"),), version=7,
    )
    proc = _process(movements=[Movement(description="Ocorreu um TERMO ESPECIAL no autos")])
    signals = SignalEngine(rules=[regra]).analyze_process(proc)
    assert len(signals) == 1
    assert signals[0].signal_code == "TESTE"
    assert signals[0].rule_version == 7
    assert signals[0].confidence == 0.9


def test_catalogo_padrao_carrega_regras_do_arquivo():
    rules = load_signal_rules()
    codes = {r.signal_code for r in rules}
    assert {"PENHORA", "EXECUCAO_FISCAL", "FALENCIA", "USUCAPIAO"}.issubset(codes)
    assert all(r.version >= 1 for r in rules)
