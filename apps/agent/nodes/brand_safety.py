"""
nodes/brand_safety.py — LangGraph node: two-stage brand safety pipeline.

Stage 1 — Keyword blocklist (config table, instant)
Stage 2 — DISABLED (Llama Guard had API access issues and over-rejection)
Stage 3 — Claude Haiku brand suitability assessment (SAFE/UNSAFE)

All topics are ingested and advance; each topic gets brand_safe=True/False.
Unsafe topics are still published but ad slots are disabled on the article page.
Results are written to brand_safety_log.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from nodes.brand_safety_filters import BrandSafetyLLMFilter, KeywordFilter, LlamaGuardFilter
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)


class BrandSafetyNode:
    """Orchestrator for two-tier brand safety pipeline (Tier 2 Llama Guard disabled)."""
    
    def __init__(self) -> None:
        self.keyword_filter = KeywordFilter()
        # self.llama_guard_filter = LlamaGuardFilter()  # Disabled - API issues
        self.brand_safety_filter = BrandSafetyLLMFilter()
    
    def process_topic(self, topic: dict[str, Any], batch_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Process a single topic through all three tiers.
        Returns (is_safe, log_entry)
        """
        topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
        topic_title = topic.get("title", "")
        headline_cluster = topic.get("headline_cluster", "")
        
        # Initialize log entry
        log_entry = {
            "id": str(uuid.uuid4()),
            "batch_id": batch_id,
            "topic_id": topic_id,
            "topic_title": topic_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tier1_passed": False,
            "tier1_blocked_keyword": None,
            "tier2_passed": False,
            "tier2_flagged_categories": [],
            "tier3_passed": False,
            "tier3_explanation": "",
            "overall_passed": False
        }
        
        # Tier 1: Keyword Filter
        tier1_safe, blocked_keyword = self.keyword_filter.check(topic_title, headline_cluster)
        log_entry["tier1_passed"] = tier1_safe
        log_entry["tier1_blocked_keyword"] = blocked_keyword
        
        if not tier1_safe:
            log_entry["overall_passed"] = False
            return False, log_entry
        
        # Tier 2: Llama Guard Filter - DISABLED (API access issues)
        # Skip Llama Guard check due to API access problems and over-rejection
        tier2_safe = True  # Always pass Tier 2
        flagged_categories = []  # No categories flagged
        log_entry["tier2_passed"] = tier2_safe
        log_entry["tier2_flagged_categories"] = flagged_categories
        log_entry["tier2_skipped"] = True  # Mark as intentionally skipped
        
        # Note: Tier 2 no longer blocks topics
        
        # Tier 3: Brand Safety LLM Filter
        tier3_safe, explanation = self.brand_safety_filter.check(topic_title, headline_cluster)
        log_entry["tier3_passed"] = tier3_safe
        log_entry["tier3_explanation"] = explanation
        
        # Overall result (Tier 2 disabled, so only check Tier 1 + Tier 3)
        overall_safe = tier1_safe and tier3_safe  # Removed tier2_safe dependency
        log_entry["overall_passed"] = overall_safe
        
        return overall_safe, log_entry


def check_brand_safety(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — run three-stage brand safety checks on every candidate topic.

    All topics are ingested; each topic gains 'brand_safe': True or False.
    Unsafe topics continue through the pipeline but ad slots are disabled on the article page.

    Updates state keys:
      topics          — all topics, each with 'brand_safe': bool
      topics_rejected — count of topics flagged UNSAFE (for metrics only)
    """
    batch_id: str = state["batch_id"]
    topics: list[dict[str, Any]] = state.get("topics", [])
    log.info("check_brand_safety: checking %d topics  batch_id=%s", len(topics), batch_id)

    brand_safety_node = BrandSafetyNode()
    all_topics: list[dict[str, Any]] = []
    rejected_count: int = 0
    log_entries: list[dict[str, Any]] = []

    for topic in topics:
        is_safe, log_entry = brand_safety_node.process_topic(topic, batch_id)
        log_entries.append(log_entry)
        topic["brand_safe"] = is_safe
        all_topics.append(topic)
        if not is_safe:
            rejected_count += 1

    try:
        if log_entries:
            db.client.table("brand_safety_log").insert(log_entries).execute()
            log.debug("check_brand_safety: inserted %d log entries", len(log_entries))
    except Exception as e:
        log.error("check_brand_safety: failed to insert log entries: %s", e)

    log.info(
        "check_brand_safety: %d approved, %d rejected (all ingested)",
        len(all_topics) - rejected_count, rejected_count,
    )
    return {
        "topics":         all_topics,
        "topics_rejected": state.get("topics_rejected", 0) + rejected_count,
    }
