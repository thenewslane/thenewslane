"""
generator.py — LTX-Video inference via diffusers.

Loads Lightricks/LTX-Video on CUDA (bfloat16) and generates short video clips
from text prompts.  Called by app.py.

Model: Lightricks/LTX-Video
Hardware target: Vast.ai RTX 4090 spot (~$0.40/hr)
Cost math: 8 clips × ~1 min render = 8 min → 8/60 × $0.40 ≈ $0.053/video
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Optional

import torch

# Lazy import: only resolved at first generate_clip call so the Flask app
# can start quickly even while the model is not yet downloaded.
_pipe = None


def _load_pipeline():
    global _pipe  # noqa: PLW0603
    if _pipe is not None:
        return _pipe

    from diffusers import LTXPipeline  # noqa: PLC0415

    print("[generator] Loading LTX-Video model (first run may download ~5 GB)...", flush=True)
    _pipe = LTXPipeline.from_pretrained(
        "Lightricks/LTX-Video",
        torch_dtype=torch.bfloat16,
    ).to("cuda")
    print("[generator] Model loaded on CUDA.", flush=True)
    return _pipe


class VideoGenerator:
    """Wraps LTX-Video diffusers pipeline for clip generation."""

    def __init__(self) -> None:
        self.pipe = _load_pipeline()

    def generate_clip(
        self,
        prompt: str,
        duration_secs: int = 8,
        negative_prompt: str = "text, watermark, logo, ugly, blurry, distorted, faces",
    ) -> bytes:
        """
        Generate a single video clip and return raw MP4 bytes.

        Args:
            prompt: Text description of the scene.
            duration_secs: Target duration in seconds (default 8).
            negative_prompt: Things to avoid in the generated clip.

        Returns:
            Raw bytes of the generated MP4 file.
        """
        fps = 15
        n_frames = duration_secs * fps  # e.g. 8 × 15 = 120 frames

        result = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            height=480,
            width=848,
            num_frames=n_frames,
            guidance_scale=3.0,
            num_inference_steps=40,
        )

        frames = result.frames[0]  # list of PIL Images

        # Export frames to MP4 via imageio
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            import imageio  # noqa: PLC0415
            writer = imageio.get_writer(tmp_path, fps=fps, codec="libx264", quality=7)
            for frame in frames:
                import numpy as np  # noqa: PLC0415
                writer.append_data(np.array(frame))
            writer.close()
            return Path(tmp_path).read_bytes()
        finally:
            Path(tmp_path).unlink(missing_ok=True)
