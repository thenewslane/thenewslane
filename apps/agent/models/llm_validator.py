"""
models/llm_validator.py — LLM-based validator for borderline viral scores.

Calls Claude Haiku 3.5 only for topics whose score falls in the 8–12 band.
  yes answer → score + 2.6
  no  answer → score - 2.6

Outside the band: score is returned unchanged, no API call is made.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from utils.logger import get_logger

log = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
# Reduced by 80% to be more permissive

_LLM_BAND_LOW:   float = 8.0   # was 40.0
_LLM_BAND_HIGH:  float = 12.0  # was 60.0
_SCORE_BOOST:    float = 2.6   # was 13.0
_HAIKU_MODEL:    str   = "claude-haiku-4-5-20251001"


# ── Result object ─────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Output of LLMValidator.validate()."""

    adjusted_score: float
    llm_called:     bool
    llm_verdict:    bool | None    # True=yes(boost), False=no(penalise), None=ambiguous/error
    llm_reasoning:  str | None
    llm_confidence: float | None   # 1.0=confident yes/no, 0.5=ambiguous


# ── LLMValidator ──────────────────────────────────────────────────────────────


class LLMValidator:
    """
    Uses Claude Haiku 3.5 to validate borderline viral predictions.

    Only invoked when the raw score is in [LLM_BAND_LOW, LLM_BAND_HIGH].
    All other scores pass through unchanged.
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic()

    def validate(
        self,
        topic_name: str,
        score: float,
        signal_summary: str,
    ) -> ValidationResult:
        """
        Validate a topic score using Claude Haiku.

        Args:
            topic_name:     The topic keyword / title.
            score:          Current 0–100 score from LinearScorer.
            signal_summary: Human-readable summary of engagement signals.

        Returns:
            ValidationResult with adjusted_score and LLM metadata.
        """
        if not (_LLM_BAND_LOW <= score <= _LLM_BAND_HIGH):
            return ValidationResult(
                adjusted_score=score,
                llm_called=False,
                llm_verdict=None,
                llm_reasoning=None,
                llm_confidence=None,
            )

        prompt = (
            f"Based on this trending topic and its signals, will it gain significantly more "
            f"attention in the next 4 hours? "
            f"Topic: {topic_name}. "
            f"Current signals: {signal_summary}. "
            f"Answer yes or no followed by one sentence of reasoning."
        )

        try:
            message = self._client.messages.create(
                model=_HAIKU_MODEL,
                max_tokens=64,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text.strip().lower()
        except Exception as exc:
            log.warning("LLMValidator: API call failed for %r: %s", topic_name, exc)
            return ValidationResult(
                adjusted_score=score,
                llm_called=True,
                llm_verdict=None,
                llm_reasoning=f"API error: {exc}",
                llm_confidence=None,
            )

        # ── Parse yes / no ────────────────────────────────────────────────────
        if response_text.startswith("yes"):
            verdict    = True
            adjusted   = min(score + _SCORE_BOOST, 100.0)
            confidence = 1.0
        elif response_text.startswith("no"):
            verdict    = False
            adjusted   = max(score - _SCORE_BOOST, 0.0)
            confidence = 1.0
        else:
            verdict    = None
            adjusted   = score   # no adjustment for ambiguous response
            confidence = 0.5
            log.warning(
                "LLMValidator: ambiguous response for %r: %r",
                topic_name,
                response_text,
            )

        # Extract the reasoning sentence (everything after the first word)
        parts = response_text.split(None, 1)
        reasoning = parts[1].strip() if len(parts) > 1 else response_text

        return ValidationResult(
            adjusted_score=round(adjusted, 2),
            llm_called=True,
            llm_verdict=verdict,
            llm_reasoning=reasoning,
            llm_confidence=confidence,
        )
