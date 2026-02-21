"""
main.py — Agent pipeline entry point.

Run directly to trigger one full pipeline batch immediately (useful for testing):
    python main.py

Override the batch ID:
    BATCH_ID=batch_test_001 python main.py

Start the Inngest scheduler (serves on :8000 for Inngest to call on cron):
    python main.py --schedule
"""

from __future__ import annotations

import os
import sys
import time
import traceback
import uuid

from config.settings import settings  # validates .env at import time
from utils.logger import get_logger

log = get_logger(__name__)


def run_pipeline(batch_id: str | None = None) -> dict:
    """
    Execute one full pipeline batch.

    Steps:
      1. Create a runs_log row (status='running')
      2. Attach Supabase error-logging handler
      3. Build initial AgentState and invoke the LangGraph pipeline
      4. Finalise the runs_log row with stats
      5. Return the final state dict

    Raises on unrecoverable errors (after marking the run as 'failed').
    """
    # Defer graph import to avoid module-level side effects on --schedule path
    from graph import pipeline  # noqa: PLC0415
    from utils.logger import attach_supabase, detach_supabase  # noqa: PLC0415
    from utils.supabase_client import db  # noqa: PLC0415

    bid = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
    log.info("═══ Pipeline batch starting  batch_id=%s ═══", bid)

    # ── Create batch row ──────────────────────────────────────────────────────
    try:
        db.insert_batch(bid)
    except Exception as exc:
        log.error("Failed to create runs_log row: %s", exc)
        raise

    attach_supabase(bid)

    # ── Initial AgentState ────────────────────────────────────────────────────
    initial_state: dict = {
        "batch_id":                   bid,
        "run_start_time":             time.time(),
        "raw_topics":                 [],
        "viral_scored_topics":        [],
        "brand_safe_topics":          [],
        "classified_topics":          [],
        "content_generated_topics":   [],
        "media_generated_topics":     [],
        "published_topic_ids":        [],
        "errors":                     [],
    }

    # ── Run graph ─────────────────────────────────────────────────────────────
    try:
        final_state = pipeline.invoke(initial_state)

        published = len(final_state.get("published_topic_ids", []))
        errors    = final_state.get("errors", [])
        status    = "partial" if errors else "completed"
        elapsed   = round(time.time() - initial_state["run_start_time"], 1)

        log.info(
            "Pipeline completed  status=%s  published=%d  errors=%d  elapsed=%.1fs",
            status, published, len(errors), elapsed,
        )

    except Exception as exc:
        log.error("Pipeline failed with unhandled exception: %s", exc)
        log.error(traceback.format_exc())
        from utils.supabase_client import db as _db  # noqa: PLC0415
        _db.log_run(bid, status="failed", error_message=str(exc), completed=True)
        detach_supabase()
        raise

    # ── Finalise runs_log ─────────────────────────────────────────────────────
    raw_count        = len(final_state.get("raw_topics", []))
    processed_count  = len(final_state.get("viral_scored_topics", []))
    published_count  = len(final_state.get("published_topic_ids", []))
    # Rejected = processed but not published (brand safety failures + content failures)
    rejected_count   = max(0, processed_count - published_count)

    from utils.supabase_client import db as _db2  # noqa: PLC0415
    _db2.log_run(
        bid,
        status=status,
        signals_collected=raw_count,
        topics_processed=processed_count,
        topics_published=published_count,
        topics_rejected=rejected_count,
        error_message="; ".join(final_state.get("errors", [])) or None,
        completed=True,
    )

    detach_supabase()
    log.info("═══ Batch %s finished ═══", bid)
    return final_state


def _start_scheduler() -> None:
    """Start the Inngest Flask server so the CRON trigger can be served."""
    from scheduler import create_app  # noqa: PLC0415

    flask_app = create_app()
    log.info("Starting Inngest scheduler on http://0.0.0.0:8000")
    flask_app.run(host="0.0.0.0", port=8000, debug=False)


def main() -> None:
    args = sys.argv[1:]

    if "--schedule" in args:
        _start_scheduler()
        return

    # Direct run — execute one batch immediately
    batch_id = os.environ.get("BATCH_ID")
    try:
        final_state = run_pipeline(batch_id)

        published = len(final_state.get("published_topic_ids", []))
        errors    = final_state.get("errors", [])
        elapsed   = round(time.time() - final_state.get("run_start_time", time.time()), 1)

        print(f"\n{'═' * 60}")
        print(f"  theNewslane pipeline — batch complete")
        print(f"  Published topics : {published}")
        print(f"  Errors           : {len(errors)}")
        print(f"  Run time         : {elapsed}s")
        if errors:
            print(f"  Error details:")
            for e in errors:
                print(f"    • {e[:140]}")
        print(f"{'═' * 60}\n")

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
