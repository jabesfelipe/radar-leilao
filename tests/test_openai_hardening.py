"""Integração OpenAI/LLM: sem chave, erros simulados (auth, rate limit, timeout, provider),
configuração de timeout/retries e garantia de que nenhum segredo vaza. SEM chamadas reais:
tudo com dublês/mocks."""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from backend.app.ai import agents as agents_module
from backend.app.ai.gateway import ERROR_CATEGORIES, LLMCall, LLMGateway, build_gateway, classify_provider_error, sanitize_error
from backend.app.ai.graph import _gateway_or_none
from backend.app.config import settings
from backend.app.logging_config import SecretRedactingFilter
from backend.app.redaction import redact
from backend.app.request_context import get_correlation_id, set_correlation_id

KEY = "sk-proj-AbCdEf1234567890SECRETKEY"


# ------------------------------------------------------------------ dublês de erro (nomes como no SDK)

class AuthenticationError(Exception):
    status_code = 401


class PermissionDeniedError(Exception):
    status_code = 403


class RateLimitError(Exception):
    status_code = 429


class APITimeoutError(Exception):
    pass


class APIConnectionError(Exception):
    pass


class BadRequestError(Exception):
    status_code = 400


class InternalServerError(Exception):
    status_code = 500


class ProviderQueFalha:
    def __init__(self, exc: Exception):
        self.exc = exc

    def chat(self, messages, **kw):
        raise self.exc

    def structured_chat(self, schema, messages, **kw):
        raise self.exc

    def embed(self, texts):
        raise self.exc


def _gateway(exc: Exception) -> LLMGateway:
    return LLMGateway(ProviderQueFalha(exc), "openai", "gpt-4o-mini")


# ------------------------------------------------------------------ sem chave

def test_sem_chave_nenhuma_chamada_e_gateway_indisponivel(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    with pytest.raises(RuntimeError):
        build_gateway()
    assert _gateway_or_none() is None


def test_sem_chave_os_cinco_agentes_respondem_sem_chave_sem_rede(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    db = SimpleNamespace(get=lambda *a, **k: None)
    resultados = [
        agents_module.DocumentAgent(db, None).run(1, "ctx", [1]),
        agents_module.LegalAgent(db, None).run(1, "ctx", [1]),
        agents_module.FinancialAgent(db, None).run(1, "ctx", [1], {}),
        agents_module.MarketAgent(db, None).run(1, "ctx", [1], {}),
        agents_module.ChecklistAgent(db, None).run(1, "ctx", [1], []),
    ]
    assert [r.agent for r in resultados] == ["documental", "juridico", "financeiro", "mercado", "checklist"]
    for r in resultados:
        assert r.llm_call.status == "SEM_CHAVE" and r.llm_used is False


# ------------------------------------------------------------------ classificação e sanitização de erros

@pytest.mark.parametrize("exc,categoria", [
    (AuthenticationError("Incorrect API key"), "AUTENTICACAO"),
    (PermissionDeniedError("no access"), "AUTENTICACAO"),
    (RateLimitError("429"), "RATE_LIMIT"),
    (APITimeoutError("Request timed out."), "TIMEOUT"),
    (TimeoutError("t"), "TIMEOUT"),
    (APIConnectionError("Connection error."), "CONEXAO"),
    (BadRequestError("bad"), "REQUISICAO_INVALIDA"),
    (InternalServerError("oops"), "PROVEDOR"),
    (ValueError("x"), "DESCONHECIDO"),
])
def test_classificacao_de_erros_do_provider(exc, categoria):
    assert classify_provider_error(exc) == categoria
    assert categoria in ERROR_CATEGORIES


def test_classificacao_com_excecoes_reais_do_sdk():
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx")
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    assert classify_provider_error(openai.AuthenticationError("x", response=httpx.Response(401, request=request), body=None)) == "AUTENTICACAO"
    assert classify_provider_error(openai.RateLimitError("x", response=httpx.Response(429, request=request), body=None)) == "RATE_LIMIT"
    assert classify_provider_error(openai.APITimeoutError(request=request)) == "TIMEOUT"
    assert classify_provider_error(openai.APIConnectionError(request=request)) == "CONEXAO"


@pytest.mark.parametrize("exc,categoria", [
    (AuthenticationError(f"Incorrect API key provided: {KEY}. Authorization: Bearer {KEY}"), "AUTENTICACAO"),
    (RateLimitError(f"Rate limit reached for gpt-4o-mini; key={KEY}"), "RATE_LIMIT"),
    (APITimeoutError(f"timeout conectando com OPENAI_API_KEY={KEY}"), "TIMEOUT"),
    (InternalServerError(f"erro 500 url=postgresql://radar:SENHA@postgres/db token={KEY}"), "PROVEDOR"),
])
def test_gateway_converte_erro_em_llmcall_sem_segredos(exc, categoria):
    call = _gateway(exc).structured_chat(object, [{"role": "user", "content": "oi"}])
    assert call.status == "ERRO" and call.error_category == categoria
    texto = f"{call.error_message} {call.to_dict()}"
    assert KEY not in texto and "AbCdEf1234567890" not in texto and "SENHA" not in texto
    assert "radar:" not in (call.error_message or "")


def test_gateway_chat_tambem_nao_propaga_excecao():
    call = _gateway(RateLimitError("429")).chat([{"role": "user", "content": "oi"}])
    assert call.status == "ERRO" and call.error_category == "RATE_LIMIT"


def test_agentes_tratam_cada_erro_do_provider_sem_quebrar(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    db = SimpleNamespace(get=lambda *a, **k: None)
    for exc, categoria in [(AuthenticationError("401"), "AUTENTICACAO"), (RateLimitError("429"), "RATE_LIMIT"), (APITimeoutError("t"), "TIMEOUT")]:
        gateway = _gateway(exc)
        resultados = [
            agents_module.DocumentAgent(db, gateway).run(1, "ctx", [1]),
            agents_module.LegalAgent(db, gateway).run(1, "ctx", [1]),
            agents_module.FinancialAgent(db, gateway).run(1, "ctx", [1], {}),
            agents_module.MarketAgent(db, gateway).run(1, "ctx", [1], {}),
            agents_module.ChecklistAgent(db, gateway).run(1, "ctx", [1], []),
        ]
        for r in resultados:
            assert r.llm_call.status == "ERRO" and r.llm_call.error_category == categoria
            assert r.llm_used is False and r.facts == [] and r.pending


def test_supervisor_sanitiza_excecao_inesperada_de_agente(monkeypatch):
    class AgenteQuebrado:
        name = "documental"
        def run(self, *a, **k):
            raise RuntimeError(f"falha interna com {KEY} e postgresql://u:senha@h/db")

    sup = agents_module.Supervisor(SimpleNamespace(get=lambda *a, **k: None), _gateway(ValueError("x")))
    monkeypatch.setattr(agents_module, "DocumentAgent", lambda db, gw: AgenteQuebrado())
    results = sup.run(1, ["documental"], "ctx", [])
    assert results[0].llm_call.status == "ERRO"
    assert KEY not in (results[0].llm_call.error_message or "") and "senha" not in (results[0].llm_call.error_message or "")


@pytest.mark.parametrize("bruto", [
    f"Incorrect API key provided: {KEY}",
    f"Authorization: Bearer {KEY}",
    f"OPENAI_API_KEY={KEY}",
    "api_key: sk-abcdefghijklmnop",
    "conn postgresql+psycopg://radar:SenhaForte@postgres:5432/radar_leilao falhou",
    "password=SenhaForte123 e token=abc.def.ghi",
    "X-Admin-Token: tok-secreto-123",
    "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.assinaturaassinatura",
])
def test_redact_remove_segredos(bruto):
    limpo = redact(bruto)
    for pedaco in ("AbCdEf1234567890", "SenhaForte", "tok-secreto-123", "sk-abcdefghijklmnop", "assinaturaassinatura", "abc.def.ghi"):
        assert pedaco not in limpo
    assert sanitize_error(bruto) == limpo


def test_redact_trunca_mensagens_longas():
    assert len(redact("x" * 10000)) <= 2000


# ------------------------------------------------------------------ logs

def test_filtro_de_log_redige_segredos_e_anexa_correlation_id():
    class Coletor(logging.Handler):
        def __init__(self):
            super().__init__()
            self.linhas = []
        def emit(self, record):
            self.linhas.append(self.format(record))

    coletor = Coletor()
    coletor.setFormatter(logging.Formatter("[%(correlation_id)s] %(message)s"))
    coletor.addFilter(SecretRedactingFilter())
    logger = logging.getLogger("radar.teste-redacao")
    logger.setLevel(logging.INFO)
    logger.addHandler(coletor)
    try:
        cid = set_correlation_id("corr-id-de-teste-01")
        logger.warning("falhou com key=%s url=%s", KEY, "postgresql://radar:SenhaForte@db/radar")
        try:
            raise RuntimeError(f"boom {KEY}")
        except RuntimeError:
            logger.exception("erro com token=%s", "tok-123456")
    finally:
        logger.removeHandler(coletor)
    saida = "\n".join(coletor.linhas)
    assert cid == "corr-id-de-teste-01" and get_correlation_id() == cid
    assert saida.startswith("[corr-id-de-teste-01]")
    assert KEY not in saida and "AbCdEf1234567890" not in saida and "SenhaForte" not in saida and "tok-123456" not in saida
    assert "Traceback" in saida  # o detalhe técnico fica no log interno (sanitizado)


# ------------------------------------------------------------------ timeout / retries configuráveis

def test_provider_aplica_timeout_retries_e_limite_de_saida(monkeypatch):
    chamadas = {}

    class FakeChat:
        def __init__(self, **kwargs):
            chamadas["chat"] = kwargs

    class FakeEmbeddings:
        def __init__(self, **kwargs):
            chamadas["emb"] = kwargs

    import langchain_openai
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChat)
    monkeypatch.setattr(langchain_openai, "OpenAIEmbeddings", FakeEmbeddings)
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real", raising=False)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 12.0, raising=False)
    monkeypatch.setattr(settings, "llm_max_retries", 0, raising=False)
    monkeypatch.setattr(settings, "llm_max_output_tokens", 700, raising=False)
    from backend.app.ai.providers.openai_provider import OpenAIProvider
    OpenAIProvider()
    assert chamadas["chat"]["timeout"] == 12.0 and chamadas["chat"]["max_retries"] == 0 and chamadas["chat"]["max_tokens"] == 700
    assert chamadas["emb"]["timeout"] == 12.0 and chamadas["emb"]["max_retries"] == 0
    monkeypatch.setattr(settings, "llm_max_output_tokens", None, raising=False)
    OpenAIProvider()
    assert "max_tokens" not in chamadas["chat"]


def test_padroes_de_resiliencia_ficam_abaixo_do_timeout_do_proxy():
    # proxy_read_timeout do nginx = 300 s: uma chamada isolada (1 + retries) x timeout deve caber.
    assert (1 + settings.llm_max_retries) * settings.llm_timeout_seconds <= 300


def test_llmcall_to_dict_inclui_categoria_sem_conteudo():
    call = LLMCall(status="ERRO", error_category="RATE_LIMIT", content={"secreto": "x"})
    data = call.to_dict()
    assert data["error_category"] == "RATE_LIMIT" and "content" not in data
