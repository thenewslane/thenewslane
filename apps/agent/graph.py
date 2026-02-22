"""
graph.py — LangGraph StateGraph for the theNewslane AI pipeline.

Node sequence:
  collect → predict_viral → filter_brand_safety → classify →
  generate_content → source_video → generate_media → publish

Conditional edge after predict_viral:
  If no topics score ≥ 10 → END (logged, pipeline completes gracefully).

Error handling:
  Each node wrapper catches all exceptions, appends to `errors` list,
  and returns control to LangGraph so the next node still runs.
"""

from __future__ import annotations

import operator
import re
import time
import traceback
from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict

import httpx
from langgraph.graph import END, StateGraph

from utils.logger import get_logger

log = get_logger(__name__)


# ── Shared pipeline state ─────────────────────────────────────────────────────


class AgentState(TypedDict):
    """Typed state threaded through every node in the pipeline."""

    batch_id: str
    run_start_time: float

    # Data accumulated by each stage
    raw_topics: list[Any]                          # list[RawTopic] from collect
    viral_scored_topics: list[dict[str, Any]]      # topics scoring ≥ 10
    brand_safe_topics: list[dict[str, Any]]        # brand-approved topics
    classified_topics: list[dict[str, Any]]        # topics with category
    content_generated_topics: list[dict[str, Any]] # topics with article content
    media_generated_topics: list[dict[str, Any]]   # topics with media assets
    published_topic_ids: list[str]                 # DB IDs of published topics

    # Errors are appended (reducer), never replaced, across all nodes
    errors: Annotated[list[str], operator.add]


# ── Node: collect ─────────────────────────────────────────────────────────────


def _node_collect(state: AgentState) -> dict[str, Any]:
    """Collect trending signals from Twitter, Google Trends, Reddit + NewsAPI."""
    from nodes.signal_collector import collect_signals  # noqa: PLC0415

    log.info("[collect] starting  batch_id=%s", state["batch_id"])
    try:
        result = collect_signals({"batch_id": state["batch_id"]})
        raw = result.get("raw_signals", [])
        log.info("[collect] %d raw topics collected", len(raw))
        return {"raw_topics": raw}
    except Exception as exc:
        msg = f"collect: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"raw_topics": [], "errors": [msg]}


# ── Node: predict_viral ───────────────────────────────────────────────────────


def _node_predict_viral(state: AgentState) -> dict[str, Any]:
    """Score raw topics; only keep those scoring ≥ 50."""
    from nodes.viral_predictor import predict_virality  # noqa: PLC0415

    log.info("[predict_viral] scoring %d topics  batch_id=%s",
             len(state.get("raw_topics", [])), state["batch_id"])
    try:
        inner = {
            "batch_id":   state["batch_id"],
            "raw_signals": state.get("raw_topics", []),
        }
        result = predict_virality(inner)
        passing: list[dict[str, Any]] = result.get("topics", [])

        # Normalise field names so downstream nodes have consistent keys
        normalised: list[dict[str, Any]] = []
        for t in passing:
            normalised.append({
                **t,
                # `id` = DB UUID created by predict_virality
                "id":             t.get("id") or t.get("topic_id"),
                # `title` = title-cased keyword (or existing title)
                "title":          t.get("title") or str(t.get("keyword", "")).title(),
                "headline_cluster": t.get("headline_cluster", ""),
            })

        log.info("[predict_viral] %d topics passed", len(normalised))
        return {"viral_scored_topics": normalised}
    except Exception as exc:
        msg = f"predict_viral: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"viral_scored_topics": [], "errors": [msg]}


# ── Conditional: early-exit if no viral topics ────────────────────────────────


def _route_after_viral(state: AgentState) -> str:
    """Route to filter_brand_safety or END depending on viral results."""
    if not state.get("viral_scored_topics"):
        log.info("[predict_viral] no topics scored ≥ 10 — ending batch %s", state["batch_id"])
        return END  # type: ignore[return-value]
    return "filter_brand_safety"


# ── Node: filter_brand_safety ─────────────────────────────────────────────────


def _node_filter_brand_safety(state: AgentState) -> dict[str, Any]:
    """Run three-tier brand safety checks on viral-scored topics."""
    from nodes.brand_safety import check_brand_safety  # noqa: PLC0415

    topics = state.get("viral_scored_topics", [])
    log.info("[filter_brand_safety] checking %d topics", len(topics))
    try:
        inner = {
            "batch_id":       state["batch_id"],
            "topics":         topics,
            "topics_rejected": 0,
        }
        result = check_brand_safety(inner)
        safe = result.get("topics", [])
        log.info("[filter_brand_safety] %d topics approved", len(safe))
        return {"brand_safe_topics": safe}
    except Exception as exc:
        msg = f"filter_brand_safety: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"brand_safe_topics": [], "errors": [msg]}


# ── Node: classify ────────────────────────────────────────────────────────────


def _node_classify(state: AgentState) -> dict[str, Any]:
    """Classify brand-safe topics into content categories via Claude Haiku."""
    from nodes.classification_node import classify_topics  # noqa: PLC0415

    topics = state.get("brand_safe_topics", [])
    log.info("[classify] classifying %d topics", len(topics))
    try:
        inner = {"batch_id": state["batch_id"], "topics": topics}
        result = classify_topics(inner)
        classified = result.get("topics", [])
        log.info("[classify] %d topics classified", len(classified))
        return {"classified_topics": classified}
    except Exception as exc:
        msg = f"classify: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        # Pass topics through without classification on error
        return {"classified_topics": topics, "errors": [msg]}


# ── Node: generate_content ────────────────────────────────────────────────────


def _node_generate_content(state: AgentState) -> dict[str, Any]:
    """Generate article, social copy, and SEO content via Claude Sonnet."""
    from nodes.content_generation_node import generate_content_sync  # noqa: PLC0415

    topics = state.get("classified_topics", [])
    log.info("[generate_content] generating for %d topics", len(topics))
    try:
        inner = {"batch_id": state["batch_id"], "topics": topics}
        result = generate_content_sync(inner)
        enriched = result.get("topics", [])
        ok = sum(1 for t in enriched if t.get("content_generated"))
        log.info("[generate_content] %d/%d topics succeeded", ok, len(topics))
        return {"content_generated_topics": enriched}
    except Exception as exc:
        msg = f"generate_content: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"content_generated_topics": topics, "errors": [msg]}


# ── Node: source_video ────────────────────────────────────────────────────────


def _node_source_video(state: AgentState) -> dict[str, Any]:
    """Source existing YouTube/Vimeo videos for each topic."""
    from nodes.video_sourcing_node import source_videos  # noqa: PLC0415

    topics = state.get("content_generated_topics", [])
    log.info("[source_video] sourcing videos for %d topics", len(topics))
    try:
        inner = {"batch_id": state["batch_id"], "topics": topics}
        result = source_videos(inner)
        sourced = result.get("topics", [])
        found = sum(1 for t in sourced if t.get("video_type") in ("youtube", "vimeo"))
        log.info("[source_video] %d/%d topics have existing video", found, len(topics))
        # Store in media_generated_topics so generate_media picks them up
        return {"media_generated_topics": sourced}
    except Exception as exc:
        msg = f"source_video: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"media_generated_topics": topics, "errors": [msg]}


# ── Node: generate_media ──────────────────────────────────────────────────────


def _node_generate_media(state: AgentState) -> dict[str, Any]:
    """Generate thumbnails (Flux) and AI videos (Kling) via Replicate."""
    from nodes.media_generation_node import generate_media  # noqa: PLC0415

    topics = state.get("media_generated_topics", [])
    log.info("[generate_media] generating media for %d topics", len(topics))
    try:
        inner = {"batch_id": state["batch_id"], "topics": topics}
        result = generate_media(inner)
        with_media = result.get("topics", [])
        ok = sum(1 for t in with_media if t.get("media_generated"))
        log.info("[generate_media] %d/%d topics have media", ok, len(topics))
        return {"media_generated_topics": with_media}
    except Exception as exc:
        msg = f"generate_media: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"media_generated_topics": topics, "errors": [msg]}


# ── Node: publish ─────────────────────────────────────────────────────────────


def _node_publish(state: AgentState) -> dict[str, Any]:
    """
    Publish each topic: UPDATE the trending_topics row (created by predict_viral)
    with all generated content/media, set status='published', then trigger ISR
    revalidation and IndexNow.
    """
    from config.settings import settings  # noqa: PLC0415
    from utils.supabase_client import db  # noqa: PLC0415

    batch_id: str = state["batch_id"]
    topics: list[dict[str, Any]] = state.get("media_generated_topics", [])
    log.info("[publish] publishing %d topics  batch_id=%s", len(topics), batch_id)

    published_ids: list[str] = []
    errors: list[str] = []

    def _fire_external(slug: str) -> None:
        """Best-effort ISR revalidation + IndexNow (sync, non-blocking)."""
        if not settings.revalidate_secret:
            return
        for url, payload in [
            (settings.revalidate_endpoint,
             {"secret": settings.revalidate_secret, "slug": slug}),
            (settings.indexnow_endpoint,
             {"secret": settings.revalidate_secret,
              "url": f"{settings.site_url}/trending/{slug}"}),
        ]:
            try:
                httpx.post(url, json=payload, timeout=10)
            except Exception as exc:
                log.warning("[publish] external call failed (%s): %s", url, exc)

    for topic in topics:
        topic_id: str | None = topic.get("id") or topic.get("topic_id")
        if not topic_id:
            err = f"publish: topic has no id: {topic.get('title', 'unknown')}"
            log.error(err)
            errors.append(err)
            continue
        
        # Skip topics without essential content - don't publish empty articles
        if not topic.get("summary_16w") or not topic.get("article_50w"):
            title = topic.get("title", "unknown")[:30]
            log.warning(f"[publish] skipping topic '{title}' - missing content (summary_16w or article_50w)")
            continue

        # Determine slug: prefer content-generated, fall back to keyword-based
        slug: str = (topic.get("slug") or "").strip()
        if not slug:
            kw = str(topic.get("keyword") or topic.get("title") or "")
            slug = re.sub(r"[^a-z0-9\s-]", "", kw.lower())
            slug = re.sub(r"\s+", "-", slug.strip())[:80].strip("-")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Map video_type to the DB CHECK constraint values
        _vtype_map = {
            "youtube": "youtube_embed",
            "vimeo":   "vimeo_embed",
            "ai_needed": "kling_generated",
        }
        raw_vtype = topic.get("video_type", "none")
        db_video_type: str | None = _vtype_map.get(raw_vtype)  # None for "none"/unknown

        # Bundle social content into social_copy JSONB column
        social_copy: dict[str, Any] = {}
        if topic.get("facebook_post"):
            social_copy["facebook"] = topic["facebook_post"]
        if topic.get("instagram_caption"):
            social_copy["instagram"] = topic["instagram_caption"]
        if topic.get("twitter_thread"):
            social_copy["twitter"] = topic["twitter_thread"]
        if topic.get("youtube_script"):
            social_copy["youtube"] = topic["youtube_script"]

        # Bundle extra metadata into schema_blocks JSONB column
        schema_blocks: dict[str, Any] = {}
        for key in ("seo_title", "meta_description", "faq", "headline_cluster",
                    "embed_url", "channel_name", "video_id", "image_prompt",
                    "video_url_portrait"):
            if topic.get(key):
                schema_blocks[key] = topic[key]

        # Convert iab_categories list → iab_tags TEXT[]
        iab_tags: list[str] = topic.get("iab_categories") or []

        patch: dict[str, Any] = {
            "status":       "published",
            "published_at": now_iso,
            "batch_id":     batch_id,
            "slug":         slug,
            "title":        topic.get("title") or topic.get("keyword", ""),
            "viral_tier":   topic.get("viral_tier"),
            "viral_score":  topic.get("viral_score"),
            # Content fields — mapped to actual schema columns
            "summary":      topic.get("summary_16w") or "",
            "article":      topic.get("article_50w") or "",
            "script":       topic.get("youtube_script") or "",
            "iab_tags":     iab_tags,
            "social_copy":  social_copy or None,
            "schema_blocks": schema_blocks or None,
            # Media fields
            "thumbnail_url": topic.get("thumbnail_url"),
            "video_url":     topic.get("video_url"),
            "video_type":    db_video_type,
        }
        # Strip None values so we don't overwrite nullable DB columns with null
        patch = {k: v for k, v in patch.items() if v is not None}

        try:
            db.client.table("trending_topics").update(patch).eq("id", topic_id).execute()
            published_ids.append(topic_id)
            log.info("[publish] published %s  id=%s  slug=%s",
                     topic.get("title", "?"), topic_id, slug)
            _fire_external(slug)
        except Exception as exc:
            err = f"publish: failed for {topic_id}: {exc}"
            log.error(err)
            errors.append(err)

    log.info("[publish] done  published=%d  errors=%d", len(published_ids), len(errors))
    result: dict[str, Any] = {"published_topic_ids": published_ids}
    if errors:
        result["errors"] = errors
    return result


# ── Graph assembly ─────────────────────────────────────────────────────────────


def build_graph() -> Any:
    """Build and compile the 8-node pipeline StateGraph."""
    g = StateGraph(AgentState)

    g.add_node("collect",             _node_collect)
    g.add_node("predict_viral",       _node_predict_viral)
    g.add_node("filter_brand_safety", _node_filter_brand_safety)
    g.add_node("classify",            _node_classify)
    g.add_node("generate_content",    _node_generate_content)
    g.add_node("source_video",        _node_source_video)
    g.add_node("generate_media",      _node_generate_media)
    g.add_node("publish",             _node_publish)

    g.set_entry_point("collect")
    g.add_edge("collect", "predict_viral")

    g.add_conditional_edges(
        "predict_viral",
        _route_after_viral,
        {"filter_brand_safety": "filter_brand_safety", END: END},
    )

    g.add_edge("filter_brand_safety", "classify")
    g.add_edge("classify",            "generate_content")
    g.add_edge("generate_content",    "source_video")
    g.add_edge("source_video",        "generate_media")
    g.add_edge("generate_media",      "publish")
    g.add_edge("publish",             END)

    return g.compile()


# Compiled graph — imported by main.py and scheduler.py
pipeline = build_graph()
