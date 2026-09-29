"""JUR-03 — testes de integração do Search Orchestrator (sem rede).

Usa um provider falso, dirigido por um mapa tribunal->comportamento, para simular
sucesso, vazio, timeout, indisponibilidade e não-suportado, exercitando execução
paralela, isolamento de falha, status agregado, dedup, idempotência e reanálise.
"""
from __future__ import annotations

from judicial_api.catalog.loader import default_catalog
from judicial_api.enums import ErrorCode, SearchEventType, SearchStatus, SourceStatus
from judicial_api.errors import JudicialError
from judicial_api.models import JusticeType, Process, SearchRequest
from judicial_api.orchestration.orchestrator import OrchestratorConfig, SearchOrchestrator
from judicial_api.orchestration.resilience import RetryPolicy
from judicial_api.orchestration.store import InMemorySearchStore
from judicial_api.providers.base import JudicialProvider
from judicial_api.registry.base import ProviderRegistry


def _proc(tribunal, numero):
    return Process(process_number=numero, tribunal=tribunal, justice_type=JusticeType.STATE)


class ScriptedProvider(JudicialProvider):
    """Provider falso: comportamento por tribunal definido em ``behavior``.

    behavior[tribunal] = ("ok", [Process...]) | ("empty", []) |
        ("raise", JudicialError) | ("raise_then_ok", (n_falhas, [Process...]))
    """

    code = "DATAJUD"

    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = {}

    def search(self, request, tribunal):
        self.calls[tribunal] = self.calls.get(tribunal, 0) + 1
        kind, payload = self.behavior.get(tribunal, ("empty", []))
        if kind == "ok":
            return list(payload)
        if kind == "empty":
            return []
        if kind == "raise":
            raise payload
        if kind == "raise_then_ok":
            n_falhas, processos = payload
            if self.calls[tribunal] <= n_falhas:
                raise JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504, tribunal=tribunal)
            return list(processos)
        return []

    def get_capabilities(self, tribunal):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize(self, raw, tribunal):
        return []


class OneProviderRegistry(ProviderRegistry):
    def __init__(self, provider):
        self._p = provider

    def get_provider(self, code):
        return self._p if code == self._p.code else None

    def provider_for_tribunal(self, tribunal_code):
        return self._p

    def list_providers(self):
        return [self._p]


def _orchestrator(behavior, config=None):
    provider = ScriptedProvider(behavior)
    return (
        SearchOrchestrator(
            OneProviderRegistry(provider),
            catalog=default_catalog(),
            store=InMemorySearchStore(),
            config=config or OrchestratorConfig(),
            sleep=lambda _: None,  # sem espera real
        ),
        provider,
    )


def test_completed_quando_todas_sucedem_com_processos():
    orch, _ = _orchestrator({
        "TJPR": ("ok", [_proc("TJPR", "1")]),
        "TJSP": ("ok", [_proc("TJSP", "2")]),
    })
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"]))
    assert res.status == SearchStatus.COMPLETED
    assert res.completeness.successful_sources == 2
    assert len(res.processes) == 2


def test_empty_quando_todas_sucedem_sem_processos():
    orch, _ = _orchestrator({"TJPR": ("empty", []), "TJSP": ("empty", [])})
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"]))
    assert res.status == SearchStatus.EMPTY
    assert res.completeness.failed_sources == 0


def test_partial_quando_uma_falha_e_outra_sucede():
    # regra crítica: EMPTY != PARTIAL
    orch, _ = _orchestrator({
        "TJPR": ("ok", [_proc("TJPR", "1")]),
        "TJSP": ("raise", JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504, tribunal="TJSP")),
    })
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"]))
    assert res.status == SearchStatus.PARTIAL
    assert res.completeness.successful_sources == 1
    assert res.completeness.failed_sources == 1
    tjsp = next(s for s in res.sources if s.tribunal == "TJSP")
    assert tjsp.status == SourceStatus.TIMEOUT
    assert tjsp.error.code == ErrorCode.PROVIDER_TIMEOUT.value
    assert res.reanalyze.recommended is True
    assert "TJSP" in res.reanalyze.sources_affected


def test_failed_quando_todas_falham():
    orch, _ = _orchestrator({
        "TJPR": ("raise", JudicialError(ErrorCode.PROVIDER_UNAVAILABLE, "down", http_status=502, tribunal="TJPR")),
        "TJSP": ("raise", JudicialError(ErrorCode.PROVIDER_TIMEOUT, "timeout", http_status=504, tribunal="TJSP")),
    })
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"]))
    assert res.status == SearchStatus.FAILED


def test_unsupported_conta_como_partial_e_nao_reanalisavel():
    orch, _ = _orchestrator({
        "TJPR": ("ok", [_proc("TJPR", "1")]),
        "TJSP": ("raise", JudicialError(ErrorCode.UNSUPPORTED_SEARCH_CRITERIA, "n/a", http_status=422, tribunal="TJSP")),
    })
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"]))
    assert res.status == SearchStatus.PARTIAL
    assert res.completeness.unsupported_sources == 1
    # UNSUPPORTED não é reprocessável
    assert "TJSP" not in res.reanalyze.sources_affected


def test_falha_isolada_nao_derruba_as_demais():
    orch, provider = _orchestrator({
        "TJPR": ("ok", [_proc("TJPR", "1")]),
        "TJSP": ("raise", JudicialError(ErrorCode.PROVIDER_SERVER_ERROR, "500", http_status=502, tribunal="TJSP")),
        "TRF4": ("ok", [_proc("TRF4", "3")]),
    })
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP", "TRF4"]))
    ok = {s.tribunal for s in res.sources if s.status == SourceStatus.SUCCESS}
    assert ok == {"TJPR", "TRF4"}


def test_deduplicacao_por_tribunal_e_numero():
    orch, _ = _orchestrator({
        "TJPR": ("ok", [_proc("TJPR", "1"), _proc("TJPR", "1"), _proc("TJPR", "2")]),
    })
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    numeros = sorted(p.process_number for p in res.processes)
    assert numeros == ["1", "2"]


def test_retry_transitorio_recupera_e_conta_tentativas():
    orch, provider = _orchestrator({
        "TJPR": ("raise_then_ok", (2, [_proc("TJPR", "1")])),
    }, config=OrchestratorConfig(retry=RetryPolicy(max_attempts=3)))
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    assert res.status == SearchStatus.COMPLETED
    tjpr = next(s for s in res.sources if s.tribunal == "TJPR")
    assert tjpr.attempts == 3  # 2 falhas + 1 sucesso


def test_idempotencia_request_hash_persistido():
    orch, _ = _orchestrator({"TJPR": ("ok", [_proc("TJPR", "1")])})
    store = orch._store  # store injetado
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    rec = store.get(res.search_id)
    assert rec is not None
    assert store.find_by_request_hash(rec.request_hash) is rec


def test_eventos_de_auditoria_registrados():
    orch, _ = _orchestrator({"TJPR": ("ok", [_proc("TJPR", "1")])})
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    rec = orch._store.get(res.search_id)
    tipos = [e.type for e in rec.events]
    assert SearchEventType.SEARCH_CREATED in tipos
    assert SearchEventType.SOURCE_SELECTED in tipos
    assert SearchEventType.SOURCE_SUCCESS in tipos
    assert SearchEventType.SEARCH_COMPLETED in tipos


def test_reanalise_reprocessa_somente_fontes_que_falharam():
    provider = ScriptedProvider({
        "TJPR": ("ok", [_proc("TJPR", "1")]),
        "TJSP": ("raise_then_ok", (1, [_proc("TJSP", "2")])),
    })
    orch = SearchOrchestrator(
        OneProviderRegistry(provider), catalog=default_catalog(),
        store=InMemorySearchStore(), config=OrchestratorConfig(retry=RetryPolicy(max_attempts=1)),
        sleep=lambda _: None,
    )
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR", "TJSP"]))
    assert res.status == SearchStatus.PARTIAL  # TJSP falhou (1 tentativa)

    chamadas_tjpr_antes = provider.calls["TJPR"]
    res2 = orch.retry_failed(res.search_id)
    # TJPR (sucesso) NÃO foi reconsultado; TJSP sim (agora sucede)
    assert provider.calls["TJPR"] == chamadas_tjpr_antes
    assert res2.status == SearchStatus.COMPLETED
    assert {s.tribunal for s in res2.sources if s.status == SourceStatus.SUCCESS} == {"TJPR", "TJSP"}
    assert sorted(p.process_number for p in res2.processes) == ["1", "2"]


def test_get_retorna_resultado_persistido():
    orch, _ = _orchestrator({"TJPR": ("ok", [_proc("TJPR", "1")])})
    res = orch.search(SearchRequest(process_number="x", tribunals=["TJPR"]))
    again = orch.get(res.search_id)
    assert again is not None and again.search_id == res.search_id
    assert orch.get("inexistente") is None
