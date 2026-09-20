from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Radar Leilão API"
    database_url: str = "postgresql+psycopg://radar:radar_local@localhost:5432/radar_leilao"
    upload_dir: str = "backend/uploads"
    llm_api_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
