"""
utils/supabase_client.py — Typed Supabase client wrapper for the agent pipeline.

Uses the service-role key (bypasses RLS) so the pipeline can write to all tables.
All methods raise on unexpected errors; callers should handle exceptions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from config.settings import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseClient:
    """Thin wrapper around supabase-py providing typed helpers for the pipeline."""

    def __init__(self) -> None:
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

    # ── Batch / runs_log ──────────────────────────────────────────────────────

    def insert_batch(self, batch_id: str | None = None) -> dict[str, Any]:
        """
        Create a new runs_log row with status='running'.
        Returns the inserted row dict (including the generated UUID id).
        """
        bid = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
        row = {
            "batch_id": bid,
            "status": "running",
            "started_at": _now_iso(),
            "signals_collected": 0,
            "topics_processed": 0,
            "topics_published": 0,
            "topics_rejected": 0,
        }
        result = self._client.table("runs_log").insert(row).execute()
        return result.data[0]

    def get_latest_batch(self) -> dict[str, Any] | None:
        """Return the most recently created runs_log row, or None."""
        result = (
            self._client.table("runs_log")
            .select("*")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data
        return rows[0] if rows else None

    def log_run(
        self,
        batch_id: str,
        *,
        status: str | None = None,
        signals_collected: int | None = None,
        topics_processed: int | None = None,
        topics_published: int | None = None,
        topics_rejected: int | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
        completed: bool = False,
    ) -> None:
        """
        Update an existing runs_log row.
        Pass only the fields you want to change; others are left unchanged.
        Set completed=True to also stamp completed_at.
        """
        patch: dict[str, Any] = {}
        if status is not None:
            patch["status"] = status
        if signals_collected is not None:
            patch["signals_collected"] = signals_collected
        if topics_processed is not None:
            patch["topics_processed"] = topics_processed
        if topics_published is not None:
            patch["topics_published"] = topics_published
        if topics_rejected is not None:
            patch["topics_rejected"] = topics_rejected
        if error_message is not None:
            patch["error_message"] = error_message[:2000]  # column limit
        if metadata is not None:
            patch["metadata"] = metadata
        if completed:
            patch["completed_at"] = _now_iso()
            if "status" not in patch:
                patch["status"] = "completed"

        if patch:
            self._client.table("runs_log").update(patch).eq("batch_id", batch_id).execute()

    # ── Trending topics ───────────────────────────────────────────────────────

    def update_topic_status(
        self,
        topic_id: str,
        status: str,
        *,
        rejection_reason: str | None = None,
        published_at: datetime | None = None,
        viral_tier: int | None = None,
        viral_score: float | None = None,
    ) -> None:
        """
        Update trending_topics.status and optional metadata fields.

        Valid statuses: pending | predicting | brand_checking |
                        generating | published | rejected
        """
        patch: dict[str, Any] = {"status": status}
        if rejection_reason is not None:
            patch["rejection_reason"] = rejection_reason
        if published_at is not None:
            patch["published_at"] = published_at.isoformat()
        if viral_tier is not None:
            patch["viral_tier"] = viral_tier
        if viral_score is not None:
            patch["viral_score"] = viral_score

        self._client.table("trending_topics").update(patch).eq("id", topic_id).execute()

    def insert_topic(self, topic: dict[str, Any]) -> dict[str, Any]:
        """Insert a new trending_topics row. Returns the inserted row."""
        result = self._client.table("trending_topics").insert(topic).execute()
        return result.data[0]

    def get_topics_by_status(self, status: str, batch_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch trending_topics rows matching status (and optionally batch_id)."""
        q = self._client.table("trending_topics").select("*").eq("status", status)
        if batch_id:
            q = q.eq("batch_id", batch_id)
        return q.execute().data or []

    # ── Config ────────────────────────────────────────────────────────────────

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Read a single value from the config table by key.
        Returns the parsed JSONB value, or default if the key doesn't exist.
        """
        result = (
            self._client.table("config")
            .select("value")
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        if result.data is None:
            return default
        return result.data.get("value", default)

    def set_config_value(self, key: str, value: Any, description: str = "") -> None:
        """Upsert a config row."""
        self._client.table("config").upsert(
            {"key": key, "value": value, "description": description},
            on_conflict="key",
        ).execute()

    # ── Raw signals ───────────────────────────────────────────────────────────

    def insert_signals(self, signals: list[dict[str, Any]]) -> int:
        """Bulk-insert raw_signals rows. Returns count inserted."""
        if not signals:
            return 0
        self._client.table("raw_signals").insert(signals).execute()
        return len(signals)

    # ── Viral predictions ─────────────────────────────────────────────────────

    def insert_viral_prediction(self, prediction: dict[str, Any]) -> dict[str, Any]:
        """Insert a viral_predictions row. Returns the inserted row."""
        result = self._client.table("viral_predictions").insert(prediction).execute()
        return result.data[0]

    # ── Brand safety ─────────────────────────────────────────────────────────

    def insert_brand_safety_log(self, log: dict[str, Any]) -> dict[str, Any]:
        """Insert a brand_safety_log row. Returns the inserted row."""
        result = self._client.table("brand_safety_log").insert(log).execute()
        return result.data[0]

    # ── Passthrough ───────────────────────────────────────────────────────────

    @property
    def client(self) -> Client:
        """Direct access to the underlying supabase-py Client for ad-hoc queries."""
        return self._client


# Module-level singleton
db = SupabaseClient()
