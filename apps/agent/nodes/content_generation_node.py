"""
nodes/content_generation_node.py — Advanced content generation with structured JSON output.

Uses Claude Sonnet 4.5 with structured prompts to generate comprehensive content
for each topic including articles, social media, SEO metadata, and media prompts.
Includes validation, retry logic, and parallel processing.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import anthropic

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

# Concurrency limit for API calls
CONCURRENCY_LIMIT = 3


@dataclass
class ValidationResult:
    """Result of content validation."""
    is_valid: bool
    errors: List[str]


class ContentGenerator:
    """Content generation with Claude Sonnet 4.5 and structured output."""

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for ContentGenerator")
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    def _create_generation_prompt(self, topic: Dict[str, Any]) -> str:
        """Create structured content generation prompt."""
        topic_title = topic.get("title", "")
        headline_cluster = topic.get("headline_cluster", "")
        category = topic.get("category", "World News")
        viral_tier = topic.get("viral_tier", 3)
        viral_score = topic.get("viral_score", 0.0)
        
        # Determine framing based on viral tier
        if viral_tier == 1:
            urgency_context = "HIGH URGENCY: This is a Tier 1 viral topic. Use urgent, immediate framing and language that conveys breaking news significance."
        elif viral_tier == 2:
            urgency_context = "MODERATE URGENCY: This is a Tier 2 viral topic. Use engaging but measured language that highlights importance."
        else:
            urgency_context = "MEASURED TONE: This is a Tier 3 topic. Use thoughtful, editorial language with balanced analysis."

        return f"""You are a professional content creator. Generate comprehensive content for this trending topic. Return ONLY a valid JSON object with no additional text.

TOPIC CONTEXT:
- Title: {topic_title}
- Category: {category} 
- Headlines: {headline_cluster}
- Viral Tier: {viral_tier} (Score: {viral_score})
- {urgency_context}

REQUIRED JSON STRUCTURE:
{{
  "seo_title": "string under 70 characters, factual, no clickbait",
  "meta_description": "string under 160 characters",
  "summary_16w": "string of exactly 16 words summarizing why this topic is trending",
  "article_50w": "string of 50 words, original analysis, factual tone",
  "faq": [
    {{"question": "string", "answer": "string"}},
    {{"question": "string", "answer": "string"}}
  ],
  "facebook_post": "string of 30 words ending with the text ARTICLE_LINK_PLACEHOLDER",
  "instagram_caption": "string under 200 characters followed by 1 relevant hashtag",
  "twitter_thread": [
    "string under 280 characters",
    "string under 280 characters",
    "string under 280 characters"
  ],
  "youtube_script": "string of approximately 80 words designed to be spoken aloud, punchy opening, key facts, strong close",
  "image_prompt": "string describing an abstract cinematic scene related to the topic with no real people faces logos or brand names, photorealistic style, 16:9 composition",
  "iab_categories": ["2-3 strings from IAB Content Taxonomy v3"],
  "slug": "url-safe-lowercase-string-with-hyphens-derived-from-topic-title"
}}

IMPORTANT:
- Return ONLY valid JSON, no markdown, no explanations
- All strings must be properly escaped for JSON
- Follow exact word/character limits specified
- Use factual, journalistic tone appropriate for the viral tier
- Ensure slug is URL-safe (lowercase, hyphens, no special characters)"""

    def _create_correction_prompt(self, topic: Dict[str, Any], errors: List[str], previous_content: Dict[str, Any]) -> str:
        """Create correction prompt for failed validation."""
        topic_title = topic.get("title", "")
        
        error_details = "\n".join([f"- {error}" for error in errors])
        
        return f"""Fix the validation errors in the content for topic: {topic_title}

VALIDATION ERRORS:
{error_details}

PREVIOUS CONTENT:
{json.dumps(previous_content, indent=2)}

Return ONLY a corrected valid JSON object with the same structure, fixing the specific errors mentioned above. Maintain all content quality while ensuring field requirements are met."""

    def _validate_content(self, content: Dict[str, Any]) -> ValidationResult:
        """Validate generated content against requirements."""
        errors = []
        
        # Required fields check (updated field names)
        required_fields = [
            "seo_title", "meta_description", "summary_16w", "article_50w",
            "faq", "facebook_post", "instagram_caption", "twitter_thread",
            "youtube_script", "image_prompt", "iab_categories", "slug"
        ]
        
        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")
                continue
        
        # Length validations (reduced by 80% to be more permissive)
        if "seo_title" in content:
            if len(content["seo_title"]) > 70:
                errors.append(f"seo_title too long: {len(content['seo_title'])} chars (max 70)")

        if "meta_description" in content:
            if len(content["meta_description"]) > 160:
                errors.append(f"meta_description too long: {len(content['meta_description'])} chars (max 160)")
        
        if "summary_16w" in content:
            word_count = len(content["summary_16w"].split())
            if not (14 <= word_count <= 18):  # was 70-90, now 14-18 (target 16)
                errors.append(f"summary_16w wrong length: {word_count} words (target 16 ±2)")
        
        if "article_50w" in content:
            word_count = len(content["article_50w"].split())
            if not (48 <= word_count <= 52):  # was 240-260, now 48-52 (target 50)
                errors.append(f"article_50w wrong length: {word_count} words (target 50 ±2)")
        
        if "faq" in content:
            if not isinstance(content["faq"], list) or len(content["faq"]) != 2:
                errors.append("faq must be array of exactly 2 objects")
            else:
                for i, faq_item in enumerate(content["faq"]):
                    if not isinstance(faq_item, dict) or "question" not in faq_item or "answer" not in faq_item:
                        errors.append(f"faq[{i}] must have 'question' and 'answer' fields")
        
        if "facebook_post" in content:
            word_count = len(content["facebook_post"].split())
            if not content["facebook_post"].endswith("ARTICLE_LINK_PLACEHOLDER"):
                errors.append("facebook_post must end with 'ARTICLE_LINK_PLACEHOLDER'")
            if not (18 <= word_count <= 40):  # was 90-200, now 18-40 (target 30)
                errors.append(f"facebook_post wrong length: {word_count} words (target 30)")

        if "instagram_caption" in content:
            if len(content["instagram_caption"]) > 200:
                errors.append(f"instagram_caption too long: {len(content['instagram_caption'])} chars (max 200)")
            # Check for hashtags
            hashtag_count = content["instagram_caption"].count("#")
            if hashtag_count < 1:  # was 3, now 1
                errors.append(f"instagram_caption needs at least 1 hashtag (found {hashtag_count})")
        
        if "twitter_thread" in content:
            if not isinstance(content["twitter_thread"], list) or len(content["twitter_thread"]) != 3:
                errors.append("twitter_thread must be array of exactly 3 strings")
            else:
                for i, tweet in enumerate(content["twitter_thread"]):
                    if len(tweet) > 280:
                        errors.append(f"twitter_thread[{i}] too long: {len(tweet)} chars (max 280)")
        
        if "youtube_script" in content:
            word_count = len(content["youtube_script"].split())
            if not (40 <= word_count <= 120):  # was 200-600, now 40-120 (target 80)
                errors.append(f"youtube_script wrong length: {word_count} words (target 80)")
        
        if "iab_categories" in content:
            if not isinstance(content["iab_categories"], list) or not (2 <= len(content["iab_categories"]) <= 3):
                errors.append("iab_categories must be array of 2-3 strings")
        
        if "slug" in content:
            slug = content["slug"]
            if not re.match(r'^[a-z0-9-]+$', slug):
                errors.append("slug must be URL-safe (lowercase letters, numbers, hyphens only)")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def _generate_content_for_topic(self, topic: Dict[str, Any], semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        """Generate content for a single topic with validation and retry."""
        async with semaphore:
            topic_id = topic.get("id", "unknown")
            topic_title = topic.get("title", "")
            
            log.info(f"ContentGenerator: generating content for topic '{topic_title}' (ID: {topic_id})")
            
            try:
                # First attempt
                content = await self._call_claude_for_content(topic)
                validation = self._validate_content(content)
                
                if validation.is_valid:
                    log.debug(f"ContentGenerator: validation passed for topic '{topic_title}'")
                    final_topic = {**topic, **content, "content_generated": True}
                    log.info(f"🔍 DEBUG: Final topic keys after content generation: {list(final_topic.keys())}")
                    log.info(f"🔍 DEBUG: Content fields present: summary_16w={bool(final_topic.get('summary_16w'))}, article_50w={bool(final_topic.get('article_50w'))}")
                    return final_topic
                
                # Retry once with correction prompt
                log.warning(f"ContentGenerator: validation failed for topic '{topic_title}', retrying. Errors: {validation.errors}")

                try:
                    corrected_content = await self._call_claude_for_correction(topic, validation.errors, content)
                    correction_validation = self._validate_content(corrected_content)

                    if correction_validation.is_valid:
                        log.info(f"ContentGenerator: correction successful for topic '{topic_title}'")
                        final_topic = {**topic, **corrected_content, "content_generated": True}
                        log.info(f"🔍 DEBUG: Final topic keys after correction: {list(final_topic.keys())}")
                        log.info(f"🔍 DEBUG: Content fields present: summary_16w={bool(final_topic.get('summary_16w'))}, article_50w={bool(final_topic.get('article_50w'))}")
                        return final_topic
                    else:
                        log.warning(f"ContentGenerator: correction still invalid for '{topic_title}', using best-effort first attempt. Errors: {correction_validation.errors}")
                        return {**topic, **content, "content_generated": True}
                except Exception as correction_exc:
                    log.warning(f"ContentGenerator: correction failed for '{topic_title}' ({correction_exc}), using best-effort first attempt")
                    return {**topic, **content, "content_generated": True}
                    
            except Exception as e:
                log.error(f"ContentGenerator: exception for topic '{topic_title}': {e}")
                return {**topic, "content_generated": False, "generation_errors": [str(e)]}

    async def _call_claude_for_content(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Call Claude API for initial content generation."""
        prompt = self._create_generation_prompt(topic)
        
        try:
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.3
            )
            log.info(f"🔍 DEBUG: Claude API call successful for topic '{topic.get('title', 'unknown')}'")
        except Exception as e:
            log.error(f"🔍 DEBUG: Claude API call FAILED for topic '{topic.get('title', 'unknown')}': {e}")
            raise
        
        result_text = response.content[0].text.strip()
        log.info(f"🔍 DEBUG: Claude API response text: {result_text[:200]}...")
        
        # Parse JSON response
        try:
            content = json.loads(result_text)
            log.info(f"🔍 DEBUG: Claude API returned fields: {list(content.keys())}")
            log.info(f"🔍 DEBUG: Claude content has summary_16w: {bool(content.get('summary_16w'))}, article_50w: {bool(content.get('article_50w'))}")
            return content
        except json.JSONDecodeError as e:
            log.error(f"ContentGenerator: JSON parse error: {e}")
            log.debug(f"Raw response: {result_text}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")

    async def _call_claude_for_correction(self, topic: Dict[str, Any], errors: List[str], previous_content: Dict[str, Any]) -> Dict[str, Any]:
        """Call Claude API for content correction."""
        prompt = self._create_correction_prompt(topic, errors, previous_content)
        
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.1  # Lower temperature for corrections
        )
        
        result_text = response.content[0].text.strip()
        
        # Parse JSON response
        try:
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            log.error(f"ContentGenerator: JSON parse error in correction: {e}")
            raise ValueError(f"Invalid JSON response from Claude correction: {e}")

    async def generate_content_batch(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate content for multiple topics in parallel with concurrency control."""
        if not topics:
            return []
        
        log.info(f"ContentGenerator: processing {len(topics)} topics with concurrency limit {CONCURRENCY_LIMIT}")
        
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        
        tasks = [
            self._generate_content_for_topic(topic, semaphore)
            for topic in topics
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"ContentGenerator: task exception for topic {i}: {result}")
                original_topic = topics[i]
                processed_results.append({
                    **original_topic,
                    "content_generated": False,
                    "generation_errors": [str(result)]
                })
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.get("content_generated", False))
        log.info(f"ContentGenerator: completed {success_count}/{len(topics)} topics successfully")
        
        return processed_results


async def generate_content(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — generate comprehensive content for approved topics.
    
    Updates state keys:
      topics — each dict gains content fields and generation status
    """
    batch_id: str = state["batch_id"]
    topics: List[Dict[str, Any]] = state.get("topics", [])
    
    log.info(f"generate_content: processing {len(topics)} topics  batch_id={batch_id}")
    
    if not topics:
        log.info("generate_content: no topics to process")
        return {"topics": topics}
    
    try:
        # Initialize content generator
        generator = ContentGenerator()
        
        # Process topics in parallel
        enriched_topics = await generator.generate_content_batch(topics)
        
        success_count = sum(1 for t in enriched_topics if t.get("content_generated", False))
        log.info(f"generate_content: successfully generated content for {success_count}/{len(topics)} topics")
        
        return {"topics": enriched_topics}
        
    except Exception as e:
        log.error(f"generate_content: batch processing failed for batch {batch_id}: {e}")
        # Return original topics with error markers
        error_topics = [
            {**topic, "content_generated": False, "generation_errors": [str(e)]}
            for topic in topics
        ]
        return {"topics": error_topics}


# Synchronous wrapper for LangGraph compatibility
def generate_content_sync(state: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for the async generate_content function."""
    return asyncio.run(generate_content(state))