"""DataJudProvider — provider concreto do DataJud/CNJ (JUR-02).

Um ÚNICO provider atende todas as fontes do catálogo (TJPR, TJSP, TRFs, TRTs,
superiores, eleitorais, militares). A diferença entre tribunais é dado de
catálogo (alias/endpoint/capacidades), não código.

Responsabilidades desta task:
- construir a query do DataJud (Elasticsearch) a partir de SearchRequest;
- autenticar via header ``Authorization: APIKey <chave>`` (chave de config externa);
- encapsular a paginação específica do DataJud (``search_after``) — o domínio
  não conhece Elasticsearch;
- normalizar a resposta bruta no contrato ``Process``;
- expor ``get_capabilities`` (do catálogo) e ``health_check``.

Fora do escopo (JUR-03+): orquestração multi-fonte, concorrência, retry,
timeouts, persistência, sinais. A consulta a uma fonte individual funciona aqui.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..catalog.loader import CatalogEntry, JudicialCatalog, default_catalog
from ..enums import ErrorCode
from ..errors import JudicialError
from ..models import (
    Movement,
    Party,
    Process,
    ProviderStatus,
    SearchRequest,
    Subject,
    TribunalCapabilities,
)
from .base import JudicialProvider

PROVIDER_CODE = "DATAJUD"


@runtime_checkable
class HttpResponse(Protocol):
    status_code: int

    def json(self) -> Any: ...


@runtime_checkable
class HttpTransport(Protocol):
    """Transporte HTTP mínimo e injetável (permite testes sem rede)."""

    def post(self, url: str, *, json: dict, headers: dict, timeout: float) -> HttpResponse: ...


def only_digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


class DataJudProvider(JudicialProvider):
    """Provider do DataJud dirigido por catálogo.

    O ``transport`` é injetável; quando ausente, permanece ``None`` e qualquer
    tentativa de rede falha de forma controlada (CONFIGURATION_ERROR). Isso mantém
    a JUR-02 testável sem chamadas reais e sem exigir a API key.
    """

    code = PROVIDER_CODE

    def __init__(
        self,
        catalog: JudicialCatalog | None = None,
        *,
        api_key: str | None = None,
        transport: HttpTransport | None = None,
        default_timeout_ms: int = 8000,
    ) -> None:
        self._catalog = catalog or default_catalog()
        self._api_key = api_key
        self._transport = transport
        self._default_timeout_ms = default_timeout_ms

    # ------------------------------------------------------------------
    # Catálogo / capacidades
    # ------------------------------------------------------------------
    def _entry_or_error(self, tribunal: str) -> CatalogEntry:
        canonical = self._catalog.resolve_alias(tribunal) or tribunal
        entry = self._catalog.get(canonical)
        if entry is None:
            raise JudicialError(
                ErrorCode.CONFIGURATION_ERROR,
                f"Tribunal '{tribunal}' não está no catálogo.",
                http_status=400,
                provider=self.code,
                tribunal=tribunal,
            )
        return entry

    def get_capabilities(self, tribunal: str) -> TribunalCapabilities:
        return self._entry_or_error(tribunal).to_capabilities()

    # ------------------------------------------------------------------
    # Construção da query (Elasticsearch do DataJud)
    # ------------------------------------------------------------------
    def build_query(self, request: SearchRequest, entry: CatalogEntry, *, page_size: int, search_after: list | None = None) -> dict:
        """Monta o corpo da query do DataJud a partir dos critérios suportados.

        Só usa critérios comprovadamente suportados pela fonte (capabilities do
        catálogo). Se nenhum critério suportado for informado, ergue
        UNSUPPORTED_SEARCH_CRITERIA (SPEC §3) — nunca simula capacidade.
        """
        supports = entry.capabilities
        must: list[dict] = []

        if request.process_number and supports.process_number:
            # Campo canônico do DataJud é numeroProcesso sem máscara (só dígitos).
            must.append({"match": {"numeroProcesso": only_digits(request.process_number)}})

        # Critérios pessoais (nome/cpf/cnpj) não são campos públicos pesquisáveis
        # no DataJud: se o consumidor pedir e a fonte não suportar, é explicitamente
        # não suportado — não inventamos filtro.
        pediu_pessoa = any([request.name, request.cpf, request.cnpj])
        pessoa_suportada = supports.name or supports.cpf or supports.cnpj

        if not must:
            if pediu_pessoa and not pessoa_suportada:
                raise JudicialError(
                    ErrorCode.UNSUPPORTED_SEARCH_CRITERIA,
                    "Esta fonte não suporta pesquisa por nome/CPF/CNPJ.",
                    http_status=422,
                    provider=self.code,
                    tribunal=entry.code,
                )
            raise JudicialError(
                ErrorCode.UNSUPPORTED_SEARCH_CRITERIA,
                "Nenhum critério de pesquisa suportado foi informado para esta fonte.",
                http_status=422,
                provider=self.code,
                tribunal=entry.code,
            )

        body: dict = {
            "size": page_size,
            "query": {"bool": {"must": must}},
            # Ordenação estável exigida pela paginação search_after do DataJud.
            "sort": [{"@timestamp": {"order": "asc"}}, {"_id": {"order": "asc"}}],
        }
        if search_after:
            body["search_after"] = search_after
        return body

    # ------------------------------------------------------------------
    # Execução com paginação encapsulada (search_after)
    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        if not self._api_key:
            raise JudicialError(
                ErrorCode.CONFIGURATION_ERROR,
                "API key do DataJud não configurada.",
                http_status=500,
                provider=self.code,
            )
        # Formato oficial: "Authorization: APIKey <chave pública>".
        return {"Authorization": f"APIKey {self._api_key}", "Content-Type": "application/json"}

    def search(self, request: SearchRequest, tribunal: str) -> list[Process]:
        """Consulta uma fonte e devolve processos normalizados, percorrendo todas
        as páginas via search_after (encapsulado). Respeita page_size e
        max_pages_per_source do request."""
        entry = self._entry_or_error(tribunal)
        if self._transport is None:
            raise JudicialError(
                ErrorCode.CONFIGURATION_ERROR,
                "Transporte HTTP não configurado para consulta real.",
                http_status=500,
                provider=self.code,
                tribunal=entry.code,
            )
        headers = self._headers()
        timeout_s = self._default_timeout_ms / 1000.0
        page_size = max(1, request.page_size)
        max_pages = max(1, request.max_pages_per_source)

        processes: list[Process] = []
        search_after: list | None = None
        for _ in range(max_pages):
            body = self.build_query(request, entry, page_size=page_size, search_after=search_after)
            response = self._transport.post(entry.search_url, json=body, headers=headers, timeout=timeout_s)
            payload = self._read_payload(response, entry)
            hits = self._hits(payload)
            if not hits:
                break
            processes.extend(self.normalize(payload, entry.code))
            last_sort = hits[-1].get("sort")
            if not last_sort or len(hits) < page_size:
                break
            search_after = last_sort
        return processes

    @staticmethod
    def _hits(payload: dict) -> list[dict]:
        return (payload or {}).get("hits", {}).get("hits", []) or []

    def _read_payload(self, response: HttpResponse, entry: CatalogEntry) -> dict:
        status = getattr(response, "status_code", None)
        if status == 401 or status == 403:
            raise JudicialError(
                ErrorCode.AUTHENTICATION_ERROR,
                "Falha de autenticação no DataJud.",
                http_status=502,
                retryable=False,
                provider=self.code,
                tribunal=entry.code,
            )
        if status == 429:
            raise JudicialError(
                ErrorCode.RATE_LIMITED, "DataJud limitou a taxa de requisições.",
                http_status=502, provider=self.code, tribunal=entry.code,
            )
        if status is not None and status >= 500:
            raise JudicialError(
                ErrorCode.PROVIDER_SERVER_ERROR, "Erro no servidor do DataJud.",
                http_status=502, provider=self.code, tribunal=entry.code,
            )
        if status is not None and status >= 400:
            raise JudicialError(
                ErrorCode.PROVIDER_SERVER_ERROR, "Requisição rejeitada pelo DataJud.",
                http_status=502, provider=self.code, tribunal=entry.code,
            )
        try:
            return response.json() or {}
        except Exception as exc:  # noqa: BLE001 - normalizamos qualquer falha de parse
            raise JudicialError(
                ErrorCode.PARSE_ERROR, "Resposta do DataJud não pôde ser interpretada.",
                http_status=502, retryable=False, provider=self.code, tribunal=entry.code,
            ) from exc

    # ------------------------------------------------------------------
    # Normalização inicial
    # ------------------------------------------------------------------
    def normalize(self, raw: Any, tribunal: str) -> list[Process]:
        """Converte o payload bruto (Elasticsearch do DataJud) em Process[].

        Aceita tanto o payload completo (com hits.hits) quanto uma lista de hits.
        Campos ausentes são tolerados (a fonte varia por tribunal).
        """
        entry = self._entry_or_error(tribunal)
        hits = raw if isinstance(raw, list) else self._hits(raw)
        result: list[Process] = []
        for hit in hits:
            source = hit.get("_source", hit) if isinstance(hit, dict) else {}
            result.append(self._normalize_source(source, entry, source_identifier=hit.get("_id") if isinstance(hit, dict) else None))
        return result

    def _normalize_source(self, source: dict, entry: CatalogEntry, *, source_identifier: str | None) -> Process:
        classe = source.get("classe") or {}
        orgao = source.get("orgaoJulgador") or {}
        subjects = [
            Subject(code=str(a.get("codigo")) if a.get("codigo") is not None else None, name=a.get("nome"))
            for a in (source.get("assuntos") or [])
            if isinstance(a, dict)
        ]
        movements = [
            Movement(
                movement_date=m.get("dataHora"),
                code=str(m.get("codigo")) if m.get("codigo") is not None else None,
                description=m.get("nome"),
            )
            for m in (source.get("movimentos") or [])
            if isinstance(m, dict)
        ]
        # A API pública do DataJud não expõe partes de forma padronizada/pública;
        # mantemos a lista vazia por padrão (não inventamos partes).
        parties: list[Party] = []

        return Process(
            process_number=str(source.get("numeroProcesso") or ""),
            tribunal=entry.code,
            justice_type=entry.justice_type,
            jurisdiction=str(source.get("grau")) if source.get("grau") is not None else None,
            court=orgao.get("nome"),
            class_code=str(classe.get("codigo")) if classe.get("codigo") is not None else None,
            class_name=classe.get("nome"),
            subjects=subjects,
            parties=parties,
            movements=movements,
            electronic=None,
            last_movement_at=source.get("dataHoraUltimaAtualizacao"),
            source_identifier=source_identifier,
        )

    # ------------------------------------------------------------------
    # Saúde do provider
    # ------------------------------------------------------------------
    def health_check(self) -> ProviderStatus:
        # Nesta fase reportamos disponibilidade de configuração (não faz rede):
        # AVAILABLE quando há transporte e credencial; caso contrário NOT_CONFIGURED.
        configured = self._transport is not None and bool(self._api_key)
        return ProviderStatus(provider=self.code, status="AVAILABLE" if configured else "NOT_CONFIGURED")
