from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from ..config import settings
from ..logging_config import get_logger
from ..privacy import redact_pii, sanitize_messages, sanitize_texts
from ..redaction import redact

log = get_logger("llm")


def sanitize_error(message: str) -> str:
    """Mensagem de erro segura para log/persistência (sem chaves, tokens, URLs de banco
    e sem dados pessoais que o provider possa ecoar de volta no erro)."""
    return redact_pii(redact(message), force=True)


# Categorias de falha do provider (sem depender do SDK: classificação pelo nome da
# classe da exceção e do status HTTP, quando disponível).
ERROR_CATEGORIES = ("AUTENTICACAO", "RATE_LIMIT", "TIMEOUT", "CONEXAO", "REQUISICAO_INVALIDA", "PROVEDOR", "ORCAMENTO", "DESCONHECIDO")


class ProviderResponseInvalid(Exception):
    """Resposta do provider recebida (e cobrada), porém inválida. Carrega os tokens para a contabilização."""

    def __init__(self, message: str, input_tokens: int | None = None, output_tokens: int | None = None, request_id: str | None = None):
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.request_id = request_id


def classify_provider_error(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)
    if "budgetexceeded" in name:
        return "ORCAMENTO"
    if "authentication" in name or "permissiondenied" in name or status in (401, 403):
        return "AUTENTICACAO"
    if "ratelimit" in name or status == 429:
        return "RATE_LIMIT"
    if "timeout" in name or isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if "connection" in name:
        return "CONEXAO"
    if "badrequest" in name or "unprocessable" in name or status in (400, 404, 422):
        return "REQUISICAO_INVALIDA"
    if "internalserver" in name or "apistatus" in name or (isinstance(status, int) and status >= 500):
        return "PROVEDOR"
    return "DESCONHECIDO"


class ChatProvider(Protocol):
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> Any: ...
    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> Any: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class ProviderResponse:
    content: Any
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMCall:
    content: Any = None
    provider: str = "desconhecido"
    model: str = "desconhecido"
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    request_id: str | None = None
    status: str = "CONCLUIDO"
    error_type: str | None = None
    error_message: str | None = None
    error_category: str | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens

    @classmethod
    def unavailable(cls, provider: str, model: str, error_message: str, status: str = "SEM_CHAVE") -> "LLMCall":
        return cls(provider=provider, model=model, status=status, error_type="ConfigurationError", error_message=sanitize_error(error_message))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["total_tokens"] = self.total_tokens
        data.pop("content", None)
        return data


@dataclass
class LLMGateway:
    provider: ChatProvider
    provider_name: str
    model: str
    # Registra o uso de EMBEDDINGS (que não devolvem tokens) em llm_runs; ``build_gateway`` liga o
    # registrador real. Gateways montados à mão (testes) não gravam nada.
    usage_recorder: Any = None

    def _execute(self, operation: Any) -> LLMCall:
        started = time.perf_counter()
        log.info("llm chamada iniciada: provider=%s modelo=%s", self.provider_name, self.model)
        try:
            raw = operation()
            elapsed = int((time.perf_counter() - started) * 1000)
            if isinstance(raw, ProviderResponse):
                log.info("llm chamada concluida: provider=%s modelo=%s duracao_ms=%d", self.provider_name, self.model, elapsed)
                return LLMCall(content=raw.content, provider=self.provider_name, model=self.model, input_tokens=raw.input_tokens, output_tokens=raw.output_tokens, duration_ms=elapsed, request_id=raw.request_id, status="CONCLUIDO")
            log.info("llm chamada concluida: provider=%s modelo=%s duracao_ms=%d", self.provider_name, self.model, elapsed)
            return LLMCall(content=raw, provider=self.provider_name, model=self.model, duration_ms=elapsed, status="CONCLUIDO")
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            # error_message já sanitizado (nunca expõe chave/token/credencial).
            category = classify_provider_error(exc)
            log.warning("llm chamada falhou: provider=%s modelo=%s duracao_ms=%d tipo=%s categoria=%s erro=%s",
                        self.provider_name, self.model, elapsed, type(exc).__name__, category, sanitize_error(str(exc)))
            # Uma resposta recebida mas inválida (ex.: JSON fora do schema) JÁ foi cobrada: os tokens vêm
            # anexados à exceção pelo provider e entram em llm_runs/orçamento mesmo com status ERRO.
            return LLMCall(provider=self.provider_name, model=self.model, input_tokens=getattr(exc, "input_tokens", None), output_tokens=getattr(exc, "output_tokens", None), duration_ms=elapsed, request_id=getattr(exc, "request_id", None), status="ERRO", error_type=type(exc).__name__, error_message=sanitize_error(str(exc)), error_category=category)

    # Ponto ÚNICO de saída para o provider externo: dados pessoais são mascarados aqui
    # (minimização), de modo que nenhum agente/serviço precise lembrar de fazê-lo.
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> LLMCall:
        safe = sanitize_messages(messages)
        return self._execute(lambda: self.provider.chat(safe, **kwargs))

    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> LLMCall:
        safe = sanitize_messages(messages)
        return self._execute(lambda: self.provider.structured_chat(schema, safe, **kwargs))

    def embed(self, texts: list[str]) -> list[list[float]]:
        safe = sanitize_texts(texts)
        started = time.perf_counter()
        try:
            vectors = self.provider.embed(safe)
        except Exception as exc:
            category = classify_provider_error(exc)
            log.warning("embedding falhou: provider=%s textos=%d duracao_ms=%d categoria=%s", self.provider_name, len(safe), int((time.perf_counter() - started) * 1000), category)
            if self.usage_recorder:
                self.usage_recorder(model=settings.embedding_model, texts=safe, status="ERRO", error_category=category, error_message=sanitize_error(str(exc)))
            raise
        log.info("embedding concluido: provider=%s textos=%d duracao_ms=%d", self.provider_name, len(safe), int((time.perf_counter() - started) * 1000))
        if self.usage_recorder:
            self.usage_recorder(model=settings.embedding_model, texts=safe, status="CONCLUIDO")
        return vectors


class BudgetExceeded(RuntimeError):
    """Orçamento mensal de LLM atingido (ver ai/budget.py). Subclasse de RuntimeError para
    ser tratada pelos chamadores como 'LLM indisponível' (sem chamada ao provider)."""


def build_gateway() -> LLMGateway:
    if settings.llm_budget_usd_month is not None:
        from .budget import month_status
        status = month_status()
        if status.get("excedido"):
            raise BudgetExceeded("Orçamento mensal de IA atingido")
        if status.get("sem_preco"):
            # Sem preço em llm_pricing o custo da chamada é desconhecido (None) e o orçamento nunca
            # dispararia: falha FECHADA em vez de gastar sem contabilizar.
            raise BudgetExceeded("Modelo sem preço cadastrado em llm_pricing: o orçamento não pode ser aplicado")
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from .providers.openai_provider import OpenAIProvider
        from .usage import record_embedding_usage
        return LLMGateway(OpenAIProvider(), "openai", settings.llm_model, usage_recorder=record_embedding_usage)
    raise ValueError(f"Provider de LLM não suportado: {provider}")
