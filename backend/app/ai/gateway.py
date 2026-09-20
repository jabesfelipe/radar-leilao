from dataclasses import dataclass
from typing import Any, Protocol
from ..config import settings


class ChatProvider(Protocol):
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...
    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> Any: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class LLMGateway:
    provider: ChatProvider
    provider_name: str
    model: str

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self.provider.chat(messages, **kwargs)

    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        return self.provider.structured_chat(schema, messages, **kwargs)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.provider.embed(texts)


def build_gateway() -> LLMGateway:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from .providers.openai_provider import OpenAIProvider
        return LLMGateway(OpenAIProvider(), "openai", settings.llm_model)
    raise ValueError(f"Provider de LLM não suportado: {provider}")
