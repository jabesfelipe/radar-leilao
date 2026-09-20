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
    llm_api_key: str | None = None
    openai_api_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @model_validator(mode="after")
    def postgres_is_required(self):
        if not self.database_url.startswith("postgresql"):
            raise ValueError("O Radar exige PostgreSQL; SQLite não é suportado")
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
