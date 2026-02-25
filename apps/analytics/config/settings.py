"""
config/settings.py — Validated settings for the analytics service.

Reads from apps/analytics/.env (falls back to environment variables).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="Async PostgreSQL connection string (postgresql+asyncpg://...)",
    )
    database_url_sync: str = Field(
        default="",
        description="Sync PostgreSQL connection string for training scripts (postgresql://...)",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    model_artifacts_dir: str = Field(
        default=str(Path(__file__).parent.parent / "ml" / "artifacts"),
        description="Directory containing trained .joblib model files",
    )

    feature_pipeline_interval_minutes: int = Field(
        default=15,
        description="How often the feature engineering pipeline runs (minutes)",
    )

    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8001, description="Server bind port")

    @model_validator(mode="after")
    def _derive_sync_url(self) -> "Settings":
        if not self.database_url_sync and self.database_url:
            sync_url = self.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
            object.__setattr__(self, "database_url_sync", sync_url)
        return self


settings = Settings()
