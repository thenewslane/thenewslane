"""
config/settings.py — Validated settings object for the agent pipeline.

Reads from apps/agent/.env (and falls back to environment variables).
All required vars raise ValueError at import time if missing.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives alongside this package (apps/agent/.env)
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Required ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(..., description="Supabase service-role key (bypasses RLS)")

    # ── Signal collection ─────────────────────────────────────────────────────
    newsapi_key: str = Field(default="", description="NewsAPI.org key")
    youtube_api_key: str = Field(default="", description="YouTube Data API v3 key")

    # ── AI / ML ───────────────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key (Llama Guard inference)")
    replicate_api_key: str = Field(default="", description="Replicate API key (Flux, Kling video)")
    together_api_key: str = Field(default="", description="Together.ai API key (Stable Diffusion/FLUX image generation)")
    openai_api_key: str = Field(default="", description="OpenAI API key (optional; thumbnails use Together.ai, not OpenAI in batch)")

    # ── Media (copyright-free first; AI only when no applicable image) ─────────
    unsplash_access_key: str = Field(default="", description="Unsplash API access key (free tier)")
    pexels_api_key: str = Field(default="", description="Pexels API key (free)")
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs TTS key")
    elevenlabs_voice_id: str = Field(default="pNInz6obpgDQGcFmaJgB", description="ElevenLabs voice ID (default: Adam, neutral male news voice)")

    # ── Distribution ─────────────────────────────────────────────────────────
    onesignal_app_id: str = Field(default="", description="OneSignal App ID")
    onesignal_api_key: str = Field(default="", description="OneSignal REST API key")

    # ── Email ─────────────────────────────────────────────────────────────────
    resend_api_key: str = Field(default="", description="Resend email API key")

    # ── Publication identity ──────────────────────────────────────────────────
    publication_name: str = Field(default="theNewslane")
    publication_domain: str = Field(default="thenewslane.com")
    author_name: str = Field(default="Aadi")

    # ── Webhook / ISR ────────────────────────────────────────────────────────
    webhook_secret: str = Field(default="", description="Shared secret for /api/revalidate calls")
    revalidate_secret: str = Field(default="", description="ISR revalidation secret (= webhook_secret if not set)")
    slack_webhook_url: str = Field(default="", description="Slack incoming webhook URL for pipeline notifications")

    # ── Pipeline tuning ───────────────────────────────────────────────────────
    pipeline_cron: str = Field(default="0 3 * * *", description="Inngest CRON expression (default: once daily at 03:00 UTC)")
    pipeline_interval_minutes: int = Field(default=1440, description="Built-in loop interval in minutes (used by --schedule; 1440 = once per day)")
    batch_size_limit: int = Field(default=50, description="Max topics to process per batch")
    trends_geo: str = Field(default="US", description="ISO country code for Google Trends geo filter")
    newsapi_max_topics: int = Field(default=20, description="Max topics to query in NewsAPI per batch")

    # ── Fact-check ─────────────────────────────────────────────────────────────
    pause_fact_check: bool = Field(default=True, description="If True, skip LLM/date verification; set fact_check=yes and publish for all content")

    # ── Async publish & HITL ───────────────────────────────────────────────────
    publish_concurrency: int = Field(default=2, description="Max concurrent publish operations (async)")
    publish_hitl_delay_min: float = Field(default=2.0, description="HITL min delay (sec) before each publish")
    publish_hitl_delay_max: float = Field(default=10.0, description="HITL max delay (sec) before each publish")
    media_concurrency: int = Field(default=2, description="Max concurrent image/media generations per batch")
    media_hitl_delay_min: float = Field(default=0.0, description="HITL min delay (sec) before starting each media task")
    media_hitl_delay_max: float = Field(default=2.0, description="HITL max delay (sec) before starting each media task")

    # ── Thumbnail defaults ─────────────────────────────────────────────────────
    thumbnail_min_width: int = Field(default=1200, description="Minimum thumbnail width in pixels")
    default_logo_url: str = Field(default="", description="URL of theNewslane default logo (used when no image found)")

    @model_validator(mode="after")
    def _validate_required(self) -> "Settings":
        missing: list[str] = []
        if not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_service_key:
            missing.append("SUPABASE_SERVICE_KEY")
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                f"Check apps/agent/.env"
            )
        # Fall back revalidate_secret to webhook_secret
        if not self.revalidate_secret and self.webhook_secret:
            object.__setattr__(self, "revalidate_secret", self.webhook_secret)
        return self

    @property
    def site_url(self) -> str:
        return f"https://{self.publication_domain}"

    @property
    def revalidate_endpoint(self) -> str:
        return f"{self.site_url}/api/revalidate"

    @property
    def indexnow_endpoint(self) -> str:
        return f"{self.site_url}/api/indexnow"


# Module-level singleton — imported by all pipeline modules
settings = Settings()
