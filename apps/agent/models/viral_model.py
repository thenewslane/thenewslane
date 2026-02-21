"""
models/viral_model.py — Viral prediction model.

Phase 1 (current): weighted linear model with VADER sentiment.
Phase 2 (after 30 days of labelled data): XGBoost classifier.

Feature weights are loaded from the config table so they can be tuned
via the admin panel without redeploying the agent.

Feature Engineering:
  cross_platform_score    — normalised count of platforms mentioning the topic
  velocity_ratio          — current mentions / baseline mentions (last 4h)
  acceleration_score      — rate of change of velocity
  publication_gap_score   — inverse of how many articles already published
  sentiment_polarity      — VADER compound score mapped to 0-1
  time_of_day_multiplier  — peak hours (8-10am, 6-8pm ET) score higher
  category_multiplier     — category-specific weighting from config
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ── Default weights (overridden by config table at runtime) ───────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "cross_platform":   0.30,
    "velocity":         0.25,
    "acceleration":     0.20,
    "publication_gap":  0.10,
    "sentiment":        0.15,
}

TIER_1_THRESHOLD = 0.75
TIER_2_THRESHOLD = 0.45
LLM_VALIDATION_BAND = (0.40, 0.60)  # score range that triggers Claude Haiku review


@dataclass
class ViralScore:
    cross_platform_score:   float = 0.0
    velocity_ratio:         float = 0.0
    acceleration_score:     float = 0.0
    publication_gap_score:  float = 0.0
    sentiment_polarity:     float = 0.0
    time_of_day_multiplier: float = 1.0
    category_multiplier:    float = 1.0
    weighted_score:         float = 0.0
    tier_assigned:          int | None = None
    llm_validated:          bool | None = None
    llm_confidence:         float | None = None
    llm_reasoning:          str | None = None
    rejected:               bool = False
    rejection_reason:       str | None = None

    def to_db_dict(self) -> dict[str, Any]:
        return {
            "cross_platform_score":  round(self.cross_platform_score, 4),
            "velocity_ratio":        round(self.velocity_ratio, 4),
            "acceleration_score":    round(self.acceleration_score, 4),
            "publication_gap_score": round(self.publication_gap_score, 4),
            "sentiment_polarity":    round(self.sentiment_polarity, 4),
            "time_of_day_multiplier": round(self.time_of_day_multiplier, 3),
            "category_multiplier":   round(self.category_multiplier, 3),
            "weighted_score":        round(self.weighted_score, 4),
            "tier_assigned":         self.tier_assigned,
            "llm_validated":         self.llm_validated,
            "llm_confidence":        self.llm_confidence,
            "llm_reasoning":         self.llm_reasoning,
            "rejected":              self.rejected,
            "rejection_reason":      self.rejection_reason,
        }


class ViralPredictor:
    """
    Computes viral scores for candidate topics.
    Weights are loaded from the Supabase config table on first use.
    """

    def __init__(self) -> None:
        self._weights: dict[str, float] | None = None
        self._vader = SentimentIntensityAnalyzer()

    @property
    def weights(self) -> dict[str, float]:
        if self._weights is None:
            try:
                cfg = db.get_config_value("viral_prediction_weights")
                self._weights = cfg if isinstance(cfg, dict) else DEFAULT_WEIGHTS
            except Exception:
                self._weights = DEFAULT_WEIGHTS
        return self._weights

    def sentiment_score(self, text: str) -> float:
        """Map VADER compound (-1 to 1) to 0-1 scale."""
        compound = self._vader.polarity_scores(text)["compound"]
        return (compound + 1) / 2

    def compute(
        self,
        *,
        cross_platform: float,
        velocity: float,
        acceleration: float,
        publication_gap: float,
        text: str,
        time_multiplier: float = 1.0,
        category_multiplier: float = 1.0,
    ) -> ViralScore:
        """Compute a ViralScore for a single topic."""
        sentiment = self.sentiment_score(text)
        w = self.weights

        raw = (
            cross_platform * w.get("cross_platform", DEFAULT_WEIGHTS["cross_platform"])
            + velocity     * w.get("velocity",       DEFAULT_WEIGHTS["velocity"])
            + acceleration * w.get("acceleration",   DEFAULT_WEIGHTS["acceleration"])
            + publication_gap * w.get("publication_gap", DEFAULT_WEIGHTS["publication_gap"])
            + sentiment    * w.get("sentiment",      DEFAULT_WEIGHTS["sentiment"])
        )
        weighted = float(np.clip(raw * time_multiplier * category_multiplier, 0, 1))

        tier: int | None
        if weighted >= TIER_1_THRESHOLD:
            tier = 1
        elif weighted >= TIER_2_THRESHOLD:
            tier = 2
        else:
            tier = 3

        return ViralScore(
            cross_platform_score=cross_platform,
            velocity_ratio=velocity,
            acceleration_score=acceleration,
            publication_gap_score=publication_gap,
            sentiment_polarity=sentiment,
            time_of_day_multiplier=time_multiplier,
            category_multiplier=category_multiplier,
            weighted_score=weighted,
            tier_assigned=tier,
        )
