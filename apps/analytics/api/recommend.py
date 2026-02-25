"""
api/recommend.py — Recommendation endpoints.

GET /api/v1/predict/recommendation/{user_id}
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cache.redis_client import RedisCache
from db.engine import get_session
from ml.inference import ModelInference

router = APIRouter(prefix="/predict", tags=["recommendations"])


class ArticleSuggestion(BaseModel):
    topic_id: str
    title: str
    slug: str
    category: str | None = None
    score: float


class OfferSuggestion(BaseModel):
    type: str
    reason: str


class RecommendationResponse(BaseModel):
    user_id: str
    articles: list[ArticleSuggestion]
    offer: OfferSuggestion | None = None
    cached: bool = False


@router.get("/recommendation/{user_id}", response_model=RecommendationResponse)
async def predict_recommendation(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    cache = RedisCache()
    cache_key = f"pred:recommendation:{user_id}"

    cached = await cache.get_json(cache_key)
    if cached:
        cached["cached"] = True
        return RecommendationResponse(**cached)

    inference = ModelInference()
    result = await inference.predict_recommendation(user_id, session)

    if result is None:
        raise HTTPException(
            status_code=404, detail="User not found or no features available"
        )

    await cache.set_json(cache_key, result, ttl=600)
    return RecommendationResponse(**result, cached=False)
