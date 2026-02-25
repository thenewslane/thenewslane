"""
cache/redis_client.py — Redis connection and typed get/set helpers.

Key patterns:
    pred:{prediction_type}:{user_id}   TTL 300s (propensity)
    pred:persona:{user_id}             TTL 900s
    pred:recommendation:{user_id}      TTL 600s
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from config.settings import settings

log = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


def _get_pool() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


class RedisCache:
    """Thin async wrapper with JSON serialization."""

    def __init__(self) -> None:
        self._r = _get_pool()

    async def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await self._r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            log.warning("Redis GET failed for key=%s, treating as miss", key)
            return None

    async def set_json(
        self, key: str, value: dict[str, Any], ttl: int = 300
    ) -> None:
        try:
            await self._r.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception:
            log.warning("Redis SET failed for key=%s", key)

    async def delete(self, key: str) -> None:
        try:
            await self._r.delete(key)
        except Exception:
            log.warning("Redis DELETE failed for key=%s", key)

    async def invalidate_user(self, user_id: str) -> None:
        """Remove all cached predictions for a user."""
        for pred_type in ("subscribe", "churn", "register", "ltv", "persona", "recommendation"):
            await self.delete(f"pred:{pred_type}:{user_id}")
