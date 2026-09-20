from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from ..config import settings


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

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens

    @classmethod
    def unavailable(cls, provider: str, model: str, error_message: str) -> "LLMCall":
        return cls(provider=provider, model=model, status="SEM_CHAVE", error_type="ConfigurationError", error_message=error_message)

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
        try:
            raw = operation()
            elapsed = int((time.perf_counter() - started) * 1000)
            if isinstance(raw, ProviderResponse):
                return LLMCall(content=raw.content, provider=self.provider_name, model=self.model, input_tokens=raw.input_tokens, output_tokens=raw.output_tokens, duration_ms=elapsed, request_id=raw.request_id, status="CONCLUIDO")
            return LLMCall(content=raw, provider=self.provider_name, model=self.model, duration_ms=elapsed, status="CONCLUIDO")
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            return LLMCall(provider=self.provider_name, model=self.model, duration_ms=elapsed, status="ERRO", error_type=type(exc).__name__, error_message=str(exc)[:2000])

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
