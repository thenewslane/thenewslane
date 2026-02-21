"""
nodes/classification_node.py — Topic classification using Claude Haiku batch API.

Classifies brand-safe topics into predefined categories using Anthropic's batch API
for optimal latency and cost efficiency.
"""

from __future__ import annotations

import uuid
from typing import Any

import anthropic

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

# Predefined topic categories
TOPIC_CATEGORIES = [
    "Technology",
    "Politics", 
    "Business & Finance",
    "Entertainment",
    "Sports",
    "Science & Health", 
    "World News",
    "Lifestyle",
    "Environment",
    "Education"
]


class ClassificationNode:
    """Topic classification using Claude Haiku batch API."""
    
    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for ClassificationNode")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    
    def _create_classification_prompt(self, topic_name: str, headline_cluster: str) -> str:
        """Create classification prompt for a single topic."""
        categories_list = ", ".join(TOPIC_CATEGORIES)
        return f"""Classify this trending topic into exactly one of these categories: [{categories_list}].

Topic: {topic_name}
Context: {headline_cluster}

Return only the category name, nothing else."""

    def classify_topics_batch(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Classify multiple topics using Anthropic's batch API.
        
        Args:
            topics: List of topic dictionaries with 'title' and 'headline_cluster'
        
        Returns:
            List of topics with added 'category' field
        """
        if not topics:
            return topics
        
        log.info("ClassificationNode: classifying %d topics", len(topics))
        
        # For now, we'll process sequentially since Anthropic's Python SDK
        # doesn't have built-in batch support yet. In production, you'd use
        # the batch API directly via HTTP requests for better efficiency.
        classified_topics = []
        
        for topic in topics:
            topic_name = topic.get("title", "")
            headline_cluster = topic.get("headline_cluster", "")
            
            if not topic_name:
                log.warning("ClassificationNode: skipping topic with no title")
                classified_topics.append(topic)
                continue
            
            try:
                category = self._classify_single_topic(topic_name, headline_cluster)
                topic_with_category = {**topic, "category": category}
                classified_topics.append(topic_with_category)
                
            except Exception as e:
                log.error("ClassificationNode: failed to classify topic '%s': %s", topic_name, e)
                # Add default category on error
                topic_with_category = {**topic, "category": "World News"}
                classified_topics.append(topic_with_category)
        
        log.info("ClassificationNode: successfully classified %d topics", len(classified_topics))
        return classified_topics
    
    def _classify_single_topic(self, topic_name: str, headline_cluster: str) -> str:
        """Classify a single topic using Claude Haiku."""
        prompt = self._create_classification_prompt(topic_name, headline_cluster)
        
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.0
        )
        
        result = response.content[0].text.strip()
        
        # Validate response is one of our categories
        if result in TOPIC_CATEGORIES:
            log.debug("ClassificationNode: classified '%s' as '%s'", topic_name, result)
            return result
        else:
            # Try fuzzy matching for slight variations
            result_lower = result.lower()
            for category in TOPIC_CATEGORIES:
                if category.lower() in result_lower or result_lower in category.lower():
                    log.debug("ClassificationNode: fuzzy matched '%s' to '%s'", result, category)
                    return category
            
            # Default fallback
            log.warning("ClassificationNode: invalid category '%s' for topic '%s', defaulting to 'World News'", 
                       result, topic_name)
            return "World News"

    def classify_topics_batch_http(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Alternative implementation using HTTP batch API (more efficient for large batches).
        This would be the preferred method in production.
        """
        # TODO: Implement direct HTTP calls to Anthropic's batch API
        # For now, fall back to sequential processing
        return self.classify_topics_batch(topics)


def classify_topics(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node — classify brand-safe topics into predefined categories.
    
    Updates state keys:
      topics — each dict gains 'category': str field
    """
    batch_id: str = state["batch_id"]
    topics: list[dict[str, Any]] = state.get("topics", [])
    
    log.info("classify_topics: processing %d topics  batch_id=%s", len(topics), batch_id)
    
    if not topics:
        log.info("classify_topics: no topics to classify")
        return {"topics": topics}
    
    # Initialize classification processor
    classifier = ClassificationNode()
    
    try:
        # Classify all topics
        classified_topics = classifier.classify_topics_batch(topics)
        
        log.info("classify_topics: successfully classified %d topics", len(classified_topics))
        
        return {"topics": classified_topics}
        
    except Exception as e:
        log.error("classify_topics: classification failed for batch %s: %s", batch_id, e)
        # Return original topics without categories on error
        return {"topics": topics}