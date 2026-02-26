"""
webhook_server.py — HTTP server that runs the pipeline when POSTed to.

Used so Vercel Cron (or any scheduler) can trigger the pipeline by POSTing
to RUNNER_WEBHOOK_URL. Start with:

    python main.py --webhook

Environment:
  RUNNER_WEBHOOK_SECRET — optional; if set, require Authorization: Bearer <this>
  WEBHOOK_PORT — port to listen on (default 8000)

Vercel cron: set RUNNER_WEBHOOK_URL to https://your-agent-host/run and ensure
the cron route sends Authorization: Bearer <CRON_SECRET> (set RUNNER_WEBHOOK_SECRET
to the same value as CRON_SECRET in the agent .env).
"""

from __future__ import annotations

import os
import threading

from flask import Flask, request, jsonify

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

app = Flask(__name__)

# Track in-flight run to avoid overlapping (optional)
_pipeline_lock = threading.Lock()
_pipeline_running = False


def _run_pipeline_in_thread(min_publish: int = 0) -> None:
    global _pipeline_running
    try:
        if min_publish > 0:
            from main import run_pipeline_until  # noqa: PLC0415
            log.info("Webhook: running pipeline until %d stories published", min_publish)
            run_pipeline_until(target=min_publish)
        else:
            from main import run_pipeline  # noqa: PLC0415
            run_pipeline()
    except Exception as exc:
        log.exception("Webhook-triggered pipeline failed: %s", exc)
    finally:
        with _pipeline_lock:
            _pipeline_running = False


def _validate_secret() -> bool:
    secret = getattr(settings, "runner_webhook_secret", "") or os.environ.get("RUNNER_WEBHOOK_SECRET", "")
    if secret:
        auth = request.headers.get("Authorization") or ""
        token = auth.split("Bearer ", 1)[-1].strip() if auth.startswith("Bearer ") else ""
        if token != secret:
            return False
    return True


@app.route("/run", methods=["POST"])
@app.route("/", methods=["POST"])
def run_pipeline_webhook():
    """
    Accept POST to trigger one pipeline run. Returns 202 immediately.

    Optional JSON body:
      { "min_publish": 5 }  — run repeatedly until N stories are published
    """
    global _pipeline_running

    if not _validate_secret():
        log.warning("Webhook rejected: invalid or missing Authorization")
        return jsonify({"error": "Unauthorised"}), 401

    with _pipeline_lock:
        if _pipeline_running:
            log.info("Webhook: pipeline already running, ignoring duplicate trigger")
            return jsonify({"ok": True, "triggered": False, "message": "Pipeline already running"}), 200
        _pipeline_running = True

    body = request.get_json(silent=True) or {}
    min_publish = int(body.get("min_publish", 0))

    thread = threading.Thread(
        target=_run_pipeline_in_thread,
        args=(min_publish,),
        daemon=True,
    )
    thread.start()

    msg = f"Pipeline started (target: {min_publish} stories)" if min_publish > 0 else "Pipeline run started"
    log.info("Webhook: %s", msg)
    return jsonify({"ok": True, "triggered": True, "min_publish": min_publish, "message": msg}), 202


@app.route("/health", methods=["GET"])
def health():
    """Liveness/readiness probe."""
    return jsonify({"ok": True}), 200


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    port = port or int(os.environ.get("WEBHOOK_PORT", "8000"))
    log.info("Webhook server listening on http://%s:%s  (POST /run to trigger pipeline)", host, port)
    app.run(host=host, port=port, debug=False, threaded=True)
