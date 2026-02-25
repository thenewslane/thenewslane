"""
api/persona.py — Persona prediction endpoint.

GET /api/v1/predict/persona/{user_id}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cache.redis_client import RedisCache
from db.engine import get_session
from ml.inference import ModelInference

router = APIRouter(prefix="/predict", tags=["personas"])


class PersonaResponse(BaseModel):
    user_id: str
    persona: str
    confidence: float
    traits: dict
    model_version: str
    cached: bool = False


@router.get("/persona/{user_id}", response_model=PersonaResponse)
async def predict_persona(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    cache = RedisCache()
    cache_key = f"pred:persona:{user_id}"

    cached = await cache.get_json(cache_key)
    if cached:
        cached["cached"] = True
        return PersonaResponse(**cached)

    inference = ModelInference()
    result = await inference.predict_persona(user_id, session)

    if result is None:
        raise HTTPException(
            status_code=404, detail="User not found or no persona computed"
        )

    await cache.set_json(cache_key, result, ttl=900)
    return PersonaResponse(**result, cached=False)
