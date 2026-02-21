"""
models/linear_scorer.py — Weighted linear scorer for viral prediction.

Formula (all features normalised to [0, 1] before weighting):
    raw = (cross_platform × w1) + (velocity × w2) + (acceleration × w3)
          + (publication_gap × w4) + (sentiment × w5)
    score_0_100 = clip(raw × time_multiplier × category_multiplier × 100, 0, 100)

Weights are loaded from the Supabase config table (key: "viral_prediction_weights")
so they can be adjusted from the admin panel without redeployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.feature_engineer import FeatureVector
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "cross_platform":  0.30,
    "velocity_ratio":  0.25,
    "acceleration":    0.20,
    "publication_gap": 0.10,
    "sentiment":       0.10,
}

# Normalisation scale factors (raw feature → [0, 1])
_CROSS_PLATFORM_MAX: float = 4.0   # maximum number of platforms
_VELOCITY_MAX:       float = 5.0   # cap at 5× growth; beyond that, same score
_ACCEL_RANGE_LO:     float = -2.0  # [-2, 2] mapped to [0, 1]
_ACCEL_RANGE_HI:     float =  2.0
_PUB_GAP_MAX:        float = 10.0  # already capped in FeatureEngineer
_SENTIMENT_MAX:      float =  1.0  # VADER compound abs value


# ── Result object ─────────────────────────────────────────────────────────────


@dataclass
class ScorerResult:
    """Output of LinearScorer.score()."""

    raw_score: float                          # 0.0–100.0 before LLM adjustment
    cross_platform_score: float
    velocity_ratio: float
    acceleration: float
    publication_gap_score: float
    sentiment_score: float
    time_multiplier: float
    category_multiplier: float
    weights_used: dict[str, float] = field(default_factory=dict)


# ── LinearScorer ──────────────────────────────────────────────────────────────


class LinearScorer:
    """
    Applies weighted linear scoring to a FeatureVector and returns a 0–100 score.

    Weights are loaded lazily from the Supabase config table on first call.
    Falls back to DEFAULT_WEIGHTS if the config table is unavailable.
    """

    def __init__(self) -> None:
        self._weights: dict[str, float] | None = None

    @property
    def weights(self) -> dict[str, float]:
        if self._weights is None:
            try:
                cfg = db.get_config_value("viral_prediction_weights")
                self._weights = cfg if isinstance(cfg, dict) else DEFAULT_WEIGHTS
            except Exception:
                log.warning("LinearScorer: could not load weights from config; using defaults")
                self._weights = DEFAULT_WEIGHTS
        return self._weights

    @staticmethod
    def _normalise(fv: FeatureVector) -> dict[str, float]:
        """Map each feature to [0, 1] for the weighted sum."""
        cross = min(fv.cross_platform_score, _CROSS_PLATFORM_MAX) / _CROSS_PLATFORM_MAX

        velocity = min(fv.velocity_ratio, _VELOCITY_MAX) / _VELOCITY_MAX

        accel_clamped = max(_ACCEL_RANGE_LO, min(fv.acceleration, _ACCEL_RANGE_HI))
        accel = (accel_clamped - _ACCEL_RANGE_LO) / (_ACCEL_RANGE_HI - _ACCEL_RANGE_LO)

        pub_gap = min(fv.publication_gap_score, _PUB_GAP_MAX) / _PUB_GAP_MAX

        sentiment = min(fv.sentiment_score, _SENTIMENT_MAX)

        return {
            "cross_platform":  cross,
            "velocity_ratio":  velocity,
            "acceleration":    accel,
            "publication_gap": pub_gap,
            "sentiment":       sentiment,
        }

    def score(self, fv: FeatureVector) -> ScorerResult:
        """
        Compute the viral score for a FeatureVector.

        Returns a ScorerResult with raw_score in [0, 100] before any LLM
        adjustment.
        """
        w = self.weights
        n = self._normalise(fv)

        weighted_sum = (
            n["cross_platform"]  * w.get("cross_platform",  DEFAULT_WEIGHTS["cross_platform"])
            + n["velocity_ratio"]  * w.get("velocity_ratio",  DEFAULT_WEIGHTS["velocity_ratio"])
            + n["acceleration"]    * w.get("acceleration",    DEFAULT_WEIGHTS["acceleration"])
            + n["publication_gap"] * w.get("publication_gap", DEFAULT_WEIGHTS["publication_gap"])
            + n["sentiment"]       * w.get("sentiment",       DEFAULT_WEIGHTS["sentiment"])
        )

        raw_score = min(
            weighted_sum * fv.time_multiplier * fv.category_multiplier * 100.0,
            100.0,
        )
        raw_score = max(raw_score, 0.0)

        return ScorerResult(
            raw_score=round(raw_score, 2),
            cross_platform_score=fv.cross_platform_score,
            velocity_ratio=fv.velocity_ratio,
            acceleration=fv.acceleration,
            publication_gap_score=fv.publication_gap_score,
            sentiment_score=fv.sentiment_score,
            time_multiplier=fv.time_multiplier,
            category_multiplier=fv.category_multiplier,
            weights_used=dict(w),
        )
