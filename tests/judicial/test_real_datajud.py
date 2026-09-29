"""JUR-05 — testes REAIS contra o DataJud (SPEC §84).

FORA da suíte padrão: só executam quando explicitamente habilitados por ambiente,
exigindo credencial real. Nunca rodam em CI/local por padrão para não depender de
rede nem consumir a API pública sem intenção.

Habilitar:

    RUN_REAL_DATAJUD_TESTS=true JUDICIAL_DATAJUD_API_KEY=<chave> \
        pytest -q tests/judicial/test_real_datajud.py
"""
from __future__ import annotations

import os

import pytest

_ENABLED = os.getenv("RUN_REAL_DATAJUD_TESTS", "").strip().lower() in ("1", "true", "yes")

pytestmark = pytest.mark.skipif(
    not _ENABLED,
    reason="Testes reais do DataJud desabilitados. Defina RUN_REAL_DATAJUD_TESTS=true para habilitar.",
)


@pytest.fixture
def real_provider():
    from judicial_api.catalog.loader import default_catalog
    from judicial_api.providers.datajud import DataJudProvider
    from judicial_api.providers.http_transport import HttpxTransport

    api_key = os.getenv("JUDICIAL_DATAJUD_API_KEY")
    if not api_key:
        pytest.skip("JUDICIAL_DATAJUD_API_KEY não configurada.")

    return DataJudProvider(default_catalog(), api_key=api_key, transport=HttpxTransport(), default_timeout_ms=15000)


def test_real_consulta_por_numero_processo(real_provider):
    from judicial_api.models import SearchRequest

    # Consulta por número de processo (critério comprovado do DataJud). Um número
    # inexistente deve retornar simplesmente uma lista vazia, sem erro.
    request = SearchRequest(process_number="0000000-00.0000.0.00.0000")
    processos = real_provider.search(request, "TJPR")
    assert isinstance(processos, list)


def test_real_health_check_configurado(real_provider):
    status = real_provider.health_check()
    assert status.provider == "DATAJUD"
    assert status.status == "AVAILABLE"
