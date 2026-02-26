"""
scripts/rehash_published.py — Rewrite and humanise all published articles.

One-time batch usage:
    python scripts/rehash_published.py [--limit N] [--dry-run] [--older-than-days D]

Scheduler import:
    from scripts.rehash_published import run_rehash_batch
    run_rehash_batch(older_than_days=7, limit=50)

Each article is sent to Claude with instructions to produce 100% original,
humanised content while preserving all facts and direct quotes verbatim.
A JSON report is written to rehash_report_{timestamp}.json on completion.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

# Allow running from repo root or from apps/agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

# ── Author persona assignment (mirrors content_generation_node logic) ─────────

_PERSONAS_PATH = Path(__file__).parent.parent / "data" / "author_personas.json"
try:
    _PERSONAS: list[dict] = json.loads(_PERSONAS_PATH.read_text())
except Exception:
    _PERSONAS = [{"name": "theNewslane Editorial", "honorific": "Staff Writer"}]


def _assign_author_persona(topic_id: str) -> dict:
    idx = int(hashlib.md5(topic_id.encode()).hexdigest(), 16) % len(_PERSONAS)
    return _PERSONAS[idx]


# ── Claude rehash prompt ──────────────────────────────────────────────────────

_REHASH_SYSTEM = """\
You are an expert editorial rewriter working for theNewslane, a global news publication.
Your task is to produce a fully original, humanised rewrite of an existing published article.
"""

_REHASH_USER_TMPL = """\
Rewrite the following published article so it is 100% original and reads naturally — like a
skilled human journalist wrote it from scratch after researching the same story.

EXISTING CONTENT:
Title: {title}
Summary: {summary}
Article body:
{article}

REWRITING RULES (mandatory):
1. Produce a completely rewritten version of every field below.
2. Keep all factual claims, statistics, and data points accurate.
3. Preserve any direct quotes from real named individuals verbatim, enclosed in quotation marks,
   with the speaker's full name and title correctly attributed.
4. Never copy sentence structures, word sequences of 5+ words, or distinctive phrasing from the input.
5. Write in a natural, engaging journalistic style — varied sentence lengths, active voice where possible.
6. Always include the correct honorific/title on first mention of any real person
   (e.g. Dr. Jane Smith, Senator Mike Lee, CEO Tim Cook). Never strip honorifics.
7. The rewritten title must convey the same story without sharing any phrasing with the original title.
8. Keep word count and structure roughly comparable to the original.

Return ONLY a valid JSON object with exactly these fields (no markdown, no extra text):
{{
  "title":              "rewritten headline under 70 chars",
  "summary":            "rewritten 30-word summary",
  "article":            "rewritten full article body",
  "facebook_post":      "rewritten 30-word Facebook post ending with ARTICLE_LINK_PLACEHOLDER",
  "instagram_caption":  "rewritten caption under 200 chars followed by 1 relevant hashtag",
  "twitter_thread":     ["tweet1 under 280 chars", "tweet2 under 280 chars", "tweet3 under 280 chars"],
  "youtube_script":     "rewritten spoken narration of approximately 80 words"
}}"""


async def _rehash_topic(client, topic: dict, dry_run: bool = False) -> dict | None:
    """Send one topic to Claude for rehash. Returns updated fields dict or None on failure."""
    topic_id  = topic.get("id", "")
    title     = topic.get("title") or ""
    summary   = topic.get("summary") or ""
    article   = topic.get("article") or ""

    if not article.strip():
        log.warning("rehash: skipping %s — empty article body", topic_id)
        return None

    prompt = _REHASH_USER_TMPL.format(
        title=title,
        summary=summary,
        article=article[:6000],  # cap to avoid exceeding context
    )

    raw = ""
    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            system=_REHASH_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            temperature=0.4,
        )
        if not response.content:
            log.error(
                "rehash: empty content array for %s (stop_reason=%s)",
                topic_id, response.stop_reason,
            )
            return None
        raw = response.content[0].text.strip()
        if not raw:
            log.error(
                "rehash: empty text for %s (stop_reason=%s)",
                topic_id, response.stop_reason,
            )
            return None
        # Strip markdown code fences that the model may add despite instructions
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw.rstrip())
            raw = raw.strip()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("rehash: JSON parse error for %s: %s | raw[:300]=%r", topic_id, e, raw[:300])
        return None
    except Exception as e:
        log.error("rehash: Claude API error for %s: %s", topic_id, e)
        return None

    persona = _assign_author_persona(topic_id)
    return {
        "title":            data.get("title") or title,
        "summary":          data.get("summary") or summary,
        "article":          data.get("article") or article,
        "social_copy": {
            "facebook":  data.get("facebook_post"),
            "instagram": data.get("instagram_caption"),
            "twitter":   data.get("twitter_thread"),
            "youtube":   data.get("youtube_script"),
        },
        "author_name":      persona["name"],
        "author_honorific": persona["honorific"],
        "updated_at":       datetime.now(timezone.utc).isoformat(),
    }


def _fire_revalidation(slug: str) -> None:
    """Trigger Next.js ISR revalidation for the updated slug (best-effort)."""
    if not settings.revalidate_secret or not settings.revalidate_endpoint:
        return
    try:
        httpx.post(
            settings.revalidate_endpoint,
            json={"secret": settings.revalidate_secret, "slug": slug},
            timeout=10,
        )
    except Exception as exc:
        log.warning("rehash: revalidation failed for slug=%s: %s", slug, exc)


async def _run_batch_async(
    *,
    older_than_days: int | None = None,
    limit: int | None = None,
    batch_size: int = 10,
    dry_run: bool = False,
) -> dict:
    """Core async implementation. Returns a summary dict."""
    import anthropic as _anthropic
    from supabase import create_client

    db = create_client(settings.supabase_url, settings.supabase_service_key)
    client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Build query
    query = (
        db.table("trending_topics")
        .select("id, title, slug, summary, article, social_copy, author_name, published_at")
        .eq("status", "published")
    )
    if older_than_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        query = query.lte("published_at", cutoff)

    all_rows: list[dict] = []
    offset = 0
    while True:
        page = query.range(offset, offset + batch_size - 1).execute().data or []
        if not page:
            break
        all_rows.extend(page)
        offset += batch_size
        if limit and len(all_rows) >= limit:
            all_rows = all_rows[:limit]
            break

    total = len(all_rows)
    print(f"[rehash] {total} topics to process (dry_run={dry_run})", flush=True)

    sem = asyncio.Semaphore(3)
    updated = 0
    failed  = 0
    report_actions: list[dict] = []

    async def process(topic: dict) -> None:
        nonlocal updated, failed
        async with sem:
            tid    = topic.get("id", "?")
            slug   = topic.get("slug", "")
            title  = topic.get("title", "")[:60]
            result = await _rehash_topic(client, topic, dry_run=dry_run)
            if result is None:
                failed += 1
                report_actions.append({"id": tid, "status": "failed", "title": title})
                return
            if not dry_run:
                try:
                    db.table("trending_topics").update(result).eq("id", tid).execute()
                    _fire_revalidation(slug)
                except Exception as e:
                    log.error("rehash: DB update failed for %s: %s", tid, e)
                    failed += 1
                    report_actions.append({"id": tid, "status": "db_error", "title": title, "error": str(e)})
                    return
            updated += 1
            print(f"  [rehash] {'(dry) ' if dry_run else ''}updated: {title}", flush=True)
            report_actions.append({"id": tid, "status": "dry_run" if dry_run else "updated", "title": title})

    await asyncio.gather(*[process(row) for row in all_rows])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = Path(f"rehash_report_{ts}.json")
    report = {
        "total":     total,
        "updated":   updated,
        "failed":    failed,
        "dry_run":   dry_run,
        "timestamp": ts,
        "actions":   report_actions,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"[rehash] Done. {updated}/{total} updated. Report: {report_path}", flush=True)
    return report


def run_rehash_batch(*, older_than_days: int | None = None, limit: int | None = None) -> dict:
    """
    Importable entry point for the Inngest scheduler.
    Synchronously runs the rehash batch and returns the summary dict.
    """
    return asyncio.run(_run_batch_async(older_than_days=older_than_days, limit=limit))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rehash and humanise published articles.")
    parser.add_argument("--limit",           type=int,   default=None,  help="Max topics to process")
    parser.add_argument("--batch-size",      type=int,   default=10,    help="DB page size")
    parser.add_argument("--older-than-days", type=int,   default=None,  help="Only process articles older than N days")
    parser.add_argument("--dry-run",         action="store_true",       help="Preview without DB writes")
    args = parser.parse_args()

    t0 = time.time()
    result = asyncio.run(_run_batch_async(
        older_than_days=args.older_than_days,
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    ))
    print(f"[rehash] Elapsed: {round(time.time() - t0, 1)}s", flush=True)
