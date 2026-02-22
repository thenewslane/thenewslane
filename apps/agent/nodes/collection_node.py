"""
nodes/collection_node.py — Free multi-platform signal collection.

Collects trending topics from 5 free sources:
1. Google Trends RSS feeds (daily + realtime)
2. NewsAPI (enhanced with multiple categories)
3. RSS feeds (BBC, Reuters, CNN, Sky News)
4. Pytrends (trending searches)
5. Hacker News API (top stories)

Topics are deduplicated across platforms with rapidfuzz fuzzy matching,
persisted to raw_signals, and returned as RawTopic dataclass instances.
"""

from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import httpx
from pytrends.request import TrendReq
from rapidfuzz import fuzz, process

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MERGE_THRESHOLD = 14  # token_set_ratio score (0-100) for fuzzy matching (reduced by 80%)

# RSS feed URLs
RSS_FEEDS = {
    "bbc": "https://feeds.bbci.co.uk/news/rss.xml",
    "reuters": "https://feeds.reuters.com/reuters/topNews", 
    "cnn": "http://rss.cnn.com/rss/edition.rss",
    "sky_news": "https://feeds.skynews.com/feeds/rss/home.xml"
}

# Google Trends RSS feeds (Note: These may not be publicly available)
GOOGLE_TRENDS_RSS = {
    "daily": "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
    "realtime": "https://trends.google.com/trends/trendingsearches/realtime/rss?geo=US&category=all"
}

# NewsAPI categories to fetch in parallel
NEWSAPI_CATEGORIES = ["general", "technology", "entertainment", "sports", "science", "health"]


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


def _normalize_platform(platform: str) -> str:
    """
    Normalize platform names to match Supabase check constraint values.
    
    Accepted values: twitter, google_trends, reddit, newsapi, rss
    """
    platform_mapping = {
        # Google Trends sources
        "google_trends": "google_trends",
        
        # News sources → newsapi
        "google_news": "newsapi", 
        "newsapi": "newsapi",
        "hacker_news": "newsapi",  # Tech news → newsapi
        
        # RSS feeds → rss
        "rss_feeds": "rss",
        "rss": "rss",
        
        # Social media (for future use)
        "twitter": "twitter",
        "reddit": "reddit",
    }
    
    normalized = platform_mapping.get(platform, platform)
    if normalized not in ["twitter", "google_trends", "reddit", "newsapi", "rss"]:
        log.warning(f"Unknown platform '{platform}' mapped to 'newsapi' as fallback")
        return "newsapi"
    
    return normalized


# ---------------------------------------------------------------------------
# Source 1: Google Trends RSS
# ---------------------------------------------------------------------------


async def _fetch_google_trends_rss() -> list[dict[str, Any]]:
    """Fetch trending topics from Google Trends RSS feeds."""
    rows: list[dict[str, Any]] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for feed_name, url in GOOGLE_TRENDS_RSS.items():
            try:
                log.debug(f"Fetching Google Trends RSS: {feed_name}")
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                
                # Parse XML manually to extract trending topics
                root = ET.fromstring(resp.content)
                
                for item in root.findall(".//item"):
                    title_elem = item.find("title")
                    if title_elem is None or not title_elem.text:
                        continue
                    
                    raw_title = title_elem.text.strip()
                    keyword = _normalize(raw_title)
                    if not keyword:
                        continue
                    
                    # Try to extract traffic info from description
                    desc_elem = item.find("description")
                    traffic_info = 0
                    if desc_elem and desc_elem.text:
                        # Look for numbers in description that might indicate traffic
                        import re
                        numbers = re.findall(r'(\d+(?:,\d+)*)', desc_elem.text)
                        if numbers:
                            try:
                                traffic_info = int(numbers[0].replace(',', ''))
                            except ValueError:
                                pass
                    
                    rows.append({
                        "keyword": keyword,
                        "traffic": traffic_info,
                        "platform_row": {
                            "platform": _normalize_platform("google_trends"),
                            "topic_keyword": keyword,
                            "source_id": f"trends_rss_{feed_name}",
                            "title": raw_title,
                            "raw_data": {
                                "feed": feed_name,
                                "title": raw_title,
                                "traffic_estimate": traffic_info
                            },
                            "engagement_data": {
                                "traffic_estimate": traffic_info,
                                "feed_type": feed_name
                            }
                        }
                    })
                    
            except Exception as exc:
                log.error(f"Failed to fetch Google Trends RSS {feed_name}: {exc}")
    
    log.info(f"Google Trends RSS: collected {len(rows)} topics")
    return rows


# ---------------------------------------------------------------------------
# Source 2: Enhanced NewsAPI
# ---------------------------------------------------------------------------


async def _fetch_newsapi_headlines() -> list[dict[str, Any]]:
    """Fetch top headlines from NewsAPI across multiple categories."""
    if not settings.newsapi_key:
        log.warning("NewsAPI key missing - skipping NewsAPI collection")
        return []
    
    rows: list[dict[str, Any]] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        
        for category in NEWSAPI_CATEGORIES:
            task = _fetch_newsapi_category(client, category)
            tasks.append(task)
        
        # Fetch all categories in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            category = NEWSAPI_CATEGORIES[i]
            if isinstance(result, Exception):
                log.error(f"NewsAPI category {category} failed: {result}")
                continue
                
            rows.extend(result)
    
    log.info(f"NewsAPI: collected {len(rows)} topics across {len(NEWSAPI_CATEGORIES)} categories")
    return rows


async def _fetch_newsapi_category(client: httpx.AsyncClient, category: str) -> list[dict[str, Any]]:
    """Fetch headlines for a specific NewsAPI category."""
    try:
        resp = await client.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                "category": category,
                "country": "us",
                "pageSize": 20,
                "language": "en",
                "apiKey": settings.newsapi_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        
        rows = []
        for rank, article in enumerate(articles, start=1):
            raw_title = article.get("title", "").split(" - ")[0].strip()  # Remove source suffix
            keyword = _normalize(raw_title)
            if not keyword or len(keyword) < 5:
                continue
            
            rows.append({
                "keyword": keyword,
                "rank": rank,
                "platform_row": {
                    "platform": _normalize_platform("google_news"),
                    "topic_keyword": keyword,
                    "title": raw_title,
                    "url": article.get("url", ""),
                    "source_id": article.get("url", ""),
                    "raw_data": article,
                    "engagement_data": {
                        "rank": rank,
                        "category": category,
                        "source": article.get("source", {}).get("name", ""),
                        "published_at": article.get("publishedAt", "")
                    }
                }
            })
            
        return rows
        
    except Exception as exc:
        log.error(f"NewsAPI category {category} failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Source 3: RSS feeds
# ---------------------------------------------------------------------------


async def _fetch_rss_feeds() -> list[dict[str, Any]]:
    """Fetch articles from major RSS feeds."""
    rows: list[dict[str, Any]] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        
        for feed_name, feed_url in RSS_FEEDS.items():
            task = _fetch_single_rss_feed(client, feed_name, feed_url)
            tasks.append(task)
        
        # Fetch all feeds in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            feed_name = list(RSS_FEEDS.keys())[i]
            if isinstance(result, Exception):
                log.error(f"RSS feed {feed_name} failed: {result}")
                continue
                
            rows.extend(result)
    
    log.info(f"RSS feeds: collected {len(rows)} topics from {len(RSS_FEEDS)} feeds")
    return rows


async def _fetch_single_rss_feed(client: httpx.AsyncClient, feed_name: str, feed_url: str) -> list[dict[str, Any]]:
    """Fetch articles from a single RSS feed."""
    try:
        resp = await client.get(feed_url, follow_redirects=True)
        resp.raise_for_status()
        
        # Parse RSS feed
        feed = feedparser.parse(resp.content)
        
        rows = []
        for i, entry in enumerate(feed.entries[:15]):  # Limit to 15 per feed
            title = getattr(entry, 'title', '').strip()
            if not title:
                continue
                
            keyword = _normalize(title)
            if not keyword:
                continue
            
            published = getattr(entry, 'published', '')
            link = getattr(entry, 'link', '')
            
            rows.append({
                "keyword": keyword,
                "rank": i + 1,
                "platform_row": {
                    "platform": _normalize_platform("rss_feeds"),
                    "topic_keyword": keyword,
                    "title": title,
                    "url": link,
                    "source_id": link,
                    "raw_data": {
                        "feed_name": feed_name,
                        "title": title,
                        "link": link,
                        "published": published
                    },
                    "engagement_data": {
                        "feed_name": feed_name,
                        "rank": i + 1,
                        "published": published
                    }
                }
            })
            
        return rows
        
    except Exception as exc:
        log.error(f"RSS feed {feed_name} failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# Source 4: Pytrends
# ---------------------------------------------------------------------------


async def _fetch_pytrends() -> list[dict[str, Any]]:
    """Fetch trending searches using pytrends."""
    rows: list[dict[str, Any]] = []
    
    try:
        # Pytrends is synchronous, so run in thread pool
        def _pytrends_sync():
            pytrends = TrendReq(hl='en-US', tz=360)
            
            # Get trending searches
            trending_searches = pytrends.trending_searches(pn='united_states')
            
            topics = []
            if trending_searches is not None and not trending_searches.empty:
                # Get top 20 trending topics
                for i, topic in enumerate(trending_searches.head(20)[0].tolist()):
                    topics.append({
                        "topic": str(topic),
                        "rank": i + 1
                    })
            
            return topics
        
        # Run Pytrends API call in thread pool
        loop = asyncio.get_event_loop()
        topics = await loop.run_in_executor(None, _pytrends_sync)
        
        for topic_data in topics:
            topic = topic_data["topic"].strip()
            if not topic:
                continue
                
            keyword = _normalize(topic)
            if not keyword:
                continue
            
            rows.append({
                "keyword": keyword,
                "rank": topic_data["rank"],
                "platform_row": {
                    "platform": _normalize_platform("google_trends"),
                    "topic_keyword": keyword,
                    "title": topic,
                    "source_id": f"pytrends_{topic_data['rank']}",
                    "raw_data": {
                        "original_topic": topic,
                        "rank": topic_data["rank"],
                        "source": "pytrends"
                    },
                    "engagement_data": {
                        "rank": topic_data["rank"],
                        "source": "pytrends"
                    }
                }
            })
            
    except Exception as exc:
        log.error(f"Pytrends collection failed: {exc}")
    
    log.info(f"Pytrends: collected {len(rows)} topics")
    return rows


# ---------------------------------------------------------------------------
# Source 5: Hacker News
# ---------------------------------------------------------------------------


async def _fetch_hacker_news() -> list[dict[str, Any]]:
    """Fetch top stories from Hacker News API."""
    rows: list[dict[str, Any]] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Get top story IDs
            resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            resp.raise_for_status()
            story_ids = resp.json()[:30]  # Get top 30 stories
            
            # Fetch story details in parallel (limit concurrency)
            semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests
            
            async def fetch_story(story_id: int, rank: int):
                async with semaphore:
                    try:
                        story_resp = await client.get(
                            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        )
                        story_resp.raise_for_status()
                        return rank, story_resp.json()
                    except Exception as exc:
                        log.warning(f"Failed to fetch HN story {story_id}: {exc}")
                        return rank, None
            
            tasks = [fetch_story(story_id, rank) for rank, story_id in enumerate(story_ids, 1)]
            story_results = await asyncio.gather(*tasks)
            
            for rank, story in story_results:
                if not story or story.get("type") != "story":
                    continue
                    
                title = story.get("title", "").strip()
                if not title:
                    continue
                    
                keyword = _normalize(title)
                if not keyword:
                    continue
                
                rows.append({
                    "keyword": keyword,
                    "score": story.get("score", 0),
                    "platform_row": {
                        "platform": _normalize_platform("hacker_news"),
                        "topic_keyword": keyword,
                        "title": title,
                        "url": story.get("url", ""),
                        "source_id": str(story.get("id", "")),
                        "raw_data": story,
                        "engagement_data": {
                            "score": story.get("score", 0),
                            "descendants": story.get("descendants", 0),  # comment count
                            "rank": rank,
                            "time": story.get("time", 0)
                        }
                    }
                })
                
        except Exception as exc:
            log.error(f"Hacker News collection failed: {exc}")
    
    log.info(f"Hacker News: collected {len(rows)} topics")
    return rows


# ---------------------------------------------------------------------------
# NewsAPI enrichment (for topics without news counts)
# ---------------------------------------------------------------------------


async def _fetch_newsapi_counts(keywords: list[str]) -> dict[str, int]:
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
                log.warning("NewsAPI enrichment failed for %r: %s", kw, exc)
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
    log.info("collection: starting free source collection  batch_id=%s  geo=%s", batch_id, geo)

    # Run all 5 free sources in parallel
    results = await asyncio.gather(
        _fetch_google_trends_rss(),
        _fetch_newsapi_headlines(),
        _fetch_rss_feeds(),
        _fetch_pytrends(),
        _fetch_hacker_news(),
        return_exceptions=True,
    )

    # Organize results by source
    source_data = {
        "google_trends_rss": results[0] if isinstance(results[0], list) else [],
        "newsapi": results[1] if isinstance(results[1], list) else [],
        "rss_feeds": results[2] if isinstance(results[2], list) else [],
        "pytrends": results[3] if isinstance(results[3], list) else [],
        "hacker_news": results[4] if isinstance(results[4], list) else [],
    }

    # Log any failures
    source_names = ["google_trends_rss", "newsapi", "rss_feeds", "pytrends", "hacker_news"]
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            log.error("collection: %s source failed: %s", source_names[i], result)

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

    # Process Google Trends RSS
    for item in source_data["google_trends_rss"]:
        topic = _get_or_create(item["keyword"])
        normalized_platform = _normalize_platform("google_trends")
        if normalized_platform not in topic.platforms:
            topic.platforms.append(normalized_platform)
        if topic.trends_interest is None:
            topic.trends_interest = item.get("traffic", 0)
        pr = dict(item["platform_row"])
        pr["platform"] = normalized_platform  # Ensure normalized platform is used
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)


    # Process NewsAPI
    for item in source_data["newsapi"]:
        topic = _get_or_create(item["keyword"])
        normalized_platform = _normalize_platform("google_news")
        if normalized_platform not in topic.platforms:
            topic.platforms.append(normalized_platform)
        topic.news_count = max(topic.news_count, 1)  # Indicate news presence
        pr = dict(item["platform_row"])
        pr["platform"] = normalized_platform  # Ensure normalized platform is used
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)

    # Process RSS Feeds
    for item in source_data["rss_feeds"]:
        topic = _get_or_create(item["keyword"])
        normalized_platform = _normalize_platform("rss_feeds")
        if normalized_platform not in topic.platforms:
            topic.platforms.append(normalized_platform)
        topic.news_count = max(topic.news_count, 1)  # Indicate news presence
        pr = dict(item["platform_row"])
        pr["platform"] = normalized_platform  # Ensure normalized platform is used
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)

    # Process Pytrends
    for item in source_data["pytrends"]:
        topic = _get_or_create(item["keyword"])
        normalized_platform = _normalize_platform("google_trends")
        if normalized_platform not in topic.platforms:
            topic.platforms.append(normalized_platform)
        if topic.trends_interest is None:
            topic.trends_interest = 100 - (item.get("rank", 20) * 5)  # Convert rank to interest
        pr = dict(item["platform_row"])
        pr["platform"] = normalized_platform  # Ensure normalized platform is used
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)

    # Process Hacker News
    for item in source_data["hacker_news"]:
        topic = _get_or_create(item["keyword"])
        normalized_platform = _normalize_platform("hacker_news")
        if normalized_platform not in topic.platforms:
            topic.platforms.append(normalized_platform)
        # Use HN score as a tech interest metric
        if topic.trends_interest is None:
            topic.trends_interest = min(100, item.get("score", 0) // 5)  # Scale down HN scores
        pr = dict(item["platform_row"])
        pr["platform"] = normalized_platform  # Ensure normalized platform is used
        pr["batch_id"] = batch_id
        pr["topic_keyword"] = topic.keyword
        topic.raw_rows.append(pr)

    topics = list(topic_map.values())
    log.info("collection: %d unique topics after fuzzy merge", len(topics))

    # ── NewsAPI enrichment for topics without news counts ─────────────────
    keywords_to_enrich = [t.keyword for t in topics if t.news_count == 0]
    if keywords_to_enrich:
        news_counts = await _fetch_newsapi_counts(keywords_to_enrich)
        
        for topic in topics:
            if topic.news_count == 0:
                enriched_count = news_counts.get(topic.keyword, 0)
                if enriched_count > 0:
                    topic.news_count = enriched_count
                    topic.raw_rows.append(
                        {
                            "batch_id": batch_id,
                            "platform": _normalize_platform("google_news"),
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