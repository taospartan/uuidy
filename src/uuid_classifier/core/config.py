"""Application configuration via Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://uuidy:uuidy@localhost:5432/uuidy"

    # SerpAPI
    serpapi_key: str | None = None

    # Cache
    cache_ttl_days: int = 30


# Global settings instance
settings = Settings()
