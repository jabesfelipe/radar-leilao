from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from ..config import settings
from ..logging_config import get_logger
from ..redaction import redact

log = get_logger("llm")


def sanitize_error(message: str) -> str:
    """Mensagem de erro segura para log/persistência (sem chaves, tokens, URLs de banco)."""
    return redact(message)


# Categorias de falha do provider (sem depender do SDK: classificação pelo nome da
# classe da exceção e do status HTTP, quando disponível).
ERROR_CATEGORIES = ("AUTENTICACAO", "RATE_LIMIT", "TIMEOUT", "CONEXAO", "REQUISICAO_INVALIDA", "PROVEDOR", "DESCONHECIDO")


def classify_provider_error(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)
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
    def unavailable(cls, provider: str, model: str, error_message: str) -> "LLMCall":
        return cls(provider=provider, model=model, status="SEM_CHAVE", error_type="ConfigurationError", error_message=sanitize_error(error_message))

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
            return LLMCall(provider=self.provider_name, model=self.model, duration_ms=elapsed, status="ERRO", error_type=type(exc).__name__, error_message=sanitize_error(str(exc)), error_category=category)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> LLMCall:
        return self._execute(lambda: self.provider.chat(messages, **kwargs))

    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> LLMCall:
        return self._execute(lambda: self.provider.structured_chat(schema, messages, **kwargs))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.provider.embed(texts)


def build_gateway() -> LLMGateway:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from .providers.openai_provider import OpenAIProvider
        return LLMGateway(OpenAIProvider(), "openai", settings.llm_model)
    raise ValueError(f"Provider de LLM não suportado: {provider}")
