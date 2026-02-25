"""
backfill_thumbnails.py — Add thumbnail_url to all published articles missing one.

Priority:
  1. YouTube thumbnail — articles that have schema_blocks['video_id']
     (no API key needed, URL is always valid)
  2. Wikipedia REST API — search by title, get page thumbnail (free, no key)
  3. Mark as skipped (DALL-E billing limit exceeded; YouTube API quota exceeded)

Run:
    cd apps/agent && .venv/bin/python3 backfill_thumbnails.py
"""

from __future__ import annotations

import asyncio
import sys

import httpx

sys.path.insert(0, ".")
from utils.supabase_client import db
from utils.logger import get_logger

log = get_logger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; NewsBot/1.0)"
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


def _sb(topic: dict, key: str) -> str | None:
    sb = topic.get("schema_blocks") or {}
    if isinstance(sb, list):
        sb = sb[0] if sb else {}
    v = sb.get(key)
    return str(v) if v else None


def youtube_thumbnail(video_id: str) -> str:
    """YouTube hqdefault thumbnail — always valid for real video IDs."""
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


async def wikipedia_thumbnail(title: str, client: httpx.AsyncClient) -> str | None:
    """Search Wikipedia for the topic and return its page thumbnail URL."""
    try:
        # Step 1: search Wikipedia for the topic
        r = await client.get(
            WIKI_SEARCH,
            params={
                "action": "query",
                "list": "search",
                "srsearch": title[:100],
                "srlimit": 3,
                "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if r.status_code != 200:
            return None

        results = r.json().get("query", {}).get("search", [])
        if not results:
            return None

        # Step 2: get the page summary+thumbnail
        page_title = results[0]["title"]
        r2 = await client.get(
            WIKI_SUMMARY.format(title=page_title.replace(" ", "_")),
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        if r2.status_code != 200:
            return None

        data = r2.json()
        thumb = (data.get("thumbnail") or {}).get("source")
        if not thumb:
            return None

        # Upgrade to a larger size for better quality
        for small, large in [("/200px-", "/1200px-"), ("/320px-", "/1200px-"),
                               ("/400px-", "/1200px-"), ("/640px-", "/1200px-")]:
            if small in thumb:
                thumb = thumb.replace(small, large)
                break

        return thumb

    except Exception as exc:
        log.debug("Wikipedia search failed for '%s': %s", title, exc)
        return None


async def backfill() -> None:
    print("\n══════ Thumbnail backfill ══════")

    result = (
        db.client.table("trending_topics")
        .select("id, title, video_type, schema_blocks")
        .eq("status", "published")
        .is_("thumbnail_url", "null")
        .order("published_at", desc=True)
        .execute()
    )
    topics = result.data or []
    print(f"Articles needing thumbnails: {len(topics)}\n")
    if not topics:
        print("Nothing to do — all articles already have thumbnails.")
        return

    ok = wiki_ok = yt_ok = skipped = 0
    BATCH = 5  # parallel Wikipedia requests

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:

        async def process_one(topic: dict) -> tuple[str, str | None, str]:
            tid   = topic["id"]
            title = topic.get("title", "")
            vtype = topic.get("video_type", "")
            vid   = _sb(topic, "video_id")

            # ── 1. YouTube (no quota, no API call) ────────────────────────
            if vid:
                url = youtube_thumbnail(vid)
                return tid, url, "yt"

            # ── 2. Wikipedia ───────────────────────────────────────────────
            url = await wikipedia_thumbnail(title, client)
            if url:
                return tid, url, "wiki"

            return tid, None, "skip"

        # Process in batches to avoid hammering Wikipedia
        all_tasks = [process_one(t) for t in topics]
        results: list[tuple[str, str | None, str]] = []
        for i in range(0, len(all_tasks), BATCH):
            batch_results = await asyncio.gather(*all_tasks[i:i+BATCH])
            results.extend(batch_results)
            await asyncio.sleep(0.3)

        # Update DB for successful results
        for i, (tid, url, source) in enumerate(results):
            title = topics[i].get("title", "")[:55]
            if not url:
                print(f"  ✗ [{i+1}] {title}")
                skipped += 1
                continue

            print(f"  ✓ [{i+1}] {title}")
            print(f"       {source}: {url[:80]}")
            try:
                db.client.table("trending_topics") \
                    .update({"thumbnail_url": url}) \
                    .eq("id", tid) \
                    .execute()
                ok += 1
                if source == "yt":
                    yt_ok += 1
                else:
                    wiki_ok += 1
            except Exception as exc:
                print(f"       ✗ DB update failed: {exc}")
                skipped += 1

    print(f"\n══════ Done: {ok} updated "
          f"(YouTube: {yt_ok}, Wikipedia: {wiki_ok}), "
          f"{skipped} skipped ══════\n")


if __name__ == "__main__":
    asyncio.run(backfill())
