"""
nodes/signal_collector.py — LangGraph node: collect signals from all platforms.

Delegates to collection_node.collect_signals_node() which runs three Apify
actors (Twitter, Google Trends, Reddit) in parallel, enriches with NewsAPI,
and persists all raw rows to the raw_signals table.
"""

from __future__ import annotations

from typing import Any

from config.settings import settings
from nodes.collection_node import RawTopic, collect_signals_node
from utils.logger import get_logger

log = get_logger(__name__)


def collect_signals(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — collect trending signals from all configured platforms.

    Updates state keys:
      raw_signals         (list[RawTopic]) — merged topic objects
      signals_collected   (int)            — total unique topics collected
    """
    batch_id: str = state["batch_id"]
    geo: str = state.get("geo", settings.trends_geo)

    log.info("collect_signals: starting  batch_id=%s  geo=%s", batch_id, geo)

    topics: list[RawTopic] = collect_signals_node(batch_id, geo)

    log.info("collect_signals: collected %d topics", len(topics))
    return {
        "raw_signals": topics,
        "signals_collected": len(topics),
    }
