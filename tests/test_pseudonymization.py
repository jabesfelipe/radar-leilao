"""Pseudonimização de PESSOAS FÍSICAS (auditoria final — homologação v1.0.2).

Mostra o que é efetivamente removido do que sai para a OpenAI **e o que continua identificável**.
Regex de CPF/e-mail NÃO é anonimização: nomes só são trocados quando CONHECIDOS (cadastro estruturado
ou rótulo jurídico no texto). Os testes de "limite" documentam o risco residual de forma executável.
Provider falso captura o envio; nenhuma chamada à OpenAI.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from backend.app import models
from backend.app.ai.agents import DocumentAgent
from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app.config import settings
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.extraction import RegistrationExtraction, ExtractionReference, extract_document
from backend.app.privacy import NameAliaser

TITULAR = "Ana Paula Ferreira Lima"


# ---------------------------------------------------------------- aliaser (unidade)

def test_nome_conhecido_vira_papel_em_qualquer_caixa_e_acentuacao():
    a = NameAliaser()
    assert a.alias_for("João da Silva Santos", "TITULAR") == "[TITULAR]"
    saida = a.apply("Constou JOAO DA SILVA SANTOS como titular; joão da silva santos assinou. CPF 123.456.789-09.")
    assert "SILVA" not in saida.upper() and saida.count("[TITULAR]") == 2 and "[CPF]" in saida


def test_papeis_sao_numerados_e_distintos_para_pessoas_diferentes():
    a = NameAliaser()
    assert a.alias_for("Maria Souza Campos", "PARTE PASSIVA") == "[PARTE PASSIVA 1]"
    assert a.alias_for("Pedro Álvares Neto", "PARTE PASSIVA") == "[PARTE PASSIVA 2]"
    assert a.alias_for("maria souza campos", "PARTE PASSIVA") == "[PARTE PASSIVA 1]"   # mesma pessoa, mesmo apelido


def test_empresas_e_entes_publicos_permanecem_identificados():
    a = NameAliaser()
    for entidade in ("Banco Exemplo S.A.", "Condomínio Edifício Aurora", "Prefeitura Municipal de São Paulo", "Construtora Beta Ltda"):
        assert a.alias_for(entidade, "PARTE ATIVA") == entidade
    assert a.names == []


def test_restauracao_local_devolve_o_nome_original():
    a = NameAliaser()
    a.alias_for(TITULAR, "TITULAR")
    enviado = a.apply(f"O titular {TITULAR} constituiu alienação fiduciária.")
    assert TITULAR not in enviado
    assert a.restore(enviado.replace("O titular", "Segundo o registro, o titular")) == f"Segundo o registro, o titular {TITULAR} constituiu alienação fiduciária."
    assert a.restore_obj({"statement": ["[TITULAR] assinou"], "n": 1}) == {"statement": [f"{TITULAR} assinou"], "n": 1}


def test_aprende_nomes_apos_rotulos_juridicos_com_o_papel_do_rotulo():
    a = NameAliaser()
    texto = "R.3 - Proprietário: JOSÉ CARLOS DE OLIVEIRA, casado com Maria Helena Prado. Executado: Paulo Ricardo Mendes."
    a.learn_from_text(texto)
    saida = a.apply(texto)
    for nome in ("JOSÉ CARLOS", "OLIVEIRA", "Maria Helena", "Paulo Ricardo"):
        assert nome not in saida, saida
    assert "[PROPRIETARIO 1]" in saida and "[EXECUTADO 1]" in saida and "[CONJUGE 1]" in saida


# ---- LIMITES (risco residual, documentado de forma executável) ---------------------------------

def test_LIMITE_nome_sem_cadastro_e_sem_rotulo_continua_identificavel():
    a = NameAliaser()
    a.alias_for(TITULAR, "TITULAR")
    texto = "Na sessão, o leiloeiro Roberto Campos Dias e a testemunha Luciana Moraes Pinto assinaram."
    a.learn_from_text(texto)
    assert a.apply(texto) == texto            # nada trocado: sem NER, nomes soltos NÃO são detectados


def test_LIMITE_referencia_parcial_ao_nome_nao_e_trocada():
    a = NameAliaser()
    a.alias_for(TITULAR, "TITULAR")
    assert "Ferreira Lima" in a.apply("A Sra. Ferreira Lima compareceu; Ana Paula Ferreira Lima assinou.")
    assert "[TITULAR]" in a.apply("A Sra. Ferreira Lima compareceu; Ana Paula Ferreira Lima assinou.")


def test_LIMITE_endereco_numero_de_processo_e_cnpj_nao_sao_mascarados():
    a = NameAliaser()
    texto = "Rua das Flores, 123, apto 45; processo 0001234-56.2026.8.26.0100; CNPJ 12.345.678/0001-90."
    assert a.apply(texto) == texto


def test_pseudonimizacao_desligada_com_llm_redact_pii_false(monkeypatch):
    monkeypatch.setattr(settings, "llm_redact_pii", False)
    from backend.app.privacy_context import aliaser_for_property
    a = aliaser_for_property(SimpleNamespace(), 1)
    assert a.enabled is False and a.apply("Nome Qualquer Pessoa CPF 123.456.789-09") == "Nome Qualquer Pessoa CPF 123.456.789-09"


# ---------------------------------------------------------------- integração: agente, embeddings e extração

class _Provider:
    def __init__(self, resposta=None):
        self.chat_messages = None
        self.embedded: list[str] = []
        self.resposta = resposta

    def structured_chat(self, schema, messages, **kwargs):
        self.chat_messages = messages
        return ProviderResponse(content=self.resposta, input_tokens=100, output_tokens=20)

    def chat(self, *a, **k):
        return ProviderResponse(content="")

    def embed(self, texts):
        self.embedded.extend(texts)
        return [[0.1] * settings.embedding_dimensions for _ in texts]


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)


def _imovel_com_titular(db):
    prop = models.Property(title="Imóvel Pseudo", address="Rua P, 1", city="São Paulo", state="SP", area_m2=50, bedrooms=2)
    db.add(prop); db.flush()
    db.add(models.PropertyRegistration(property_id=prop.id, registration_number="1", holder=TITULAR))
    db.add(models.LegalProcess(property_id=prop.id, number="0001234-56.2026.8.26.0100", polo_active="Condomínio Aurora", polo_passive="Marcos Vinícius Teixeira"))
    db.flush(); db.refresh(prop)
    return prop


def test_agente_envia_papeis_no_lugar_dos_nomes_e_grava_resposta_com_o_nome_real(db):
    from backend.app.ai.contracts import AgentResponse, Finding
    prop = _imovel_com_titular(db)
    resposta = AgentResponse(summary="[TITULAR] é o devedor", findings=[Finding(kind="fato", statement="[TITULAR] constituiu alienação fiduciária", chunk_ids=[], evidence_excerpt="[TITULAR] assinou")], pending=["confirmar [PARTE PASSIVA 1]"])
    provider = _Provider(resposta)
    contexto = f"[chunk_id=1] Matrícula. Titular: {TITULAR}. Executado: Marcos Vinícius Teixeira. Credor: Condomínio Aurora. Contato: fulano@example.com, CPF 123.456.789-09."
    resultado = DocumentAgent(db, LLMGateway(provider, "fake", "m")).run(prop.id, contexto, [1])
    enviado = json.dumps(provider.chat_messages, ensure_ascii=False)
    for sensivel in (TITULAR, "Ferreira Lima", "Marcos Vinícius", "fulano@example.com", "123.456.789-09"):
        assert sensivel not in enviado, f"{sensivel!r} saiu para o provider"
    assert "[TITULAR]" in enviado and "Condomínio Aurora" in enviado          # papéis preservados; empresa permanece
    assert resultado.facts[0]["statement"] == f"{TITULAR} constituiu alienação fiduciária"   # restaurado localmente
    assert resultado.facts[0]["evidence_excerpt"] == f"{TITULAR} assinou"
    assert resultado.interpretation == f"{TITULAR} é o devedor"
    assert "Marcos Vinícius Teixeira" in resultado.pending[0]


def test_embeddings_de_chunks_enviam_nomes_conhecidos_como_papeis_e_o_banco_mantem_o_original(db, monkeypatch):
    prop = _imovel_com_titular(db)
    provider = _Provider()
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    monkeypatch.setattr("backend.app.documents.embedding.build_gateway", lambda: LLMGateway(provider, "fake", "m"))
    doc = models.Document(property_id=prop.id, name="m.txt", document_type="MATRICULA", source="t")
    db.add(doc); db.flush()
    texto = (f"Matrícula 1. Titular: {TITULAR}. Contato fulano@example.com. Executado: Marcos Vinícius Teixeira. " * 12).encode()
    DocumentPipeline(db).ingest(doc, texto, "m.txt")
    enviado = " ".join(provider.embedded)
    assert provider.embedded and TITULAR not in enviado and "Marcos Vinícius" not in enviado and "fulano@example.com" not in enviado
    guardado = db.query(models.DocumentChunk).join(models.DocumentVersion).filter(models.DocumentVersion.document_id == doc.id).first()
    assert TITULAR in guardado.content          # o texto armazenado NÃO é alterado


def test_extracao_envia_papeis_e_persiste_o_titular_com_o_nome_real(db, monkeypatch):
    prop = _imovel_com_titular(db)
    doc = models.Document(property_id=prop.id, name="m.txt", document_type="MATRICULA", source="t")
    db.add(doc); db.flush()
    versao = DocumentPipeline(db).ingest(doc, (f"Matrícula 123. Proprietário: {TITULAR}. " * 10).encode(), "m.txt")
    saida = RegistrationExtraction(registration_number="123", holder="[TITULAR]", references=[
        ExtractionReference(field="registration_number", value="123"), ExtractionReference(field="holder", value="[TITULAR]")])
    provider = _Provider(saida)
    resultado = extract_document(db, prop.id, versao.id, "MATRICULA", gateway_override=LLMGateway(provider, "fake", "m"))
    assert resultado.success
    assert TITULAR not in json.dumps(provider.chat_messages, ensure_ascii=False)
    assert resultado.output.holder == TITULAR
    assert {r.value for r in resultado.output.references if r.field == "holder"} == {TITULAR}
