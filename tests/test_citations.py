"""Validação de citações (v1.0.4): o trecho "literal" precisa vir do documento e sustentar a afirmação.

Casos reais da 1ª execução com a OpenAI (caso-01, sintético): números do snapshot financeiro atribuídos ao edital,
pergunta do checklist apresentada como trecho literal e afirmações sem relação com o chunk citado.
"""
from datetime import date
from decimal import Decimal

from backend.app.citations import (
    FORTE, FRACA, INVALIDA, MODERADA, assess_citation, best_window, excerpt_in_text, numbers_in, value_in_text,
)

EDITAL = ("3. SITUAÇÃO DO IMÓVEL: o imóvel encontra-se OCUPADO. A desocupação é de responsabilidade e\n"
          "custo exclusivos do arrematante, inclusive eventual ação de imissão na posse. Não há visitação interna. "
          "O imóvel é vendido em caráter \"ad corpus\", no estado em que se encontra.\n"
          "5. PAGAMENTO: à vista, em até 24 horas após o encerramento do leilão, por transferência\n"
          "bancária. Não se admite parcelamento nem utilização de FGTS.\n"
          "6. COMISSÃO DO LEILOEIRO: 5% (cinco por cento) sobre o valor do arremate.")
MATRICULA = ("AV.3/99.901 — Em 14/08/2021. PENHORA. Procede-se à averbação da penhora determinada nos autos\n"
             "da reclamação trabalhista nº 0001234-56.2020.5.02.0001, para garantia do débito de R$ 37.500,00.")
PERGUNTA = "A vaga de garagem possui matrícula própria?"


def test_trecho_literal_que_cobre_a_afirmacao_e_forte():
    r = assess_citation("Imóvel ocupado; desocupação por conta do arrematante", EDITAL, "o imóvel encontra-se OCUPADO. A desocupação é de responsabilidade e custo exclusivos do arrematante")
    assert r.strength == FORTE and r.is_proof


def test_quebras_de_linha_espacos_aspas_e_acentos_sao_normalizados():
    assert excerpt_in_text("A desocupação é de responsabilidade e custo exclusivos", EDITAL)
    assert excerpt_in_text("vendido em caráter ad corpus", EDITAL)
    assert excerpt_in_text("A DESOCUPACAO E DE RESPONSABILIDADE", EDITAL)


def test_marcador_de_mascaramento_copiado_pelo_modelo_vale_como_lacuna():
    # O gateway envia "CPF [CPF]"; o modelo copia o marcador no trecho (1ª execução real v1.0.4, campo holder).
    texto = "Proprietário: Carlos Eduardo Teste Silva, brasileiro, CPF 111.222.333-96, pelo valor de R$ 310.000,00."
    assert excerpt_in_text("Proprietário: Carlos Eduardo Teste Silva, brasileiro, CPF [CPF], pelo valor", texto)
    assert not excerpt_in_text("Proprietário: Outra Pessoa, CPF [CPF]", texto)


def test_reticencias_separam_partes_que_precisam_aparecer_em_ordem():
    assert excerpt_in_text("PAGAMENTO: à vista ... Não se admite parcelamento", EDITAL)
    assert not excerpt_in_text("Não se admite parcelamento ... PAGAMENTO: à vista", EDITAL)


def test_trecho_que_nao_existe_no_documento_e_invalido():
    r = assess_citation("O imóvel está livre de ônus", MATRICULA, "Nada consta: imóvel livre e desembaraçado")
    assert r.strength == INVALIDA and not r.is_proof and r.excerpt is None


def test_pergunta_do_checklist_nunca_e_trecho_literal():
    documento = MATRICULA + "\n" + PERGUNTA   # mesmo que o texto da pergunta aparecesse no documento
    r = assess_citation("O imóvel possui matrícula própria para a vaga", documento, PERGUNTA, forbidden=[PERGUNTA])
    assert r.strength == INVALIDA and "checklist" in r.reason


def test_resposta_ou_resumo_do_modelo_nao_e_trecho_literal():
    r = assess_citation("Há penhora trabalhista", MATRICULA, "Existe uma penhora trabalhista averbada na matrícula do imóvel")
    assert r.strength == INVALIDA


def test_valor_do_snapshot_financeiro_atribuido_ao_documento_e_invalido():
    # 1ª execução: "O resultado líquido da operação é de R$ -26.550,00" citando o edital.
    r = assess_citation("O resultado líquido da operação é de R$ -26.550,00", EDITAL)
    assert r.strength == INVALIDA and "26550" in r.reason.replace(".", "")
    r2 = assess_citation("O preço médio dos comparáveis de venda é R$ 329.466,67", EDITAL, "preco_medio: 329466.6666666667")
    assert r2.strength == INVALIDA


def test_percentual_calculado_pelo_modelo_nao_invalida_sozinho_mas_nao_vira_prova():
    r = assess_citation("O ROI da operação é de -7,78%", EDITAL)
    assert r.strength in (FRACA, INVALIDA) and not r.is_proof


def test_afirmacao_sem_trecho_informado_usa_frase_do_proprio_documento():
    r = assess_citation("Pagamento à vista em 24 horas, sem FGTS; comissão do leiloeiro de 5%", EDITAL)
    assert r.is_proof and r.strength == MODERADA       # derivado da fonte: nunca FORTE
    assert r.excerpt and r.excerpt in EDITAL


def test_trecho_generico_que_nao_comprova_a_afirmacao_e_fraco():
    r = assess_citation("Divergência de área entre matrícula e edital", MATRICULA)
    assert r.strength == FRACA and not r.is_proof


def test_chunk_vazio_e_invalido():
    assert assess_citation("qualquer fato", "").strength == INVALIDA


def test_numeros_em_formato_brasileiro():
    assert Decimal("240000") in numbers_in("lance mínimo de R$ 240.000,00")
    assert Decimal("62") in numbers_in("área privativa de 62,00 m²")
    assert numbers_in("AV.3 e 1 vaga") == set()


def test_valor_tipado_em_qualquer_grafia():
    assert value_in_text(date(2024, 10, 10), "São Paulo, 10 de outubro de 2024.")
    assert value_in_text(date(2024, 11, 12), "2º leilão: 12/11/2024, às 10h00")
    assert value_in_text(Decimal("240000.00"), "lance mínimo de R$ 240.000,00")
    assert value_in_text("99901", "MATRÍCULA Nº 99.901 — FICHA 01")
    assert not value_in_text("RI", "Matrícula 123")       # sem casar pedaço de palavra
    assert not value_in_text(date(2024, 10, 11), "São Paulo, 10 de outubro de 2024.")


def test_janela_literal_vem_do_documento():
    assert "penhora" in best_window("penhora trabalhista", MATRICULA).lower()
    assert best_window("assunto inexistente", MATRICULA) == ""
