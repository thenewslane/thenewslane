"""
nodes/viral_predictor.py — LangGraph node: viral prediction scoring.

Applies the weighted linear model (→ XGBoost after 30 days of labelled data):
  cross_platform_score × w1
  + velocity_ratio × w2
  + acceleration_score × w3
  + publication_gap_score × w4
  + sentiment_polarity × w5
  × time_of_day_multiplier
  × category_multiplier
  = weighted_score

Topics scoring 40-60% are passed to the Claude Haiku LLM validator.
Topics are then assigned Tier 1 (≥0.75) / Tier 2 (≥0.45) / Tier 3 (<0.45).
Tier 3 topics can be rejected if below a minimum threshold from config.
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


def predict_virality(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — score each raw signal group and produce candidate topics.

    Updates state keys:
      topics           (list[dict]) — candidate topics with viral_tier + weighted_score
      topics_processed (int)
      topics_rejected  (int)
    """
    batch_id: str = state["batch_id"]
    signals: list[dict[str, Any]] = state.get("raw_signals", [])
    log.info("predict_virality: scoring %d signals  batch_id=%s", len(signals), batch_id)

    topics: list[dict[str, Any]] = []
    rejected = 0

    # TODO: implement viral prediction model
    # from models.viral_model import ViralPredictor
    # predictor = ViralPredictor()
    # for signal_group in group_signals_by_topic(signals):
    #     score = predictor.score(signal_group)
    #     if score.weighted_score < MIN_THRESHOLD:
    #         rejected += 1
    #         continue
    #     topics.append({**signal_group, **score.model_dump(), 'batch_id': batch_id})

    log.info(
        "predict_virality: %d topics passed, %d rejected",
        len(topics), rejected,
    )
    return {
        "topics":          topics,
        "topics_processed": len(topics) + rejected,
        "topics_rejected":  rejected,
    }
