"""Orçamento (v1.0.4): modelo sem preço cadastrado falha FECHADO também quando só o teto POR ANÁLISE existe.

Antes, ``build_gateway`` só verificava o preço quando ``LLM_BUDGET_USD_MONTH`` estava definido: com apenas
``LLM_BUDGET_USD_PER_ANALYSIS`` o custo de cada chamada ficava None e o teto por análise nunca disparava.
Nenhuma chamada externa.
"""
import pytest

from backend.app.ai import gateway as gateway_module
from backend.app.ai.budget import pricing_missing, unavailable_reason
from backend.app.ai.gateway import BudgetExceeded, build_gateway
from backend.app.config import settings


class _ProviderFalso:
    def __init__(self):
        pass


@pytest.fixture
def so_teto_por_analise(monkeypatch):
    monkeypatch.setattr(settings, "llm_budget_usd_month", None)
    monkeypatch.setattr(settings, "llm_budget_usd_per_analysis", 0.10)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr("backend.app.ai.providers.openai_provider.OpenAIProvider", _ProviderFalso)


def test_so_teto_por_analise_e_modelo_sem_preco_bloqueia_antes_de_chamar(monkeypatch, so_teto_por_analise):
    monkeypatch.setattr("backend.app.ai.budget.pricing_missing", lambda db=None: True)
    with pytest.raises(BudgetExceeded, match="sem preço"):
        build_gateway()


def test_so_teto_por_analise_com_preco_cadastrado_libera(monkeypatch, so_teto_por_analise):
    monkeypatch.setattr("backend.app.ai.budget.pricing_missing", lambda db=None: False)
    gw = build_gateway()
    assert isinstance(gw, gateway_module.LLMGateway) and isinstance(gw.provider, _ProviderFalso)


def test_motivo_de_indisponibilidade_informa_falta_de_preco(monkeypatch, so_teto_por_analise):
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real")
    monkeypatch.setattr("backend.app.ai.budget.pricing_missing", lambda db=None: True)
    status, mensagem = unavailable_reason()
    assert status == "ORCAMENTO_EXCEDIDO" and "sem preço" in mensagem


class LengthFinishReasonError(Exception):
    """Mesmo nome da exceção do SDK da OpenAI para resposta truncada pelo limite de saída."""


class _Usage:
    prompt_tokens, completion_tokens = 1385, 1500


class _Completion:
    usage = _Usage()


@pytest.mark.parametrize("exc", [
    LengthFinishReasonError("Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=1500, prompt_tokens=3149, total_tokens=4649)"),
    type("LengthFinishReasonError", (Exception,), {"completion": _Completion()})("length limit was reached"),
])
def test_resposta_truncada_pelo_limite_de_saida_e_contabilizada(exc):
    # 1ª execução real v1.0.4 (LLM_MAX_OUTPUT_TOKENS=1500): a chamada truncada é cobrada; antes os tokens ficavam None
    # e o custo não entrava em llm_runs nem no teto por análise.
    from backend.app.ai.gateway import LLMGateway

    class Provider:
        def structured_chat(self, schema, messages, **kwargs):
            raise exc

    call = LLMGateway(Provider(), "openai", "gpt-4o-mini").structured_chat(dict, [{"role": "user", "content": "x"}])
    assert call.status == "ERRO" and call.error_category == "LIMITE_DE_SAIDA"
    assert call.output_tokens == 1500 and call.input_tokens in (3149, 1385)


@pytest.mark.parametrize("mensal,por_analise", [(None, None), (0.50, None), (None, 0.10)])
def test_politica_exige_os_dois_limites_antes_de_qualquer_chamada(monkeypatch, mensal, por_analise):
    monkeypatch.setattr(settings, "llm_require_budget", True)
    monkeypatch.setattr(settings, "llm_budget_usd_month", mensal)
    monkeypatch.setattr(settings, "llm_budget_usd_per_analysis", por_analise)
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-real")
    monkeypatch.setattr("backend.app.ai.providers.openai_provider.OpenAIProvider", _ProviderFalso)
    with pytest.raises(BudgetExceeded, match="obrigatórios"):
        build_gateway()
    status, mensagem = unavailable_reason()
    assert status == "ORCAMENTO_EXCEDIDO" and "obrigatórios" in mensagem


def test_politica_com_os_dois_limites_libera(monkeypatch):
    monkeypatch.setattr(settings, "llm_require_budget", True)
    monkeypatch.setattr(settings, "llm_budget_usd_month", None)
    monkeypatch.setattr(settings, "llm_budget_usd_per_analysis", 0.10)
    monkeypatch.setattr(settings, "llm_budget_usd_month", 0.50)
    monkeypatch.setattr("backend.app.ai.budget.month_status", lambda db=None: {"limite_usd": 0.5, "gasto_usd": 0.0, "excedido": False, "sem_preco": False})
    monkeypatch.setattr("backend.app.ai.providers.openai_provider.OpenAIProvider", _ProviderFalso)
    assert isinstance(build_gateway().provider, _ProviderFalso)


def test_compose_de_producao_liga_a_politica_e_o_exemplo_define_os_limites():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    assert "LLM_REQUIRE_BUDGET: ${LLM_REQUIRE_BUDGET:-true}" in (raiz / "docker-compose.prod.yml").read_text(encoding="utf-8")
    exemplo = (raiz / ".env.prod.example").read_text(encoding="utf-8").splitlines()
    for linha in ("LLM_BUDGET_USD_MONTH=0.50", "LLM_BUDGET_USD_PER_ANALYSIS=0.10", "LLM_REQUIRE_BUDGET=true", "LLM_MAX_OUTPUT_TOKENS=1500"):
        assert linha in exemplo


def test_preco_do_modelo_padrao_existe_e_modelo_desconhecido_nao(db, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_model", "gpt-4o-mini")
    assert pricing_missing(db) is False
    monkeypatch.setattr(settings, "llm_model", "modelo-sem-preco-cadastrado")
    assert pricing_missing(db) is True
