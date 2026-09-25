from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Radar Leilão API"
    database_url: str = "postgresql+psycopg://radar:radar_local@localhost:5432/radar_leilao"
    storage_dir: str = "storage/documents"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    rag_vector_weight: float = 0.7
    rag_text_weight: float = 0.3
    rag_default_limit: int = 8
    rag_max_limit: int = 50
    rag_text_config: str = "portuguese"
    # Document Intelligence: detecção de extração insuficiente + OCR opcional (local-first).
    # ocr_enabled só tenta OCR quando um motor local estiver disponível (import-guard);
    # se indisponível, a limitação é registrada no metadata sem quebrar o pipeline.
    ocr_enabled: bool = False
    ocr_language: str = "por"
    # Sinais objetivos de extração insuficiente (sem número mágico único):
    # documento binário (pdf/imagem) com menos de N caracteres por página estimada,
    # ou densidade de texto muito baixa frente ao tamanho do arquivo original.
    extraction_min_chars: int = 200
    extraction_min_chars_per_kb: float = 1.0
    llm_api_key: str | None = None
    openai_api_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @model_validator(mode="after")
    def validate_runtime(self):
        if not self.database_url.startswith("postgresql"):
            raise ValueError("O Radar exige PostgreSQL; SQLite não é suportado")
        if self.rag_vector_weight < 0 or self.rag_text_weight < 0 or self.rag_vector_weight + self.rag_text_weight <= 0:
            raise ValueError("Os pesos do ranking RAG devem ser não negativos e somar um valor maior que zero")
        if self.rag_default_limit < 1 or self.rag_max_limit < self.rag_default_limit:
            raise ValueError("Os limites do RAG são inválidos")
        return self

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def effective_llm_api_key(self) -> str | None:
        return self.openai_api_key or self.llm_api_key


settings = Settings()
