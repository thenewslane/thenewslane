"""
backfill_recent_null_content.py — Backfill NULL summary/article for recent or all topics.

Use case:
  Rows with NULL/empty summary or article should be filled before fact-check runs.
  Fact-check runs only on rows where both summary and article are populated.

  - Use --all to update all rows where summary or article is null/empty (scans up to --limit).
  - Use --id 759bc8 to fix a specific topic by id (prefix match).

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
    # Be robust: if Claude wraps JSON with extra text, extract the JSON object.
    candidate = text
    if "{" in text and "}" in text:
        candidate = text[text.find("{") : text.rfind("}") + 1]
    try:
        payload = json.loads(candidate)
    except Exception:
        log.warning("Claude returned non-JSON (%.180s...)", text)
        return None, None

    summary = payload.get("summary")
    article = payload.get("article")
    summary_out = summary.strip() if isinstance(summary, str) and summary.strip() else None
    article_out = article.strip() if isinstance(article, str) and article.strip() else None
    return summary_out, article_out


def _row_needs_backfill(r: dict[str, Any]) -> tuple[bool, bool]:
    summary = r.get("summary")
    article = r.get("article")
    summary_missing = summary is None or (isinstance(summary, str) and not summary.strip())
    article_missing = article is None or (isinstance(article, str) and not article.strip())
    return summary_missing, article_missing


def _plan_for_row(r: dict[str, Any], use_llm: bool) -> BackfillPlan | None:
    topic_id = str(r.get("id") or "")
    slug = str(r.get("slug") or "").strip()
    title = str(r.get("title") or "").strip()
    if not topic_id or not slug or not title:
        return None

    summary_missing, article_missing = _row_needs_backfill(r)
    if not summary_missing and not article_missing:
        return None

    schema_blocks = r.get("schema_blocks")
    set_summary: str | None = None
    set_article: str | None = None

    if summary_missing:
        set_summary = _schema_fallback_summary(schema_blocks)

    if use_llm and (article_missing or (summary_missing and not set_summary)):
        regen_summary, regen_article = _regen_summary_and_article(title=title, schema_blocks=schema_blocks)
        if summary_missing:
            set_summary = set_summary or regen_summary
        if article_missing:
            set_article = regen_article

    if set_summary is None and set_article is None:
        return None

    return BackfillPlan(
        topic_id=topic_id,
        slug=slug,
        title=title,
        set_summary=set_summary,
        set_article=set_article,
    )


def build_plan(hours: float | None, *, limit: int, use_llm: bool, id_prefix: str | None = None) -> list[BackfillPlan]:
    """
    If id_prefix is set, fetch rows and filter to id containing that prefix (e.g. 759bc8).
    If hours is None, do not filter by created_at (scan all within limit).
    """
    q = (
        db.client.table("trending_topics")
        .select("id, slug, title, summary, article, schema_blocks, created_at, status, fact_check")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if hours is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        q = q.gte("created_at", cutoff)
    res = q.execute()
    rows: list[dict[str, Any]] = res.data or []

    if id_prefix:
        id_prefix = id_prefix.strip().lower()
        rows = [r for r in rows if id_prefix in str(r.get("id") or "").lower()]
        if not rows:
            return []

    plans: list[BackfillPlan] = []
    for r in rows:
        summary_missing, article_missing = _row_needs_backfill(r)
        if not summary_missing and not article_missing:
            continue
        plan = _plan_for_row(r, use_llm)
        if plan:
            plans.append(plan)
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
    ap.add_argument("--hours", type=float, default=5.0, help="Lookback window (default: 5 hours). Ignored if --all or --id.")
    ap.add_argument("--all", action="store_true", help="Scan all topics (no time filter); fix any with null/empty summary or article.")
    ap.add_argument("--id", dest="id_prefix", metavar="ID", help="Backfill only topic whose id contains this (e.g. 759bc8).")
    ap.add_argument("--dry-run", action="store_true", help="Print changes without updating DB")
    ap.add_argument("--limit", type=int, default=250, help="Max rows to scan (default: 250). Use 2000+ for --all.")
    ap.add_argument(
        "--use-llm",
        action="store_true",
        help="Use Claude to regenerate missing fields (slow). Defaults to off for --dry-run, on for live runs.",
    )
    args = ap.parse_args()

    use_llm = args.use_llm if args.dry_run else True
    hours: float | None = args.hours
    id_prefix: str | None = getattr(args, "id_prefix", None)
    if args.all:
        hours = None
    limit = args.limit
    if id_prefix:
        hours = 99999.0  # large window so we fetch enough rows to find the id
        limit = max(limit, 2000)
        print(f"Finding topic with id containing '{id_prefix}' and backfilling if empty…")
    elif args.all:
        limit = max(limit, 5000)  # default to scanning many rows when updating "all" nulls
        print("Finding all rows with NULL/empty summary or article…")
    else:
        print(f"Finding rows with NULL summary/article since last {args.hours}h…")

    plans = build_plan(hours, limit=limit, use_llm=use_llm, id_prefix=id_prefix)
    if id_prefix and not plans:
        print(f"No topic found with id containing '{id_prefix}', or topic already has summary and article.")
    apply_plan(plans, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

