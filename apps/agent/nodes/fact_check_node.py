"""
nodes/fact_check_node.py — Fact-checking intermediary agent.

Picks rows from trending_topics where fact_check='no', runs date/data verification
and cross-checks, then sets fact_check='yes' and status='published' and triggers
ISR revalidation and IndexNow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# Max rows to process per run
FACT_CHECK_BATCH_LIMIT = 50


def _fire_external(slug: str) -> None:
    """Trigger Vercel revalidate and IndexNow for a published slug."""
    if not getattr(settings, "revalidate_secret", None) or not settings.revalidate_secret:
        return
    revalidate = getattr(settings, "revalidate_endpoint", "") or ""
    indexnow = getattr(settings, "indexnow_endpoint", "") or ""
    site_url = getattr(settings, "site_url", "") or "https://thenewslane.com"
    for url, payload in [
        (revalidate, {"secret": settings.revalidate_secret, "slug": slug}),
        (indexnow, {"secret": settings.revalidate_secret, "url": f"{site_url}/trending/{slug}"}),
    ]:
        if not url:
            continue
        try:
            httpx.post(url, json=payload, timeout=10)
        except Exception as exc:
            log.warning("[fact_check] external call failed (%s): %s", url, exc)


def verify_topic(row: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Run fact-check and date/data verification on a topic row.
    Returns (passed: bool, list of correction notes or errors).

    Overridden in Steps 6–7 with date verification and LLM cross-check.
    """
    # Stub: pass all for now
    return True, []


def run_fact_check_batch() -> tuple[List[str], List[str]]:
    """
    Fetch all trending_topics with fact_check='no', verify each, set fact_check='yes'
    and status='published' for passed rows, then trigger revalidate/IndexNow.

    Returns (published_ids, errors).
    """
    try:
        result = (
            db.client.table("trending_topics")
            .select("id, slug, title, summary, article, published_at, created_at, schema_blocks")
            .eq("fact_check", "no")
            .order("created_at", desc=False)
            .limit(FACT_CHECK_BATCH_LIMIT)
            .execute()
        )
    except Exception as exc:
        log.error("[fact_check] query failed: %s", exc)
        return [], [str(exc)]

    rows = result.data or []
    if not rows:
        log.debug("[fact_check] no rows with fact_check=no")
        return [], []

    now_iso = datetime.now(timezone.utc).isoformat()
    published_ids: List[str] = []
    errors: List[str] = []

    for row in rows:
        topic_id = row.get("id")
        slug = (row.get("slug") or "").strip()
        title = (row.get("title") or "?")[:40]
        if not topic_id or not slug:
            errors.append(f"fact_check: row missing id or slug")
            continue

        passed, notes = verify_topic(row)
        if notes:
            log.info("[fact_check] %s  notes=%s", title, notes)

        if not passed:
            errors.append(f"fact_check: failed for {slug} ({title})")
            continue

        try:
            db.client.table("trending_topics").update({
                "fact_check": "yes",
                "status": "published",
                "published_at": now_iso,
                "updated_at": now_iso,
            }).eq("id", topic_id).execute()
            log.info("[fact_check] published  id=%s  slug=%s  %s", topic_id, slug, title)
            published_ids.append(str(topic_id))
            _fire_external(slug)
        except Exception as exc:
            errors.append(f"fact_check: update failed for {topic_id}: {exc}")

    return published_ids, errors
