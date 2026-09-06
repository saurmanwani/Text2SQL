from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Text2SQL"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8090
    app_secret: str = "change-me-in-production"
    log_level: str = "INFO"

    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5-coder:7b"
    llm_api_key: str = ""
    llm_base_url: str = ""

    metadata_database_url: str = "sqlite:///./data/text2sql.db"
    chroma_persist_directory: str = "./data/chroma"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
