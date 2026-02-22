"""
nodes/publish_node.py — Publication and distribution for completed topics.

Handles the final publication stage:
1. Insert complete records into trending_topics table
2. Trigger Vercel ISR revalidation for new articles  
3. Submit URLs to search engines via IndexNow
4. Return published topic IDs for tracking
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# Publication settings
REVALIDATE_TIMEOUT = 30  # seconds
INDEXNOW_TIMEOUT = 15   # seconds


class PublishService:
    """Service for publishing topics and triggering external updates."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    def prepare_topic_record(self, topic: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
        """
        Prepare a topic dictionary for database insertion.
        
        Args:
            topic: Complete topic with all generated content and media
            batch_id: Current processing batch ID
            
        Returns:
            Dict ready for trending_topics table insertion
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Generate ID if not present
        topic_id = topic.get("id", f"topic_{uuid.uuid4().hex}")
        
        # Build complete record
        record = {
            "id": topic_id,
            "batch_id": batch_id,
            "status": "published",
            "created_at": now,
            "published_at": now,
            
            # Topic basics
            "title": topic.get("title", ""),
            "slug": topic.get("slug", ""),
            "category": topic.get("category", "World News"),
            "headline_cluster": topic.get("headline_cluster", ""),
            
            # Viral prediction
            "viral_tier": topic.get("viral_tier", 3),
            "viral_score": topic.get("viral_score", 0.0),
            
            # Content fields
            "seo_title": topic.get("seo_title", ""),
            "meta_description": topic.get("meta_description", ""),
            "summary_16w": topic.get("summary_16w", ""),
            "article_50w": topic.get("article_50w", ""),
            "faq": topic.get("faq", []),
            "facebook_post": topic.get("facebook_post", ""),
            "instagram_caption": topic.get("instagram_caption", ""),
            "twitter_thread": topic.get("twitter_thread", []),
            "youtube_script": topic.get("youtube_script", ""),
            "iab_categories": topic.get("iab_categories", []),
            
            # Media assets
            "thumbnail_url": topic.get("thumbnail_url"),
            "video_url": topic.get("video_url"),
            "video_url_portrait": topic.get("video_url_portrait"),
            "video_type": topic.get("video_type", "none"),
            "video_id": topic.get("video_id"),
            "embed_url": topic.get("embed_url"),
            "channel_name": topic.get("channel_name"),
            
            # Processing flags
            "brand_safe": topic.get("brand_safe", False),
            "content_generated": topic.get("content_generated", False),
            "media_generated": topic.get("media_generated", False),
            
            # Additional metadata
            "metadata": {
                "processing_pipeline": "agent_v1",
                "video_source": topic.get("video_type", "none"),
                "generation_errors": {
                    "content": topic.get("generation_errors", []),
                    "media": topic.get("media_generation_errors", [])
                }
            }
        }
        
        return record
    
    async def insert_topic_to_database(self, topic_record: Dict[str, Any]) -> str:
        """
        Insert topic record into trending_topics table.
        
        Args:
            topic_record: Prepared topic record for database
            
        Returns:
            str: Inserted topic ID
        """
        try:
            result = db.client.table("trending_topics").insert(topic_record).execute()
            
            if not result.data:
                raise Exception("No data returned from database insert")
            
            inserted_record = result.data[0]
            topic_id = inserted_record["id"]
            
            log.info(f"Published topic to database: {topic_id} (slug: {topic_record.get('slug', 'N/A')})")
            return topic_id
            
        except Exception as e:
            log.error(f"Database insert failed for topic {topic_record.get('id', 'unknown')}: {e}")
            raise
    
    async def trigger_revalidation(self, slug: str) -> bool:
        """
        Trigger Vercel ISR revalidation for a new article.
        
        Args:
            slug: Article slug to revalidate
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not settings.revalidate_secret:
            log.warning("Revalidate secret not configured, skipping ISR revalidation")
            return False
        
        try:
            revalidate_url = settings.revalidate_endpoint
            payload = {
                "secret": settings.revalidate_secret,
                "path": f"/articles/{slug}"
            }
            
            log.debug(f"Triggering ISR revalidation for slug: {slug}")
            
            response = await self.http_client.post(
                revalidate_url,
                json=payload,
                timeout=REVALIDATE_TIMEOUT
            )
            
            if response.status_code == 200:
                log.info(f"ISR revalidation successful for slug: {slug}")
                return True
            else:
                log.warning(f"ISR revalidation failed for slug {slug}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            log.error(f"ISR revalidation error for slug {slug}: {e}")
            return False
    
    async def submit_to_indexnow(self, slug: str) -> bool:
        """
        Submit article URL to search engines via IndexNow.
        
        Args:
            slug: Article slug to submit for indexing
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            article_url = f"{settings.site_url}/articles/{slug}"
            indexnow_url = settings.indexnow_endpoint
            
            payload = {
                "url": article_url,
                "key": settings.revalidate_secret  # Using same secret for simplicity
            }
            
            log.debug(f"Submitting to IndexNow: {article_url}")
            
            response = await self.http_client.post(
                indexnow_url,
                json=payload,
                timeout=INDEXNOW_TIMEOUT
            )
            
            if response.status_code in [200, 202]:
                log.info(f"IndexNow submission successful for URL: {article_url}")
                return True
            else:
                log.warning(f"IndexNow submission failed for {article_url}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            log.error(f"IndexNow submission error for slug {slug}: {e}")
            return False
    
    async def publish_topic(self, topic: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
        """
        Publish a single topic through the complete publication pipeline.
        
        Args:
            topic: Complete topic with all content and media
            batch_id: Processing batch ID
            
        Returns:
            Dict with publication results
        """
        topic_title = topic.get("title", "Unknown")
        slug = topic.get("slug", "")
        
        log.info(f"Publishing topic: {topic_title}")
        
        publication_result = {
            "topic_id": topic.get("id"),
            "published": False,
            "database_inserted": False,
            "revalidation_triggered": False,
            "indexnow_submitted": False,
            "errors": []
        }
        
        try:
            # Step 1: Prepare and insert database record
            topic_record = self.prepare_topic_record(topic, batch_id)
            topic_id = await self.insert_topic_to_database(topic_record)
            publication_result["topic_id"] = topic_id
            publication_result["database_inserted"] = True
            
            # Step 2: Trigger ISR revalidation and IndexNow in parallel
            if slug:
                revalidation_task = self.trigger_revalidation(slug)
                indexnow_task = self.submit_to_indexnow(slug)
                
                revalidation_success, indexnow_success = await asyncio.gather(
                    revalidation_task, 
                    indexnow_task,
                    return_exceptions=True
                )
                
                # Handle revalidation result
                if isinstance(revalidation_success, Exception):
                    publication_result["errors"].append(f"Revalidation error: {revalidation_success}")
                else:
                    publication_result["revalidation_triggered"] = revalidation_success
                
                # Handle IndexNow result
                if isinstance(indexnow_success, Exception):
                    publication_result["errors"].append(f"IndexNow error: {indexnow_success}")
                else:
                    publication_result["indexnow_submitted"] = indexnow_success
            else:
                publication_result["errors"].append("No slug available for external API calls")
            
            # Consider publication successful if database insert worked
            publication_result["published"] = publication_result["database_inserted"]
            
            if publication_result["published"]:
                log.info(f"Topic published successfully: {topic_id}")
            else:
                log.error(f"Topic publication failed: {topic_title}")
            
            return publication_result
            
        except Exception as e:
            log.error(f"Publication failed for topic '{topic_title}': {e}")
            publication_result["errors"].append(str(e))
            return publication_result


async def publish_topics_batch(topics: List[Dict[str, Any]], batch_id: str) -> List[Dict[str, Any]]:
    """
    Publish multiple topics with controlled concurrency.
    
    Args:
        topics: List of complete topic dictionaries
        batch_id: Processing batch ID
        
    Returns:
        List of publication results
    """
    if not topics:
        return []
    
    log.info(f"Publishing batch: {len(topics)} topics")
    
    async with PublishService() as service:
        # Limit concurrency for database operations
        semaphore = asyncio.Semaphore(3)
        
        async def publish_with_limit(topic):
            async with semaphore:
                return await service.publish_topic(topic, batch_id)
        
        tasks = [publish_with_limit(topic) for topic in topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any task-level exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"Publication task exception for topic {i}: {result}")
                topic_id = topics[i].get("id", f"topic_{i}")
                processed_results.append({
                    "topic_id": topic_id,
                    "published": False,
                    "errors": [str(result)]
                })
            else:
                processed_results.append(result)
    
    # Log publication statistics
    success_count = sum(1 for r in processed_results if r.get("published", False))
    log.info(f"Publication batch complete: {success_count}/{len(topics)} topics published successfully")
    
    return processed_results


def publish_topics(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — publish completed topics to database and external APIs.
    
    Updates state keys:
      published_topic_ids — list of successfully published topic IDs
      publication_results — detailed results for each topic
    """
    batch_id: str = state["batch_id"]
    topics: List[Dict[str, Any]] = state.get("topics", [])
    
    log.info(f"publish_topics: processing {len(topics)} topics  batch_id={batch_id}")
    
    if not topics:
        return {
            "published_topic_ids": [],
            "publication_results": []
        }
    
    try:
        # Filter for topics that have completed all processing stages
        publishable_topics = []
        for topic in topics:
            if (topic.get("brand_safe", False) and 
                topic.get("content_generated", False)):
                publishable_topics.append(topic)
            else:
                log.warning(f"Skipping incomplete topic: {topic.get('id', 'unknown')} "
                          f"(brand_safe: {topic.get('brand_safe')}, "
                          f"content_generated: {topic.get('content_generated')})")
        
        if not publishable_topics:
            log.warning("No topics are ready for publication")
            return {
                "published_topic_ids": [],
                "publication_results": []
            }
        
        log.info(f"Publishing {len(publishable_topics)} ready topics out of {len(topics)} total")
        
        # Run async publication
        publication_results = asyncio.run(publish_topics_batch(publishable_topics, batch_id))
        
        # Extract published topic IDs
        published_topic_ids = [
            r["topic_id"] for r in publication_results 
            if r.get("published", False) and r.get("topic_id")
        ]
        
        log.info(f"publish_topics: successfully published {len(published_topic_ids)} topics")
        
        return {
            "published_topic_ids": published_topic_ids,
            "publication_results": publication_results
        }
        
    except Exception as e:
        log.error(f"publish_topics: batch processing failed for batch {batch_id}: {e}")
        return {
            "published_topic_ids": [],
            "publication_results": [],
            "publication_error": str(e)
        }