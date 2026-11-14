from typing import Any
from ...config import settings
from ..gateway import ProviderResponse, ProviderResponseInvalid


class OpenAIProvider:
    """Implementação OpenAI isolada; o restante da aplicação só conhece o LLM Gateway."""

    def __init__(self) -> None:
        if not settings.effective_llm_api_key:
            raise RuntimeError("LLM_API_KEY/OpenAI_API_KEY ainda não configurada")
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        # Timeout e retries explícitos e configuráveis (ver Settings.llm_*): evitam
        # depender do padrão da biblioteca (timeout longo) e limitam o custo de retries.
        chat_kwargs: dict[str, Any] = {
            "model": settings.llm_model,
            "api_key": settings.effective_llm_api_key,
            "temperature": 0,
            "timeout": settings.llm_timeout_seconds,
            "max_retries": settings.llm_max_retries,
        }
        if settings.llm_max_output_tokens:
            chat_kwargs["max_tokens"] = settings.llm_max_output_tokens
        self.chat_model = ChatOpenAI(**chat_kwargs)
        self.embedding_model = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.effective_llm_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    @staticmethod
    def _messages(messages: list[dict[str, str]]):
        from langchain_core.messages import HumanMessage, SystemMessage
        converted = []
        for message in messages:
            cls = SystemMessage if message.get("role") == "system" else HumanMessage
            converted.append(cls(content=message.get("content", "")))
        return converted

    @staticmethod
    def _usage(message: Any) -> tuple[int | None, int | None, str | None]:
        usage = getattr(message, "usage_metadata", None) or {}
        response_metadata = getattr(message, "response_metadata", None) or {}
        usage = usage or response_metadata.get("token_usage", {}) or response_metadata.get("usage", {}) or {}
        input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
        output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
        request_id = response_metadata.get("id") or response_metadata.get("request_id")
        return input_tokens, output_tokens, request_id

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        result = self.chat_model.invoke(self._messages(messages), **kwargs)
        input_tokens, output_tokens, request_id = self._usage(result)
        return ProviderResponse(content=str(result.content), input_tokens=input_tokens, output_tokens=output_tokens, request_id=request_id, metadata=getattr(result, "response_metadata", {}) or {})

    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> ProviderResponse:
        # method explícito (v1.0.4): no modo padrão (json_schema estrito) o gpt-4o-mini às vezes gera até o limite de
        # saída (LLM_MAX_OUTPUT_TOKENS) sem fechar o JSON — resposta truncada, cobrada e descartada. Com function calling o
        # mesmo schema e contexto devolvem ~380 tokens (diagnóstico da homologação v1.0.4, caso-01).
        result = self.chat_model.with_structured_output(schema, include_raw=True, method="function_calling").invoke(self._messages(messages), **kwargs)
        raw = result.get("raw")
        input_tokens, output_tokens, request_id = self._usage(raw)
        if result.get("parsing_error"):
            # A OpenAI já cobrou esta chamada: leva os tokens junto para llm_runs/orçamento.
            raise ProviderResponseInvalid(str(result["parsing_error"]), input_tokens, output_tokens, request_id) from result["parsing_error"]
        return ProviderResponse(content=result.get("parsed"), input_tokens=input_tokens, output_tokens=output_tokens, request_id=request_id, metadata=getattr(raw, "response_metadata", {}) or {})

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_model.embed_documents(texts)
