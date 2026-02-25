"""
app.py — Flask API server for the self-hosted video generation worker.

Endpoints:
  GET  /health           → {"status": "ok", "device": "cuda"}
  POST /generate-clip    → {"video_b64": "<base64-encoded MP4>", "duration_ms": <int>}

Expected POST body:
  {"prompt": "...", "duration": 8}

Run:
  python app.py            # starts on port 5001
"""

from __future__ import annotations

import base64
import time
import torch
from flask import Flask, jsonify, request

app = Flask(__name__)

# Module-level generator (lazy-loaded on first /generate-clip request)
_generator = None


def _get_generator():
    global _generator  # noqa: PLW0603
    if _generator is None:
        from generator import VideoGenerator  # noqa: PLC0415
        _generator = VideoGenerator()
    return _generator


@app.get("/health")
def health():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return jsonify({"status": "ok", "device": device})


@app.post("/generate-clip")
def generate_clip():
    data = request.get_json(force=True, silent=True) or {}
    prompt: str = str(data.get("prompt") or "").strip()
    duration: int = max(1, min(int(data.get("duration") or 8), 30))

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    t0 = time.time()
    try:
        gen = _get_generator()
        video_bytes = gen.generate_clip(prompt=prompt, duration_secs=duration)
        elapsed_ms = int((time.time() - t0) * 1000)
        video_b64 = base64.b64encode(video_bytes).decode("ascii")
        return jsonify({"video_b64": video_b64, "duration_ms": elapsed_ms})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    # Eager model load on startup so first request is fast
    _get_generator()
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=False)
