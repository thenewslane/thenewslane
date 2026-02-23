"""
tests/test_video_assembler.py — Integration tests for video_assembler.py.

These tests require:
  • FFmpeg binary in $PATH
  • Pillow (for generating test images without external assets)

Run:
    cd apps/agent && .venv/bin/python -m pytest tests/test_video_assembler.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ── Pytest markers ────────────────────────────────────────────────────────────

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="FFmpeg binary not found in PATH",
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _probe(path: str) -> dict:
    """Return basic stream info via ffprobe."""
    import json

    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            path,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ffprobe failed: {result.stderr}"
    return json.loads(result.stdout)


def _video_stream(probe_data: dict) -> dict:
    for s in probe_data["streams"]:
        if s["codec_type"] == "video":
            return s
    pytest.fail("No video stream found in output")


def _audio_stream(probe_data: dict) -> dict | None:
    for s in probe_data["streams"]:
        if s["codec_type"] == "audio":
            return s
    return None


def _make_test_image(path: Path, width: int = 1242, height: int = 2208) -> Path:
    """
    Create a solid-colour JPEG test image using either Pillow or FFmpeg
    (whichever is available).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

        img = Image.new("RGB", (width, height), color=(30, 80, 160))
        draw = ImageDraw.Draw(img)
        # Diagonal gradient-like stripes for visual interest
        for i in range(0, width + height, 80):
            draw.line([(i, 0), (0, i)], fill=(20, 60, 120), width=4)
        draw.rectangle([100, 100, width - 100, 350], fill=(0, 0, 0, 128))
        draw.text((120, 140), "TEST IMAGE", fill="white")
        img.save(str(path), "JPEG", quality=92)
    except ImportError:
        # Fall back to FFmpeg lavfi
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x1E50A0:s={width}x{height}",
                "-vframes", "1",
                str(path),
            ],
            check=True,
            capture_output=True,
        )
    return path


def _make_silent_audio(path: Path, duration: float = 12.0) -> Path:
    """Generate a short silent MP3 for voiceover tests."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(duration),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tmp_dir():
    d = tempfile.mkdtemp(prefix="va_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def test_image(tmp_dir):
    return _make_test_image(tmp_dir / "input.jpg")


@pytest.fixture(scope="module")
def short_video(tmp_dir, test_image):
    """5-second Ken Burns clip used as a shared base for downstream tests."""
    from utils.video_assembler import create_ken_burns_video

    out = str(tmp_dir / "base_5s.mp4")
    create_ken_burns_video(str(test_image), out, duration=5)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1 — Ken Burns
# ═══════════════════════════════════════════════════════════════════════════════


@requires_ffmpeg
def test_ken_burns_creates_file(tmp_dir, test_image):
    from utils.video_assembler import create_ken_burns_video

    out = str(tmp_dir / "kb_5s.mp4")
    result = create_ken_burns_video(str(test_image), out, duration=5)

    # On macOS /var/folders is a symlink to /private/var/folders; samefile handles that
    assert os.path.samefile(result, out)
    assert Path(out).exists()
    assert Path(out).stat().st_size > 10_000, "Output file suspiciously small"


@requires_ffmpeg
def test_ken_burns_video_properties(tmp_dir, test_image):
    from utils.video_assembler import create_ken_burns_video

    out = str(tmp_dir / "kb_props.mp4")
    create_ken_burns_video(str(test_image), out, duration=5)

    probe = _probe(out)
    vs    = _video_stream(probe)

    assert vs["width"]  == 1080, f"Expected width 1080, got {vs['width']}"
    assert vs["height"] == 1920, f"Expected height 1920, got {vs['height']}"
    assert vs["codec_name"] == "h264"

    duration = float(probe["format"]["duration"])
    assert 4.5 <= duration <= 6.0, f"Expected ~5s duration, got {duration:.2f}s"


@requires_ffmpeg
def test_ken_burns_no_audio_track(short_video):
    probe = _probe(short_video)
    audio = _audio_stream(probe)
    assert audio is None, "Ken Burns output should have no audio track"


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2 — Text overlay
# ═══════════════════════════════════════════════════════════════════════════════


@requires_ffmpeg
def test_text_overlay_creates_file(tmp_dir, short_video):
    from utils.video_assembler import add_text_overlay

    out = str(tmp_dir / "overlay.mp4")
    result = add_text_overlay(
        short_video, out,
        title="Breaking: Scientists Discover Water on Mars",
        source_name="theNewslane",
    )
    assert os.path.samefile(result, out)
    assert Path(out).exists()
    assert Path(out).stat().st_size > 10_000


@requires_ffmpeg
def test_text_overlay_preserves_resolution(tmp_dir, short_video):
    from utils.video_assembler import add_text_overlay

    out = str(tmp_dir / "overlay_res.mp4")
    add_text_overlay(short_video, out, title="Test Title", source_name="Source")

    vs = _video_stream(_probe(out))
    assert vs["width"]  == 1080
    assert vs["height"] == 1920


@requires_ffmpeg
def test_text_overlay_long_title_wraps(tmp_dir, short_video):
    """A title longer than 40 chars must not raise an exception."""
    from utils.video_assembler import add_text_overlay

    long_title = (
        "Scientists Make Unprecedented Discovery of Liquid Water "
        "Deep Beneath the Surface of Mars, Raising New Questions About Life"
    )
    out = str(tmp_dir / "overlay_long.mp4")
    # Should not raise
    add_text_overlay(short_video, out, title=long_title, source_name="theNewslane")
    assert Path(out).exists()


@requires_ffmpeg
def test_text_overlay_ai_badge(tmp_dir, short_video):
    """is_ai_generated=True must succeed and produce a valid file."""
    from utils.video_assembler import add_text_overlay

    out = str(tmp_dir / "overlay_ai.mp4")
    add_text_overlay(
        short_video, out,
        title="AI-Powered News Digest",
        source_name="theNewslane",
        is_ai_generated=True,
    )
    assert Path(out).exists()
    assert Path(out).stat().st_size > 10_000


@requires_ffmpeg
def test_text_overlay_special_chars(tmp_dir, short_video):
    """Titles with colons and apostrophes must not crash FFmpeg."""
    from utils.video_assembler import add_text_overlay

    out = str(tmp_dir / "overlay_special.mp4")
    add_text_overlay(
        short_video, out,
        title="It's Here: The World's Fastest GPU",
        source_name="theNewslane",
    )
    assert Path(out).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3 — Voiceover merge
# ═══════════════════════════════════════════════════════════════════════════════


@requires_ffmpeg
def test_merge_voiceover_creates_file(tmp_dir, short_video):
    from utils.video_assembler import merge_voiceover

    audio = _make_silent_audio(tmp_dir / "vo_12s.mp3", duration=12.0)
    out   = str(tmp_dir / "merged.mp4")
    result = merge_voiceover(short_video, str(audio), out)

    assert os.path.samefile(result, out)
    assert Path(out).exists()
    assert Path(out).stat().st_size > 10_000


@requires_ffmpeg
def test_merge_voiceover_has_audio_track(tmp_dir, short_video):
    from utils.video_assembler import merge_voiceover

    audio = _make_silent_audio(tmp_dir / "vo_probe.mp3", duration=8.0)
    out   = str(tmp_dir / "merged_probe.mp4")
    merge_voiceover(short_video, str(audio), out)

    probe = _probe(out)
    audio_s = _audio_stream(probe)
    assert audio_s is not None, "Merged video must have an audio track"
    assert audio_s["codec_name"] == "aac"


@requires_ffmpeg
def test_merge_voiceover_duration_matches_audio(tmp_dir, short_video):
    """Output duration should match the 12 s audio, even though video is 5 s."""
    from utils.video_assembler import merge_voiceover

    audio_dur = 12.0
    audio     = _make_silent_audio(tmp_dir / "vo_dur.mp3", duration=audio_dur)
    out       = str(tmp_dir / "merged_dur.mp4")
    merge_voiceover(short_video, str(audio), out)

    actual_dur = float(_probe(out)["format"]["duration"])
    assert abs(actual_dur - audio_dur) < 1.5, (
        f"Expected ~{audio_dur}s, got {actual_dur:.2f}s"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4 — Full Shorts package
# ═══════════════════════════════════════════════════════════════════════════════


@requires_ffmpeg
def test_shorts_package_no_voiceover(tmp_dir, test_image):
    """Full pipeline without voiceover — silent MP4."""
    from utils.video_assembler import create_shorts_package

    out = str(tmp_dir / "shorts_silent.mp4")
    result = create_shorts_package(
        thumbnail_path=str(test_image),
        output_path=out,
        title="Breaking: Scientists Discover Water on Mars",
        source_name="theNewslane",
        duration=5,
    )

    assert os.path.samefile(result, out)
    assert Path(out).exists()

    probe = _probe(out)
    vs    = _video_stream(probe)
    assert vs["width"]  == 1080
    assert vs["height"] == 1920
    assert float(probe["format"]["duration"]) > 4.0


@requires_ffmpeg
def test_shorts_package_with_voiceover(tmp_dir, test_image):
    """Full pipeline with voiceover — duration follows the audio."""
    from utils.video_assembler import create_shorts_package

    vo  = _make_silent_audio(tmp_dir / "vo_pkg.mp3", duration=12.0)
    out = str(tmp_dir / "shorts_voiced.mp4")
    create_shorts_package(
        thumbnail_path=str(test_image),
        output_path=out,
        title="Olympic Gold: USA Wins Ice Hockey After 46 Years",
        source_name="theNewslane",
        voiceover_path=str(vo),
        duration=5,
    )

    probe   = _probe(out)
    vs      = _video_stream(probe)
    audio_s = _audio_stream(probe)
    dur     = float(probe["format"]["duration"])

    assert vs["width"]  == 1080
    assert vs["height"] == 1920
    assert audio_s is not None
    assert abs(dur - 12.0) < 1.5, f"Expected ~12s, got {dur:.2f}s"


@requires_ffmpeg
def test_shorts_package_with_ai_video(tmp_dir, short_video, test_image):
    """When ai_video_path is provided, Ken Burns is skipped."""
    from utils.video_assembler import create_shorts_package

    out = str(tmp_dir / "shorts_ai_video.mp4")
    create_shorts_package(
        thumbnail_path=str(test_image),
        output_path=out,
        title="Tech Breakthrough: AI Writes Its Own Code",
        source_name="theNewslane",
        ai_video_path=short_video,
        is_ai_generated=True,
        duration=5,
    )

    assert Path(out).exists()
    vs = _video_stream(_probe(out))
    assert vs["width"]  == 1080
    assert vs["height"] == 1920


@requires_ffmpeg
def test_shorts_package_missing_ai_video_falls_back(tmp_dir, test_image):
    """Non-existent ai_video_path must silently fall back to Ken Burns."""
    from utils.video_assembler import create_shorts_package

    out = str(tmp_dir / "shorts_fallback.mp4")
    create_shorts_package(
        thumbnail_path=str(test_image),
        output_path=out,
        title="Fallback Test",
        source_name="theNewslane",
        ai_video_path="/tmp/does_not_exist_12345.mp4",
        duration=5,
    )
    assert Path(out).exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Standalone runner — creates a real sample Shorts video
# ═══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    """
    Run directly to produce a sample Shorts video you can preview:
        cd apps/agent && .venv/bin/python tests/test_video_assembler.py
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.video_assembler import create_shorts_package  # noqa: E402

    if shutil.which("ffmpeg") is None:
        print("✗ FFmpeg not found in PATH — install with: brew install ffmpeg")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_p  = Path(tmp)
        img    = _make_test_image(tmp_p / "sample.jpg")
        output = Path.home() / "Desktop" / "sample_shorts.mp4"

        print(f"Building sample Shorts video → {output}")
        create_shorts_package(
            thumbnail_path=str(img),
            output_path=str(output),
            title="Breaking: Scientists Discover Evidence of Life on Mars",
            source_name="theNewslane",
            duration=10,
        )

    if output.exists():
        size_mb = output.stat().st_size / 1_048_576
        print(f"✓ Created {output}  ({size_mb:.1f} MB)")
        print(f"  Open with: open '{output}'")
    else:
        print("✗ Output file was not created")
        sys.exit(1)
