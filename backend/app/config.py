"""Application settings loaded from environment variables.

Security note: API keys and secrets are loaded here from the environment.
They must never be exposed to the frontend or committed to the repository.
See AGENTS.md hard rules and .env.example for allowed values.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: str = "development"
    app_name: str = "knowledge-base-rag"
    app_debug: bool = True

    # --- Backend ---
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_log_level: str = "info"

    # --- Demo model configuration ---
    anthropic_api_key: str | None = None
    anthropic_base_url: str | None = None
    gen_model: str = "claude-opus-4-8"
    embed_model: str = "BAAI/bge-m3"
    regulatory_test_site_url: str = "http://localhost:3001"
    data_dir: Path = Path("./data")

    # --- PostgreSQL + pgvector (reserved for post-demo builds) ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "kb_rag"
    postgres_user: str = "kb_admin"
    postgres_password: str = "changeme"

    # --- File Storage ---
    upload_dir: Path = Path("./uploads")
    max_upload_size_mb: int = 100

    # --- Model Gateway (reserved for post-demo builds) ---
    model_provider: str = "mock"
    model_api_key: str | None = None
    model_endpoint: str | None = None
    model_deployment_name: str | None = None

    # --- Embedding Service (reserved for post-demo builds) ---
    embedding_provider: str = "mock"
    embedding_api_key: str | None = None
    embedding_model_name: str | None = None

    # --- Search Gateway ---
    search_gateway_enabled: bool = False
    search_allowlist: str = ""

    # --- Audit Logging ---
    audit_log_level: str = "standard"
    audit_retention_days: int = 90

    # --- Security ---
    secret_key: str = Field(default="changeme-generate-a-real-secret-key", repr=False)

    @field_validator("anthropic_base_url")
    @classmethod
    def validate_anthropic_base_url(cls, value: str | None) -> str | None:
        """Require HTTPS for configured external model gateways."""

        if not value:
            return None
        normalized = value.rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("ANTHROPIC_BASE_URL must use https://")
        return normalized

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy database URL for PostgreSQL."""

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync SQLAlchemy database URL for Alembic migrations."""

        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a Settings instance. Can be used as a FastAPI dependency."""

    return Settings()


settings = get_settings()
