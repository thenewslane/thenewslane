"""
nodes/publisher.py — LangGraph node: publish topics to Supabase + trigger ISR.

For each fully-generated topic:
  1. Insert/update trending_topics row with status='published'
  2. POST to /api/revalidate  (ISR cache invalidation)
  3. POST to /api/indexnow    (notify search engines)
  4. Send push notification via OneSignal
"""

from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)


def _revalidate(slug: str) -> None:
    """Ping the ISR revalidation endpoint for a published article."""
    if not settings.revalidate_secret:
        log.warning("REVALIDATE_SECRET not set — skipping ISR revalidation for %s", slug)
        return
    try:
        resp = httpx.post(
            settings.revalidate_endpoint,
            json={"secret": settings.revalidate_secret, "slug": slug},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Revalidated %s  status=%d", slug, resp.status_code)
    except Exception as exc:
        log.warning("ISR revalidation failed for %s: %s", slug, exc)


def _indexnow(url: str) -> None:
    """Notify IndexNow of a newly published URL."""
    if not settings.revalidate_secret:
        return
    try:
        resp = httpx.post(
            settings.indexnow_endpoint,
            json={"secret": settings.revalidate_secret, "url": url},
            timeout=10,
        )
        log.info("IndexNow pinged for %s  status=%d", url, resp.status_code)
    except Exception as exc:
        log.warning("IndexNow ping failed for %s: %s", url, exc)


def publish_topic(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — publish each generated topic and trigger downstream hooks.

    Updates state keys:
      topics_published (int)
      topics_rejected  (int)
      errors           (list[str])
    """
    batch_id: str = state["batch_id"]
    topics: list[dict[str, Any]] = state.get("topics", [])
    log.info("publish_topic: publishing %d topics  batch_id=%s", len(topics), batch_id)

    published = 0
    rejected = 0
    errors: list[str] = []

    for topic in topics:
        topic_id: str | None = topic.get("id")
        slug: str | None = topic.get("slug")

        if not topic_id or not slug:
            errors.append(f"Topic missing id/slug: {topic.get('title', 'unknown')}")
            rejected += 1
            continue

        try:
            from datetime import datetime, timezone  # noqa: PLC0415

            published_at = datetime.now(timezone.utc)

            db.update_topic_status(
                topic_id,
                "published",
                published_at=published_at,
                viral_tier=topic.get("viral_tier"),
                viral_score=topic.get("weighted_score"),
            )

            article_url = f"{settings.site_url}/trending/{slug}"
            _revalidate(slug)
            _indexnow(article_url)

            published += 1
            log.info("Published: %s  url=%s", topic.get("title", slug), article_url)

        except Exception as exc:
            msg = f"Failed to publish topic {slug}: {exc}"
            log.error(msg)
            errors.append(msg)
            rejected += 1

    log.info("publish_topic: published=%d  failed=%d", published, rejected)
    return {
        "topics_published": state.get("topics_published", 0) + published,
        "topics_rejected":  state.get("topics_rejected",  0) + rejected,
        "errors":           errors,
    }
