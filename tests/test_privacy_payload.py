"""Privacidade (v1.0.4): o que CHEGA ao provider, capturado no próprio provider (não só o retorno de uma função).

Cobre o caminho da extração estruturada (aliaser + gateway) e o gateway direto (agentes, RAG, embeddings), com
formatos variados. Identificadores necessários à análise (número da matrícula, processo CNJ, CNPJ, endereço do
imóvel) continuam sendo enviados por decisão documentada (HOMOLOGACAO-QUALIDADE-IA.md §6).
"""
import json

from backend.app.ai.gateway import LLMGateway, ProviderResponse
from backend.app.extraction import RegistrationExtraction, extract_document
from backend.app.privacy import redact_pii
from tests.test_extraction import FakeDb, fake_rag, version_for

PII = {
    "cpf_formatado": "111.222.333-96",
    "cpf_digitos": "11122233396",
    "rg": "RG nº 12.345.678-9",
    "email": "fulano.teste@exemplo.com.br",
    "telefone_ddd": "(11) 98765-4321",
    "telefone_intl": "+55 11 98765-4321",
    "conta": "conta corrente nº 12345-6",
}
NECESSARIOS = ("99.901", "0001234-56.2020.5.02.0001", "00.000.000/0002-00", "Rua das Acácias Fictícias")

TEXTO = (
    "MATRÍCULA Nº 99.901. Imóvel na Rua das Acácias Fictícias, nº 123. Banco Fictício S.A., CNPJ 00.000.000/0002-00. "
    "Proprietário: Carlos Eduardo Teste Silva, CPF {cpf_formatado}, também inscrito como {cpf_digitos}, {rg}, "
    "e-mail {email}, telefone {telefone_ddd} ou {telefone_intl}, {conta}. "
    "Penhora nos autos nº 0001234-56.2020.5.02.0001."
).format(**PII)


class Capturador:
    def __init__(self, content=None):
        self.content = content; self.enviado = []

    def structured_chat(self, schema, messages, **kwargs):
        self.enviado.append(json.dumps(messages, ensure_ascii=False))
        return ProviderResponse(content=self.content, input_tokens=1, output_tokens=1)

    def chat(self, messages, **kwargs):
        self.enviado.append(json.dumps(messages, ensure_ascii=False))
        return ProviderResponse(content="ok", input_tokens=1, output_tokens=1)

    def embed(self, texts):
        self.enviado.append(json.dumps(texts, ensure_ascii=False))
        return [[0.0] for _ in texts]


def _sem_pii(payload: str):
    for nome, valor in PII.items():
        assert valor not in payload, f"{nome} chegou ao provider"
    assert "Carlos Eduardo Teste Silva" not in payload


def test_extracao_envia_documento_mascarado_e_pseudonimizado(monkeypatch):
    fake_rag(monkeypatch, chunks=[{"chunk_id": 11, "page": 1, "section": None, "content": TEXTO}])
    provider = Capturador(RegistrationExtraction())
    extract_document(FakeDb(version_for()), 1, 3, "MATRICULA", LLMGateway(provider, "fake", "m"))
    [payload] = provider.enviado
    _sem_pii(payload)
    for valor in NECESSARIOS:
        assert valor in payload, f"{valor} é necessário à análise e deve continuar no contexto"


def test_gateway_mascara_chat_estruturado_e_embeddings():
    provider = Capturador({})
    gw = LLMGateway(provider, "fake", "m")
    gw.chat([{"role": "user", "content": TEXTO}])
    gw.structured_chat(dict, [{"role": "user", "content": TEXTO}])
    gw.embed([TEXTO])
    assert len(provider.enviado) == 3
    for payload in provider.enviado:
        for nome, valor in PII.items():
            assert valor not in payload, f"{nome} chegou ao provider"


def test_cpf_so_com_digitos_e_mascarado_apenas_com_digito_verificador_valido():
    assert redact_pii("inscrito como 11122233396.") == "inscrito como [CPF]."
    # 11 dígitos que não são CPF válido (ex.: protocolo/inscrição) permanecem.
    assert redact_pii("protocolo 12345678901") == "protocolo 12345678901"
    assert redact_pii("00000000000") == "00000000000"
    # parte de número maior com ponto (ex.: protocolo 202202.11122233396.1) não é tratada como CPF isolado
    assert redact_pii("protocolo 2022.11122233396.1") == "protocolo 2022.11122233396.1"
