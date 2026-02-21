"""
scheduler.py — Inngest CRON scheduler for the pipeline.

Registers the pipeline as an Inngest function triggered every 4 hours.
Serve with a lightweight HTTP server (e.g. Flask or the Inngest dev server)
so Inngest can invoke it:

    python scheduler.py

Environment variables read from config/settings.py (.env).
"""

from __future__ import annotations

import inngest
import inngest.flask  # Inngest Flask integration
from flask import Flask

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

# ── Inngest client ────────────────────────────────────────────────────────────

inngest_client = inngest.Inngest(
    app_id="thenewslane-agent",
    is_production=True,          # set False for local dev with inngest dev server
)

# ── Pipeline CRON function ────────────────────────────────────────────────────


@inngest_client.create_function(
    fn_id="run-pipeline",
    trigger=inngest.TriggerCron(cron=settings.pipeline_cron),  # default: "0 */4 * * *"
)
def run_pipeline_cron(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Triggered by Inngest CRON every 4 hours.
    Delegates to main.run_pipeline() so logic stays in one place.
    """
    import uuid  # noqa: PLC0415

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"
    log.info("Inngest CRON triggered  batch_id=%s  cron=%s", batch_id, settings.pipeline_cron)

    def execute() -> dict:
        from main import run_pipeline  # noqa: PLC0415

        return run_pipeline(batch_id)

    result: dict = step.run("execute-pipeline", execute)
    return result


# ── Manual-trigger function (for testing / backfills) ─────────────────────────


@inngest_client.create_function(
    fn_id="run-pipeline-manual",
    trigger=inngest.TriggerEvent(event="pipeline/run"),
)
def run_pipeline_manual(ctx: inngest.Context, step: inngest.Step) -> dict:
    """
    Triggered by publishing an Inngest event: { name: 'pipeline/run', data: { batch_id?: string } }
    Useful for ad-hoc runs and backfills.
    """
    batch_id: str | None = (ctx.event.data or {}).get("batch_id")

    def execute() -> dict:
        from main import run_pipeline  # noqa: PLC0415

        return run_pipeline(batch_id)

    return step.run("execute-pipeline", execute)


# ── Flask app (Inngest serve target) ─────────────────────────────────────────


def create_app() -> Flask:
    app = Flask(__name__)
    inngest.flask.serve(
        app,
        inngest_client,
        [run_pipeline_cron, run_pipeline_manual],
    )
    return app


if __name__ == "__main__":
    flask_app = create_app()
    log.info("Starting Inngest scheduler on http://0.0.0.0:8000")
    flask_app.run(host="0.0.0.0", port=8000, debug=False)
