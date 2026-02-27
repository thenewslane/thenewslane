"""
main.py — Agent pipeline entry point.

Usage
─────
Run one batch immediately (useful for testing):
    python main.py

Run in debug mode (verbose logging, step-by-step output):
    python main.py --debug

Run continuously every N minutes (built-in loop — no external dependencies):
    python main.py --schedule

Run via Inngest (requires Inngest account + public URL):
    python main.py --inngest

Run webhook server (for Vercel Cron / RUNNER_WEBHOOK_URL):
    python main.py --webhook

Override the interval (seconds) or batch ID:
    PIPELINE_INTERVAL_MINUTES=10 python main.py --schedule
    BATCH_ID=batch_test_001 python main.py

Pipeline steps (in order)
──────────────────────────
  1. collect             — Fetch signals (Google Trends, NewsAPI, RSS, etc.)
  2. predict_viral       — Score topics; keep only viral-scoring
  3. filter_brand_safety — Brand-safety checks
  4. classify            — Assign category (Technology, Sports, etc.)
  5. generate_content   — Generate article, summary, social copy (Claude)
  6. source_video        — Find YouTube/Vimeo or mark ai_needed
  7. generate_media     — Thumbnails and optional AI video
  8. publish             — Write to DB, trigger ISR + IndexNow
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


def run_pipeline(
    batch_id: str | None = None,
    category_filter: str | None = None,
    max_topics: int | None = None,
) -> dict:
    """
    Execute one full pipeline batch.

    Steps:
      1. Create a runs_log row (status='running')
      2. Attach Supabase error-logging handler
      3. Build initial AgentState and invoke the LangGraph pipeline
      4. Finalise the runs_log row with stats
      5. Return the final state dict

    Args:
      batch_id:        Optional explicit batch ID (auto-generated if omitted).
      category_filter: Optional category name to restrict output (e.g. "Technology").
                       Applied after classify — only topics matching this category
                       proceed to content generation.
      max_topics:      Optional cap on topics entering generate_content (1-10).
                       Applied after category filtering.

    Raises on unrecoverable errors (after marking the run as 'failed').
    """
    from graph import pipeline  # noqa: PLC0415
    from utils.logger import attach_supabase, detach_supabase  # noqa: PLC0415
    from utils.supabase_client import db  # noqa: PLC0415

    bid = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
    log.info("═══ Pipeline batch starting  batch_id=%s ═══", bid)
    if category_filter:
        log.info("    category_filter=%s  max_topics=%s", category_filter, max_topics)

    try:
        db.insert_batch(bid)
    except Exception as exc:
        log.error("Failed to create runs_log row: %s", exc)
        raise

    attach_supabase(bid)

    initial_state: dict = {
        "batch_id":                 bid,
        "run_start_time":           time.time(),
        "category_filter":          category_filter,
        "max_topics":               max_topics,
        "raw_topics":               [],
        "viral_scored_topics":      [],
        "brand_safe_topics":        [],
        "classified_topics":        [],
        "content_generated_topics": [],
        "media_generated_topics":   [],
        "published_topic_ids":      [],
        "fact_checked_topic_ids":   [],
        "errors":                   [],
    }

    try:
        print("Pipeline running: collect → … → generate_content → source_video → generate_media (thumbnails) → publish → post_publish_video → fact_check", flush=True)
        final_state = pipeline.invoke(initial_state)

        published = len(final_state.get("published_topic_ids", [])) + len(final_state.get("fact_checked_topic_ids", []))
        errors    = final_state.get("errors", [])
        status    = "partial" if errors else "completed"
        elapsed   = round(time.time() - initial_state["run_start_time"], 1)

        # Make early exit visible (e.g. no viral topics)
        raw_count = len(final_state.get("raw_topics", []))
        viral_count = len(final_state.get("viral_scored_topics", []))
        if raw_count and not viral_count and not published and not errors:
            print("Pipeline ended early: no topics passed viral scoring (nothing to publish).", flush=True)
        elif not raw_count:
            print("Pipeline ended: no signals collected.", flush=True)

        log.info(
            "Pipeline completed  status=%s  published=%d  errors=%d  elapsed=%.1fs",
            status, published, len(errors), elapsed,
        )

    except Exception as exc:
        print(f"Pipeline failed: {exc}", flush=True)
        log.error("Pipeline failed with unhandled exception: %s", exc)
        log.error(traceback.format_exc())
        from utils.supabase_client import db as _db  # noqa: PLC0415
        _db.log_run(bid, status="failed", error_message=str(exc), completed=True)
        detach_supabase()
        raise

    raw_count       = len(final_state.get("raw_topics", []))
    processed_count = len(final_state.get("viral_scored_topics", []))
    # Topics published this run: from publish node (direct) + any legacy drafts approved by fact_check
    published_count = len(final_state.get("published_topic_ids", [])) + len(final_state.get("fact_checked_topic_ids", []))
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


# ── Run-until-target mode (used by manual trigger) ───────────────────────────


def run_pipeline_until(target: int = 5, max_runs: int = 10) -> dict:
    """
    Run the pipeline repeatedly until at least `target` stories are published
    across all runs, or `max_runs` attempts are exhausted.

    Each run goes through the full process: collect → viral → safety →
    classify → generate → media → publish. Same checks as a cron run.

    Returns a summary dict with total published count and per-run details.
    """
    target = max(1, min(20, target))
    max_runs = max(1, min(20, max_runs))

    log.info("╔══════════════════════════════════════════════════╗")
    log.info("║  Pipeline: run-until-target mode                 ║")
    log.info("║  Target : %d stories                              ║", target)
    log.info("║  Max runs: %d                                     ║", max_runs)
    log.info("╚══════════════════════════════════════════════════╝")

    total_published = 0
    run_details: list[dict] = []

    for run_num in range(1, max_runs + 1):
        log.info("┌─ Run %d/%d (need %d more stories) ──────────────", run_num, max_runs, target - total_published)
        t0 = time.time()

        try:
            state = run_pipeline()
            published = len(state.get("published_topic_ids", [])) + len(state.get("fact_checked_topic_ids", []))
            errors = len(state.get("errors", []))
            elapsed = round(time.time() - t0, 1)
            total_published += published

            run_details.append({
                "run": run_num,
                "published": published,
                "errors": errors,
                "elapsed_sec": elapsed,
            })

            log.info("└─ Run %d: published=%d  total=%d/%d  elapsed=%.1fs",
                      run_num, published, total_published, target, elapsed)

            if total_published >= target:
                log.info("Target reached: %d/%d stories published after %d run(s)", total_published, target, run_num)
                break

        except Exception as exc:
            elapsed = round(time.time() - t0, 1)
            log.error("└─ Run %d FAILED after %.1fs: %s", run_num, elapsed, exc)
            run_details.append({
                "run": run_num,
                "published": 0,
                "errors": 1,
                "elapsed_sec": elapsed,
                "error": str(exc),
            })

        # Brief pause between runs to avoid hammering APIs
        if run_num < max_runs and total_published < target:
            log.info("Pausing 30s before next run...")
            time.sleep(30)

    summary = {
        "target": target,
        "total_published": total_published,
        "runs_completed": len(run_details),
        "target_reached": total_published >= target,
        "details": run_details,
    }
    log.info("Pipeline run-until complete: %s", summary)
    return summary


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
    debug = "--debug" in args
    if debug:
        args = [a for a in args if a != "--debug"]
        # Ensure DEBUG-level logs are visible
        import logging  # noqa: PLC0415
        logging.getLogger("agent").setLevel(logging.DEBUG)
        for h in logging.getLogger("agent").handlers:
            h.setLevel(logging.DEBUG)
        print("DEBUG MODE: verbose logging enabled, steps will be printed below.\n", flush=True)

    if "--schedule" in args:
        # Self-contained built-in loop — no external dependencies
        _start_loop()
        return

    if "--inngest" in args:
        # Inngest-managed CRON (requires Inngest account + public URL)
        _start_inngest()
        return

    if "--webhook" in args:
        # HTTP server: POST /run triggers pipeline (for Vercel Cron → RUNNER_WEBHOOK_URL)
        from webhook_server import serve  # noqa: PLC0415
        serve()
        return

    # Direct single run — print immediately so user sees response
    batch_id = os.environ.get("BATCH_ID")

    # Parse optional --category=NAME and --max-topics=N flags
    category_filter: str | None = None
    max_topics: int | None = None
    for arg in args:
        if arg.startswith("--category="):
            category_filter = arg.split("=", 1)[1].strip()
        elif arg.startswith("--max-topics="):
            try:
                max_topics = max(1, min(10, int(arg.split("=", 1)[1])))
            except ValueError:
                pass

    print("Starting theNewslane pipeline (single batch)...", flush=True)
    if debug:
        print("Steps: 1 collect → 2 predict_viral → 3 filter_brand_safety → 4 classify → 5 filter_category → 6 generate_content → 7 source_video → 8 generate_media → 9 publish", flush=True)
    if batch_id:
        print(f"  BATCH_ID={batch_id}", flush=True)
    if category_filter:
        print(f"  CATEGORY_FILTER={category_filter}", flush=True)
    if max_topics:
        print(f"  MAX_TOPICS={max_topics}", flush=True)
    print("  Log output will stream below. This may take several minutes.\n", flush=True)

    try:
        final_state = run_pipeline(batch_id, category_filter=category_filter, max_topics=max_topics)

        published = len(final_state.get("published_topic_ids", [])) + len(final_state.get("fact_checked_topic_ids", []))
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

    except Exception as exc:
        print(f"Pipeline failed: {exc}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Unbuffered stdout so output appears immediately (e.g. in IDE/CI)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    main()
