"""
main.py — Agent pipeline entry point.

Usage
─────
Run one batch immediately (useful for testing):
    python main.py

Run continuously every N minutes (built-in loop — no external dependencies):
    python main.py --schedule

Run via Inngest (requires Inngest account + public URL):
    python main.py --inngest

Override the interval (seconds) or batch ID:
    PIPELINE_INTERVAL_MINUTES=10 python main.py --schedule
    BATCH_ID=batch_test_001 python main.py
"""

from __future__ import annotations

import os
import signal
import sys
import time
import traceback
import uuid

from config.settings import settings  # validates .env at import time
from utils.logger import get_logger

log = get_logger(__name__)


# ── Single batch ──────────────────────────────────────────────────────────────


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
    from graph import pipeline  # noqa: PLC0415
    from utils.logger import attach_supabase, detach_supabase  # noqa: PLC0415
    from utils.supabase_client import db  # noqa: PLC0415

    bid = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
    log.info("═══ Pipeline batch starting  batch_id=%s ═══", bid)

    try:
        db.insert_batch(bid)
    except Exception as exc:
        log.error("Failed to create runs_log row: %s", exc)
        raise

    attach_supabase(bid)

    initial_state: dict = {
        "batch_id":                 bid,
        "run_start_time":           time.time(),
        "raw_topics":               [],
        "viral_scored_topics":      [],
        "brand_safe_topics":        [],
        "classified_topics":        [],
        "content_generated_topics": [],
        "media_generated_topics":   [],
        "published_topic_ids":      [],
        "errors":                   [],
    }

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

    raw_count       = len(final_state.get("raw_topics", []))
    processed_count = len(final_state.get("viral_scored_topics", []))
    published_count = len(final_state.get("published_topic_ids", []))
    rejected_count  = max(0, processed_count - published_count)

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


# ── Built-in continuous scheduler ────────────────────────────────────────────


def _start_loop() -> None:
    """
    Run the pipeline on a fixed interval using a self-contained background loop.

    No external dependencies (Inngest, cron daemon, etc.) required.

    Interval: PIPELINE_INTERVAL_MINUTES env var (default 5).
    Behaviour:
      • Starts the first run immediately.
      • Sleeps the configured interval between runs, checking every second so
        SIGINT / SIGTERM result in an instant, clean shutdown.
      • Errors in a single run are logged and swallowed — the loop continues.
    """
    interval_minutes = int(os.environ.get("PIPELINE_INTERVAL_MINUTES", settings.pipeline_interval_minutes))
    interval_seconds = interval_minutes * 60

    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║  theNewslane pipeline scheduler — built-in loop  ║")
    log.info("║  Interval : every %d minutes                      ║", interval_minutes)
    log.info("║  Stop     : Ctrl-C or SIGTERM                     ║")
    log.info("╚══════════════════════════════════════════════════╝")

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    _stop = [False]

    def _handle_signal(signum: int, _frame: object) -> None:
        log.info("Signal %d received — stopping after current run…", signum)
        _stop[0] = True

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # ── Main loop ─────────────────────────────────────────────────────────────
    run_number = 0

    while not _stop[0]:
        run_number += 1
        log.info("┌─ Scheduler: starting run #%d ─────────────────────", run_number)
        t0 = time.time()

        try:
            result    = run_pipeline()
            published = len(result.get("published_topic_ids", []))
            elapsed   = round(time.time() - t0, 1)
            log.info(
                "└─ Run #%d complete — %d topic(s) published in %.1fs",
                run_number, published, elapsed,
            )
        except Exception as exc:
            elapsed = round(time.time() - t0, 1)
            log.error("└─ Run #%d FAILED after %.1fs: %s", run_number, elapsed, exc)

        if _stop[0]:
            break

        next_run_at = time.strftime("%H:%M:%S", time.localtime(time.time() + interval_seconds))
        log.info("Sleeping %d min — next run at %s  (Ctrl-C to stop)", interval_minutes, next_run_at)

        # Sleep in 1-second ticks so Ctrl-C is instant
        for _ in range(interval_seconds):
            if _stop[0]:
                break
            time.sleep(1)

    log.info("Scheduler stopped after %d run(s).", run_number)


# ── Inngest scheduler (optional, requires external account) ──────────────────


def _start_inngest() -> None:
    """Start the Inngest Flask server so the CRON trigger can be served."""
    from scheduler import create_app  # noqa: PLC0415

    flask_app = create_app()
    log.info("Starting Inngest scheduler on http://0.0.0.0:8000")
    flask_app.run(host="0.0.0.0", port=8000, debug=False)


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    args = sys.argv[1:]

    if "--schedule" in args:
        # Self-contained built-in loop — no external dependencies
        _start_loop()
        return

    if "--inngest" in args:
        # Inngest-managed CRON (requires Inngest account + public URL)
        _start_inngest()
        return

    # Direct single run — print immediately so user sees response
    batch_id = os.environ.get("BATCH_ID")
    print("Starting theNewslane pipeline (single batch)...", flush=True)
    if batch_id:
        print(f"  BATCH_ID={batch_id}", flush=True)
    print("  Log output will stream below. This may take several minutes.\n", flush=True)

    try:
        final_state = run_pipeline(batch_id)

        published = len(final_state.get("published_topic_ids", []))
        errors    = final_state.get("errors", [])
        elapsed   = round(time.time() - final_state.get("run_start_time", time.time()), 1)

        print(f"\n{'═' * 60}", flush=True)
        print(f"  theNewslane pipeline — batch complete", flush=True)
        print(f"  Published topics : {published}", flush=True)
        print(f"  Errors           : {len(errors)}", flush=True)
        print(f"  Run time         : {elapsed}s", flush=True)
        if errors:
            print("  Error details:", flush=True)
            for e in errors:
                print(f"    • {e[:140]}", flush=True)
        print(f"{'═' * 60}\n", flush=True)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    # Unbuffered stdout so output appears immediately (e.g. in IDE/CI)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    main()
