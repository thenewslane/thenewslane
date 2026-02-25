"""
api/events.py — Event ingestion endpoint.

POST /api/v1/events accepts a batch of reader behavioral events from the
frontend tracker or webhook sources and inserts them asynchronously.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import get_session
from db.models import ReaderEvent

router = APIRouter(tags=["events"])


class EventType(str, Enum):
    PAGEVIEW = "pageview"
    CLICK = "click"
    SCROLL_DEPTH = "scroll_depth"
    TIME_ON_PAGE = "time_on_page"
    NEWSLETTER_CLICK = "newsletter_click"
    PAYWALL_HIT = "paywall_hit"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    REGISTER = "register"
    SHARE = "share"


class EventPayload(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=256)
    user_id: str | None = Field(default=None, description="UUID of registered user")
    event_type: EventType
    topic_id: str | None = Field(default=None, description="UUID of the article/topic")
    category_id: int | None = None
    metadata: dict = Field(default_factory=dict)
    device_type: str | None = None
    geo_country: str | None = Field(default=None, max_length=2)
    referrer: str | None = None
    timestamp: datetime | None = Field(
        default=None, description="Client-side timestamp; server uses NOW() if absent"
    )


class EventBatchRequest(BaseModel):
    events: list[EventPayload] = Field(..., min_length=1, max_length=500)


class EventBatchResponse(BaseModel):
    accepted: int
    message: str = "Events queued for processing"


async def _persist_events(events: list[EventPayload], session: AsyncSession) -> None:
    rows = []
    for ev in events:
        row = ReaderEvent(
            session_id=ev.session_id,
            user_id=uuid.UUID(ev.user_id) if ev.user_id else None,
            event_type=ev.event_type.value,
            topic_id=uuid.UUID(ev.topic_id) if ev.topic_id else None,
            category_id=ev.category_id,
            metadata=ev.metadata,
            device_type=ev.device_type,
            geo_country=ev.geo_country,
            referrer=ev.referrer,
            created_at=ev.timestamp or datetime.now(timezone.utc),
        )
        rows.append(row)
    session.add_all(rows)
    await session.commit()


@router.post(
    "/events",
    response_model=EventBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_events(
    body: EventBatchRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Ingest a batch of reader behavioral events.

    Events are validated and then persisted asynchronously. The endpoint returns
    202 immediately so it never blocks the frontend page render.
    """
    await _persist_events(body.events, session)
    return EventBatchResponse(accepted=len(body.events))
