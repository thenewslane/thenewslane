"""
backfill_recent_null_content.py — Backfill NULL summary/article for recent topics.

Use case:
  Some rows created recently may have NULL summary/article (e.g. due to a pipeline
  transient error). This script finds rows from the last N hours and fills:
    - summary (TEXT)
    - article (TEXT)

Strategy:
  - If summary is NULL: try schema_blocks.meta_description or schema_blocks.seo_title
  - If still missing OR article is NULL: regenerate via Claude (Haiku) with a small JSON

Notes:
  - Requires apps/agent/.env (ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY)
  - Safe by default with --dry-run
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)


@dataclass
class BackfillPlan:
    topic_id: str
    slug: str
    title: str
    set_summary: str | None
    set_article: str | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _schema_fallback_summary(schema_blocks: Any) -> str | None:
    if not isinstance(schema_blocks, dict):
        return None
    for key in ("meta_description", "seo_title"):
        v = schema_blocks.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _regen_summary_and_article(*, title: str, schema_blocks: Any) -> tuple[str | None, str | None]:
    """
    Regenerate minimal fields via Claude.
    Returns (summary, article).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    headline_cluster = ""
    source_url = ""
    if isinstance(schema_blocks, dict):
        headline_cluster = str(schema_blocks.get("headline_cluster") or "")
        source_url = str(schema_blocks.get("source_url") or "")

    prompt = f"""You are editing a trending-news article record for a website.
Fill ONLY these fields as valid JSON with no extra text:
{{
  "summary": "1–2 sentences, factual, no wrong years",
  "article": "a complete article body in multiple paragraphs; do not invent dates; avoid mentioning specific years unless certain"
}}

Context:
- Title: {title}
- Source URL (if any): {source_url or "—"}
- Headlines/context (if any): {headline_cluster[:1200] or "—"}

Rules:
- Return ONLY valid JSON.
- If you are not certain about a year, do NOT include a year.
"""

    resp = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1200,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    text = (resp.content[0].text if resp.content else "").strip()
    try:
        payload = json.loads(text)
    except Exception:
        log.warning("Claude returned non-JSON (%.120s...)", text)
        return None, None

    summary = payload.get("summary")
    article = payload.get("article")
    summary_out = summary.strip() if isinstance(summary, str) and summary.strip() else None
    article_out = article.strip() if isinstance(article, str) and article.strip() else None
    return summary_out, article_out


def build_plan(hours: float) -> list[BackfillPlan]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    # Fetch a bounded set and filter in Python (simpler than OR filters)
    res = (
        db.client.table("trending_topics")
        .select("id, slug, title, summary, article, schema_blocks, created_at, status, fact_check")
        .gte("created_at", cutoff)
        .order("created_at", desc=False)
        .limit(250)
        .execute()
    )
    rows: list[dict[str, Any]] = res.data or []

    plans: list[BackfillPlan] = []
    for r in rows:
        topic_id = str(r.get("id") or "")
        slug = str(r.get("slug") or "").strip()
        title = str(r.get("title") or "").strip()
        if not topic_id or not slug or not title:
            continue

        summary = r.get("summary")
        article = r.get("article")
        if summary is not None and article is not None:
            continue  # only backfill NULLs (not empty strings)

        schema_blocks = r.get("schema_blocks")
        set_summary: str | None = None
        set_article: str | None = None

        if summary is None:
            set_summary = _schema_fallback_summary(schema_blocks)

        if article is None or (summary is None and not set_summary):
            regen_summary, regen_article = _regen_summary_and_article(title=title, schema_blocks=schema_blocks)
            if summary is None:
                set_summary = set_summary or regen_summary
            if article is None:
                set_article = regen_article

        if set_summary is None and set_article is None:
            continue

        plans.append(
            BackfillPlan(
                topic_id=topic_id,
                slug=slug,
                title=title,
                set_summary=set_summary,
                set_article=set_article,
            )
        )

    return plans


def apply_plan(plans: list[BackfillPlan], *, dry_run: bool) -> None:
    if not plans:
        print("No rows to backfill.")
        return

    print(f"Backfill candidates: {len(plans)} (dry_run={dry_run})")
    for p in plans:
        print(f"- {p.slug}  id={p.topic_id}")
        if p.set_summary:
            print(f"  summary: {p.set_summary[:120]}{'…' if len(p.set_summary) > 120 else ''}")
        if p.set_article:
            print(f"  article: {len(p.set_article)} chars")

        if dry_run:
            continue

        patch: dict[str, Any] = {"updated_at": _now_iso()}
        if p.set_summary is not None:
            patch["summary"] = p.set_summary
        if p.set_article is not None:
            patch["article"] = p.set_article

        db.client.table("trending_topics").update(patch).eq("id", p.topic_id).execute()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=5.0, help="Lookback window (default: 5 hours)")
    ap.add_argument("--dry-run", action="store_true", help="Print changes without updating DB")
    args = ap.parse_args()

    print(f"Finding rows with NULL summary/article since last {args.hours}h…")
    plans = build_plan(args.hours)
    apply_plan(plans, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

