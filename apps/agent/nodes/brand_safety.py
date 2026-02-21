"""
nodes/brand_safety.py — LangGraph node: three-stage brand safety pipeline.

Stage 1 — Keyword blocklist (config table, instant)
Stage 2 — Llama Guard 3 via Groq (toxicity / safety classification)
Stage 3 — Claude Haiku brand suitability score (0–1, threshold from config)

Topics only advance when overall_passed = True.
Results are written to brand_safety_log.
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


def check_brand_safety(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — run three-stage brand safety checks on every candidate topic.

    Updates state keys:
      topics          — each dict gains 'brand_safe': bool
      topics_rejected — incremented for each failed topic
    """
    batch_id: str = state["batch_id"]
    topics: list[dict[str, Any]] = state.get("topics", [])
    log.info("check_brand_safety: checking %d topics  batch_id=%s", len(topics), batch_id)

    approved: list[dict[str, Any]] = []
    rejected_count: int = 0

    # TODO: implement three-stage brand safety
    # from brand_safety_checks import keyword_check, llama_guard_check, haiku_check
    # blocklist = db.get_config_value('keyword_blocklist', default=[])
    # for topic in topics:
    #     kw_pass, blocked = keyword_check(topic['title'], blocklist)
    #     llama_pass, llama_score, llama_cats = llama_guard_check(topic)
    #     haiku_pass, haiku_score, haiku_reason = haiku_check(topic)
    #     overall = kw_pass and llama_pass and haiku_pass
    #     db.insert_brand_safety_log({...})
    #     if overall:
    #         topic['brand_safe'] = True
    #         approved.append(topic)
    #     else:
    #         rejected_count += 1

    log.info(
        "check_brand_safety: %d approved, %d rejected",
        len(approved), rejected_count,
    )
    return {
        "topics":         approved,
        "topics_rejected": state.get("topics_rejected", 0) + rejected_count,
    }
