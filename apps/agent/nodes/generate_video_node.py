"""
nodes/generate_video_node.py — Text-to-video generation for Tier 1 topics.

Pipeline per eligible topic:
  1. Claude Haiku expands title + summary → 8 visual scene descriptions
  2. Generate 8 × 8-second clips via fal.ai LTX-Video or self-hosted GPU worker
     (self-hosted auto-falls back to fal.ai on any connection error)
  3. edge-tts voiceover from article summary
  4. FFmpeg: stitch clips → mix with voiceover → final.mp4
  5. Upload to Supabase Storage (bucket: media, path: videos/{topic_id}.mp4)
  6. Update trending_topics.video_url + video_type = 'kling_generated'

Only processes topics with viral_tier == 1 and no existing video (video_type != "youtube"/"vimeo").
VIDEO_BACKEND env var switches between "fal" (default) and "selfhosted".
"""

from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
import httpx

from config.settings import settings
from nodes.media_generation_node import StorageManager
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

CLIP_DURATION_SECS = 8          # seconds per scene clip
_DEFAULT_CLIPS = 8              # number of scene clips


# ── Prompt expansion via Claude Haiku ─────────────────────────────────────────


async def _expand_scenes(
    client: anthropic.AsyncAnthropic,
    title: str,
    summary: str,
    n_clips: int,
) -> List[str]:
    """
    Ask Claude Haiku to expand a news headline into `n_clips` cinematic scene
    descriptions suitable for a text-to-video model.

    Returns a list of prompt strings (len == n_clips).  Falls back to generic
    prompts derived from the title if Claude fails.
    """
    system = (
        "You are a cinematic art director for a news video. "
        "Given a news headline and summary, produce exactly {n} numbered visual scene "
        "descriptions for a text-to-video model. "
        "Rules: documentary style, no faces, no text overlays, no logos, no brand names. "
        "Each scene must be 1-2 sentences, vivid and specific. "
        "Output only a JSON array of {n} strings, nothing else."
    ).format(n=n_clips)

    user = f"Headline: {title}\n\nSummary: {summary[:500]}"

    try:
        msg = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = (msg.content[0].text or "").strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        scenes: List[str] = json.loads(raw)
        if isinstance(scenes, list) and len(scenes) == n_clips:
            log.info("[generate_video] Haiku expanded %d scenes for '%s'", n_clips, title[:40])
            return scenes
    except Exception as exc:
        log.warning("[generate_video] Scene expansion failed for '%s': %s", title[:40], exc)

    # Fallback: repeat a generic cinematic prompt
    fallback = (
        f"Cinematic wide shot illustrating the news story: {title}. "
        "Documentary style, dramatic natural lighting, no people, no text."
    )
    return [fallback] * n_clips


# ── Clip generation via fal.ai ────────────────────────────────────────────────


async def _generate_clip_fal(scene_prompt: str, duration_secs: int) -> bytes:
    """
    Call fal.ai LTX-Video API to generate a single clip.
    Returns raw MP4 bytes.
    """
    try:
        import fal_client  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("fal-client is not installed — pip install fal-client") from exc

    fal_key = getattr(settings, "fal_key", "")
    if not fal_key:
        raise RuntimeError("FAL_KEY is not configured in .env")

    model = getattr(settings, "video_model", "fal-ai/ltx-video")

    log.info("[generate_video] fal.ai clip: model=%s  prompt='%s...'", model, scene_prompt[:60])

    import os  # noqa: PLC0415
    os.environ["FAL_KEY"] = fal_key  # fal_client reads from env

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: fal_client.subscribe(
            model,
            arguments={
                "prompt": scene_prompt,
                "negative_prompt": "text, watermark, logo, ugly, blurry, distorted, people, faces",
                "num_frames": duration_secs * 15,  # 15 fps
                "width": 848,
                "height": 480,
                "guidance_scale": 3.0,
                "num_inference_steps": 40,
            },
            with_logs=False,
        ),
    )

    video_url: Optional[str] = None
    if isinstance(result, dict):
        # Common fal.ai response shapes
        video_url = (
            (result.get("video") or {}).get("url")
            or result.get("video_url")
            or result.get("url")
        )

    if not video_url:
        raise RuntimeError(f"fal.ai returned no video URL: {result}")

    async with httpx.AsyncClient(timeout=120.0) as http:
        resp = await http.get(video_url)
        resp.raise_for_status()
        return resp.content


# ── Clip generation via self-hosted worker ────────────────────────────────────


async def _generate_clip_selfhosted(scene_prompt: str, duration_secs: int) -> bytes:
    """
    POST to the self-hosted video worker and return raw MP4 bytes.
    The worker is expected to respond with {"video_b64": "<base64>"}.
    """
    worker_url = getattr(settings, "video_worker_url", "http://localhost:5001")
    endpoint = f"{worker_url.rstrip('/')}/generate-clip"

    log.info("[generate_video] selfhosted clip: endpoint=%s  prompt='%s...'", endpoint, scene_prompt[:60])

    async with httpx.AsyncClient(timeout=300.0) as http:
        resp = await http.post(
            endpoint,
            json={"prompt": scene_prompt, "duration": duration_secs},
        )
        resp.raise_for_status()
        data = resp.json()

    video_b64 = data.get("video_b64") or ""
    if not video_b64:
        raise RuntimeError(f"Self-hosted worker returned no video_b64: {data}")

    return base64.b64decode(video_b64)


# ── Dispatch: selfhosted with fal.ai fallback ─────────────────────────────────


async def _generate_clip(scene_prompt: str, duration_secs: int) -> bytes:
    """Route clip generation based on VIDEO_BACKEND setting."""
    backend = getattr(settings, "video_backend", "fal").lower()

    if backend == "selfhosted":
        try:
            return await _generate_clip_selfhosted(scene_prompt, duration_secs)
        except Exception as exc:
            log.warning(
                "[generate_video] Self-hosted clip failed (%s) — falling back to fal.ai: %s",
                type(exc).__name__, exc,
            )
            return await _generate_clip_fal(scene_prompt, duration_secs)

    # Default: fal.ai directly
    return await _generate_clip_fal(scene_prompt, duration_secs)


# ── Voiceover via edge-tts ────────────────────────────────────────────────────


async def _generate_voiceover(text: str, out_path: str) -> bool:
    """
    Use edge-tts to synthesise a voiceover MP3.
    Returns True on success, False on failure (non-fatal).
    """
    try:
        import edge_tts  # noqa: PLC0415
    except ImportError:
        log.warning("[generate_video] edge-tts not installed — skipping voiceover")
        return False

    # Trim to ~200 words so voiceover fits within the ~64-second video
    words = text.split()
    trimmed = " ".join(words[:200])

    try:
        communicate = edge_tts.Communicate(trimmed, "en-US-AriaNeural")
        await communicate.save(out_path)
        log.info("[generate_video] Voiceover saved to %s", out_path)
        return True
    except Exception as exc:
        log.warning("[generate_video] edge-tts failed: %s", exc)
        return False


# ── FFmpeg assembly ───────────────────────────────────────────────────────────


def _ffmpeg_run(args: List[str]) -> None:
    """Run an ffmpeg command; raise RuntimeError on non-zero exit."""
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-1000:]}")


def _assemble_video(clip_paths: List[str], voiceover_path: Optional[str], out_path: str) -> None:
    """
    1. Write a concat file-list
    2. Stitch clips → raw.mp4
    3. If voiceover exists: mix audio → final.mp4
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        filelist = Path(tmp_dir) / "filelist.txt"
        raw_mp4 = Path(tmp_dir) / "raw.mp4"

        # Write filelist for concat demuxer
        filelist.write_text(
            "\n".join(f"file '{p}'" for p in clip_paths),
            encoding="utf-8",
        )

        # Step A: concatenate clips
        _ffmpeg_run([
            "-f", "concat", "-safe", "0",
            "-i", str(filelist),
            "-c", "copy",
            str(raw_mp4),
        ])

        # Step B: mix with voiceover if available
        if voiceover_path and Path(voiceover_path).exists():
            _ffmpeg_run([
                "-i", str(raw_mp4),
                "-i", voiceover_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                out_path,
            ])
        else:
            # No audio: just copy raw video to final output
            import shutil  # noqa: PLC0415
            shutil.copy2(str(raw_mp4), out_path)

    log.info("[generate_video] Assembled video → %s", out_path)


# ── Per-topic video generator ─────────────────────────────────────────────────


async def _generate_video_for_topic(
    topic: Dict[str, Any],
    anthropic_client: anthropic.AsyncAnthropic,
    storage: StorageManager,
) -> Dict[str, Any]:
    """
    Run the full video generation pipeline for one Tier 1 topic.

    Returns the topic dict with video_url and video_type set,
    or the original topic unchanged on any failure.
    """
    topic_id: str = str(topic.get("id") or topic.get("topic_id") or uuid.uuid4().hex)
    title: str = (topic.get("title") or topic.get("keyword") or "News").strip()
    summary: str = (topic.get("summary") or topic.get("summary_30w") or title).strip()
    n_clips: int = max(1, getattr(settings, "video_clips", _DEFAULT_CLIPS))

    log.info("[generate_video] Starting video for topic %s ('%s')", topic_id, title[:50])

    with tempfile.TemporaryDirectory(prefix=f"vidgen_{topic_id}_") as tmp_dir:
        tmp = Path(tmp_dir)

        # ── 1. Expand scenes via Claude Haiku ─────────────────────────────────
        scenes = await _expand_scenes(anthropic_client, title, summary, n_clips)

        # ── 2. Generate clips (sequential to avoid GPU OOM / API rate limits) ─
        clip_paths: List[str] = []
        for i, scene in enumerate(scenes):
            clip_path = str(tmp / f"clip_{i:02d}.mp4")
            try:
                video_bytes = await _generate_clip(scene, CLIP_DURATION_SECS)
                Path(clip_path).write_bytes(video_bytes)
                clip_paths.append(clip_path)
                log.info(
                    "[generate_video] Clip %d/%d done for topic %s (%d bytes)",
                    i + 1, n_clips, topic_id, len(video_bytes),
                )
            except Exception as exc:
                log.warning(
                    "[generate_video] Clip %d/%d failed for topic %s: %s",
                    i + 1, n_clips, topic_id, exc,
                )

        if not clip_paths:
            log.error("[generate_video] All clips failed for topic %s — skipping", topic_id)
            return topic

        # ── 3. Voiceover via edge-tts ─────────────────────────────────────────
        vo_path = str(tmp / "voiceover.mp3")
        has_vo = await _generate_voiceover(summary, vo_path)

        # ── 4. FFmpeg assembly ────────────────────────────────────────────────
        final_path = str(tmp / "final.mp4")
        try:
            _assemble_video(clip_paths, vo_path if has_vo else None, final_path)
        except Exception as exc:
            log.error("[generate_video] FFmpeg assembly failed for topic %s: %s", topic_id, exc)
            return topic

        # ── 5. Upload to Supabase Storage ─────────────────────────────────────
        object_name = f"{topic_id}.mp4"
        try:
            video_url = await storage.upload_file(final_path, "videos", object_name)
            log.info("[generate_video] Uploaded video for topic %s → %s", topic_id, video_url)
        except Exception as exc:
            log.error("[generate_video] Upload failed for topic %s: %s", topic_id, exc)
            return topic

    # ── 6. Update DB ──────────────────────────────────────────────────────────
    try:
        db.client.table("trending_topics").update(
            {"video_url": video_url, "video_type": "kling_generated"}
        ).eq("id", topic_id).execute()
        log.info("[generate_video] DB updated for topic %s", topic_id)
    except Exception as exc:
        log.warning("[generate_video] DB update failed for topic %s: %s", topic_id, exc)

    # ── 7. Return enriched topic dict ─────────────────────────────────────────
    return {
        **topic,
        "video_url": video_url,
        "video_type": "kling_generated",
    }


# ── Batch entry point ──────────────────────────────────────────────────────────


async def generate_videos_batch(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process Tier 1 topics that don't already have a sourced video.
    All other topics pass through unchanged.
    """
    if not topics:
        return []

    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    storage = StorageManager()

    eligible = [
        t for t in topics
        if t.get("viral_tier") == 1
        and t.get("video_type") not in ("youtube", "vimeo", "kling_generated")
    ]
    skip = [t for t in topics if t not in eligible]

    log.info(
        "[generate_video] %d Tier 1 topics eligible for video generation, %d passing through",
        len(eligible), len(skip),
    )

    processed: List[Dict[str, Any]] = list(skip)

    # Process eligible topics sequentially to avoid GPU/API saturation
    for topic in eligible:
        try:
            result = await _generate_video_for_topic(topic, anthropic_client, storage)
            processed.append(result)
        except Exception as exc:
            log.error(
                "[generate_video] Unhandled exception for topic %s: %s\n%s",
                topic.get("id"), exc, traceback.format_exc(),
            )
            processed.append(topic)

    videos_generated = sum(
        1 for t in processed
        if t.get("video_type") == "kling_generated" and t.get("video_url")
    )
    log.info(
        "[generate_video] Batch complete: %d/%d videos generated",
        videos_generated, len(eligible),
    )
    return processed


# ── LangGraph node ─────────────────────────────────────────────────────────────


def generate_videos(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node — generate text-to-video for Tier 1 topics."""
    batch_id: str = state["batch_id"]
    topics: List[Dict[str, Any]] = state.get("topics", [])

    log.info("[generate_video] node start: %d topics  batch_id=%s", len(topics), batch_id)

    if not topics:
        return {"topics": topics}

    tier1 = sum(1 for t in topics if t.get("viral_tier") == 1)
    print(
        f"[generate_video] {tier1} Tier 1 topics eligible for AI video generation "
        f"(backend={getattr(settings, 'video_backend', 'fal')})",
        flush=True,
    )

    if tier1 == 0:
        log.info("[generate_video] No Tier 1 topics — skipping video generation")
        return {"topics": topics}

    try:
        enriched = asyncio.run(generate_videos_batch(topics))
        done = sum(1 for t in enriched if t.get("video_url") and t.get("video_type") == "kling_generated")
        print(f"[generate_video] Done: {done}/{tier1} Tier 1 topics have AI video.", flush=True)
        # Build telemetry map
        video_urls = {
            str(t.get("id")): t["video_url"]
            for t in enriched
            if t.get("video_url") and t.get("video_type") == "kling_generated"
        }
        return {"topics": enriched, "video_urls": video_urls}
    except Exception as exc:
        msg = f"generate_video: {exc}\n{traceback.format_exc()}"
        log.error(msg)
        return {"topics": topics, "errors": [msg]}
