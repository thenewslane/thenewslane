"""
scripts/backfill_author_personas.py — Backfill author personas (bylines).

Assigns author_name and author_honorific from data/author_personas.json using
the same deterministic hash-based assignment as the content generation pipeline.

Run:
    python scripts/backfill_author_personas.py [--dry-run]       # only NULL or "theNewslane Editorial"
    python scripts/backfill_author_personas.py [--dry-run] --all   # all topics
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

# Allow running from repo root or from apps/agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

_PERSONAS_PATH = Path(__file__).parent.parent / "data" / "author_personas.json"
try:
    _PERSONAS: list[dict] = json.loads(_PERSONAS_PATH.read_text())
except Exception:
    _PERSONAS = [{"name": "theNewslane Editorial", "honorific": "Staff Writer"}]


def _assign(topic_id: str) -> dict:
    idx = int(hashlib.md5(topic_id.encode()).hexdigest(), 16) % len(_PERSONAS)
    return _PERSONAS[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill author personas (bylines) from data/author_personas.json.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without DB writes")
    parser.add_argument("--all", action="store_true", help="Update all topics; default is only NULL or placeholder bylines")
    args = parser.parse_args()

    from supabase import create_client
    db = create_client(settings.supabase_url, settings.supabase_service_key)

    if args.all:
        resp = db.table("trending_topics").select("id, title").execute()
        rows = list(resp.data or [])
    else:
        # Target: rows where author_name is NULL or still holds the migration placeholder
        all_rows: list[dict] = []
        for filter_fn in [
            lambda q: q.is_("author_name", "null"),
            lambda q: q.eq("author_name", "theNewslane Editorial"),
        ]:
            page = filter_fn(
                db.table("trending_topics").select("id, title")
            ).execute().data or []
            all_rows.extend(page)
        seen: set[str] = set()
        rows = []
        for r in all_rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                rows.append(r)

    print(f"[backfill] {len(rows)} topics to assign personas to (dry_run={args.dry_run})", flush=True)

    updated = 0
    for row in rows:
        tid     = row["id"]
        title   = (row.get("title") or "")[:60]
        persona = _assign(tid)

        if args.dry_run:
            print(f"  [DRY RUN] {title} → {persona['name']}, {persona['honorific']}", flush=True)
        else:
            try:
                db.table("trending_topics").update({
                    "author_name":      persona["name"],
                    "author_honorific": persona["honorific"],
                }).eq("id", tid).execute()
                print(f"  Updated: {title} → {persona['name']}, {persona['honorific']}", flush=True)
            except Exception as e:
                log.error("backfill: failed to update %s: %s", tid, e)
                continue

        updated += 1

    action = "Would update" if args.dry_run else "Updated"
    print(f"[backfill] Done. {action} {updated}/{len(rows)} topics.", flush=True)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"[backfill] Elapsed: {round(time.time() - t0, 1)}s", flush=True)
