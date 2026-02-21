"""
nodes/signal_collector.py — LangGraph node: collect signals from all platforms.

Platforms:
  - Twitter/X trending (Apify actor)
  - Reddit rising (Apify actor)
  - YouTube trending (YouTube Data API v3)
  - Google Trends (Apify actor)
  - NewsAPI top headlines

Each source's raw results are stored in raw_signals (DB) and returned in state.
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


def collect_signals(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — collect trending signals from all configured platforms.

    Updates state keys:
      raw_signals       (list[dict])  — all collected signal rows
      signals_collected (int)         — total count
    """
    batch_id: str = state["batch_id"]
    log.info("collect_signals: starting  batch_id=%s", batch_id)

    all_signals: list[dict[str, Any]] = []

    # TODO: implement each platform collector
    # from signal_sources.twitter import collect_twitter
    # from signal_sources.reddit import collect_reddit
    # from signal_sources.youtube import collect_youtube
    # from signal_sources.google_trends import collect_google_trends
    # from signal_sources.newsapi import collect_newsapi
    #
    # collectors = [collect_twitter, collect_reddit, collect_youtube,
    #               collect_google_trends, collect_newsapi]
    # for collector in collectors:
    #     try:
    #         signals = collector(batch_id)
    #         all_signals.extend(signals)
    #     except Exception as exc:
    #         log.error("Collector %s failed: %s", collector.__name__, exc)

    log.info("collect_signals: collected %d signals", len(all_signals))
    return {
        "raw_signals":     all_signals,
        "signals_collected": len(all_signals),
    }
