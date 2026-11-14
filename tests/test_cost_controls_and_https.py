"""Controle de custo da OpenAI e exigência de HTTPS (P0 — homologação v1.0.2).

Nenhuma chamada à OpenAI: o orçamento é lido de ``llm_runs`` (PostgreSQL real) e o HTTPS é
verificado com requisições reais ao app (``TestClient``).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app import models
from backend.app.ai import budget
from backend.app.ai.agents import DocumentAgent
from backend.app.ai.gateway import BudgetExceeded, build_gateway
from backend.app.config import Settings, settings
from backend.app.https_guard import HSTS_VALUE
from backend.app.main import app


def _run(db, custo, criado_em=None):
    run = models.LLMRun(agent="documental", provider="openai", model="gpt-4o-mini", total_cost=Decimal(str(custo)), status="CONCLUIDO")
    db.add(run); db.flush()
    if criado_em is not None:
        run.created_at = criado_em
        db.flush()
    return run


# ---- orçamento --------------------------------------------------------------

def test_sem_teto_configurado_nunca_bloqueia(db, monkeypatch):
    monkeypatch.setattr(settings, "llm_budget_usd_month", None)
    assert budget.month_status(db) == {"limite_usd": None, "gasto_usd": None, "excedido": False, "sem_preco": False}


def test_gasto_do_mes_soma_llm_runs_e_ignora_meses_anteriores(db, monkeypatch):
    monkeypatch.setattr(settings, "llm_budget_usd_month", 1.0)
    antes = budget.month_status(db)["gasto_usd"]
    _run(db, "0.60"); _run(db, "0.30")
    _run(db, "9.00", criado_em=datetime(2020, 1, 15))  # outro mês: não conta
    status = budget.month_status(db)
    assert round(status["gasto_usd"] - antes, 6) == 0.9
    assert status["limite_usd"] == 1.0


def test_teto_atingido_marca_excedido(db, monkeypatch):
    monkeypatch.setattr(settings, "llm_budget_usd_month", 0.0001)
    _run(db, "0.50")
    assert budget.month_status(db)["excedido"] is True


def test_agente_devolve_ORCAMENTO_EXCEDIDO_sem_chamar_o_provider(db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    monkeypatch.setattr(settings, "llm_budget_usd_month", 0.0001)
    _run(db, "0.50")
    result = DocumentAgent(db, gateway=None).run(property_id=1, context="")
    assert result.llm_call.status == "ORCAMENTO_EXCEDIDO" and result.llm_used is False
    assert "Orçamento mensal" in result.llm_call.error_message


def test_sem_chave_continua_SEM_CHAVE_mesmo_com_teto(db, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "llm_budget_usd_month", 100.0)
    assert budget.unavailable_reason(db)[0] == "SEM_CHAVE"


def test_build_gateway_nao_cria_provider_quando_o_orcamento_acabou(monkeypatch):
    monkeypatch.setattr(settings, "llm_budget_usd_month", 1.0)
    monkeypatch.setattr("backend.app.ai.budget.month_status", lambda db=None: {"limite_usd": 1.0, "gasto_usd": 2.0, "excedido": True})
    with pytest.raises(BudgetExceeded):
        build_gateway()
    assert issubclass(BudgetExceeded, RuntimeError)  # chamadores já tratam RuntimeError como "IA indisponível"


def test_valores_vazios_do_compose_viram_nao_configurado():
    cfg = Settings(llm_budget_usd_month="", llm_max_output_tokens="  ")
    assert cfg.llm_budget_usd_month is None and cfg.llm_max_output_tokens is None
    assert Settings(llm_budget_usd_month="12.5").llm_budget_usd_month == 12.5


def test_estimativa_de_custo_de_embedding_na_telemetria(db, monkeypatch, tmp_path):
    from backend.app.documents.pipeline import DocumentPipeline
    from backend.app.documents import embedding as emb

    class Fake:
        def embed(self, texts):
            return [[0.1] * settings.embedding_dimensions for _ in texts]

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    monkeypatch.setattr("backend.app.documents.embedding.build_gateway", lambda: Fake())
    prop = models.Property(title="Imóvel Custo", address="Rua", city="São Paulo", state="SP", area_m2=1, bedrooms=1)
    db.add(prop); db.flush()
    doc = models.Document(property_id=prop.id, name="c.txt", document_type="EDITAL", source="t")
    db.add(doc); db.flush()
    version = DocumentPipeline(db).ingest(doc, ("palavra " * 800).encode(), "c.txt")
    for chunk in db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == version.id):
        chunk.embedding = None
    db.flush()
    telemetria = emb.embed_pending_chunks(db, version.id)
    assert telemetria["tokens_estimados"] > 0
    assert telemetria["custo_estimado_usd"] == pytest.approx(telemetria["tokens_estimados"] * settings.embedding_price_per_1m_usd / 1_000_000, abs=1e-6)


# ---- HTTPS ------------------------------------------------------------------

@pytest.fixture
def http_client():
    return TestClient(app)


def test_sem_exigencia_de_https_http_continua_funcionando_e_sem_hsts(http_client, monkeypatch):
    monkeypatch.setattr(settings, "require_https", False)
    r = http_client.get("/health")
    assert r.status_code == 200 and "strict-transport-security" not in r.headers


def test_exigir_https_recusa_api_em_http_com_426(http_client, monkeypatch):
    monkeypatch.setattr(settings, "require_https", True)
    r = http_client.post("/api/auth/login", json={"email": "a@b.co", "password": "x"})
    assert r.status_code == 426 and "HTTPS" in r.json()["detail"]
    assert r.headers.get("x-request-id")  # a resposta 426 também carrega o id de correlação


def test_exigir_https_aceita_requisicao_encaminhada_como_https_e_envia_hsts(http_client, monkeypatch):
    monkeypatch.setattr(settings, "require_https", True)
    r = http_client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert r.status_code == 200 and r.headers["strict-transport-security"] == HSTS_VALUE
    login = http_client.post("/api/auth/login", json={"email": "nao-existe@example.com", "password": "x"}, headers={"X-Forwarded-Proto": "https"})
    assert login.status_code != 426  # chegou à aplicação (credencial inválida => 401)


def test_health_e_isento_para_healthchecks_internos_em_http(http_client, monkeypatch):
    monkeypatch.setattr(settings, "require_https", True)
    assert http_client.get("/health").status_code == 200


def test_cabecalho_forjado_http_nao_burla_quando_proxy_define_o_esquema(http_client, monkeypatch):
    monkeypatch.setattr(settings, "require_https", True)
    r = http_client.get("/api/imoveis", headers={"X-Forwarded-Proto": "http"})
    assert r.status_code == 426
