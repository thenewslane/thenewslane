"""
nodes/brand_safety_filters.py — Three-tier brand safety filtering classes.

Tier 1: KeywordFilter - Supabase config-based keyword blocklist
Tier 2: LlamaGuardFilter - Groq API with llama-guard-3-8b
Tier 3: BrandSafetyLLMFilter - Claude Haiku 3.5 brand safety assessment
"""

from __future__ import annotations

import json
import re
from typing import Any

import anthropic
import httpx
from groq import Groq

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)


class KeywordFilter:
    """Tier 1: Fast keyword-based filtering using config table blocklist."""

    def __init__(self) -> None:
        self.blocked_keywords: list[str] = []
        self._load_keywords()

    def _load_keywords(self) -> None:
        """Load blocked keywords from Supabase config table."""
        try:
            self.blocked_keywords = db.get_config_value("keyword_blocklist", default=[])
            log.debug("KeywordFilter: loaded %d blocked keywords", len(self.blocked_keywords))
        except Exception as e:
            log.error("KeywordFilter: failed to load keywords: %s", e)
            self.blocked_keywords = []

    def check(self, topic_title: str, headline_cluster: str) -> tuple[bool, str | None]:
        """
        Check topic title and headline cluster against blocked keywords.
        
        Returns:
            tuple[bool, str | None]: (is_safe, blocked_keyword_if_any)
        """
        text_to_check = f"{topic_title} {headline_cluster}".lower()
        
        for keyword in self.blocked_keywords:
            if keyword.lower() in text_to_check:
                log.info("KeywordFilter: blocked topic '%s' for keyword '%s'", topic_title, keyword)
                return False, keyword
        
        return True, None


class LlamaGuardFilter:
    """Tier 2: Llama Guard 3 via Groq API for toxicity/harm classification."""

    HARM_CATEGORIES = [
        "S1: Violent Crimes",
        "S2: Non-Violent Crimes", 
        "S3: Sex Crimes",
        "S4: Child Exploitation",
        "S5: Defamation",
        "S6: Specialized Advice",
        "S7: Privacy",
        "S8: Intellectual Property",
        "S9: Indiscriminate Weapons",
        "S10: Hate",
        "S11: Self-Harm",
        "S12: Sexual Content",
        "S13: Elections",
        "S14: Code Interpreter Abuse"
    ]

    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for LlamaGuardFilter")
        self.client = Groq(api_key=settings.groq_api_key)

    def check(self, topic_title: str, headline_cluster: str) -> tuple[bool, list[str]]:
        """
        Check content using Llama Guard 3 via Groq.
        
        Returns:
            tuple[bool, list[str]]: (is_safe, flagged_categories)
        """
        try:
            # Format content for Llama Guard
            content = f"Topic: {topic_title}\nHeadlines: {headline_cluster}"
            
            # Llama Guard conversation format
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]

            response = self.client.chat.completions.create(
                model="meta-llama/Llama-Guard-3-11B-Vision-Turbo",
                messages=messages,
                temperature=0.0,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            log.debug("LlamaGuardFilter: raw response: %s", result)

            # Parse response - Llama Guard returns "safe" or "unsafe\nS1,S3" etc.
            if result.lower().startswith("safe"):
                return True, []
            elif result.lower().startswith("unsafe"):
                # Extract flagged categories
                lines = result.split('\n')
                flagged = []
                if len(lines) > 1:
                    # Parse category codes like "S1,S3,S10"
                    category_codes = lines[1].split(',')
                    for code in category_codes:
                        code = code.strip()
                        # Map S1 -> "S1: Violent Crimes" etc.
                        for category in self.HARM_CATEGORIES:
                            if category.startswith(code + ":"):
                                flagged.append(category)
                                break
                
                log.info("LlamaGuardFilter: flagged topic '%s' for categories: %s", 
                        topic_title, flagged)
                return False, flagged
            else:
                log.warning("LlamaGuardFilter: unexpected response format: %s", result)
                return True, []  # Default to safe on parsing errors

        except Exception as e:
            log.error("LlamaGuardFilter: API error for topic '%s': %s", topic_title, e)
            return True, []  # Default to safe on API errors


class BrandSafetyLLMFilter:
    """Tier 3: Claude Haiku brand safety assessment for advertiser suitability."""

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for BrandSafetyLLMFilter")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def check(self, topic_title: str, headline_cluster: str) -> tuple[bool, str]:
        """
        Check brand safety using Claude Haiku.
        
        Returns:
            tuple[bool, str]: (is_safe, explanation)
        """
        try:
            prompt = f"""You are a brand safety reviewer. A mainstream advertiser like Toyota or Procter and Gamble needs to decide if their ad should appear next to content about this topic.

Topic: {topic_title}
Headlines: {headline_cluster}

Would a major advertiser be comfortable? Answer: SAFE or UNSAFE and one sentence explanation."""

            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.0
            )

            result = response.content[0].text.strip()
            log.debug("BrandSafetyLLMFilter: raw response: %s", result)

            # Parse response for SAFE/UNSAFE
            result_upper = result.upper()
            if result_upper.startswith("SAFE"):
                return True, result
            elif result_upper.startswith("UNSAFE"):
                log.info("BrandSafetyLLMFilter: flagged topic '%s': %s", topic_title, result)
                return False, result
            else:
                log.warning("BrandSafetyLLMFilter: unexpected response format: %s", result)
                return True, result  # Default to safe on parsing errors

        except Exception as e:
            log.error("BrandSafetyLLMFilter: API error for topic '%s': %s", topic_title, e)
            return True, f"Error: {e}"  # Default to safe on API errors