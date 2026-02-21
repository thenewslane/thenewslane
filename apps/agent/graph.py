"""
graph.py — LangGraph pipeline graph definition.

Pipeline topology:
  collect_signals
       ↓
  predict_virality          (fan-out per topic via Send())
       ↓
  check_brand_safety
       ↓
  generate_content
       ↓
  publish_topic
       ↓
      END

Rejection paths:
  predict_virality  → END  (score too low / rejected outright)
  check_brand_safety → END (brand safety failed, no override)
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from nodes.brand_safety import check_brand_safety
from nodes.content_generator import generate_content
from nodes.publisher import publish_topic
from nodes.signal_collector import collect_signals
from nodes.viral_predictor import predict_virality
from utils.logger import get_logger

log = get_logger(__name__)


# ── Pipeline state ────────────────────────────────────────────────────────────


class PipelineState(TypedDict):
    """Shared mutable state threaded through every node in the graph."""

    # Set at pipeline entry
    batch_id: str

    # Accumulated during signal collection
    raw_signals: list[dict[str, Any]]

    # Candidate topics produced from signals
    topics: list[dict[str, Any]]

    # Counts updated by each node
    signals_collected: int
    topics_processed: int
    topics_published: int
    topics_rejected: int

    # Errors are appended (never overwritten) across parallel branches
    errors: Annotated[list[str], operator.add]


# ── Routing helpers ───────────────────────────────────────────────────────────


def _route_after_predict(state: PipelineState) -> str:
    """
    After viral prediction: only proceed to brand safety if there are
    topics that passed the score threshold.  Otherwise end the run.
    """
    eligible = [t for t in state.get("topics", []) if t.get("viral_tier") in (1, 2, 3)]
    if eligible:
        return "check_brand_safety"
    log.info("No topics passed viral prediction threshold — ending batch %s", state["batch_id"])
    return END  # type: ignore[return-value]


def _route_after_brand_safety(state: PipelineState) -> str:
    """After brand safety: only generate content for approved topics."""
    approved = [t for t in state.get("topics", []) if t.get("brand_safe")]
    if approved:
        return "generate_content"
    log.info("No topics cleared brand safety — ending batch %s", state["batch_id"])
    return END  # type: ignore[return-value]


# ── Graph assembly ────────────────────────────────────────────────────────────


def build_graph() -> Any:
    """Build and compile the pipeline StateGraph."""
    g = StateGraph(PipelineState)

    g.add_node("collect_signals",    collect_signals)
    g.add_node("predict_virality",   predict_virality)
    g.add_node("check_brand_safety", check_brand_safety)
    g.add_node("generate_content",   generate_content)
    g.add_node("publish_topic",      publish_topic)

    g.set_entry_point("collect_signals")

    g.add_edge("collect_signals", "predict_virality")

    g.add_conditional_edges(
        "predict_virality",
        _route_after_predict,
        {"check_brand_safety": "check_brand_safety", END: END},
    )

    g.add_conditional_edges(
        "check_brand_safety",
        _route_after_brand_safety,
        {"generate_content": "generate_content", END: END},
    )

    g.add_edge("generate_content", "publish_topic")
    g.add_edge("publish_topic",    END)

    return g.compile()


# Compiled graph — imported by main.py and scheduler.py
pipeline = build_graph()
