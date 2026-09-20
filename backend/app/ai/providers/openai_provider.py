from typing import Any
from ...config import settings


class OpenAIProvider:
    """Implementação OpenAI isolada; o restante da aplicação só conhece LLMGateway."""

    def __init__(self) -> None:
        if not settings.effective_llm_api_key:
            raise RuntimeError("LLM_API_KEY/OpenAI_API_KEY ainda não configurada")
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        self.chat_model = ChatOpenAI(model=settings.llm_model, api_key=settings.effective_llm_api_key, temperature=0)
        self.embedding_model = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.effective_llm_api_key)

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        converted = []
        for message in messages:
            cls = SystemMessage if message.get("role") == "system" else HumanMessage
            converted.append(cls(content=message.get("content", "")))
        result = self.chat_model.invoke(converted, **kwargs)
        return str(result.content)

    def structured_chat(self, schema: Any, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        from langchain_core.messages import HumanMessage, SystemMessage
        converted = []
        for message in messages:
            cls = SystemMessage if message.get("role") == "system" else HumanMessage
            converted.append(cls(content=message.get("content", "")))
        return self.chat_model.with_structured_output(schema).invoke(converted, **kwargs)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_model.embed_documents(texts)
