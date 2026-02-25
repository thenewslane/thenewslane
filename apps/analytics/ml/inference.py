"""
ml/inference.py — Model loader and real-time prediction engine.

Loads .joblib model artifacts from disk, runs inference against user
features, and returns prediction results with explainability metadata.
Handles cold-start fallbacks for unknown users.
"""

from __future__ import annotations

import json
import logging
from glob import glob
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.models import ReaderEvent, ReaderFeatures, ReaderPersona, TrendingTopic
from ml.explainability import get_top_feature_importances

log = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(settings.model_artifacts_dir)

PROPENSITY_FEATURES = [
    "session_count",
    "total_pageviews",
    "articles_read_last_7d",
    "articles_read_last_30d",
    "avg_time_on_page_sec",
    "avg_scroll_depth_pct",
    "newsletter_open_rate",
    "total_paywall_hits",
    "total_shares",
    "days_since_registration",
    "days_since_last_visit",
    "visit_frequency_weekly",
]

LTV_FEATURES = PROPENSITY_FEATURES + ["is_subscriber"]

MONTHLY_SUB_REVENUE = 9.99
AD_RPM = 3.50
AVG_ADS_PER_PAGEVIEW = 2


class ModelInference:
    """Loads model artifacts and provides prediction methods."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def _load_latest(self, prefix: str) -> dict[str, Any] | None:
        """Load the most recent .joblib artifact matching the given prefix."""
        if prefix in self._cache:
            return self._cache[prefix]

        pattern = str(ARTIFACTS_DIR / f"{prefix}*.joblib")
        files = sorted(glob(pattern), reverse=True)
        if not files:
            log.warning("No model artifact found for prefix=%s", prefix)
            return None

        artifact = joblib.load(files[0])
        self._cache[prefix] = artifact
        log.info("Loaded model artifact: %s", files[0])
        return artifact

    async def _get_user_features(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Fetch computed features for a user from reader_features."""
        import uuid

        result = await session.execute(
            select(ReaderFeatures).where(
                ReaderFeatures.user_id == uuid.UUID(user_id)
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        return {
            "session_count": row.session_count or 0,
            "total_pageviews": row.total_pageviews or 0,
            "articles_read_last_7d": row.articles_read_last_7d or 0,
            "articles_read_last_30d": row.articles_read_last_30d or 0,
            "avg_time_on_page_sec": float(row.avg_time_on_page_sec or 0),
            "avg_scroll_depth_pct": float(row.avg_scroll_depth_pct or 0),
            "newsletter_open_rate": float(row.newsletter_open_rate or 0),
            "total_paywall_hits": row.total_paywall_hits or 0,
            "total_shares": row.total_shares or 0,
            "days_since_registration": row.days_since_registration or 0,
            "days_since_last_visit": row.days_since_last_visit or 0,
            "visit_frequency_weekly": float(row.visit_frequency_weekly or 0),
            "is_subscriber": 1 if row.is_subscriber else 0,
            "category_distribution": row.category_distribution or {},
            "top_category_id": row.top_category_id,
        }

    async def predict_propensity(
        self, user_id: str, propensity_type: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Run propensity prediction for a user."""
        artifact = self._load_latest(f"propensity_{propensity_type}")
        if artifact is None:
            return await self._cold_start_propensity(user_id, propensity_type, session)

        features = await self._get_user_features(user_id, session)
        if features is None:
            return await self._cold_start_propensity(user_id, propensity_type, session)

        model = artifact["model"]
        feature_cols = artifact["feature_columns"]

        X = np.array([[features.get(f, 0) for f in feature_cols]])
        proba = model.predict_proba(X)[0]
        score = float(proba[1]) if len(proba) > 1 else float(proba[0])

        top_features = get_top_feature_importances(model, feature_cols, X)

        return {
            "user_id": user_id,
            "type": propensity_type,
            "score": round(score, 4),
            "confidence": round(min(score, 1.0 - score) * 2, 4),
            "top_features": top_features,
            "model_version": artifact["model_version"],
        }

    async def predict_ltv(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Run LTV prediction for a user."""
        artifact = self._load_latest("ltv")
        if artifact is None:
            return await self._cold_start_ltv(user_id, session)

        features = await self._get_user_features(user_id, session)
        if features is None:
            return await self._cold_start_ltv(user_id, session)

        model = artifact["model"]
        feature_cols = artifact["feature_columns"]

        X = np.array([[features.get(f, 0) for f in feature_cols]])
        predicted = float(model.predict(X)[0])
        predicted = max(predicted, 0.0)

        is_sub = features.get("is_subscriber", 0)
        sub_rev = MONTHLY_SUB_REVENUE * 12 * is_sub
        ad_rev = max(predicted - sub_rev, 0.0)

        top_features = get_top_feature_importances(model, feature_cols, X)

        return {
            "user_id": user_id,
            "predicted_ltv_12m": round(predicted, 2),
            "breakdown": {
                "subscription": round(sub_rev, 2),
                "ad_revenue": round(ad_rev, 2),
            },
            "top_features": top_features,
            "model_version": artifact["model_version"],
        }

    async def predict_recommendation(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Generate top-3 article recommendations and next-best-offer."""
        import uuid

        features = await self._get_user_features(user_id, session)
        artifact = self._load_latest("recommender")

        if features is None and artifact is None:
            return await self._cold_start_recommendation(user_id, session)

        # Get recent published articles
        result = await session.execute(
            select(TrendingTopic)
            .where(TrendingTopic.status == "published")
            .order_by(TrendingTopic.published_at.desc())
            .limit(50)
        )
        articles = result.scalars().all()

        if not articles:
            return {
                "user_id": user_id,
                "articles": [],
                "offer": None,
            }

        # Score articles
        scored = []
        user_cat_dist = (features or {}).get("category_distribution", {})

        for article in articles:
            score = 0.0
            # Category affinity
            cat_id = str(article.category_id) if article.category_id else None
            if cat_id and cat_id in user_cat_dist:
                score += float(user_cat_dist[cat_id]) * 0.5
            # Viral score bonus
            score += float(article.viral_score or 0) * 0.3
            # Recency bonus
            if article.published_at:
                from datetime import datetime, timezone
                hours_old = (datetime.now(timezone.utc) - article.published_at).total_seconds() / 3600
                recency = max(0, 1.0 - hours_old / 168)  # decay over 1 week
                score += recency * 0.2

            scored.append({
                "topic_id": str(article.id),
                "title": article.title,
                "slug": article.slug,
                "category": article.category.name if article.category_id else None,
                "score": round(score, 4),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        top_3 = scored[:3]

        # Next best offer
        offer = self._determine_offer(features)

        return {
            "user_id": user_id,
            "articles": top_3,
            "offer": offer,
        }

    async def predict_persona(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Look up pre-computed persona for a user."""
        import uuid

        result = await session.execute(
            select(ReaderPersona).where(
                ReaderPersona.user_id == uuid.UUID(user_id)
            )
        )
        persona = result.scalar_one_or_none()

        if persona is None:
            return await self._cold_start_persona(user_id, session)

        return {
            "user_id": user_id,
            "persona": persona.persona_name,
            "confidence": float(persona.confidence or 0),
            "traits": persona.traits or {},
            "model_version": persona.model_version,
        }

    def _determine_offer(self, features: dict[str, Any] | None) -> dict[str, str] | None:
        """Determine the next best marketing offer based on user features."""
        if features is None:
            return {"type": "newsletter_signup", "reason": "New visitor — capture email"}

        paywall_hits = features.get("total_paywall_hits", 0)
        is_subscriber = features.get("is_subscriber", 0)
        visit_freq = features.get("visit_frequency_weekly", 0)
        newsletter_rate = features.get("newsletter_open_rate", 0)

        if is_subscriber:
            return None  # already subscribed

        if paywall_hits >= 3 and visit_freq >= 3:
            return {
                "type": "discount_50",
                "reason": f"High engagement ({paywall_hits} paywall hits, {visit_freq:.0f} visits/week) — likely to convert with discount",
            }

        if paywall_hits >= 1:
            return {
                "type": "free_trial",
                "reason": f"Showed subscription interest ({paywall_hits} paywall hits) — offer trial",
            }

        if newsletter_rate < 0.1 and visit_freq >= 2:
            return {
                "type": "newsletter_signup",
                "reason": "Regular visitor not on newsletter — capture email first",
            }

        return None

    # ── Cold-start fallbacks ──────────────────────────────────────────────

    async def _cold_start_propensity(
        self, user_id: str, propensity_type: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Return a low-confidence baseline propensity score."""
        return {
            "user_id": user_id,
            "type": propensity_type,
            "score": 0.1 if propensity_type == "churn" else 0.05,
            "confidence": 0.1,
            "top_features": [],
            "model_version": "cold_start",
        }

    async def _cold_start_ltv(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Return a baseline LTV estimate for unknown users."""
        return {
            "user_id": user_id,
            "predicted_ltv_12m": 2.50,
            "breakdown": {"subscription": 0.0, "ad_revenue": 2.50},
            "top_features": [],
            "model_version": "cold_start",
        }

    async def _cold_start_recommendation(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Fall back to globally trending articles for unknown users."""
        result = await session.execute(
            select(TrendingTopic)
            .where(TrendingTopic.status == "published")
            .order_by(TrendingTopic.viral_score.desc())
            .limit(3)
        )
        articles = result.scalars().all()

        top_3 = [
            {
                "topic_id": str(a.id),
                "title": a.title,
                "slug": a.slug,
                "category": a.category.name if a.category_id else None,
                "score": float(a.viral_score or 0),
            }
            for a in articles
        ]

        return {
            "user_id": user_id,
            "articles": top_3,
            "offer": {"type": "newsletter_signup", "reason": "New visitor — capture email"},
        }

    async def _cold_start_persona(
        self, user_id: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Return a default persona for users without enough data."""
        return {
            "user_id": user_id,
            "persona": "New Visitor",
            "confidence": 0.0,
            "traits": {},
            "model_version": "cold_start",
        }
