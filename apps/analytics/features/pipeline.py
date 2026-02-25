"""
features/pipeline.py — Background feature aggregation pipeline.

Runs periodically to aggregate raw reader_events into the reader_features
table for ML consumption. Uses async SQLAlchemy for all DB operations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import async_session_factory
from db.models import ReaderEvent, ReaderFeatures, UserProfile
from features.engineering import compute_features

log = logging.getLogger(__name__)


async def run_feature_pipeline_loop(interval_minutes: int = 15) -> None:
    """Long-running async loop that triggers feature computation on a schedule."""
    log.info(
        "Feature pipeline loop started — interval=%d minutes", interval_minutes
    )
    while True:
        try:
            await run_feature_pipeline()
        except Exception:
            log.exception("Feature pipeline run failed")
        await asyncio.sleep(interval_minutes * 60)


async def run_feature_pipeline() -> int:
    """
    Single run: fetch users with recent events, compute features, upsert.
    Returns the number of user feature rows upserted.
    """
    async with async_session_factory() as session:
        user_ids = await _get_active_user_ids(session)

        if not user_ids:
            log.info("Feature pipeline: no active users to process")
            return 0

        count = 0
        for uid in user_ids:
            try:
                await _compute_and_upsert_user(session, uid)
                count += 1
            except Exception:
                log.exception("Failed to compute features for user_id=%s", uid)

        log.info("Feature pipeline: upserted %d user feature rows", count)
        return count


async def _get_active_user_ids(session: AsyncSession) -> list:
    """Return user IDs that have at least one event."""
    result = await session.execute(
        select(ReaderEvent.user_id)
        .where(ReaderEvent.user_id.isnot(None))
        .distinct()
    )
    return [row[0] for row in result.all()]


async def _compute_and_upsert_user(session: AsyncSession, user_id) -> None:
    """Fetch events for a user, compute features, and upsert into reader_features."""
    result = await session.execute(
        select(ReaderEvent).where(ReaderEvent.user_id == user_id)
    )
    event_rows = result.scalars().all()

    events = [
        {
            "event_type": e.event_type,
            "topic_id": str(e.topic_id) if e.topic_id else None,
            "category_id": e.category_id,
            "metadata": e.metadata or {},
            "device_type": e.device_type,
            "geo_country": e.geo_country,
            "created_at": e.created_at,
            "session_id": e.session_id,
        }
        for e in event_rows
    ]

    user_result = await session.execute(
        select(UserProfile.created_at).where(UserProfile.id == user_id)
    )
    user_row = user_result.first()
    user_created_at = user_row[0] if user_row else None

    features = compute_features(events, user_created_at)
    features["user_id"] = user_id
    features["computed_at"] = datetime.now(timezone.utc)

    stmt = pg_insert(ReaderFeatures).values(**features)
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_={
            k: stmt.excluded[k]
            for k in features
            if k != "user_id"
        },
    )
    await session.execute(stmt)
    await session.commit()
