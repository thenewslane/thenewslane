"""
ElevenLabs voiceover generator for YouTube Shorts / Instagram Reels.

Generates MP3 narration from the youtube_script field using the
eleven_multilingual_v2 model.  Designed for Tier 1 topics only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

from config.settings import settings


log = logging.getLogger(__name__)

# Default voice: "Adam" — neutral, professional male newsreader
_DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"

_BASE_URL = "https://api.elevenlabs.io/v1"


class VoiceoverGenerator:
    """Thin wrapper around the ElevenLabs text-to-speech REST API."""

    def __init__(self) -> None:
        self.api_key: str = settings.elevenlabs_api_key
        # Allow runtime override through the env var captured by pydantic settings
        self.voice_id: str = settings.elevenlabs_voice_id or _DEFAULT_VOICE_ID

        if not self.api_key:
            log.warning("ELEVENLABS_API_KEY is not set; voiceover generation will fail.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(self, script: str, output_path: str) -> str:
        """
        Convert *script* to speech and save the MP3 at *output_path*.

        Returns the resolved absolute path of the saved MP3.
        Raises httpx.HTTPStatusError on API failures.
        """
        if not script or not script.strip():
            raise ValueError("Cannot generate voiceover: script is empty.")

        url = f"{_BASE_URL}/text-to-speech/{self.voice_id}"
        payload = {
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        log.info("[voiceover] generating %d chars with voice=%s", len(script), self.voice_id)

        with httpx.Client(timeout=120) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(response.content)

        log.info("[voiceover] saved %d bytes → %s", len(response.content), output_path)
        return str(out.resolve())

    def check_quota(self) -> int:
        """
        Return the number of characters remaining in the current billing period.

        Returns 0 on any API error so the caller can safely skip voiceover.
        """
        url = f"{_BASE_URL}/user/subscription"
        headers = {"xi-api-key": self.api_key}

        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            limit = int(data.get("character_limit", 0))
            used = int(data.get("character_count", 0))
            remaining = max(0, limit - used)
            log.info("[voiceover] quota: %d / %d chars remaining", remaining, limit)
            return remaining

        except Exception as exc:
            log.error("[voiceover] quota check failed: %s", exc)
            return 0
