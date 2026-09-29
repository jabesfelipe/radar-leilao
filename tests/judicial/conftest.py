"""Fixtures compartilhadas dos testes da Judicial API (JUR-05).

Fornece:
- um provider falso dirigido por mapa tribunal->processos (sem rede);
- um orchestrator com store em memória sobre esse provider;
- um TestClient com o orchestrator injetado via dependency_overrides.

Nenhuma credencial real nem banco de dados é necessário (SPEC §86).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from judicial_api.catalog.loader import default_catalog
from judicial_api.deps import get_orchestrator
from judicial_api.orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
from judicial_api.orchestration.resilience import RetryPolicy
from judicial_api.orchestration.store import InMemorySearchStore
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry


class FakeProvider(JudicialProvider):
    """Provider falso: devolve processos pré-definidos por tribunal, sem rede."""

    code = "DATAJUD"

    def __init__(self, processes_by_tribunal=None):
        self._map = processes_by_tribunal or {}

    def search(self, request, tribunal):
        return list(self._map.get(tribunal, []))

    def get_capabilities(self, tribunal):  # pragma: no cover - não usado nos E2E
        raise NotImplementedError

    def health_check(self):  # pragma: no cover - não usado nos E2E
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


class FakeProviderRegistry(ProviderRegistry):
    def __init__(self, provider):
        self._p = provider

    def get_provider(self, code):
        return self._p if code == self._p.code else None

    def provider_for_tribunal(self, tribunal_code):
        return self._p

    def list_providers(self):
        return [self._p]


def build_orchestrator(processes_by_tribunal=None, *, store=None) -> SearchOrchestrator:
    provider = FakeProvider(processes_by_tribunal)
    return SearchOrchestrator(
        FakeProviderRegistry(provider),
        catalog=default_catalog(),
        store=store or InMemorySearchStore(),
        config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )


@pytest.fixture(scope="session")
def judicial_engine():
    """Engine PostgreSQL para os testes de persistência do judicial_api.

    Reutiliza ``RAG_TEST_DATABASE_URL`` (mesmo harness do Radar). Garante que as
    tabelas ``judicial_*`` existam — cria via metadata quando ausentes, de modo que
    o teste rode mesmo em um banco onde a migration 0011 ainda não foi aplicada.
    Pula (skip) quando não há PostgreSQL configurado.
    """
    import os

    from sqlalchemy import create_engine, text

    from judicial_api.db import JudicialBase
    from judicial_api.persistence import models as _m  # noqa: F401 - registra tabelas

    url = os.getenv("RAG_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RAG_TEST_DATABASE_URL não configurada; teste de persistência exige PostgreSQL")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponível: {exc}")
    JudicialBase.metadata.create_all(engine)
    return engine


@pytest.fixture
def pg_store(judicial_engine):
    """PostgresSearchStore ligado ao banco de teste, com limpeza determinística.

    Como o store faz commit por operação (durável por natureza), a limpeza remove
    ao final as pesquisas criadas pelo teste (identificadas por prefixo de
    search_id), sem afetar dados de outros testes/execuções.
    """
    from sqlalchemy.orm import sessionmaker

    from judicial_api.persistence.models import JudicialSearchORM
    from judicial_api.persistence.postgres_store import PostgresSearchStore

    factory = sessionmaker(bind=judicial_engine, autoflush=False, autocommit=False, future=True)
    store = PostgresSearchStore(session_factory=factory)
    created_ids: list[str] = []
    store._created_ids = created_ids  # marca para o teste registrar o que criou

    yield store

    # Limpeza: remove as pesquisas criadas pelo teste (cascade apaga os filhos).
    if created_ids:
        session = factory()
        try:
            for sid in created_ids:
                row = session.query(JudicialSearchORM).filter_by(search_id=sid).one_or_none()
                if row is not None:
                    session.delete(row)
            session.commit()
        finally:
            session.close()


@pytest.fixture
def make_client():
    """Fábrica de TestClient com um orchestrator falso injetado.

    Uso: ``client = make_client({"TJPR": [proc]})``.
    """
    from judicial_api.app import app

    created = []

    def _factory(processes_by_tribunal=None):
        orch = build_orchestrator(processes_by_tribunal)
        app.dependency_overrides[get_orchestrator] = lambda: orch
        client = TestClient(app)
        created.append(orch)
        return client

    yield _factory
    app.dependency_overrides.pop(get_orchestrator, None)
