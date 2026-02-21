"""
tests/test_collection_node.py — Unit tests for the collection node.

Mocks:
  - _run_actor          (Apify actors)
  - httpx.AsyncClient   (NewsAPI calls)
  - db.insert_signals   (Supabase bulk insert)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from nodes.collection_node import (
    RawTopic,
    _collect_async,
    _fetch_newsapi,
    _find_canonical,
    _normalize,
    collect_signals_node,
)

# ---------------------------------------------------------------------------
# Fixtures — fake actor payloads
# ---------------------------------------------------------------------------

TWITTER_ITEMS = [
    {"name": "#AI Trends", "tweetCount": 45000, "id": "tw1"},
    {"name": "#climate change", "tweetCount": 30000, "id": "tw2"},
    {"name": "#NBA Playoffs", "tweetCount": 20000, "id": "tw3"},
]

TRENDS_ITEMS = [
    {"title": "AI Trends", "value": 95, "formattedValue": "Breakout"},
    {"title": "climate change news", "value": 80, "formattedValue": "+500%"},
    {"title": "SpaceX launch", "value": 60, "formattedValue": "+200%"},
]

REDDIT_ITEMS = [
    {
        "title": "NBA Playoffs 2025 highlights",
        "score": 42000,
        "id": "r1",
        "url": "https://reddit.com/r/nba/1",
        "subreddit": "nba",
    },
    {
        "title": "Climate change accelerating faster than expected",
        "score": 35000,
        "id": "r2",
        "url": "https://reddit.com/r/science/2",
        "subreddit": "science",
    },
    {
        "title": "New SpaceX Starship test",
        "score": 28000,
        "id": "r3",
        "url": "https://reddit.com/r/space/3",
        "subreddit": "space",
    },
]

NEWSAPI_RESPONSE = {
    "status": "ok",
    "totalResults": 47,
    "articles": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_httpx_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


def test_normalize_strips_hash() -> None:
    assert _normalize("#AITrends") == "aitrends"


def test_normalize_lowercase_and_strip() -> None:
    assert _normalize("  Climate Change  ") == "climate change"


def test_normalize_empty_string() -> None:
    assert _normalize("") == ""


# ---------------------------------------------------------------------------
# _find_canonical
# ---------------------------------------------------------------------------


def test_find_canonical_exact_match() -> None:
    canon = ["climate change", "nba playoffs"]
    result = _find_canonical("climate change", canon)
    assert result == "climate change"


def test_find_canonical_fuzzy_match() -> None:
    canon = ["climate change"]
    # "climate change news" is close enough to "climate change"
    result = _find_canonical("climate change news", canon)
    assert result == "climate change"


def test_find_canonical_no_match() -> None:
    canon = ["climate change", "nba playoffs"]
    result = _find_canonical("spacex starship", canon)
    assert result is None


def test_find_canonical_empty_list() -> None:
    assert _find_canonical("anything", []) is None


# ---------------------------------------------------------------------------
# _collect_async — full integration mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_async_returns_raw_topics() -> None:
    """All three actors succeed; topics are merged and returned."""
    with patch(
        "nodes.collection_node._run_actor",
        new=AsyncMock(
            side_effect=[TWITTER_ITEMS, TRENDS_ITEMS, REDDIT_ITEMS]
        ),
    ), patch(
        "nodes.collection_node._fetch_newsapi",
        new=AsyncMock(return_value={}),
    ):
        topics = await _collect_async("batch_test_001")

    assert isinstance(topics, list)
    assert len(topics) > 0
    for topic in topics:
        assert isinstance(topic, RawTopic)
        assert topic.keyword
        assert len(topic.platforms) >= 1


@pytest.mark.asyncio
async def test_collect_async_cross_platform_merge() -> None:
    """'climate change' from Twitter, Trends, and Reddit should merge into one topic."""
    with patch(
        "nodes.collection_node._run_actor",
        new=AsyncMock(
            side_effect=[TWITTER_ITEMS, TRENDS_ITEMS, REDDIT_ITEMS]
        ),
    ), patch(
        "nodes.collection_node._fetch_newsapi",
        new=AsyncMock(return_value={}),
    ):
        topics = await _collect_async("batch_merge_test")

    keywords = [t.keyword for t in topics]
    # "climate change" should not appear more than once
    climate_topics = [t for t in topics if "climate" in t.keyword]
    assert len(climate_topics) == 1
    climate = climate_topics[0]
    # Should have been seen on twitter AND google_trends AND reddit
    assert "twitter" in climate.platforms
    assert "google_trends" in climate.platforms
    assert "reddit" in climate.platforms


@pytest.mark.asyncio
async def test_collect_async_twitter_actor_fails_gracefully() -> None:
    """If Twitter actor raises, Reddit and Trends results are still returned."""

    async def _side_effect(actor_id: str, *args: Any, **kwargs: Any) -> list:
        if "twitter" in actor_id:
            raise RuntimeError("Twitter actor timed out")
        if "google-trends" in actor_id:
            return TRENDS_ITEMS
        return REDDIT_ITEMS

    with patch(
        "nodes.collection_node._run_actor",
        new=AsyncMock(side_effect=_side_effect),
    ), patch(
        "nodes.collection_node._fetch_newsapi",
        new=AsyncMock(return_value={}),
    ):
        topics = await _collect_async("batch_failure_test")

    # Should still have topics from Trends and Reddit
    assert len(topics) > 0
    all_platforms: set[str] = set()
    for t in topics:
        all_platforms.update(t.platforms)
    assert "twitter" not in all_platforms
    assert "google_trends" in all_platforms or "reddit" in all_platforms


@pytest.mark.asyncio
async def test_collect_async_all_actors_fail_returns_empty() -> None:
    """If all three actors fail, an empty list is returned (no crash)."""
    with patch(
        "nodes.collection_node._run_actor",
        new=AsyncMock(side_effect=RuntimeError("network error")),
    ), patch(
        "nodes.collection_node._fetch_newsapi",
        new=AsyncMock(return_value={}),
    ):
        topics = await _collect_async("batch_all_fail")

    assert topics == []


@pytest.mark.asyncio
async def test_collect_async_raw_rows_have_required_fields() -> None:
    """Every raw_row must have batch_id, platform, and topic_keyword."""
    with patch(
        "nodes.collection_node._run_actor",
        new=AsyncMock(
            side_effect=[TWITTER_ITEMS, TRENDS_ITEMS, REDDIT_ITEMS]
        ),
    ), patch(
        "nodes.collection_node._fetch_newsapi",
        new=AsyncMock(return_value={}),
    ):
        topics = await _collect_async("batch_schema_test")

    for topic in topics:
        for row in topic.raw_rows:
            assert "batch_id" in row, f"Missing batch_id in row: {row}"
            assert "platform" in row, f"Missing platform in row: {row}"
            assert "topic_keyword" in row, f"Missing topic_keyword in row: {row}"
            assert row["platform"] in (
                "twitter",
                "reddit",
                "google_trends",
                "google_news",
            ), f"Invalid platform value: {row['platform']}"


@pytest.mark.asyncio
async def test_collect_async_news_count_enrichment() -> None:
    """Topics with news articles should have news_count > 0 and a google_news row."""
    news_counts = {"aitrends": 120, "climate change": 88}

    with patch(
        "nodes.collection_node._run_actor",
        new=AsyncMock(
            side_effect=[TWITTER_ITEMS, TRENDS_ITEMS, REDDIT_ITEMS]
        ),
    ), patch(
        "nodes.collection_node._fetch_newsapi",
        new=AsyncMock(return_value=news_counts),
    ):
        topics = await _collect_async("batch_news_test")

    enriched = [t for t in topics if t.news_count > 0]
    assert len(enriched) > 0

    for topic in enriched:
        news_rows = [r for r in topic.raw_rows if r.get("platform") == "google_news"]
        assert len(news_rows) == 1
        assert news_rows[0]["engagement_data"]["article_count"] == topic.news_count


# ---------------------------------------------------------------------------
# _fetch_newsapi
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_newsapi_returns_counts() -> None:
    mock_resp = _make_httpx_response(NEWSAPI_RESPONSE)

    with patch("nodes.collection_node.settings") as mock_settings, patch(
        "httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)
    ):
        mock_settings.newsapi_key = "test_key"
        mock_settings.newsapi_max_topics = 5

        counts = await _fetch_newsapi(["climate change", "ai trends"])

    assert isinstance(counts, dict)
    for kw, count in counts.items():
        assert isinstance(count, int)
        assert count >= 0


@pytest.mark.asyncio
async def test_fetch_newsapi_empty_key_returns_empty() -> None:
    with patch("nodes.collection_node.settings") as mock_settings:
        mock_settings.newsapi_key = ""
        mock_settings.newsapi_max_topics = 20

        counts = await _fetch_newsapi(["climate change"])

    assert counts == {}


@pytest.mark.asyncio
async def test_fetch_newsapi_request_failure_returns_zero() -> None:
    with patch("nodes.collection_node.settings") as mock_settings, patch(
        "httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.RequestError("timeout"))
    ):
        mock_settings.newsapi_key = "test_key"
        mock_settings.newsapi_max_topics = 5

        counts = await _fetch_newsapi(["climate change"])

    assert counts == {"climate change": 0}


# ---------------------------------------------------------------------------
# collect_signals_node — sync entry point
# ---------------------------------------------------------------------------


def test_collect_signals_node_calls_insert_signals() -> None:
    """collect_signals_node should bulk-insert all raw rows via db.insert_signals."""
    fake_topic = RawTopic(
        keyword="ai trends",
        platforms=["twitter"],
        twitter_rank=1,
        raw_rows=[
            {
                "batch_id": "b1",
                "platform": "twitter",
                "topic_keyword": "ai trends",
                "raw_data": {},
            }
        ],
    )

    with patch(
        "nodes.collection_node._collect_async",
        new=AsyncMock(return_value=[fake_topic]),
    ), patch("nodes.collection_node.db") as mock_db:
        mock_db.insert_signals.return_value = 1
        result = collect_signals_node("b1")

    mock_db.insert_signals.assert_called_once()
    inserted_rows = mock_db.insert_signals.call_args[0][0]
    assert len(inserted_rows) == 1
    assert inserted_rows[0]["platform"] == "twitter"

    assert len(result) == 1
    assert result[0].keyword == "ai trends"


def test_collect_signals_node_returns_raw_topic_list() -> None:
    """Return value must be a list of RawTopic instances."""
    fake_topics = [
        RawTopic(keyword="test topic", platforms=["reddit"]),
    ]

    with patch(
        "nodes.collection_node._collect_async",
        new=AsyncMock(return_value=fake_topics),
    ), patch("nodes.collection_node.db") as mock_db:
        mock_db.insert_signals.return_value = 0
        result = collect_signals_node("batch_xyz")

    assert isinstance(result, list)
    assert all(isinstance(t, RawTopic) for t in result)
