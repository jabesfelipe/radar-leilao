"""Contabilização de custo da OpenAI (auditoria final — homologação v1.0.2).

Fecha os caminhos que gastavam sem aparecer em ``llm_runs``: embeddings (agora registrados, com tokens
ESTIMADOS), respostas inválidas já cobradas (tokens preservados) e o estouro do orçamento por dentro de
uma análise (teto por análise + acúmulo durante os agentes). Provider falso; nenhuma chamada à OpenAI.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app import models
from backend.app.ai import budget, usage
from backend.app.ai.agents import Supervisor
from backend.app.ai.contracts import AgentResponse
from backend.app.ai.gateway import BudgetExceeded, LLMGateway, ProviderResponse, ProviderResponseInvalid, build_gateway
from backend.app.config import settings
from backend.app.services import persist_llm_runs


class _Provider:
    def __init__(self, fail: Exception | None = None, tokens=(1000, 200)):
        self.fail = fail
        self.calls = 0
        self.tokens = tokens

    def embed(self, texts):
        self.calls += 1
        if self.fail:
            raise self.fail
        return [[0.0] for _ in texts]

    def structured_chat(self, schema, messages, **kwargs):
        self.calls += 1
        if self.fail:
            raise self.fail
        return ProviderResponse(content=AgentResponse(summary="ok"), input_tokens=self.tokens[0], output_tokens=self.tokens[1])

    def chat(self, *a, **k):
        return ProviderResponse(content="")


class _Sessao:
    """Troca ``SessionLocal`` pela sessão de teste (sem commit real) para provar o que seria gravado."""
    def __init__(self, db):
        self.db = db

    def __call__(self):
        return self

    def __enter__(self):
        return SimpleSession(self.db)

    def __exit__(self, *a):
        return False


class SimpleSession:
    def __init__(self, db):
        self.db = db

    def add(self, obj):
        self.db.add(obj)

    def commit(self):
        self.db.flush()


@pytest.fixture
def grava_na_sessao_de_teste(db, monkeypatch):
    monkeypatch.setattr("backend.app.database.SessionLocal", _Sessao(db))
    return db


# ---------------------------------------------------------------- embeddings

def test_embedding_bem_sucedido_e_registrado_em_llm_runs_com_tokens_estimados(grava_na_sessao_de_teste):
    db = grava_na_sessao_de_teste
    gravados = []
    gateway = LLMGateway(_Provider(), "openai", "gpt-4o-mini", usage_recorder=lambda **kw: gravados.append(kw))
    gateway.embed(["a" * 400, "b" * 400])
    assert gravados[0]["status"] == "CONCLUIDO" and gravados[0]["texts"] == ["a" * 400, "b" * 400]
    usage.record_embedding_usage(**gravados[0])
    run = db.query(models.LLMRun).filter(models.LLMRun.agent == "embedding").order_by(models.LLMRun.id.desc()).first()
    assert run.input_tokens == usage.estimate_tokens(["a" * 400, "b" * 400]) == 202 and run.output_tokens == 0
    assert run.total_cost == pytest.approx(Decimal(202) / 1_000_000 * Decimal(str(settings.embedding_price_per_1m_usd)))
    assert run.status == "CONCLUIDO" and "estimados" in run.error_message


@pytest.mark.parametrize("categoria,conta", [("TIMEOUT", True), ("PROVEDOR", True), ("DESCONHECIDO", True), ("AUTENTICACAO", False), ("RATE_LIMIT", False), ("REQUISICAO_INVALIDA", False), ("CONEXAO", False)])
def test_embedding_que_falha_so_conta_custo_quando_pode_ter_sido_cobrado(grava_na_sessao_de_teste, categoria, conta):
    db = grava_na_sessao_de_teste
    usage.record_embedding_usage(model="text-embedding-3-small", texts=["x" * 4000], status="ERRO", error_category=categoria, error_message="falha")
    run = db.query(models.LLMRun).filter(models.LLMRun.agent == "embedding").order_by(models.LLMRun.id.desc()).first()
    assert (run.total_cost is not None) is conta and run.status == "ERRO"


def test_gateway_registra_erro_de_embedding_e_repropaga(monkeypatch):
    gravados = []

    class Timeout(Exception):
        pass

    gateway = LLMGateway(_Provider(fail=Timeout("timeout")), "openai", "m", usage_recorder=lambda **kw: gravados.append(kw))
    with pytest.raises(Timeout):
        gateway.embed(["texto"])
    assert gravados[0]["status"] == "ERRO" and gravados[0]["error_category"] == "TIMEOUT"


def test_gateway_montado_a_mao_nao_grava_nada():
    LLMGateway(_Provider(), "fake", "m").embed(["texto"])        # sem usage_recorder: sem efeito colateral em banco


def test_build_gateway_real_liga_o_registrador_de_embeddings(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    monkeypatch.setattr(settings, "llm_budget_usd_month", None)
    gateway = build_gateway()          # só instancia o cliente; não faz chamada de rede
    assert gateway.usage_recorder is usage.record_embedding_usage


def test_embeddings_entram_no_orcamento_mensal(db, monkeypatch, grava_na_sessao_de_teste):
    monkeypatch.setattr(settings, "llm_budget_usd_month", 100.0)
    antes = budget.month_status(db)["gasto_usd"]
    usage.record_embedding_usage(model="text-embedding-3-small", texts=["y" * 4_000_000], status="CONCLUIDO")   # ~1M tokens
    depois = budget.month_status(db)["gasto_usd"]
    assert depois - antes == pytest.approx(settings.embedding_price_per_1m_usd, rel=0.01)


# ---------------------------------------------------------------- chat com resposta inválida (já cobrada)

def test_resposta_invalida_preserva_tokens_e_entra_em_llm_runs_com_custo(db):
    erro = ProviderResponseInvalid("JSON fora do schema", input_tokens=3000, output_tokens=500, request_id="req-1")
    gateway = LLMGateway(_Provider(fail=erro), "openai", "gpt-4o-mini")
    call = gateway.structured_chat(AgentResponse, [{"role": "user", "content": "x"}])
    assert call.status == "ERRO" and call.input_tokens == 3000 and call.output_tokens == 500 and call.request_id == "req-1"
    prop = models.Property(title="Custo", address="R", city="SP", state="SP", area_m2=1, bedrooms=1)
    db.add(prop); db.flush()
    run, = persist_llm_runs(db, prop, None, [dict(call.to_dict(), agent="documental")])
    assert run.total_cost is not None and run.total_cost > 0 and run.status == "ERRO"


# ---------------------------------------------------------------- orçamento fecha por dentro da análise

def _prop(db):
    prop = models.Property(title="Orçamento", address="R", city="SP", state="SP", area_m2=1, bedrooms=1)
    db.add(prop); db.flush(); db.refresh(prop)
    return prop


def test_teto_por_analise_impede_os_agentes_seguintes_sem_chamar_o_provider(db, monkeypatch):
    prop = _prop(db)
    provider = _Provider(tokens=(1_000_000, 100_000))          # gpt-4o-mini: 0,15 + 0,06 = US$ 0,21 por agente
    monkeypatch.setattr(settings, "llm_budget_usd_per_analysis", 0.10)
    resultados = Supervisor(db, LLMGateway(provider, "openai", "gpt-4o-mini")).run(prop.id, ["documental", "juridico", "financeiro"], "", [])
    status = [r.llm_call.status for r in resultados]
    assert status == ["CONCLUIDO", "ORCAMENTO_EXCEDIDO", "ORCAMENTO_EXCEDIDO"]
    assert provider.calls == 1                                   # só o 1º agente chamou a OpenAI
    assert "Teto de custo desta análise" in resultados[1].llm_call.error_message


def test_orcamento_mensal_e_conferido_durante_a_analise(db, monkeypatch):
    prop = _prop(db)
    provider = _Provider(tokens=(1_000_000, 100_000))
    base = budget.month_status(db)["gasto_usd"] if settings.llm_budget_usd_month is not None else 0.0
    monkeypatch.setattr(settings, "llm_budget_usd_month", base + 0.10)
    resultados = Supervisor(db, LLMGateway(provider, "openai", "gpt-4o-mini")).run(prop.id, ["documental", "juridico"], "", [])
    assert [r.llm_call.status for r in resultados] == ["CONCLUIDO", "ORCAMENTO_EXCEDIDO"] and provider.calls == 1
    assert "mensal" in resultados[1].llm_call.error_message


def test_sem_teto_configurado_todos_os_agentes_executam(db):
    prop = _prop(db)
    provider = _Provider()
    resultados = Supervisor(db, LLMGateway(provider, "openai", "gpt-4o-mini")).run(prop.id, ["documental", "juridico"], "", [])
    assert [r.llm_call.status for r in resultados] == ["CONCLUIDO", "CONCLUIDO"] and provider.calls == 2


def test_modelo_sem_preco_falha_fechado_quando_ha_orcamento(db, monkeypatch):
    monkeypatch.setattr(settings, "llm_budget_usd_month", 50.0)
    monkeypatch.setattr(settings, "llm_model", "modelo-sem-preco-cadastrado")
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    assert budget.month_status(db)["sem_preco"] is True
    assert budget.unavailable_reason(db)[0] == "ORCAMENTO_EXCEDIDO"
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    monkeypatch.setattr("backend.app.ai.budget.month_status", lambda d=None: {"limite_usd": 50.0, "gasto_usd": 0.0, "excedido": False, "sem_preco": True})
    with pytest.raises(BudgetExceeded, match="sem preço"):
        build_gateway()


def test_orcamento_excedido_em_embedding_nao_consome_tentativas_do_worker():
    from backend.app.ai.gateway import classify_provider_error
    from backend.app.documents.worker import TRANSIENT_ERROR_CATEGORIES
    assert classify_provider_error(BudgetExceeded("x")) == "ORCAMENTO" and "ORCAMENTO" in TRANSIENT_ERROR_CATEGORIES


def test_extracao_sem_orcamento_nao_e_mascarada_como_sem_chave(db, monkeypatch):
    from backend.app.documents.pipeline import DocumentPipeline
    from backend.app.extraction import extract_document
    import tempfile
    monkeypatch.setattr(settings, "storage_dir", tempfile.mkdtemp())
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr("backend.app.extraction.build_gateway", lambda: (_ for _ in ()).throw(BudgetExceeded("Orçamento mensal de IA atingido")))
    prop = _prop(db)
    doc = models.Document(property_id=prop.id, name="m.txt", document_type="MATRICULA", source="t")
    db.add(doc); db.flush()
    versao = DocumentPipeline(db).ingest(doc, ("Matrícula 1 texto. " * 20).encode(), "m.txt")
    r = extract_document(db, prop.id, versao.id, "MATRICULA")
    assert r.call.status == "ORCAMENTO_EXCEDIDO" and r.call.model == settings.llm_model
