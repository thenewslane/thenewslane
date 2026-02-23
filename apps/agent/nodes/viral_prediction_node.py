"""
nodes/viral_prediction_node.py — Orchestrates the viral prediction pipeline.

For each RawTopic from the collection node:
  1. FeatureEngineer  → FeatureVector
  2. LinearScorer     → 0–100 raw score
  3. LLMValidator     → adjusted score (only for 8–12 band topics)
  4. Tier assignment  → Tier 1 (16–100) / Tier 2 (13–15) / Tier 3 (10–12)
  5. DB persistence   → trending_topics + viral_predictions rows
  6. Returns only topics scoring ≥ 2 (~2% filter), sorted by score descending.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from models.feature_engineer import FeatureEngineer, FeatureVector
from models.linear_scorer import LinearScorer
from models.llm_validator import LLMValidator
from nodes.collection_node import RawTopic
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ── Tier thresholds (0–100 scale) ─────────────────────────────────────────────
# Set so only ~2% of scored topics are rejected (bottom 2%: score < 2)

TIER_1_MIN: float = 16.0   # Tier 1: 16–100
TIER_2_MIN: float = 13.0   # Tier 2: 13–15
TIER_3_MIN: float = 2.0    # Tier 3: 2–12; below 2 → rejected (~2% filter)


# ── ViralPredictionNode ───────────────────────────────────────────────────────


class ViralPredictionNode:
    """
    Orchestrates feature engineering, scoring, LLM validation, and DB writes
    for a batch of RawTopic objects.
    """

    def __init__(self) -> None:
        self._engineer  = FeatureEngineer()
        self._scorer    = LinearScorer()
        self._validator = LLMValidator()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_slug(self, keyword: str, batch_id: str) -> str:
        """Produce a URL-safe slug unique to this batch."""
        base = re.sub(r"[^a-z0-9\s-]", "", keyword.lower())
        base = re.sub(r"\s+", "-", base.strip())[:80].strip("-")
        # Append a 6-char batch suffix to guarantee uniqueness across runs
        suffix = batch_id[-6:] if len(batch_id) >= 6 else uuid.uuid4().hex[:6]
        return f"{base}-{suffix}"

    def _signal_summary(self, topic: RawTopic) -> str:
        """Human-readable signal summary for the LLM validator prompt."""
        parts: list[str] = []
        if topic.twitter_rank is not None:
            parts.append(f"Twitter rank: {topic.twitter_rank}")
        if topic.reddit_score is not None:
            parts.append(f"Reddit score: {topic.reddit_score:,}")
        if topic.trends_interest is not None:
            parts.append(f"Google Trends interest: {topic.trends_interest}")
        if topic.news_count:
            parts.append(f"News articles (24h): {topic.news_count}")
        return ", ".join(parts) if parts else "No signals available"

    def _get_previous_batch_data(self, keyword: str) -> list[dict[str, Any]]:
        """
        Fetch recent signal scores for this keyword from previous batches,
        ordered newest-first.  Returns empty list on any error.

        Each returned dict contains:
            signal_score   — aggregate engagement score computed here
            velocity_ratio — placeholder; not stored in raw_signals, so
                             we return 1.0 as a neutral default
        """
        try:
            rows = (
                db.client.table("raw_signals")
                .select("engagement_data, batch_id, collected_at")
                .eq("topic_keyword", keyword)
                .order("collected_at", desc=True)
                .limit(20)
                .execute()
            ).data or []

            # Group by batch_id (preserve order = newest first)
            batches: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                bid = row.get("batch_id", "")
                batches.setdefault(bid, []).append(row)

            results: list[dict[str, Any]] = []
            for bid, batch_rows in batches.items():
                score = 0.0
                for r in batch_rows:
                    eng = r.get("engagement_data") or {}
                    score += float(eng.get("tweet_count") or 0) / 1_000.0
                    score += float(eng.get("score") or 0) / 1_000.0
                    score += float(eng.get("interest") or 0) / 2.0
                    score += float(eng.get("article_count") or 0) / 10.0
                results.append({"signal_score": max(score, 1.0), "velocity_ratio": 1.0})

            return results[1:]  # skip the current batch (first entry = current)
        except Exception as exc:
            log.debug("Could not fetch previous batch data for %r: %s", keyword, exc)
            return []

    @staticmethod
    def _assign_tier(score: float) -> tuple[int | None, bool]:
        """Return (tier, rejected).  rejected=True when score < TIER_3_MIN."""
        if score >= TIER_1_MIN:
            return 1, False
        if score >= TIER_2_MIN:
            return 2, False
        if score >= TIER_3_MIN:
            return 3, False
        return None, True

    def _build_prediction_row(
        self,
        topic_id: str,
        batch_id: str,
        fv: FeatureVector,
        final_score: float,
        tier: int | None,
        rejected: bool,
        llm_called: bool,
        llm_verdict: bool | None,
        llm_reasoning: str | None,
        llm_confidence: float | None,
    ) -> dict[str, Any]:
        """Build the viral_predictions insert dict. Normalises values to DB ranges."""
        from models.linear_scorer import _ACCEL_RANGE_HI, _ACCEL_RANGE_LO, _PUB_GAP_MAX

        accel_normalised = (
            max(_ACCEL_RANGE_LO, min(fv.acceleration, _ACCEL_RANGE_HI)) - _ACCEL_RANGE_LO
        ) / (_ACCEL_RANGE_HI - _ACCEL_RANGE_LO)

        return {
            "topic_id":               topic_id,
            "batch_id":               batch_id,
            # Feature scores stored as 0–1 (NUMERIC(5,4) in schema)
            "cross_platform_score":   round(fv.cross_platform_score / 4.0, 4),
            "velocity_ratio":         round(fv.velocity_ratio, 4),       # NUMERIC(7,4)
            "acceleration_score":     round(accel_normalised, 4),
            "publication_gap_score":  round(fv.publication_gap_score / _PUB_GAP_MAX, 4),
            "sentiment_polarity":     round(fv.sentiment_score, 4),
            "time_of_day_multiplier": round(fv.time_multiplier, 3),
            "category_multiplier":    round(fv.category_multiplier, 3),
            # Weighted score stored as 0–1
            "weighted_score":         round(final_score / 100.0, 4),
            # LLM validation
            "llm_validated":          llm_called,
            "llm_confidence":         round(llm_confidence, 4) if llm_confidence is not None else None,
            "llm_reasoning":          llm_reasoning,
            # Decision
            "tier_assigned":          tier,
            "rejected":               rejected,
            "rejection_reason":       "Score below threshold" if rejected else None,
        }

    # ── Public entry point ────────────────────────────────────────────────────

    def run(
        self,
        batch_id: str,
        raw_topics: list[RawTopic],
        *,
        category_map: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Score, validate, persist, and return passing topics.

        Args:
            batch_id:     Current pipeline batch identifier.
            raw_topics:   RawTopic list from the collection node.
            category_map: Optional {keyword → category_slug} for multiplier lookup.

        Returns:
            List of dicts for topics scoring ≥ 50, sorted by score descending.
            Each dict has: topic_id, keyword, score, tier, raw_topic, feature_vector.
        """
        category_map = category_map or {}
        passing: list[dict[str, Any]] = []

        for topic in raw_topics:
            # ── 1. Feature engineering ────────────────────────────────────────
            prev = self._get_previous_batch_data(topic.keyword)
            fv = self._engineer.compute(
                topic,
                prev,
                category=category_map.get(topic.keyword),
            )

            # ── 2. Linear scoring ─────────────────────────────────────────────
            scorer_result = self._scorer.score(fv)
            score = scorer_result.raw_score

            # ── 3. LLM validation (8–12 band only) ────────────────────────────
            signal_summary = self._signal_summary(topic)
            validation = self._validator.validate(topic.keyword, score, signal_summary)
            final_score = validation.adjusted_score

            # ── 4. Tier assignment ────────────────────────────────────────────
            tier, rejected = self._assign_tier(final_score)

            log.info(
                "viral_prediction: %r  score=%.1f  tier=%s  rejected=%s",
                topic.keyword,
                final_score,
                tier,
                rejected,
            )

            # ── 5. Persist trending_topic ─────────────────────────────────────
            slug = self._make_slug(topic.keyword, batch_id)
            try:
                topic_row = db.insert_topic(
                    {
                        "batch_id":   batch_id,
                        "title":      topic.keyword.title(),
                        "slug":       slug,
                        "status":     "predicting",
                        "viral_tier": tier,
                        "viral_score": round(final_score / 100.0, 4),
                    }
                )
                topic_id: str = topic_row["id"]
            except Exception as exc:
                log.error(
                    "viral_prediction: failed to insert trending_topic for %r: %s",
                    topic.keyword,
                    exc,
                )
                continue

            # ── 6. Persist viral_prediction ───────────────────────────────────
            try:
                db.insert_viral_prediction(
                    self._build_prediction_row(
                        topic_id=topic_id,
                        batch_id=batch_id,
                        fv=fv,
                        final_score=final_score,
                        tier=tier,
                        rejected=rejected,
                        llm_called=validation.llm_called,
                        llm_verdict=validation.llm_verdict,
                        llm_reasoning=validation.llm_reasoning,
                        llm_confidence=validation.llm_confidence,
                    )
                )
            except Exception as exc:
                log.error(
                    "viral_prediction: failed to insert viral_prediction for %r: %s",
                    topic.keyword,
                    exc,
                )
                # Topic row created but prediction not saved; continue anyway

            # ── 7. Collect passing topics ─────────────────────────────────────
            if not rejected:
                passing.append(
                    {
                        "topic_id":      topic_id,
                        "keyword":       topic.keyword,
                        "score":         final_score,
                        "viral_tier":    tier,
                        "viral_score":   round(final_score / 100.0, 4),
                        "raw_topic":     topic,
                        "feature_vector": fv,
                    }
                )

        passing.sort(key=lambda r: r["score"], reverse=True)
        log.info(
            "viral_prediction: %d/%d topics passed  batch_id=%s",
            len(passing),
            len(raw_topics),
            batch_id,
        )
        return passing
