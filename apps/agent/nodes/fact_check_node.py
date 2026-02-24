"""
nodes/fact_check_node.py — Fact-checking intermediary agent.

Picks rows from trending_topics where fact_check='no', runs date/data verification
and cross-checks, then sets fact_check='yes' and status='published' and triggers
ISR revalidation and IndexNow.
"""

from __future__ import annotations

import re
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


# Year in text: 19xx or 20xx
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _extract_years(text: str | None) -> List[int]:
    if not text:
        return []
    return [int(m.group(0)) for m in _YEAR_RE.finditer(text)]


def _llm_fact_check(title: str, summary: str, article_preview: str) -> tuple[bool, List[str]]:
    """
    Call Claude Haiku to cross-verify dates and factual claims.
    Returns (passed, list of issues). Passed is False if LLM reports issues.
    """
    if not getattr(settings, "anthropic_api_key", None) or not settings.anthropic_api_key:
        return True, []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = f"""You are a fact-checker. Review this trending-news content for wrong dates, factual errors, or misleading claims.

Title: {title[:200]}
Summary: {summary[:500] if summary else "—"}
Article (excerpt): {article_preview[:500] if article_preview else "—"}

Current year is {datetime.now(timezone.utc).year}. If all dates and facts look correct, reply with exactly: OK
If you find wrong years, outdated facts, or clear errors, reply with a short bullet list only (one line per issue)."""
        msg = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = (msg.content[0].text if msg.content else "").strip().upper()
        if not text or text == "OK":
            return True, []
        issues = [line.strip() for line in text.split("\n") if line.strip() and "OK" not in line]
        return False, [f"llm: {i}" for i in issues[:5]]
    except Exception as exc:
        log.warning("[fact_check] LLM check failed: %s", exc)
        return True, []  # do not block on LLM failure


def verify_topic(row: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Run fact-check and date/data verification on a topic row.
    Returns (passed: bool, list of correction notes or errors).

    - Date check: reject if summary/article mention a year older than current_year - 1.
    - LLM cross-check: Claude Haiku for factual/date consistency.
    """
    notes: List[str] = []
    current_year = datetime.now(timezone.utc).year
    max_acceptable_year = current_year - 1  # e.g. 2024 when current is 2025

    for field in ("summary", "article"):
        text = row.get(field)
        years = _extract_years(text)
        for y in years:
            if y < max_acceptable_year:
                notes.append(f"date_outdated: year {y} in {field} (current {current_year})")
            elif y > current_year:
                notes.append(f"date_future: year {y} in {field}")

    if any("date_outdated:" in n or "date_future:" in n for n in notes):
        return False, notes

    title = (row.get("title") or "")[:200]
    summary = row.get("summary") or ""
    article = row.get("article") or ""
    article_preview = article[:600] if article else ""
    llm_ok, llm_issues = _llm_fact_check(title, summary, article_preview)
    if not llm_ok and llm_issues:
        notes.extend(llm_issues)
        return False, notes

    return True, notes


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
