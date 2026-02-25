"""
features/engineering.py — Feature derivation functions.

Computes time-based, frequency-based, and value-based features from raw
reader_events rows for a single user. All features are tenure-aware.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def compute_features(
    events: list[dict[str, Any]],
    user_created_at: datetime | None = None,
) -> dict[str, Any]:
    """
    Derive aggregated features from a list of raw event dicts for one user.

    Each event dict has keys: event_type, topic_id, category_id, metadata,
    device_type, geo_country, created_at, session_id.
    """
    now = datetime.now(timezone.utc)

    if not events:
        return _empty_features()

    # ── Basics ────────────────────────────────────────────────────────────
    unique_sessions = {e["session_id"] for e in events}
    session_count = len(unique_sessions)

    pageviews = [e for e in events if e["event_type"] == "pageview"]
    total_pageviews = len(pageviews)

    timestamps = [e["created_at"] for e in events if e["created_at"]]
    last_event_at = max(timestamps) if timestamps else now
    days_since_last_visit = (now - last_event_at).days

    days_since_registration = None
    if user_created_at:
        days_since_registration = (now - user_created_at).days

    # ── Time-windowed counts ──────────────────────────────────────────────
    from datetime import timedelta

    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    articles_read_last_7d = sum(
        1 for e in pageviews if e["created_at"] and e["created_at"] >= cutoff_7d
    )
    articles_read_last_30d = sum(
        1 for e in pageviews if e["created_at"] and e["created_at"] >= cutoff_30d
    )

    # ── Time on page ─────────────────────────────────────────────────────
    time_events = [
        e for e in events
        if e["event_type"] == "time_on_page" and e.get("metadata", {}).get("seconds")
    ]
    if time_events:
        avg_time = sum(e["metadata"]["seconds"] for e in time_events) / len(time_events)
    else:
        avg_time = 0.0

    # ── Scroll depth ─────────────────────────────────────────────────────
    scroll_events = [
        e for e in events
        if e["event_type"] == "scroll_depth" and e.get("metadata", {}).get("depth_pct")
    ]
    if scroll_events:
        avg_scroll = sum(e["metadata"]["depth_pct"] for e in scroll_events) / len(
            scroll_events
        )
    else:
        avg_scroll = 0.0

    # ── Category distribution ────────────────────────────────────────────
    cat_counts: Counter[int] = Counter()
    for e in pageviews:
        cid = e.get("category_id")
        if cid is not None:
            cat_counts[cid] += 1

    total_cat = sum(cat_counts.values()) or 1
    category_distribution = {
        str(k): round(v / total_cat, 4) for k, v in cat_counts.most_common()
    }
    top_category_id = cat_counts.most_common(1)[0][0] if cat_counts else None

    # ── Engagement counters ──────────────────────────────────────────────
    newsletter_clicks = sum(1 for e in events if e["event_type"] == "newsletter_click")
    newsletter_events = newsletter_clicks  # open rate = clicks / total newsletter events sent (approximated)
    newsletter_open_rate = min(newsletter_clicks / max(total_pageviews, 1), 1.0)

    total_paywall_hits = sum(1 for e in events if e["event_type"] == "paywall_hit")
    total_shares = sum(1 for e in events if e["event_type"] == "share")

    is_subscriber = any(e["event_type"] == "subscribe" for e in events)

    # ── Visit frequency ──────────────────────────────────────────────────
    if timestamps and len(timestamps) >= 2:
        span_days = max((max(timestamps) - min(timestamps)).days, 1)
        visit_frequency_weekly = round(session_count / (span_days / 7), 2)
    else:
        visit_frequency_weekly = session_count  # single session

    # ── Device & geo (mode) ──────────────────────────────────────────────
    devices = [e["device_type"] for e in events if e.get("device_type")]
    device_primary = Counter(devices).most_common(1)[0][0] if devices else None

    geos = [e["geo_country"] for e in events if e.get("geo_country")]
    geo_country = Counter(geos).most_common(1)[0][0] if geos else None

    return {
        "session_count": session_count,
        "total_pageviews": total_pageviews,
        "articles_read_last_7d": articles_read_last_7d,
        "articles_read_last_30d": articles_read_last_30d,
        "avg_time_on_page_sec": round(avg_time, 2),
        "avg_scroll_depth_pct": round(avg_scroll, 2),
        "top_category_id": top_category_id,
        "category_distribution": category_distribution,
        "newsletter_open_rate": round(newsletter_open_rate, 4),
        "total_paywall_hits": total_paywall_hits,
        "total_shares": total_shares,
        "days_since_registration": days_since_registration,
        "days_since_last_visit": days_since_last_visit,
        "visit_frequency_weekly": visit_frequency_weekly,
        "device_type_primary": device_primary,
        "geo_country": geo_country,
        "is_subscriber": is_subscriber,
    }


def _empty_features() -> dict[str, Any]:
    return {
        "session_count": 0,
        "total_pageviews": 0,
        "articles_read_last_7d": 0,
        "articles_read_last_30d": 0,
        "avg_time_on_page_sec": 0.0,
        "avg_scroll_depth_pct": 0.0,
        "top_category_id": None,
        "category_distribution": {},
        "newsletter_open_rate": 0.0,
        "total_paywall_hits": 0,
        "total_shares": 0,
        "days_since_registration": None,
        "days_since_last_visit": None,
        "visit_frequency_weekly": 0.0,
        "device_type_primary": None,
        "geo_country": None,
        "is_subscriber": False,
    }
