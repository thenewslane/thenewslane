"""
utils/video_assembler.py — FFmpeg utilities for YouTube Shorts / Instagram Reels.

All outputs are 1080×1920 (9:16 portrait) H.264 MP4, suitable for Shorts and Reels.

Public API
----------
create_ken_burns_video(image_path, output_path, duration=10)
    Slow zoom-in animation over a static image (100% → 115%) — Tier 2/3 fallback.

add_text_overlay(video_path, output_path, title, source_name, is_ai_generated=False)
    Overlay title + source attribution via Pillow (portable, no freetype needed).

merge_voiceover(video_path, audio_path, output_path)
    Mux ElevenLabs voiceover; video loops if shorter than audio; audio normalised.

create_shorts_package(thumbnail_path, output_path, title, source_name, ...)
    Full pipeline: base video → text overlay → merged audio → final MP4.
"""

from __future__ import annotations

import os
import subprocess
import textwrap
import uuid
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

SHORTS_W = 1080
SHORTS_H = 1920
DEFAULT_FPS = 30
DEFAULT_CRF = 23   # H.264 CRF — lower = better quality / larger file

# 1.15× output dimensions gives zoompan room to zoom without black bars
_KB_W = int(SHORTS_W * 1.15)  # 1242
_KB_H = int(SHORTS_H * 1.15)  # 2208

# ── Font detection ────────────────────────────────────────────────────────────

_FONT_CANDIDATES = [
    # macOS system fonts
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/SFNSDisplay.ttf",
    # Linux / Docker
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf",
]


def _find_font() -> Optional[str]:
    """Return the first available TrueType font path, or None."""
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return path
    return None


# ── Internal FFmpeg runner ────────────────────────────────────────────────────


def _run(*args: str, quiet: bool = True) -> None:
    """
    Execute ``ffmpeg -y <args>``, raising RuntimeError (with stderr tail) on failure.
    """
    cmd = ["ffmpeg", "-y", *args]
    log.debug("FFmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg exited {result.returncode}:\n{result.stderr[-3000:]}")


def _real(path: str) -> str:
    """
    Return the canonical absolute path (resolving symlinks).
    On macOS, /var/folders → /private/var/folders.  Used only internally
    when passing paths to FFmpeg; callers receive their original string back.
    """
    return os.path.realpath(path)


# ── Pillow text overlay helper ────────────────────────────────────────────────


def _build_overlay_image(
    width: int,
    height: int,
    title: str,
    source_name: str,
    is_ai_generated: bool,
    tmp_path: str,
) -> str:
    """
    Render title + attribution text onto a transparent RGBA PNG using Pillow.

    Layout
    ------
    • Semi-transparent dark scrim behind the title (top) and source (bottom).
    • Title — white, bold, 52 px, wrapped at 40 chars, with a soft shadow.
    • Source — white, 30 px, bottom-left corner.
    • AI badge — cyan ``[AI-generated]`` label above the source line (optional).

    Returns the path to the written PNG.
    """
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

    img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = _find_font()

    def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if font_path:
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                pass
        # Pillow built-in bitmap fallback (no external font needed)
        return ImageFont.load_default(size=size)

    side_pad = 60
    title_y  = 80

    # ── Title scrim (top) ─────────────────────────────────────────────────────
    scrim_h = 280
    scrim   = Image.new("RGBA", (width, scrim_h), (0, 0, 0, int(255 * 0.50)))
    img.alpha_composite(scrim, (0, 0))

    # ── Title text ────────────────────────────────────────────────────────────
    title_font  = _font(52)
    wrapped     = textwrap.fill(title, width=40, break_long_words=True)

    # Shadow
    shadow_off = 2
    draw.multiline_text(
        (side_pad + shadow_off, title_y + shadow_off),
        wrapped, font=title_font, fill=(0, 0, 0, 180), spacing=10,
    )
    # Main text
    draw.multiline_text(
        (side_pad, title_y),
        wrapped, font=title_font, fill=(255, 255, 255, 255), spacing=10,
    )

    # ── Source scrim (bottom) ─────────────────────────────────────────────────
    bottom_scrim_h = 140
    b_scrim = Image.new("RGBA", (width, bottom_scrim_h), (0, 0, 0, int(255 * 0.45)))
    img.alpha_composite(b_scrim, (0, height - bottom_scrim_h))

    # ── AI badge ──────────────────────────────────────────────────────────────
    if is_ai_generated:
        badge_font = _font(24)
        badge_y    = height - 122
        draw.text(
            (side_pad + 1, badge_y + 1), "[AI-generated]",
            font=badge_font, fill=(0, 0, 0, 160),
        )
        draw.text(
            (side_pad, badge_y), "[AI-generated]",
            font=badge_font, fill=(0, 229, 255, 217),
        )

    # ── Source attribution ────────────────────────────────────────────────────
    src_font = _font(30)
    src_y    = height - 80
    draw.text(
        (side_pad + 1, src_y + 1), source_name,
        font=src_font, fill=(0, 0, 0, 153),
    )
    draw.text(
        (side_pad, src_y), source_name,
        font=src_font, fill=(255, 255, 255, 230),
    )

    img.save(tmp_path, "PNG")
    log.debug("Overlay image written: %s", tmp_path)
    return tmp_path


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Ken Burns zoom-in effect
# ═══════════════════════════════════════════════════════════════════════════════


def create_ken_burns_video(
    image_path: str,
    output_path: str,
    duration: int = 10,
) -> str:
    """
    Render a slow zoom-in Ken Burns effect from a static image.

    The image fills a 1080×1920 portrait canvas and gently zooms from 100% to
    115% over *duration* seconds using FFmpeg's ``zoompan`` filter.

    Parameters
    ----------
    image_path : str
        Source image (JPEG / PNG). Any aspect ratio is accepted.
    output_path : str
        Destination MP4 path.
    duration : int
        Video length in seconds (default 10).

    Returns
    -------
    str
        *output_path* as passed (not re-resolved).
    """
    fps          = DEFAULT_FPS
    total_frames = duration * fps
    zoom_inc     = round(0.15 / total_frames, 7)

    # Filter graph explanation:
    #  scale  → upscale input to 1242×2208 (115% of 1080×1920), filling the
    #            frame without letterbox, then hard-crop to exact dimensions.
    #  zoompan → smooth zoom from 1.0→1.15, always centred.
    #  format  → force yuv420p for broad H.264 compatibility.
    vf = (
        f"scale={_KB_W}:{_KB_H}:force_original_aspect_ratio=increase,"
        f"crop={_KB_W}:{_KB_H},"
        f"zoompan="
        f"z='if(eq(on\\,1)\\,1.0\\,min(pzoom+{zoom_inc}\\,1.15))':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:"
        f"s={SHORTS_W}x{SHORTS_H}:"
        f"fps={fps},"
        f"format=yuv420p"
    )

    log.info(
        "Ken Burns: %s → %s  (%ds, %dfps, zoom 1.0→1.15)",
        Path(image_path).name, Path(output_path).name, duration, fps,
    )

    _run(
        "-loop", "1",
        "-i",    _real(image_path),
        "-vf",   vf,
        "-t",    str(duration),
        "-c:v",  "libx264",
        "-preset", "fast",
        "-crf",  str(DEFAULT_CRF),
        "-movflags", "+faststart",
        "-an",
        _real(output_path),
    )

    log.info("Ken Burns done → %s", output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  Text overlay  (Pillow-based, no FFmpeg freetype dependency)
# ═══════════════════════════════════════════════════════════════════════════════


def add_text_overlay(
    video_path: str,
    output_path: str,
    title: str,
    source_name: str,
    is_ai_generated: bool = False,
) -> str:
    """
    Burn title and source attribution text into a video.

    Uses **Pillow** to render text onto a transparent PNG (so no FFmpeg freetype
    dependency is required), then composites it with the video via FFmpeg's
    ``overlay`` filter.

    Parameters
    ----------
    video_path : str
        Source MP4.
    output_path : str
        Destination MP4.
    title : str
        Headline. Auto-wrapped at 40 characters.
    source_name : str
        Attribution string (e.g. ``"theNewslane"``).
    is_ai_generated : bool
        When True, adds a small ``[AI-generated]`` cyan badge above the source.

    Returns
    -------
    str
        *output_path* as passed.
    """
    tmp_png = f"/tmp/_overlay_{uuid.uuid4().hex[:8]}.png"

    try:
        _build_overlay_image(
            SHORTS_W, SHORTS_H,
            title=title,
            source_name=source_name,
            is_ai_generated=is_ai_generated,
            tmp_path=tmp_png,
        )

        log.info(
            "Text overlay: %s → %s (ai=%s)",
            Path(video_path).name, Path(output_path).name, is_ai_generated,
        )

        _run(
            "-i",  _real(video_path),
            "-i",  tmp_png,
            "-filter_complex", "overlay=0:0",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf",    str(DEFAULT_CRF),
            "-c:a",    "copy",
            "-movflags", "+faststart",
            _real(output_path),
        )

    finally:
        Path(tmp_png).unlink(missing_ok=True)

    log.info("Text overlay done → %s", output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Voiceover merge
# ═══════════════════════════════════════════════════════════════════════════════


def merge_voiceover(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """
    Mux an ElevenLabs (or any) voiceover audio file into a video.

    • Video is looped with ``-stream_loop -1`` to cover any audio length.
    • Audio is normalised to −14 LUFS (EBU R128) via ``loudnorm``.
    • Output stops when the audio ends (``-shortest``).

    Parameters
    ----------
    video_path : str
        Source MP4 (any existing audio is replaced).
    audio_path : str
        Voiceover file — MP3, M4A, WAV, etc.
    output_path : str
        Destination MP4.

    Returns
    -------
    str
        *output_path* as passed.
    """
    log.info(
        "Merge voiceover: %s + %s → %s",
        Path(video_path).name, Path(audio_path).name, Path(output_path).name,
    )

    _run(
        "-stream_loop", "-1",
        "-i",           _real(video_path),
        "-i",           _real(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v",  "copy",
        "-c:a",  "aac",
        "-b:a",  "192k",
        "-af",   "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-shortest",
        "-movflags", "+faststart",
        _real(output_path),
    )

    log.info("Voiceover merge done → %s", output_path)
    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Full Shorts package orchestrator
# ═══════════════════════════════════════════════════════════════════════════════


def create_shorts_package(
    thumbnail_path: str,
    output_path: str,
    title: str,
    source_name: str,
    ai_video_path: Optional[str] = None,
    voiceover_path: Optional[str] = None,
    duration: int = 10,
    is_ai_generated: bool = False,
) -> str:
    """
    Orchestrate the full YouTube Shorts / Reels production pipeline.

    Steps
    -----
    1. **Base video** — use *ai_video_path* if it exists, otherwise run
       :func:`create_ken_burns_video` on *thumbnail_path*.
    2. **Text overlay** — :func:`add_text_overlay` burns title + source.
    3. **Voiceover** (optional) — :func:`merge_voiceover` replaces the silent
       track with the narration file, looping video as needed.

    Parameters
    ----------
    thumbnail_path : str
        Fallback still image used when no AI video is available.
    output_path : str
        Final MP4 destination path.
    title : str
        Article headline for the text overlay.
    source_name : str
        Publication / brand name for the attribution line.
    ai_video_path : str, optional
        Pre-rendered AI video (e.g. Kling). When provided, Ken Burns is skipped.
    voiceover_path : str, optional
        ElevenLabs MP3/WAV. Omit for a silent final video.
    duration : int
        Ken Burns duration in seconds (ignored when *ai_video_path* is given).
    is_ai_generated : bool
        When True, an ``[AI-generated]`` badge is shown in the overlay.

    Returns
    -------
    str
        *output_path* as passed.
    """
    import shutil

    out     = Path(output_path)
    tmp_dir = out.parent / f"_tmp_{out.stem}_{uuid.uuid4().hex[:6]}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Base video ────────────────────────────────────────────────
        if ai_video_path and Path(ai_video_path).exists():
            log.info("Shorts: using AI video as base: %s", ai_video_path)
            base_video = ai_video_path
        else:
            if ai_video_path:
                log.warning(
                    "Shorts: ai_video_path '%s' not found — falling back to Ken Burns",
                    ai_video_path,
                )
            log.info("Shorts: creating Ken Burns base from thumbnail")
            base_video = str(tmp_dir / "01_ken_burns.mp4")
            create_ken_burns_video(thumbnail_path, base_video, duration=duration)

        # ── Step 2: Text overlay ──────────────────────────────────────────────
        overlaid = str(tmp_dir / "02_overlaid.mp4")
        add_text_overlay(
            base_video, overlaid,
            title=title, source_name=source_name,
            is_ai_generated=is_ai_generated,
        )

        # ── Step 3: Voiceover ─────────────────────────────────────────────────
        if voiceover_path and Path(voiceover_path).exists():
            merge_voiceover(overlaid, voiceover_path, output_path)
        else:
            if voiceover_path:
                log.warning(
                    "Shorts: voiceover_path '%s' not found — skipping audio merge",
                    voiceover_path,
                )
            shutil.copy2(overlaid, output_path)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    log.info("Shorts package complete → %s", output_path)
    return output_path


# ─── CLI smoke test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python video_assembler.py <image.jpg> [output.mp4]")
        sys.exit(1)

    img = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/test_shorts.mp4"

    result = create_shorts_package(
        thumbnail_path=img,
        output_path=out,
        title="Breaking: Scientists Discover Water on Mars",
        source_name="theNewslane",
    )
    print(f"✓ Created: {result}")
