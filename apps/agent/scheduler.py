"""
scheduler.py — Inngest CRON scheduler for the theNewslane pipeline.

Registers the pipeline as an Inngest function triggered every 5 minutes.
Serve with Flask so Inngest can invoke it:

    python main.py --schedule        # recommended entry point
    python scheduler.py              # alternative direct start

Environment variables read from config/settings.py (.env).
"""

from __future__ import annotations

import time
import uuid

import httpx
import inngest
import inngest.flask
from flask import Flask

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)


# ── Inngest client ────────────────────────────────────────────────────────────

inngest_client = inngest.Inngest(
    app_id="thenewslane-agent",
    is_production=True,
)


# ── Slack notification helper ──────────────────────────────────────────────────


def _send_slack(message: str) -> None:
    """Post a message to the configured Slack webhook (best-effort, never raises)."""
    webhook_url = settings.slack_webhook_url
    if not webhook_url:
        return
    try:
        resp = httpx.post(webhook_url, json={"text": message}, timeout=10)
        if resp.status_code != 200:
            log.warning("Slack webhook returned %d for message: %.80s", resp.status_code, message)
    except Exception as exc:
        log.warning("Slack notification failed: %s", exc)


# ── Pipeline CRON function ─────────────────────────────────────────────────────


@inngest_client.create_function(
    fn_id="run-pipeline",
    trigger=inngest.TriggerCron(cron=settings.pipeline_cron),  # default: "0 */4 * * *"
)
def run_pipeline_cron(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Triggered by Inngest CRON every 5 minutes.

    1. Creates a batch_id
    2. Initialises AgentState
    3. Compiles and runs the LangGraph graph (via main.run_pipeline)
    4. Logs total run time and published count to runs_log
    5. Sends Slack success or failure notification
    """
    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    log.info("Inngest CRON triggered  batch_id=%s  cron=%s", batch_id, settings.pipeline_cron)

    def execute() -> dict:
        from main import run_pipeline  # noqa: PLC0415
        return run_pipeline(batch_id)

    t0 = time.time()
    try:
        result: dict = step.run("execute-pipeline", execute)
        elapsed = round(time.time() - t0, 1)

        published = len(result.get("published_topic_ids", []))
        errors = result.get("errors", [])
        status = "partial" if errors else "completed"

        log.info(
            "Cron batch %s finished  status=%s  published=%d  elapsed=%.1fs",
            batch_id, status, published, elapsed,
        )

        _send_slack(
            f"✅ *theNewslane pipeline* `{batch_id}` — {status}\n"
            f"• Published: {published} topics\n"
            f"• Run time: {elapsed}s\n"
            f"• Errors: {len(errors)}"
        )
        return result

    except Exception as exc:
        elapsed = round(time.time() - t0, 1)
        log.error("Cron batch %s FAILED: %s", batch_id, exc)
        _send_slack(
            f"❌ *theNewslane pipeline* `{batch_id}` — FAILED\n"
            f"• Error: {str(exc)[:300]}\n"
            f"• Run time: {elapsed}s"
        )
        raise


# ── Weekly rehash CRON (humanise stale content) ───────────────────────────────


@inngest_client.create_function(
    fn_id="rehash-stale-content",
    trigger=inngest.TriggerCron(cron="0 2 * * 0"),  # every Sunday at 02:00 UTC
)
def rehash_stale_content(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Weekly freshness pass: rewrite articles older than 7 days (capped at 50 per run).

    Imports the run_rehash_batch helper from scripts/rehash_published.py so the
    same logic is shared between manual CLI runs and this scheduled job.
    """
    def execute() -> dict:
        from scripts.rehash_published import run_rehash_batch  # noqa: PLC0415
        return run_rehash_batch(older_than_days=7, limit=50)

    try:
        result: dict = step.run("rehash-stale", execute)
        updated = result.get("updated", 0)
        failed  = result.get("failed", 0)
        log.info("rehash-stale-content: updated=%d  failed=%d", updated, failed)
        _send_slack(
            f"🔄 *theNewslane rehash* — weekly freshness pass\n"
            f"• Rewritten: {updated} articles\n"
            f"• Failed: {failed}"
        )
        return result
    except Exception as exc:
        log.error("rehash-stale-content FAILED: %s", exc)
        _send_slack(f"❌ *theNewslane rehash* — FAILED\n• Error: {str(exc)[:300]}")
        raise


# ── Manual-trigger function (ad-hoc runs / backfills) ─────────────────────────


@inngest_client.create_function(
    fn_id="run-pipeline-manual",
    trigger=inngest.TriggerEvent(event="pipeline/run"),
)
def run_pipeline_manual(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Triggered by publishing an Inngest event:
        { "name": "pipeline/run", "data": { "batch_id": "<optional>" } }
    Useful for ad-hoc runs and backfills.
    """
    batch_id: str | None = (ctx.event.data or {}).get("batch_id")

    def execute() -> dict:
        from main import run_pipeline  # noqa: PLC0415
        return run_pipeline(batch_id)

    return step.run("execute-pipeline", execute)


# ── Flask app (Inngest serve target) ──────────────────────────────────────────


def create_app() -> Flask:
    """Return a Flask app with Inngest functions mounted."""
    app = Flask(__name__)
    inngest.flask.serve(
        app,
        inngest_client,
        [run_pipeline_cron, run_pipeline_manual, rehash_stale_content],
    )
    return app


if __name__ == "__main__":
    flask_app = create_app()
    log.info("Starting Inngest scheduler on http://0.0.0.0:8000")
    flask_app.run(host="0.0.0.0", port=8000, debug=False)
