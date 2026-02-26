"""
scripts/deduplicate.py — Find and remove duplicate published articles.

Three-pass strategy:
  Pass 1: Exact normalised title match
  Pass 2: Semantic TF-IDF cosine similarity on article text (threshold 0.85)
  Winner: highest viral_score; tiebreak by most recent published_at

Duplicates are marked status='rejected', rejection_reason='duplicate: kept_id={id}'.
No rows are hard-deleted (audit trail preserved).

Usage:
    python scripts/deduplicate.py [--dry-run] [--skip-semantic] [--semantic-threshold 0.85]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root or from apps/agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)


# ── Normalisation ─────────────────────────────────────────────────────────────

def _normalise_title(title: str) -> str:
    """Lowercase, strip punctuation and extra whitespace."""
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


# ── Pass 1: exact title duplicates ────────────────────────────────────────────

def _find_exact_title_dupes(rows: list[dict]) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        key = _normalise_title(row.get("title") or "")
        if key:
            groups[key].append(row["id"])
    return [ids for ids in groups.values() if len(ids) > 1]


# ── Pass 2: semantic similarity (TF-IDF + cosine) ────────────────────────────

def _find_semantic_dupes(rows: list[dict], threshold: float = 0.85) -> list[list[str]]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        log.warning("deduplicate: scikit-learn not installed — skipping semantic pass. "
                    "Run: pip install scikit-learn")
        return []

    texts = [
        (r["id"], (r.get("article") or r.get("summary") or "").strip())
        for r in rows
        if (r.get("article") or r.get("summary") or "").strip()
    ]
    if len(texts) < 2:
        return []

    ids    = [t[0] for t in texts]
    corpus = [t[1] for t in texts]

    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    matrix = vectorizer.fit_transform(corpus)
    sims   = cosine_similarity(matrix)

    # Union-find for transitive grouping
    parent: dict[str, str] = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] >= threshold:
                union(ids[i], ids[j])

    groups: dict[str, list[str]] = defaultdict(list)
    for id_ in ids:
        groups[find(id_)].append(id_)
    return [g for g in groups.values() if len(g) > 1]


# ── Winner selection ──────────────────────────────────────────────────────────

def _pick_winner(ids: list[str], rows_by_id: dict[str, dict]) -> str:
    """Keep the row with the highest viral_score; break ties by most recent published_at."""
    def score(id_: str) -> tuple:
        r  = rows_by_id[id_]
        vs = float(r.get("viral_score") or 0.0)
        pa = r.get("published_at") or ""
        return (vs, pa)
    return max(ids, key=score)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate published articles.")
    parser.add_argument("--dry-run",            action="store_true",         help="Preview without DB writes")
    parser.add_argument("--skip-semantic",       action="store_true",         help="Only run exact-match passes (faster)")
    parser.add_argument("--semantic-threshold",  type=float, default=0.85,   help="Cosine similarity threshold (default 0.85)")
    args = parser.parse_args()

    from supabase import create_client
    db = create_client(settings.supabase_url, settings.supabase_service_key)

    # Fetch all published topics
    print("[dedup] Fetching published topics…", flush=True)
    rows: list[dict] = (
        db.table("trending_topics")
        .select("id, title, slug, article, summary, viral_score, published_at")
        .eq("status", "published")
        .execute()
        .data or []
    )
    print(f"[dedup] Loaded {len(rows)} published topics", flush=True)
    rows_by_id = {r["id"]: r for r in rows}

    all_clusters: list[list[str]] = []

    # Pass 1 & 2 — exact title
    title_clusters = _find_exact_title_dupes(rows)
    print(f"[dedup] Exact title duplicates: {len(title_clusters)} clusters", flush=True)
    all_clusters.extend(title_clusters)

    # Pass 3 — semantic
    if not args.skip_semantic:
        already_duped = {id_ for cluster in all_clusters for id_ in cluster}
        remaining = [r for r in rows if r["id"] not in already_duped]
        print(f"[dedup] Running semantic pass on {len(remaining)} remaining topics…", flush=True)
        sem_clusters = _find_semantic_dupes(remaining, args.semantic_threshold)
        print(f"[dedup] Semantic near-duplicates: {len(sem_clusters)} clusters", flush=True)
        all_clusters.extend(sem_clusters)

    report: dict = {
        "total_clusters": len(all_clusters),
        "dry_run":        args.dry_run,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "actions":        [],
    }
    total_rejected = 0

    for cluster in all_clusters:
        winner = _pick_winner(cluster, rows_by_id)
        losers = [id_ for id_ in cluster if id_ != winner]

        winner_title = rows_by_id[winner].get("title", "")[:70]
        for loser_id in losers:
            reason = f"duplicate: kept_id={winner}"
            loser_title = rows_by_id[loser_id].get("title", "")[:70]
            action = {
                "rejected_id":    loser_id,
                "winner_id":      winner,
                "rejected_title": loser_title,
                "winner_title":   winner_title,
            }
            report["actions"].append(action)

            if not args.dry_run:
                try:
                    db.table("trending_topics").update({
                        "status":           "rejected",
                        "rejection_reason": reason,
                        "updated_at":       datetime.now(timezone.utc).isoformat(),
                    }).eq("id", loser_id).execute()
                except Exception as e:
                    log.error("dedup: failed to reject %s: %s", loser_id, e)
                    action["error"] = str(e)

            prefix = "[DRY RUN] " if args.dry_run else ""
            print(f"  {prefix}Rejected: {loser_title} (winner: {winner_title})", flush=True)
            total_rejected += 1

    report["total_rejected"] = total_rejected

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = Path(f"dedup_report_{ts}.json")
    report_path.write_text(json.dumps(report, indent=2))
    print(f"[dedup] Done. {total_rejected} rows {'would be ' if args.dry_run else ''}rejected. Report: {report_path}", flush=True)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"[dedup] Elapsed: {round(time.time() - t0, 1)}s", flush=True)
