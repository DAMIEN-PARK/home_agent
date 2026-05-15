from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "home_agent"
    environment: str = Field(default="dev")
    debug: bool = True

    database_url: str = Field(
        default="postgresql+asyncpg://home_agent:home_agent@localhost:5432/home_agent",
        description="Async SQLAlchemy URL (asyncpg driver).",
    )

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    anthropic_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
