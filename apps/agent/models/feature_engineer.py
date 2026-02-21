"""
models/feature_engineer.py — Feature engineering for viral prediction.

Takes a RawTopic from the collection node and transforms it into a FeatureVector
of signals ready for the LinearScorer.  All values are kept in their natural units;
LinearScorer handles per-feature normalisation before weighting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from nodes.collection_node import RawTopic
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# Peak engagement hours in UTC (≈ noon–2pm and 10pm–2am)
_PEAK_HOURS: frozenset[int] = frozenset({12, 13, 14, 22, 23, 0, 1})

# Publication gap: capped so a single viral story can't dominate
_MAX_PUBLICATION_GAP: float = 10.0

# Default category multipliers; overridden by Supabase config at runtime
DEFAULT_CATEGORY_MULTIPLIERS: dict[str, float] = {
    "entertainment":      1.3,
    "sports":             1.25,
    "technology":         1.15,
    "politics":           1.1,
}
DEFAULT_CATEGORY_MULTIPLIER: float = 1.0


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class FeatureVector:
    """
    Raw feature values for a single topic.

    Units:
        cross_platform_score  — count of platforms (1–4)
        velocity_ratio        — current_score / previous_score (default 1.0)
        acceleration          — Δvelocity_ratio (default 0.0)
        publication_gap_score — article_count / hours_since_first_article (capped 10)
        sentiment_score       — abs(VADER compound), 0.0–1.0
        time_multiplier       — 1.2 at peak hours, 1.0 otherwise
        category_multiplier   — from config table or DEFAULT_CATEGORY_MULTIPLIERS
    """

    cross_platform_score: float
    velocity_ratio: float
    acceleration: float
    publication_gap_score: float
    sentiment_score: float
    time_multiplier: float
    category_multiplier: float


# ── FeatureEngineer ───────────────────────────────────────────────────────────


class FeatureEngineer:
    """
    Computes a FeatureVector from a RawTopic and optional previous-batch data.

    previous_batch_data items (newest-first) must contain at least:
        signal_score   — aggregate engagement score for that batch
        velocity_ratio — velocity_ratio computed in that batch (for acceleration)
    """

    def __init__(self) -> None:
        self._vader = SentimentIntensityAnalyzer()
        self._category_multipliers: dict[str, float] | None = None

    @property
    def category_multipliers(self) -> dict[str, float]:
        """Lazy-load category multipliers from the config table."""
        if self._category_multipliers is None:
            try:
                cfg = db.get_config_value("category_multipliers")
                self._category_multipliers = cfg if isinstance(cfg, dict) else {}
            except Exception:
                self._category_multipliers = {}
        return self._category_multipliers

    def _category_multiplier(self, category: str | None) -> float:
        if not category:
            return DEFAULT_CATEGORY_MULTIPLIER
        slug = category.lower().strip()
        # Config table takes priority over hard-coded defaults
        cfg_val = self.category_multipliers.get(slug)
        if cfg_val is not None:
            return float(cfg_val)
        return DEFAULT_CATEGORY_MULTIPLIERS.get(slug, DEFAULT_CATEGORY_MULTIPLIER)

    def _sentiment(self, topic: RawTopic) -> float:
        """
        Run VADER on the topic keyword plus the titles of the first three raw rows.
        Returns abs(compound) so that strongly negative viral topics score high too.
        """
        texts: list[str] = [topic.keyword]
        for row in topic.raw_rows[:3]:
            headline = (
                row.get("title")
                or (row.get("raw_data") or {}).get("title")
                or ""
            )
            if headline:
                texts.append(str(headline))
        compound = self._vader.polarity_scores(" ".join(texts))["compound"]
        return abs(compound)

    def _signal_score(self, topic: RawTopic) -> float:
        """
        Aggregate engagement signal for the topic in the current batch.

        Scores are normalised per-source so no single signal dominates:
          twitter rank 1 = 50 pts (rank 50 = 1 pt)
          reddit score ≤ 50 k mapped to 0–50
          trends interest 0–100 mapped to 0–50
          news_count ≤ 200 mapped to 0–20
        """
        score = 0.0
        if topic.twitter_rank is not None:
            score += max(0.0, 51.0 - topic.twitter_rank)
        if topic.reddit_score is not None:
            score += min(topic.reddit_score / 1_000.0, 50.0)
        if topic.trends_interest is not None:
            score += topic.trends_interest / 2.0
        if topic.news_count:
            score += min(topic.news_count / 10.0, 20.0)
        return max(score, 1.0)  # avoid division by zero

    def compute(
        self,
        raw_topic: RawTopic,
        previous_batch_data: list[dict[str, Any]] | None = None,
        *,
        category: str | None = None,
        hours_since_first_article: float = 24.0,
    ) -> FeatureVector:
        """
        Compute a FeatureVector for raw_topic.

        Args:
            raw_topic:               Collected topic from the current batch.
            previous_batch_data:     Earlier batch snapshots, newest-first.
                                     Each entry should contain ``signal_score``
                                     and optionally ``velocity_ratio``.
            category:                Topic category slug (e.g. 'sports').
            hours_since_first_article: Denominator for publication_gap_score.
                                       Defaults to 24 h (NewsAPI window).
        """
        prev = previous_batch_data or []

        # ── Cross-platform score ──────────────────────────────────────────────
        cross_platform_score = float(len(raw_topic.platforms))

        # ── Velocity ratio ────────────────────────────────────────────────────
        current_score = self._signal_score(raw_topic)
        if prev:
            prev_score = float(prev[0].get("signal_score", current_score))
            velocity_ratio = current_score / max(prev_score, 1.0)
        else:
            velocity_ratio = 1.0  # neutral: no change observed

        # ── Acceleration ──────────────────────────────────────────────────────
        if len(prev) >= 2:
            prev_velocity = float(prev[1].get("velocity_ratio", velocity_ratio))
            acceleration = velocity_ratio - prev_velocity
        else:
            acceleration = 0.0

        # ── Publication gap score ─────────────────────────────────────────────
        publication_gap_score = min(
            raw_topic.news_count / max(hours_since_first_article, 1.0),
            _MAX_PUBLICATION_GAP,
        )

        # ── Sentiment ─────────────────────────────────────────────────────────
        sentiment_score = self._sentiment(raw_topic)

        # ── Time multiplier ───────────────────────────────────────────────────
        current_hour = datetime.now(timezone.utc).hour
        time_multiplier = 1.2 if current_hour in _PEAK_HOURS else 1.0

        # ── Category multiplier ───────────────────────────────────────────────
        category_multiplier = self._category_multiplier(category)

        return FeatureVector(
            cross_platform_score=cross_platform_score,
            velocity_ratio=velocity_ratio,
            acceleration=acceleration,
            publication_gap_score=publication_gap_score,
            sentiment_score=sentiment_score,
            time_multiplier=time_multiplier,
            category_multiplier=category_multiplier,
        )
