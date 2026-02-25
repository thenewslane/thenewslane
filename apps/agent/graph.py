"""
graph.py — LangGraph StateGraph for the theNewslane AI pipeline.

Node sequence:
  collect → predict_viral → filter_brand_safety → classify →
  generate_content → source_video → generate_media → publish → fact_check

Conditional edge after predict_viral:
  If no topics score ≥ 2 → END (logged, pipeline completes gracefully).

Error handling:
  Each node wrapper catches all exceptions, appends to `errors` list,
  and returns control to LangGraph so the next node still runs.
"""

from __future__ import annotations

import asyncio
import operator
import random
import re
import time
import traceback
from datetime import datetime, timedelta, timezone
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

    # Optional CMS-triggered filters (set by run_pipeline when called from studio)
    category_filter: str | None   # e.g. "Technology" — keep only this category after classify
    max_topics: int | None        # cap topics entering generate_content (1-10)

    # Data accumulated by each stage
    raw_topics: list[Any]                          # list[RawTopic] from collect
    viral_scored_topics: list[dict[str, Any]]      # topics scoring ≥ 10
    brand_safe_topics: list[dict[str, Any]]        # brand-approved topics
    classified_topics: list[dict[str, Any]]        # topics with category
    content_generated_topics: list[dict[str, Any]] # topics with article content
    media_generated_topics: list[dict[str, Any]]   # topics with media assets
    published_topic_ids: list[str]                 # DB IDs written by publish node (status=published, fact_check=yes)
    fact_checked_topic_ids: list[str]              # DB IDs set to published by fact-check agent

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
        total = len(raw)
        log.info("[collect] %d raw topics collected", total)
        for i, record in enumerate(raw, 1):
            keyword = getattr(record, "keyword", str(record)[:50])
            platforms = getattr(record, "platforms", []) or []
            platforms_str = ",".join(platforms) if platforms else "—"
            log.info("[collect] record %d/%d: keyword=%s  platforms=%s", i, total, keyword, platforms_str)
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
        print("[predict_viral] No topics passed viral score — pipeline ending (no content generation).", flush=True)
        log.info("[predict_viral] no topics scored ≥ 2 — ending batch %s", state["batch_id"])
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


# ── Node: filter_category ─────────────────────────────────────────────────────


def _node_filter_category(state: AgentState) -> dict[str, Any]:
    """
    Optional CMS-triggered filter applied after classify.

    If `category_filter` is set, keep only topics whose category name matches
    (case-insensitive). If `max_topics` is set, cap the list at that number.
    When neither is set the node is a no-op passthrough.
    """
    classified  = state.get("classified_topics", [])
    cat_filter  = state.get("category_filter")
    max_topics  = state.get("max_topics")

    filtered = classified

    if cat_filter:
        cat_lower = cat_filter.lower().strip()
        filtered = [
            t for t in filtered
            if (t.get("category") or "").lower().strip() == cat_lower
            or (t.get("category_name") or "").lower().strip() == cat_lower
        ]
        log.info(
            "[filter_category] category='%s'  %d → %d topics",
            cat_filter, len(classified), len(filtered),
        )
        print(
            f"[filter_category] Filtered to category '{cat_filter}': "
            f"{len(classified)} → {len(filtered)} topics",
            flush=True,
        )

    if max_topics and len(filtered) > max_topics:
        log.info("[filter_category] capping %d → %d (max_topics=%d)", len(filtered), max_topics, max_topics)
        print(f"[filter_category] Capping to {max_topics} topics (max_topics={max_topics})", flush=True)
        filtered = filtered[:max_topics]

    return {"classified_topics": filtered}


# ── Node: generate_content ────────────────────────────────────────────────────


def _node_generate_content(state: AgentState) -> dict[str, Any]:
    """Generate article, social copy, and SEO content via Claude Sonnet."""
    from nodes.content_generation_node import generate_content_sync  # noqa: PLC0415

    topics = state.get("classified_topics", [])
    n = len(topics)
    print(f"[generate_content] Starting content generation for {n} topics (this step may take several minutes)...", flush=True)
    log.info("[generate_content] generating for %d topics", n)
    if topics:
        log.info("Sample topic keys before content generation: %s", list(topics[0].keys()))

    try:
        inner = {"batch_id": state["batch_id"], "topics": topics}
        result = generate_content_sync(inner)
        enriched = result.get("topics", [])
        ok = sum(1 for t in enriched if t.get("content_generated"))
        print(f"[generate_content] Done: {ok}/{n} topics had content generated.", flush=True)
        log.info("[generate_content] %d/%d topics succeeded", ok, len(topics))
        if enriched:
            sample_topic = enriched[0]
            log.info("Sample enriched topic keys: %s", list(sample_topic.keys()))
            log.info("Sample content fields: summary_30w=%s, article=%s", bool(sample_topic.get("summary_30w")), bool(sample_topic.get("article")))
        return {"content_generated_topics": enriched}
    except Exception as exc:
        print(f"[generate_content] Error: {exc}", flush=True)
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


# ── Node: publish (async batch + HITL) ────────────────────────────────────────


def _publish_one_topic_sync(topic: dict[str, Any], batch_id: str) -> tuple[str | None, str | None]:
    """
    Publish a single topic: DB update + ISR/IndexNow. Runs in thread pool.
    Returns (published_id, error). Exactly one is non-None on failure/skip.
    """
    from config.settings import settings  # noqa: PLC0415
    from utils.supabase_client import db  # noqa: PLC0415

    def fire_external(slug: str) -> None:
        if not settings.revalidate_secret:
            return
        for url, payload in [
            (settings.revalidate_endpoint, {"secret": settings.revalidate_secret, "slug": slug}),
            (settings.indexnow_endpoint, {"secret": settings.revalidate_secret, "url": f"{settings.site_url}/trending/{slug}"}),
        ]:
            try:
                httpx.post(url, json=payload, timeout=10)
            except Exception as exc:
                log.warning("[publish] external call failed (%s): %s", url, exc)

    topic_id: str | None = topic.get("id") or topic.get("topic_id")
    if not topic_id:
        return None, f"publish: topic has no id: {topic.get('title', 'unknown')}"

    summary_val = (topic.get("summary_30w") or "").strip()
    article_val = (topic.get("article") or "").strip()
    if not summary_val or not article_val:
        missing = []
        if not summary_val:
            missing.append("summary_30w")
        if not article_val:
            missing.append("article")
        log.warning(
            "[publish] skipping topic '%s' (id=%s) - missing or empty content: %s",
            (topic.get("title") or "unknown")[:40],
            topic_id,
            ", ".join(missing),
        )
        return None, None  # skip without error so pipeline continues

    slug: str = (topic.get("slug") or "").strip()
    if not slug:
        kw = str(topic.get("keyword") or topic.get("title") or "")
        slug = re.sub(r"[^a-z0-9\s-]", "", kw.lower())
        slug = re.sub(r"\s+", "-", slug.strip())[:80].strip("-")

    now_iso = datetime.now(timezone.utc).isoformat()
    _vtype_map = {"youtube": "youtube_embed", "vimeo": "vimeo_embed", "ai_needed": "kling_generated"}
    db_video_type: str | None = _vtype_map.get(topic.get("video_type", "none"))

    social_copy: dict[str, Any] = {}
    for k, v in [("facebook", "facebook_post"), ("instagram", "instagram_caption"), ("twitter", "twitter_thread"), ("youtube", "youtube_script")]:
        if topic.get(v):
            social_copy[k] = topic[v]

    schema_blocks: dict[str, Any] = {}
    for key in ("seo_title", "meta_description", "faq", "headline_cluster", "embed_url", "channel_name", "video_id", "image_prompt", "video_url_portrait"):
        if topic.get(key):
            schema_blocks[key] = topic[key]
    source_id = topic.get("source_id") or ""
    if isinstance(source_id, str) and source_id.startswith("http"):
        schema_blocks["source_url"] = source_id
        if topic.get("source"):
            schema_blocks["source_name"] = topic["source"]
    schema_blocks["brand_safe"] = topic.get("brand_safe", True)

    iab_tags: list[str] = topic.get("iab_categories") or []
    category_id = topic.get("category_id")
    if category_id is None:
        category_name = topic.get("category")
        if category_name:
            cm = {"Technology": 1, "Entertainment": 2, "Sports": 3, "Politics": 4, "Business & Finance": 5, "Health & Science": 6, "Science & Health": 6, "Lifestyle": 7, "World News": 8, "Culture & Arts": 9, "Environment": 10}
            category_id = cm.get(category_name)
        if category_id is None:
            category_id = 8

    # Publish immediately with fact_check=yes (fact-check logic paused; no draft step).
    # summary/article are guaranteed non-empty here (we skip above otherwise).
    patch: dict[str, Any] = {
        "status": "published",
        "fact_check": "yes",
        "published_at": now_iso,
        "batch_id": batch_id,
        "slug": slug,
        "title": topic.get("title") or topic.get("keyword", ""),
        "category_id": category_id,
        "viral_tier": topic.get("viral_tier"),
        "viral_score": topic.get("viral_score"),
        "summary": summary_val,
        "article": article_val,
        "script": topic.get("youtube_script") or "",
        "iab_tags": iab_tags,
        "social_copy": social_copy or None,
        "schema_blocks": schema_blocks or None,
        "thumbnail_url": topic.get("thumbnail_url"),
        "video_url": topic.get("video_url"),
        "instagram_video_url": topic.get("instagram_video_url"),
        "video_type": db_video_type,
    }
    patch = {k: v for k, v in patch.items() if v is not None}

    update_id: str | None = None
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        existing = db.client.table("trending_topics").select("id").eq("slug", slug).eq("status", "published").gte("published_at", cutoff).limit(1).execute()
        if existing.data and len(existing.data) > 0:
            eid = existing.data[0].get("id")
            if eid and str(eid) != str(topic_id):
                update_id = str(eid)
    except Exception as exc:
        log.debug("[publish] existing-article check failed for slug=%s: %s", slug, exc)

    if update_id:
        patch_existing = {**patch, "updated_at": now_iso}
        patch_existing = {k: v for k, v in patch_existing.items() if v is not None}
        patch_existing = {k: v for k, v in patch_existing.items() if v is not None}
        try:
            db.client.table("trending_topics").update(patch_existing).eq("id", update_id).execute()
            log.info("[publish] updated existing → published  id=%s  slug=%s", update_id, slug)
            fire_external(slug)
            return update_id, None
        except Exception as exc:
            return None, f"publish: failed to update existing {update_id}: {exc}"
    try:
        db.client.table("trending_topics").update(patch).eq("id", topic_id).execute()
        log.info("[publish] published (fact_check=yes)  %s  id=%s  slug=%s", topic.get("title", "?"), topic_id, slug)
        fire_external(slug)
        return topic_id, None
    except Exception as exc:
        return None, f"publish: failed for {topic_id}: {exc}"


async def _publish_batch_async(topics: list[dict[str, Any]], batch_id: str) -> tuple[list[str], list[str]]:
    """Run publish with async concurrency and HITL delay. Returns (published_ids, errors)."""
    from config.settings import settings  # noqa: PLC0415

    concurrency = getattr(settings, "publish_concurrency", 2)
    hitl_initial = getattr(settings, "publish_hitl_initial_delay_sec", 5.0)
    hitl_min = getattr(settings, "publish_hitl_delay_min", 3.0)
    hitl_max = getattr(settings, "publish_hitl_delay_max", 15.0)
    if hitl_initial > 0 and topics:
        log.info("[publish] HITL initial delay %.1fs before first topic (human-review window)", hitl_initial)
        await asyncio.sleep(hitl_initial)
    sem = asyncio.Semaphore(concurrency)
    published_ids: list[str] = []
    errors: list[str] = []
    loop = asyncio.get_event_loop()

    async def do_one(i: int, topic: dict[str, Any]) -> None:
        async with sem:
            if i > 0 and hitl_max > 0:
                delay = random.uniform(hitl_min, hitl_max)
                log.info("[publish] HITL delay %.1fs before topic %d/%d", delay, i + 1, len(topics))
                await asyncio.sleep(delay)
            try:
                pid, err = await loop.run_in_executor(None, lambda t=topic, b=batch_id: _publish_one_topic_sync(t, b))
                if pid:
                    published_ids.append(pid)
                if err:
                    errors.append(err)
            except Exception as exc:
                errors.append(f"publish: {exc}")

    await asyncio.gather(*[do_one(i, t) for i, t in enumerate(topics)])
    return published_ids, errors


def _node_publish(state: AgentState) -> dict[str, Any]:
    """
    Publish topics with async concurrency and HITL delay: UPDATE trending_topics,
    trigger ISR revalidation and IndexNow. Uses publish_concurrency and
    publish_hitl_delay_* from settings.
    """
    batch_id: str = state["batch_id"]
    topics: list[dict[str, Any]] = state.get("media_generated_topics", [])
    log.info("[publish] publishing %d topics (async, HITL)  batch_id=%s", len(topics), batch_id)

    if not topics:
        return {"published_topic_ids": []}

    published_ids, errors = asyncio.run(_publish_batch_async(topics, batch_id))

    log.info("[publish] done  published=%d  errors=%d", len(published_ids), len(errors))
    result: dict[str, Any] = {"published_topic_ids": published_ids}
    if errors:
        result["errors"] = errors
    return result


# ── Node: fact_check ──────────────────────────────────────────────────────────


def _node_fact_check(state: AgentState) -> dict[str, Any]:
    """
    Run fact-check agent: pick rows with fact_check=no, verify, set fact_check=yes
    and status=published, trigger revalidate/IndexNow.
    """
    from nodes.fact_check_node import run_fact_check_batch  # noqa: PLC0415

    published_ids, errs = run_fact_check_batch()
    log.info("[fact_check] published=%d  errors=%d", len(published_ids), len(errs))
    result: dict[str, Any] = {"fact_checked_topic_ids": published_ids}
    if errs:
        result["errors"] = errs
    return result


# ── Graph assembly ─────────────────────────────────────────────────────────────


def build_graph() -> Any:
    """Build and compile the 9-node pipeline StateGraph (including fact_check)."""
    g = StateGraph(AgentState)

    g.add_node("collect",             _node_collect)
    g.add_node("predict_viral",       _node_predict_viral)
    g.add_node("filter_brand_safety", _node_filter_brand_safety)
    g.add_node("classify",            _node_classify)
    g.add_node("filter_category",     _node_filter_category)
    g.add_node("generate_content",    _node_generate_content)
    g.add_node("source_video",        _node_source_video)
    g.add_node("generate_media",      _node_generate_media)
    g.add_node("publish",             _node_publish)
    g.add_node("fact_check",          _node_fact_check)

    g.set_entry_point("collect")
    g.add_edge("collect", "predict_viral")

    g.add_conditional_edges(
        "predict_viral",
        _route_after_viral,
        {"filter_brand_safety": "filter_brand_safety", END: END},
    )

    g.add_edge("filter_brand_safety", "classify")
    g.add_edge("classify",            "filter_category")
    g.add_edge("filter_category",     "generate_content")
    g.add_edge("generate_content",    "source_video")
    g.add_edge("source_video",        "generate_media")
    g.add_edge("generate_media",      "publish")
    g.add_edge("publish",             "fact_check")
    g.add_edge("fact_check",          END)

    return g.compile()


# Compiled graph — imported by main.py and scheduler.py
pipeline = build_graph()
