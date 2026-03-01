"""
scripts/update_all_authors_to_aadi.py — Set all author names and bylines to Aadi.

Updates trending_topics.author_name to 'Aadi' and author_honorific to NULL
for every row (so the website shows "Aadi" for all articles).

Run from apps/agent:
    python scripts/update_all_authors_to_aadi.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

BATCH = 500


def main() -> None:
    parser = argparse.ArgumentParser(description="Set all author names and bylines to Aadi.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; no DB writes")
    args = parser.parse_args()

    # Fetch all topic ids so we can update in batches (PostgREST prefers filtered updates)
    result = db.client.table("trending_topics").select("id").execute()
    ids = [row["id"] for row in (result.data or [])]
    n = len(ids)
    if n == 0:
        log.info("No trending_topics rows found. Nothing to update.")
        return

    if args.dry_run:
        log.info("[dry-run] Would set author_name='Aadi', author_honorific=NULL for %d topics.", n)
        return

    patch = {"author_name": "Aadi", "author_honorific": None}
    updated = 0
    for i in range(0, n, BATCH):
        batch_ids = ids[i : i + BATCH]
        db.client.table("trending_topics").update(patch).in_("id", batch_ids).execute()
        updated += len(batch_ids)
        log.info("Updated %d / %d topics", updated, n)

    log.info("Done. All %d topics now have author_name='Aadi'.", updated)


if __name__ == "__main__":
    main()
