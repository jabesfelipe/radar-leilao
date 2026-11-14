"""Extração estruturada (v1.0.4): cada campo precisa de referência comprovada no TEXTO do documento.

Causa raiz da 1ª execução com a OpenAI real (caso-01): a validação comparava ``str(valor)`` com o ``value`` da
referência por igualdade exata — ``notice_date`` (date → "2024-10-10") contra "10 de outubro de 2024", e
``registration_number`` com grafias diferentes — e um único campo derrubava a extração inteira, enquanto o trecho
citado nunca era conferido. Documentos sintéticos; nenhuma chamada externa.
"""
from datetime import date
from decimal import Decimal

from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app.extraction import (
    CAMPO_EXTRAIDO, CAMPO_INCONCLUSIVO, CAMPO_NAO_ENCONTRADO, EXTRACAO_CONCLUIDA, EXTRACAO_ERRO, EXTRACAO_INCONCLUSIVA,
    EXTRACAO_NAO_ENCONTRADA, EXTRACAO_SEM_TEXTO, NoticeExtraction, RegistrationExtraction, extract_document,
)
from tests.test_extraction import FakeDb, FakeProvider, fake_rag, version_for

MATRICULA = ("OFICIAL DE REGISTRO DE IMÓVEIS FICTÍCIO DA COMARCA DE SÃO PAULO/SP\n"
             "MATRÍCULA Nº 99.901 — FICHA 01\n"
             "IMÓVEL: Apartamento nº 45, com área privativa de 62,00 m².\n"
             "Nada mais consta. São Paulo, 15 de outubro de 2024.")
EDITAL = ("EDITAL DE LEILÃO PÚBLICO EXTRAJUDICIAL — LEI Nº 9.514/1997\n"
          "1º leilão: 05/11/2024, às 10h00 — lance mínimo de R$ 400.000,00 (valor de avaliação).\n"
          "2º leilão: 12/11/2024, às 10h00 — lance mínimo de R$ 240.000,00.\n"
          "São Paulo, 10 de outubro de 2024. (Edital fictício, sem valor legal.)")
CHUNK_MAT = [{"chunk_id": 11, "page": None, "section": None, "content": MATRICULA}]
CHUNK_EDT = [{"chunk_id": 21, "page": None, "section": None, "content": EDITAL}]


def run(output, schema="MATRICULA"):
    return extract_document(FakeDb(version_for()), 1, 3, schema, LLMGateway(FakeProvider(output), "fake", "modelo"))


def test_matricula_com_numero_identificado_e_trecho_literal(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    out = RegistrationExtraction(registration_number="99.901", consultation_date=date(2024, 10, 15), references=[
        {"field": "registration_number", "value": "MATRÍCULA Nº 99.901", "chunk_id": 11, "excerpt": "MATRÍCULA Nº 99.901 — FICHA 01"},
        {"field": "consultation_date", "value": "15 de outubro de 2024", "chunk_id": 11, "excerpt": "São Paulo, 15 de outubro de 2024."}])
    result = run(out)
    assert result.success and result.extraction_status == EXTRACAO_CONCLUIDA
    assert result.output.registration_number == "99.901" and result.output.consultation_date == date(2024, 10, 15)
    assert result.field_status["registration_number"]["status"] == CAMPO_EXTRAIDO
    assert result.field_status["consultation_date"]["status"] == CAMPO_EXTRAIDO


def test_numero_da_matricula_sem_pontuacao_confere_pelos_digitos(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    out = RegistrationExtraction(registration_number="99901", references=[{"field": "registration_number", "value": "99901", "chunk_id": 11}])
    result = run(out)
    assert result.success and result.output.registration_number == "99901"
    # Sem trecho informado pelo modelo, o trecho literal é retirado do PRÓPRIO documento.
    assert "99.901" in result.output.references[0].excerpt


def test_matricula_sem_numero_e_ausencia_legitima(monkeypatch):
    fake_rag(monkeypatch, chunks=[{"chunk_id": 11, "page": None, "section": None, "content": "Certidão de ônus sem identificação do número."}])
    result = run(RegistrationExtraction(registration_number=None, references=[]))
    assert result.success and result.extraction_status == EXTRACAO_NAO_ENCONTRADA
    assert result.field_status["registration_number"] == {"status": CAMPO_NAO_ENCONTRADO}


def test_edital_com_data_por_extenso_identificada(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_EDT)
    out = NoticeExtraction(notice_date=date(2024, 10, 10), minimum_value=Decimal("240000.00"), appraisal_value=Decimal("400000"), references=[
        {"field": "notice_date", "value": "10 de outubro de 2024", "chunk_id": 21, "excerpt": "São Paulo, 10 de outubro de 2024."},
        {"field": "minimum_value", "value": "R$ 240.000,00", "chunk_id": 21, "excerpt": "2º leilão: 12/11/2024, às 10h00 — lance mínimo de R$ 240.000,00."},
        {"field": "appraisal_value", "value": "R$ 400.000,00", "chunk_id": 21}])
    result = run(out, "EDITAL")
    assert result.success
    assert result.output.notice_date == date(2024, 10, 10) and result.output.minimum_value == Decimal("240000.00")
    assert result.output.appraisal_value == Decimal("400000")
    assert all(result.field_status[f]["status"] == CAMPO_EXTRAIDO for f in ("notice_date", "minimum_value", "appraisal_value"))


def test_edital_sem_data_nao_e_erro(monkeypatch):
    fake_rag(monkeypatch, chunks=[{"chunk_id": 21, "page": None, "section": None, "content": "2º leilão — lance mínimo de R$ 240.000,00."}])
    out = NoticeExtraction(notice_date=None, minimum_value=Decimal("240000"), references=[{"field": "minimum_value", "value": "R$ 240.000,00", "chunk_id": 21}])
    result = run(out, "EDITAL")
    assert result.success and result.field_status["notice_date"]["status"] == CAMPO_NAO_ENCONTRADO


def test_referencia_de_pagina_inexistente_e_rejeitada(monkeypatch):
    fake_rag(monkeypatch, chunks=[{"chunk_id": 11, "page": 1, "section": None, "content": MATRICULA}])
    out = RegistrationExtraction(registration_number="99.901", references=[{"field": "registration_number", "value": "99.901", "chunk_id": 11, "page": 7}])
    result = run(out)
    assert not result.success and result.extraction_status == EXTRACAO_INCONCLUSIVA
    assert "página 7" in result.field_status["registration_number"]["motivo"]


def test_trecho_que_nao_existe_no_documento_e_rejeitado(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    out = RegistrationExtraction(registration_number="99.901", references=[{"field": "registration_number", "value": "99.901", "chunk_id": 11, "excerpt": "Matrícula 99.901 registrada em 2019 pelo cartório central"}])
    result = run(out)
    assert not result.success and result.output is None
    assert result.field_status["registration_number"]["status"] == CAMPO_INCONCLUSIVO
    assert "não aparece no documento" in result.field_status["registration_number"]["motivo"]


def test_documento_com_mais_de_um_trecho_corrige_chunk_id_errado(monkeypatch):
    # Documento em dois trechos (ex.: duas páginas): a data está no 2º, o modelo citou o 1º.
    chunks = [{"chunk_id": 31, "page": 1, "section": None, "content": "EDITAL DE LEILÃO. 1º leilão: 05/11/2024."},
              {"chunk_id": 32, "page": 2, "section": None, "content": "São Paulo, 10 de outubro de 2024. (Edital fictício.)"}]
    fake_rag(monkeypatch, chunks=chunks)
    out = NoticeExtraction(notice_date=date(2024, 10, 10), references=[{"field": "notice_date", "value": "10 de outubro de 2024", "chunk_id": 31, "excerpt": "São Paulo, 10 de outubro de 2024."}])
    result = run(out, "EDITAL")
    assert result.success and result.field_status["notice_date"] == {"status": CAMPO_EXTRAIDO, "chunk_id": 32, "page": 2}


def test_texto_ocr_com_espacos_e_quebras_irregulares(monkeypatch):
    ocr = "MATRÍCULA   Nº 99.901\n—   FICHA 01\nIMÓVEL:  Apartamento nº 45,\n\ncom área privativa de 62,00 m²."
    fake_rag(monkeypatch, chunks=[{"chunk_id": 11, "page": 1, "section": None, "content": ocr}])
    out = RegistrationExtraction(registration_number="99.901", references=[{"field": "registration_number", "value": "99.901", "chunk_id": 11, "excerpt": "MATRÍCULA Nº 99.901 — FICHA 01"}])
    assert run(out).field_status["registration_number"]["status"] == CAMPO_EXTRAIDO


def test_valor_que_nao_esta_no_documento_e_rejeitado_mesmo_com_trecho_valido(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    out = RegistrationExtraction(registration_number="12.345", references=[{"field": "registration_number", "value": "12.345", "chunk_id": 11, "excerpt": "MATRÍCULA Nº 99.901"}])
    result = run(out)
    assert not result.success and "não contém o valor" in result.field_status["registration_number"]["motivo"]


def test_campo_associado_a_trecho_de_outro_documento_e_rejeitado(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    # chunk 999 não pertence a esta versão de documento (ex.: edital ou outro imóvel).
    out = RegistrationExtraction(registration_number="99.901", references=[{"field": "registration_number", "value": "99.901", "chunk_id": 999}])
    result = run(out)
    assert not result.success and "não pertence a este documento" in result.field_status["registration_number"]["motivo"]


def test_extracao_parcial_preserva_campos_validos_e_descarta_o_invalido(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    out = RegistrationExtraction(registration_number="99.901", comarca="Campinas", references=[
        {"field": "registration_number", "value": "99.901", "chunk_id": 11},
        {"field": "comarca", "value": "Campinas", "chunk_id": 11}])
    result = run(out)
    assert result.success and result.output.registration_number == "99.901" and result.output.comarca is None
    assert result.field_status["comarca"]["status"] == CAMPO_INCONCLUSIVO
    assert [r.field for r in result.output.references] == ["registration_number"]


def test_resposta_malformada_do_modelo_e_erro(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    result = run({"consultation_date": "ontem"})
    assert not result.success and result.extraction_status == EXTRACAO_ERRO and result.call.status == "ERRO"


def test_resposta_incompleta_campo_sem_referencia_e_inconclusiva(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    result = run({"registration_number": "99.901"})   # sem "references"
    assert not result.success and result.extraction_status == EXTRACAO_INCONCLUSIVA
    # A chamada foi feita e cobrada: os tokens continuam no registro (llm_run), mesmo sem extração concluída.
    assert result.call.input_tokens == 10 and result.call.status == "ERRO"


def test_documento_sem_texto_nao_chama_o_provider(monkeypatch):
    fake_rag(monkeypatch, chunks=[])

    class NaoDeveChamar(FakeProvider):
        def structured_chat(self, *args, **kwargs):
            raise AssertionError("não deve chamar o provider sem texto")

    result = extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(NaoDeveChamar(None), "fake", "modelo"))
    assert result.extraction_status == EXTRACAO_SEM_TEXTO and result.call.status == "IGNORADO"
    assert result.call.input_tokens is None


def test_falha_de_comunicacao_com_openai_e_erro_sem_extracao(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_MAT)

    class APIConnectionError(Exception):
        pass

    class Fora(FakeProvider):
        def structured_chat(self, *args, **kwargs):
            raise APIConnectionError("Connection error.")

    result = extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(Fora(None), "fake", "modelo"))
    assert result.extraction_status == EXTRACAO_ERRO and result.call.error_category == "CONEXAO" and result.output is None


def test_nome_de_campo_com_outra_grafia_e_reconhecido(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_EDT)
    out = NoticeExtraction(notice_date=date(2024, 10, 10), references=[{"field": "Notice Date", "value": "10 de outubro de 2024", "chunk_id": 21}])
    assert run(out, "EDITAL").field_status["notice_date"]["status"] == CAMPO_EXTRAIDO


def test_referencia_com_nome_de_campo_errado_vale_so_se_o_trecho_contem_o_valor(monkeypatch):
    # 1ª execução real v1.0.4: o modelo preencheu field="property_id" (copiado do cabeçalho) em todas as referências.
    fake_rag(monkeypatch, chunks=CHUNK_EDT)
    out = NoticeExtraction(minimum_value=Decimal("240000"), notice_date=date(2024, 10, 10), references=[
        {"field": "property_id", "value": "1", "chunk_id": 21, "excerpt": "2º leilão: 12/11/2024, às 10h00 — lance mínimo de R$ 240.000,00."},
        {"field": "property_id", "value": "1", "chunk_id": 21, "excerpt": "1º leilão: 05/11/2024, às 10h00"}])
    result = run(out, "EDITAL")
    assert result.success and result.output.minimum_value == Decimal("240000")
    assert "reatribuído" in result.field_status["minimum_value"]["referencia"]
    # nenhum trecho informado contém a data do edital: o campo é descartado (não se procura o valor no documento inteiro)
    assert result.field_status["notice_date"]["status"] == CAMPO_INCONCLUSIVO and result.output.notice_date is None
    assert [(r.field, r.value) for r in result.output.references] == [("minimum_value", "240000")]


def test_valor_numerico_na_referencia_e_aceito_como_texto(monkeypatch):
    # function calling (não estrito): o modelo devolveu references[].value = 400000.0 na execução real v1.0.4.
    fake_rag(monkeypatch, chunks=CHUNK_EDT)
    result = run({"appraisal_value": 400000.0, "references": [{"field": "appraisal_value", "value": 400000.0, "chunk_id": 21, "excerpt": "lance mínimo de R$ 400.000,00 (valor de avaliação)"}]}, "EDITAL")
    assert result.success and result.output.appraisal_value == Decimal("400000")
    assert result.output.references[0].value == "400000"


def test_contexto_enviado_ao_extrator_nao_tem_metadados_do_rag(monkeypatch):
    fake_rag(monkeypatch, chunks=[{"chunk_id": 11, "page": None, "section": None, "content": MATRICULA, "property_id": 1, "document_id": 2, "final_score": 0.9}])
    capturado = {}

    class Espiao(FakeProvider):
        def structured_chat(self, schema, messages, **kwargs):
            capturado["user"] = messages[-1]["content"]
            return super().structured_chat(schema, messages, **kwargs)

    extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(Espiao(RegistrationExtraction()), "fake", "modelo"))
    assert "[chunk_id=11]" in capturado["user"] and "property_id" not in capturado["user"] and "final_score" not in capturado["user"]


class LengthFinishReasonError(Exception):
    """Mesmo nome da exceção do SDK para resposta truncada pelo limite de saída."""


class _Sequencia(FakeProvider):
    def __init__(self, respostas):
        super().__init__(None); self.respostas = list(respostas); self.chamadas = 0; self.prompts = []

    def structured_chat(self, schema, messages, **kwargs):
        self.chamadas += 1; self.prompts.append(messages[0]["content"])
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return ProviderResponse(content=resposta, input_tokens=10, output_tokens=5)


TRUNCADA = "Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=1500, prompt_tokens=1402, total_tokens=2902)"


def test_resposta_truncada_tem_uma_unica_nova_tentativa_minima_e_as_duas_chamadas_ficam_registradas(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_EDT)
    ok = NoticeExtraction(minimum_value=Decimal("240000"), references=[{"field": "minimum_value", "value": "R$ 240.000,00", "chunk_id": 21}])
    provider = _Sequencia([LengthFinishReasonError(TRUNCADA), ok])
    result = extract_document(FakeDb(version_for()), 1, 3, "EDITAL", LLMGateway(provider, "fake", "modelo"))
    assert result.success and provider.chamadas == 2 and "RESPOSTA MÍNIMA" in provider.prompts[1]
    [anterior] = result.previous_calls
    assert anterior.error_category == "LIMITE_DE_SAIDA" and anterior.output_tokens == 1500 and anterior.input_tokens == 1402


def test_segunda_resposta_truncada_encerra_em_erro_sem_terceira_chamada(monkeypatch):
    fake_rag(monkeypatch, chunks=CHUNK_EDT)
    provider = _Sequencia([LengthFinishReasonError(TRUNCADA), LengthFinishReasonError(TRUNCADA)])
    result = extract_document(FakeDb(version_for()), 1, 3, "EDITAL", LLMGateway(provider, "fake", "modelo"))
    assert not result.success and result.extraction_status == EXTRACAO_ERRO and provider.chamadas == 2
    assert len(result.previous_calls) == 1 and result.call.output_tokens == 1500


def test_persistencia_grava_origem_forca_e_trecho_da_fonte(monkeypatch):
    from backend.app import models
    from backend.app.extraction import persist_extraction
    fake_rag(monkeypatch, chunks=CHUNK_MAT)
    out = RegistrationExtraction(registration_number="99.901", references=[{"field": "registration_number", "value": "99.901", "chunk_id": 11, "excerpt": "MATRÍCULA Nº 99.901"}])
    db = FakeDb(version_for())
    result = run(out)
    captured = {}
    monkeypatch.setattr("backend.app.extraction.normalize_documentary_evidence", lambda **kw: captured.update(kw) or models.Evidence(id=1))
    persist_extraction(db, db.prop, result)
    assert captured["origin"] == "DOCUMENTO" and captured["strength"] == "FORTE" and captured["agent"] == "extracao_documental"
    assert captured["source_excerpt"] == "MATRÍCULA Nº 99.901" and captured["chunk_id"] == 11
