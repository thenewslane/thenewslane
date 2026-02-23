"""
nodes/viral_predictor.py — LangGraph node: viral prediction scoring.

Delegates to ViralPredictionNode which applies:
  FeatureEngineer → LinearScorer → LLMValidator (8-12 band) → tier assignment
  → trending_topics + viral_predictions DB rows

Topics scoring < 2 (bottom ~2%) are rejected here and excluded from the returned list.
"""

from __future__ import annotations

from typing import Any

from nodes.collection_node import RawTopic
from nodes.viral_prediction_node import ViralPredictionNode
from utils.logger import get_logger

log = get_logger(__name__)


def predict_virality(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — score each raw topic and produce candidate topics.

    Reads from state:
        batch_id     (str)           — current batch identifier
        raw_signals  (list[RawTopic]) — output from collect_signals node

    Updates state keys:
        topics           (list[dict]) — passing topics with viral_tier + viral_score
        topics_processed (int)        — total topics evaluated
        topics_rejected  (int)        — topics below the score threshold
    """
    batch_id: str = state["batch_id"]
    raw_signals: list[RawTopic] = state.get("raw_signals", [])

    log.info(
        "predict_virality: scoring %d topics  batch_id=%s",
        len(raw_signals),
        batch_id,
    )

    node = ViralPredictionNode()
    passing = node.run(batch_id, raw_signals)

    topics_processed = len(raw_signals)
    topics_rejected  = topics_processed - len(passing)

    log.info(
        "predict_virality: %d passed, %d rejected  batch_id=%s",
        len(passing),
        topics_rejected,
        batch_id,
    )

    return {
        "topics":            passing,
        "topics_processed":  topics_processed,
        "topics_rejected":   topics_rejected,
    }
