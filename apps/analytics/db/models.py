"""
db/models.py — SQLAlchemy ORM models for the analytics service.

Maps all analytics tables (reader_events, reader_features, reader_predictions,
reader_personas) and references existing tables (user_profiles, categories,
trending_topics) for foreign-key relationships.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ── Referenced existing tables (read-only reflections) ────────────────────────


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "public", "extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    features: Mapped[ReaderFeatures | None] = relationship(
        "ReaderFeatures", back_populates="user", uselist=False
    )
    persona: Mapped[ReaderPersona | None] = relationship(
        "ReaderPersona", back_populates="user", uselist=False
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "public", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)


class TrendingTopic(Base):
    __tablename__ = "trending_topics"
    __table_args__ = {"schema": "public", "extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("public.categories.id")
    )
    viral_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    viral_tier: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, default="pending")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[Category | None] = relationship("Category", lazy="joined")


# ── Analytics tables ──────────────────────────────────────────────────────────


class ReaderEvent(Base):
    __tablename__ = "reader_events"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public.user_profiles.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.trending_topics.id", ondelete="SET NULL"),
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("public.categories.id", ondelete="SET NULL")
    )
    metadata: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    device_type: Mapped[str | None] = mapped_column(Text)
    geo_country: Mapped[str | None] = mapped_column(Text)
    referrer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class ReaderFeatures(Base):
    __tablename__ = "reader_features"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.user_profiles.id", ondelete="CASCADE"),
        unique=True,
    )
    session_id: Mapped[str | None] = mapped_column(Text)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    total_pageviews: Mapped[int] = mapped_column(Integer, default=0)
    articles_read_last_7d: Mapped[int] = mapped_column(Integer, default=0)
    articles_read_last_30d: Mapped[int] = mapped_column(Integer, default=0)
    avg_time_on_page_sec: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    avg_scroll_depth_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    top_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("public.categories.id")
    )
    category_distribution: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    newsletter_open_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    total_paywall_hits: Mapped[int] = mapped_column(Integer, default=0)
    total_shares: Mapped[int] = mapped_column(Integer, default=0)
    days_since_registration: Mapped[int | None] = mapped_column(Integer)
    days_since_last_visit: Mapped[int | None] = mapped_column(Integer)
    visit_frequency_weekly: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    device_type_primary: Mapped[str | None] = mapped_column(Text)
    geo_country: Mapped[str | None] = mapped_column(Text)
    is_subscriber: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    user: Mapped[UserProfile | None] = relationship(
        "UserProfile", back_populates="features"
    )


class ReaderPrediction(Base):
    __tablename__ = "reader_predictions"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public.user_profiles.id", ondelete="CASCADE")
    )
    session_id: Mapped[str | None] = mapped_column(Text)
    prediction_type: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    top_features: Mapped[dict | None] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )


class ReaderPersona(Base):
    __tablename__ = "reader_personas"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.user_profiles.id", ondelete="CASCADE"),
        unique=True,
    )
    persona_name: Mapped[str] = mapped_column(Text, nullable=False)
    persona_slug: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_id: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    traits: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()")
    )

    user: Mapped[UserProfile | None] = relationship(
        "UserProfile", back_populates="persona"
    )
