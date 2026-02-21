"""
nodes/collection_node.py — Async multi-platform signal collection.

Runs three Apify actors (Twitter, Google Trends, Reddit) concurrently,
then fetches NewsAPI article counts for the top merged topics.
Topics are deduplicated across platforms with rapidfuzz fuzzy matching,
persisted to raw_signals, and returned as RawTopic dataclass instances.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from apify_client import ApifyClientAsync
from rapidfuzz import fuzz, process

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Merge threshold
# ---------------------------------------------------------------------------

_MERGE_THRESHOLD = 72  # token_set_ratio score (0-100)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class RawTopic:
    """A trending topic merged across one or more collection platforms."""

    keyword: str
    platforms: list[str] = field(default_factory=list)
    twitter_rank: int | None = None
    reddit_score: int | None = None
    trends_interest: int | None = None
    news_count: int = 0
    # raw DB rows ready for insert_signals(); populated by the collectors
    raw_rows: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Lowercase, strip whitespace and leading '#' from a topic string."""
    return s.lower().strip().lstrip("#").strip()


def _find_canonical(keyword: str, canonical: list[str]) -> str | None:
    """
    Return the existing canonical form if a close match is found in canonical,
    or None if keyword should be added as a new canonical entry.
    """
    if not canonical:
        return None
    match = process.extractOne(keyword, canonical, scorer=fuzz.token_set_ratio)
    if match and match[1] >= _MERGE_THRESHOLD:
        return match[0]
    return None


# ---------------------------------------------------------------------------
# Apify actor runner
# ---------------------------------------------------------------------------


async def _run_actor(
    actor_id: str,
    run_input: dict[str, Any],
    *,
    timeout_secs: int = 180,
    max_items: int = 100,
) -> list[dict[str, Any]]:
    """Call an Apify actor and return its full dataset as a list of dicts."""
    client = ApifyClientAsync(settings.apify_api_key)
    run = await client.actor(actor_id).call(
        run_input=run_input,
        timeout_secs=timeout_secs,
    )
    if run is None:
        return []
    dataset_id: str = run["defaultDatasetId"]
    result = await client.dataset(dataset_id).list_items(limit=max_items)
    return result.items or []


# ---------------------------------------------------------------------------
# Platform collectors — each returns a list of intermediate dicts
# ---------------------------------------------------------------------------


async def _fetch_twitter() -> list[dict[str, Any]]:
    """Fetch US trending topics via apidojo/twitter-trending-hashtags-scraper."""
    items = await _run_actor(
        "apidojo/twitter-trending-hashtags-scraper",
        {"country": "US", "topN": 50},
        timeout_secs=120,
        max_items=50,
    )
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(items, start=1):
        raw_keyword = item.get("name") or item.get("keyword") or ""
        keyword = _normalize(str(raw_keyword))
        if not keyword:
            continue
        rows.append(
            {
                "keyword": keyword,
                "rank": rank,
                "platform_row": {
                    "platform": "twitter",
                    "topic_keyword": keyword,
                    "source_id": str(item.get("id") or ""),
                    "raw_data": item,
                    "engagement_data": {
                        "tweet_count": item.get("tweetCount") or item.get("tweet_count"),
                        "rank": rank,
                    },
                },
            }
        )
    return rows


async def _fetch_google_trends(geo: str = "US") -> list[dict[str, Any]]:
    """Fetch rising search topics via epctex/google-trends-scraper."""
    items = await _run_actor(
        "epctex/google-trends-scraper",
        {
            "searchTerms": [],
            "geo": geo,
            "category": "all",
            "timeRange": "now 1-d",
            "outputMode": "trending",
        },
        timeout_secs=180,
        max_items=50,
    )
    rows: list[dict[str, Any]] = []
    for item in items:
        raw_keyword = item.get("title") or item.get("query") or ""
        keyword = _normalize(str(raw_keyword))
        if not keyword:
            continue
        interest = int(item.get("value") or item.get("interest") or 0)
        rows.append(
            {
                "keyword": keyword,
                "interest": interest,
                "platform_row": {
                    "platform": "google_trends",
                    "topic_keyword": keyword,
                    "raw_data": item,
                    "engagement_data": {
                        "interest": interest,
                        "formatted_value": item.get("formattedValue"),
                    },
                },
            }
        )
    return rows


async def _fetch_reddit() -> list[dict[str, Any]]:
    """Fetch hot posts from r/all via trudax/reddit-scraper."""
    items = await _run_actor(
        "trudax/reddit-scraper",
        {
            "startUrls": [{"url": "https://www.reddit.com/r/all/"}],
            "sort": "hot",
            "maxItems": 50,
            "skipComments": True,
        },
        timeout_secs=120,
        max_items=50,
    )
    rows: list[dict[str, Any]] = []
    for item in items:
        title = str(item.get("title") or "")
        if not title:
            continue
        keyword = _normalize(title)
        score = int(item.get("score") or item.get("ups") or 0)
        rows.append(
            {
                "keyword": keyword,
                "score": score,
                "platform_row": {
                    "platform": "reddit",
                    "topic_keyword": keyword,
                    "title": title,
                    "url": item.get("url") or item.get("link") or "",
                    "source_id": str(item.get("id") or ""),
                    "raw_data": item,
                    "engagement_data": {
                        "score": score,
                        "num_comments": item.get("numComments") or item.get("num_comments"),
                        "subreddit": item.get("subreddit"),
                    },
                },
            }
        )
    return rows


# ---------------------------------------------------------------------------
# NewsAPI enrichment
# ---------------------------------------------------------------------------


async def _fetch_newsapi(keywords: list[str]) -> dict[str, int]:
    """Return {keyword: total_article_count} from NewsAPI for the last 24 h."""
    if not settings.newsapi_key or not keywords:
        return {}

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    counts: dict[str, int] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for kw in keywords[: settings.newsapi_max_topics]:
            try:
                resp = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": kw,
                        "from": yesterday,
                        "pageSize": 1,
                        "language": "en",
                        "apiKey": settings.newsapi_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                counts[kw] = int(data.get("totalResults", 0))
            except Exception as exc:
                log.warning("NewsAPI failed for %r: %s", kw, exc)
                counts[kw] = 0

    return counts


# ---------------------------------------------------------------------------
# Core async pipeline
# ---------------------------------------------------------------------------


async def _collect_async(batch_id: str, geo: str = "US") -> list[RawTopic]:
    """
    Run all collectors concurrently, merge by topic, enrich with NewsAPI,
    and return the list of merged RawTopic objects.
    """
    log.info("collection: starting concurrent fetch  batch_id=%s  geo=%s", batch_id, geo)

    # Run three Apify actors in parallel; isolate per-actor failures
    twitter_result, trends_result, reddit_result = await asyncio.gather(
        _fetch_twitter(),
        _fetch_google_trends(geo),
        _fetch_reddit(),
        return_exceptions=True,
    )

    platform_data: dict[str, list[dict[str, Any]]] = {
        "twitter": twitter_result if isinstance(twitter_result, list) else [],
        "google_trends": trends_result if isinstance(trends_result, list) else [],
        "reddit": reddit_result if isinstance(reddit_result, list) else [],
    }

    for platform_name, result in [
        ("twitter", twitter_result),
        ("google_trends", trends_result),
        ("reddit", reddit_result),
    ]:
        if isinstance(result, Exception):
            log.error("collection: %s actor failed: %s", platform_name, result)

    # ── Fuzzy-merge topics across platforms ────────────────────────────────
    canonical: list[str] = []   # ordered list of canonical keyword strings
    topic_map: dict[str, RawTopic] = {}  # canonical keyword -> RawTopic

    def _get_or_create(keyword: str) -> RawTopic:
        canon = _find_canonical(keyword, canonical)
        if canon is None:
            canonical.append(keyword)
            topic_map[keyword] = RawTopic(keyword=keyword)
            return topic_map[keyword]
        return topic_map[canon]

    # Twitter
    for item in platform_data["twitter"]:
        topic = _get_or_create(item["keyword"])
        if "twitter" not in topic.platforms:
            topic.platforms.append("twitter")
        if topic.twitter_rank is None:
            topic.twitter_rank = item["rank"]
        pr = dict(item["platform_row"])
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword  # use canonical form
        topic.raw_rows.append(pr)

    # Google Trends
    for item in platform_data["google_trends"]:
        topic = _get_or_create(item["keyword"])
        if "google_trends" not in topic.platforms:
            topic.platforms.append("google_trends")
        if topic.trends_interest is None:
            topic.trends_interest = item["interest"]
        pr = dict(item["platform_row"])
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)

    # Reddit
    for item in platform_data["reddit"]:
        topic = _get_or_create(item["keyword"])
        if "reddit" not in topic.platforms:
            topic.platforms.append("reddit")
        if topic.reddit_score is None or item["score"] > topic.reddit_score:
            topic.reddit_score = item["score"]
        pr = dict(item["platform_row"])
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)

    topics = list(topic_map.values())
    log.info("collection: %d unique topics after fuzzy merge", len(topics))

    # ── NewsAPI enrichment ─────────────────────────────────────────────────
    keywords = [t.keyword for t in topics]
    news_counts = await _fetch_newsapi(keywords)

    for topic in topics:
        topic.news_count = news_counts.get(topic.keyword, 0)
        if topic.news_count > 0:
            topic.raw_rows.append(
                {
                    "batch_id": batch_id,
                    "platform": "google_news",
                    "topic_keyword": topic.keyword,
                    "raw_data": {"query": topic.keyword},
                    "engagement_data": {"article_count": topic.news_count},
                }
            )

    return topics


# ---------------------------------------------------------------------------
# Public sync entry point (LangGraph-compatible)
# ---------------------------------------------------------------------------


def collect_signals_node(batch_id: str, geo: str = "US") -> list[RawTopic]:
    """
    Synchronous entry point called by the LangGraph signal_collector node.

    Runs the async collector, bulk-inserts all raw signal rows into Supabase,
    and returns the list of merged RawTopic objects.
    """
    topics = asyncio.run(_collect_async(batch_id, geo))

    all_rows: list[dict[str, Any]] = []
    for topic in topics:
        all_rows.extend(topic.raw_rows)

    inserted = db.insert_signals(all_rows)
    log.info(
        "collection: inserted %d raw signal rows for %d topics",
        inserted,
        len(topics),
    )
    return topics
