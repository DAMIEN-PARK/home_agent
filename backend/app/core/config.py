from functools import lru_cache
from pathlib import Path

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
    # Regex for LAN clients (e.g. http://192.168.1.42:5173, http://home.local:5173).
    # When set, CORSMiddleware uses it in addition to cors_origins.
    cors_origin_regex: str | None = Field(
        default=r"^http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|[a-zA-Z0-9-]+\.local):(5173|8000)$"
    )

    anthropic_api_key: str | None = None

    # Per-agent model routing. Override via AGENT_MODELS env var (JSON).
    # Settings page (planning/screens/settings.html) is the user-facing editor.
    agent_models: dict[str, str] = Field(
        default_factory=lambda: {
            "orchestrator": "claude-sonnet-4-6",
            "schedule": "claude-haiku-4-5",
            "todo": "claude-sonnet-4-6",
            "ledger": "claude-haiku-4-5",
            "finance": "claude-opus-4-7",
            "ideas": "claude-sonnet-4-6",
            "files": "claude-sonnet-4-6",
        }
    )

    # Root directory for domain-chat file attachments. Container path; persisted
    # via the `backend_data` compose volume.
    files_root: Path = Path("/app/data/files")

    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/oauth/google/callback"
    google_calendar_id: str = "primary"


@lru_cache
def get_settings() -> Settings:
    return Settings()
