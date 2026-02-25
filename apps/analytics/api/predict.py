"""
api/predict.py — Propensity and LTV prediction endpoints.

GET /api/v1/predict/propensity/{user_id}?type=subscribe|churn|register
GET /api/v1/predict/ltv/{user_id}
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cache.redis_client import RedisCache
from db.engine import get_session
from ml.inference import ModelInference

router = APIRouter(prefix="/predict", tags=["predictions"])


class PropensityType(str, Enum):
    SUBSCRIBE = "subscribe"
    CHURN = "churn"
    REGISTER = "register"


class FeatureImportance(BaseModel):
    name: str
    importance: float
    direction: str


class PropensityResponse(BaseModel):
    user_id: str
    type: str
    score: float
    confidence: float
    top_features: list[FeatureImportance]
    model_version: str
    cached: bool = False


class LTVResponse(BaseModel):
    user_id: str
    predicted_ltv_12m: float
    breakdown: dict[str, float]
    top_features: list[FeatureImportance]
    model_version: str
    cached: bool = False


@router.get("/propensity/{user_id}", response_model=PropensityResponse)
async def predict_propensity(
    user_id: str,
    type: PropensityType = Query(..., description="Propensity type"),
    session: AsyncSession = Depends(get_session),
):
    cache = RedisCache()
    cache_key = f"pred:{type.value}:{user_id}"

    cached = await cache.get_json(cache_key)
    if cached:
        cached["cached"] = True
        return PropensityResponse(**cached)

    inference = ModelInference()
    result = await inference.predict_propensity(user_id, type.value, session)

    if result is None:
        raise HTTPException(status_code=404, detail="User not found or no features available")

    await cache.set_json(cache_key, result, ttl=300)
    return PropensityResponse(**result, cached=False)


@router.get("/ltv/{user_id}", response_model=LTVResponse)
async def predict_ltv(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    cache = RedisCache()
    cache_key = f"pred:ltv:{user_id}"

    cached = await cache.get_json(cache_key)
    if cached:
        cached["cached"] = True
        return LTVResponse(**cached)

    inference = ModelInference()
    result = await inference.predict_ltv(user_id, session)

    if result is None:
        raise HTTPException(status_code=404, detail="User not found or no features available")

    await cache.set_json(cache_key, result, ttl=300)
    return LTVResponse(**result, cached=False)
