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
