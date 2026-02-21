"""
main.py — Agent pipeline entry point.

Run directly to trigger one pipeline batch:
    python main.py

Or invoke with a specific batch ID:
    BATCH_ID=batch_test_001 python main.py
"""

from __future__ import annotations

import os
import sys
import traceback
import uuid

from config.settings import settings  # validates .env at import time
from utils.logger import attach_supabase, detach_supabase, get_logger
from utils.supabase_client import db

log = get_logger(__name__)


def run_pipeline(batch_id: str | None = None) -> dict:
    """
    Execute one full pipeline batch.

    1. Create runs_log row
    2. Attach Supabase error logging
    3. Run the LangGraph pipeline
    4. Finalise the runs_log row
    5. Return summary dict
    """
    # Defer graph import to avoid module-level side effects at import time
    from graph import pipeline  # noqa: PLC0415

    bid = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
    log.info("═══ Pipeline batch starting  batch_id=%s ═══", bid)

    # ── Create batch row ──────────────────────────────────────────────────
    try:
        db.insert_batch(bid)
    except Exception as exc:
        log.error("Failed to create runs_log row: %s", exc)
        raise

    attach_supabase(bid)

    # ── Initial pipeline state ────────────────────────────────────────────
    initial_state = {
        "batch_id":        bid,
        "raw_signals":     [],
        "topics":          [],
        "signals_collected": 0,
        "topics_processed":  0,
        "topics_published":  0,
        "topics_rejected":   0,
        "errors":          [],
    }

    # ── Run graph ─────────────────────────────────────────────────────────
    try:
        final_state = pipeline.invoke(initial_state)
        status = "partial" if final_state.get("errors") else "completed"
        log.info(
            "Pipeline completed  status=%s  published=%d  rejected=%d",
            status,
            final_state.get("topics_published", 0),
            final_state.get("topics_rejected", 0),
        )
    except Exception as exc:
        log.error("Pipeline failed with unhandled exception: %s", exc)
        log.error(traceback.format_exc())
        db.log_run(bid, status="failed", error_message=str(exc), completed=True)
        detach_supabase()
        raise

    # ── Finalise runs_log ─────────────────────────────────────────────────
    db.log_run(
        bid,
        status=status,
        signals_collected=final_state.get("signals_collected", 0),
        topics_processed=final_state.get("topics_processed",  0),
        topics_published=final_state.get("topics_published",  0),
        topics_rejected=final_state.get("topics_rejected",    0),
        error_message="; ".join(final_state.get("errors", [])) or None,
        completed=True,
    )

    detach_supabase()
    log.info("═══ Batch %s finished ═══", bid)
    return final_state


def main() -> None:
    batch_id = os.environ.get("BATCH_ID")
    try:
        run_pipeline(batch_id)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
