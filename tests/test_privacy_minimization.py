"""Minimização de dados pessoais (rodada de correções P0 — homologação v1.0.2).

Prova, com um PROVIDER FALSO que captura exatamente o que seria enviado à OpenAI, que dados
pessoais não saem do sistema (prompt de chat, texto de embeddings) nem vão para logs e
mensagens de erro. Não chama a OpenAI: o objetivo é verificar a fronteira de saída.
"""
from __future__ import annotations

import json
import logging

import pytest

from backend.app import privacy
from backend.app.ai.gateway import LLMGateway, ProviderResponse, sanitize_error
from backend.app.config import settings

CPF = "123.456.789-09"
CPF_SEM_PONTOS = "12345678909"
EMAIL = "fulano.silva@example.com"
FONE = "(11) 91234-5678"


class CapturingProvider:
    def __init__(self):
        self.chat_messages = None
        self.embedded = None

    def chat(self, messages, **kwargs):
        self.chat_messages = messages
        return ProviderResponse(content="ok")

    def structured_chat(self, schema, messages, **kwargs):
        self.chat_messages = messages
        return ProviderResponse(content=None)

    def embed(self, texts):
        self.embedded = texts
        return [[0.0] for _ in texts]


def _gateway():
    provider = CapturingProvider()
    return LLMGateway(provider, "openai", "modelo-teste"), provider


def test_redact_pii_mascara_identificadores_pessoais():
    texto = f"Titular CPF: {CPF}, CPF nº {CPF_SEM_PONTOS}, RG: 12.345.678-9, e-mail {EMAIL}, tel {FONE}, conta corrente 12345-6, agência 0001"
    saida = privacy.redact_pii(texto)
    for sensivel in (CPF, CPF_SEM_PONTOS, "12.345.678-9", EMAIL, FONE, "12345-6"):
        assert sensivel not in saida, f"{sensivel!r} vazou: {saida}"
    assert "[CPF]" in saida and "[EMAIL]" in saida and "[TELEFONE]" in saida and "[DADO BANCÁRIO]" in saida


def test_redact_pii_nao_destroi_numeros_do_processo_nem_valores():
    texto = "Processo 0001234-56.2026.8.26.0100, avaliação R$ 400.000,00, matrícula 12.345, área 62,00 m2"
    assert privacy.redact_pii(texto) == texto


def test_gateway_chat_envia_prompt_sem_dados_pessoais():
    gateway, provider = _gateway()
    messages = [{"role": "system", "content": "analise"}, {"role": "user", "content": json.dumps({"observacoes": f"contato {EMAIL} CPF {CPF}", "contexto_rag": f"proprietário CPF: {CPF_SEM_PONTOS}"}, ensure_ascii=False)}]
    gateway.structured_chat(object, messages)
    enviado = json.dumps(provider.chat_messages, ensure_ascii=False)
    assert CPF not in enviado and CPF_SEM_PONTOS not in enviado and EMAIL not in enviado
    # o original NÃO é alterado (o banco continua íntegro)
    assert CPF in messages[1]["content"]


def test_gateway_embeddings_enviam_texto_sem_dados_pessoais():
    gateway, provider = _gateway()
    gateway.embed([f"Fulano de Tal, CPF {CPF}, telefone {FONE}"])
    assert CPF not in provider.embedded[0] and FONE not in provider.embedded[0]


def test_desligar_a_minimizacao_e_explicito(monkeypatch):
    monkeypatch.setattr(settings, "llm_redact_pii", False)
    gateway, provider = _gateway()
    gateway.embed([f"CPF {CPF}"])
    assert CPF in provider.embedded[0]  # só com LLM_REDACT_PII=false


def test_partes_de_processo_pessoa_fisica_sao_pseudonimizadas_e_empresas_permanecem():
    assert privacy.minimize_party("João da Silva Santos", "PARTE ATIVA") == "[PARTE ATIVA]"
    assert privacy.minimize_party("Banco Exemplo S.A.", "PARTE ATIVA") == "Banco Exemplo S.A."
    assert privacy.minimize_party("Condomínio Edifício Aurora", "PARTE PASSIVA") == "Condomínio Edifício Aurora"
    assert privacy.minimize_party(None, "PARTE ATIVA") is None


def test_sanitize_error_remove_pii_e_segredo():
    mensagem = f"400 Bad Request: input contém CPF {CPF} e e-mail {EMAIL}; api_key=sk-segredo-1234567890"
    limpa = sanitize_error(mensagem)
    assert CPF not in limpa and EMAIL not in limpa and "sk-segredo" not in limpa


def test_logs_nao_registram_dados_pessoais_nem_credenciais(caplog):
    from backend.app.logging_config import SecretRedactingFilter

    filtro = SecretRedactingFilter()
    registro = logging.LogRecord("radar.teste", logging.WARNING, __file__, 1, "falha com CPF %s, e-mail %s, OPENAI_API_KEY=%s", (CPF, EMAIL, "sk-proj-abcdefghijk"), None)
    filtro.filter(registro)
    saida = registro.getMessage()
    assert CPF not in saida and EMAIL not in saida and "sk-proj-abcdefghijk" not in saida


def test_agente_juridico_envia_partes_pseudonimizadas(monkeypatch):
    """O snapshot do agente jurídico (que vai ao prompt) não carrega o nome da pessoa física."""
    from types import SimpleNamespace
    from backend.app.ai.agents import LegalAgent

    processo = SimpleNamespace(number="0001234-56.2026.8.26.0100", court="Vara", comarca="SP", nature="Execução", subject="Cobrança", status="Ativo",
                               polo_active="Condomínio Edifício Aurora", polo_passive="João da Silva Santos", distribution_date=None,
                               observations="contato joao@example.com", source="manual", consulted_at=None, impact=None, movements=[])
    prop = SimpleNamespace(id=1, title="t", address="a", city="c", state="SP", property_type="x", area_m2=1, bedrooms=1, processes=[processo], comparables=[], documents=[])
    db = SimpleNamespace(get=lambda model, ident: prop)
    snapshot = LegalAgent(db)._property_snapshot(1)
    partes = json.dumps(snapshot["processos"], ensure_ascii=False)
    assert "João da Silva Santos" not in partes
    assert "[PARTE PASSIVA]" in partes and "Condomínio Edifício Aurora" in partes
