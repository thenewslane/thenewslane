"""
nodes/video_sourcing_node.py — Video sourcing from YouTube and Vimeo APIs.

Searches for existing videos related to trending topics using:
1. YouTube Data API v3 (primary source)  
2. Vimeo API (fallback)

Sets video_type based on results and viral tier.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

# Video quality filters (reduced by 80% to be more permissive)
MIN_VIEW_COUNT = 200         # was 1000
MIN_DURATION_SECONDS = 6     # was 30 seconds
MAX_DURATION_SECONDS = 120   # was 600 (10 min), now 2 minutes
SEARCH_HOURS_BACK = 48


class VideoSourcingService:
    """Service for finding relevant videos from YouTube and Vimeo."""
    
    def __init__(self) -> None:
        self.youtube_api_key = settings.youtube_api_key
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    def _parse_iso8601_duration(self, duration: str) -> int:
        """
        Parse ISO 8601 duration format (PT4M13S) to seconds.
        
        Args:
            duration: ISO 8601 duration string like "PT4M13S"
            
        Returns:
            int: Duration in seconds
        """
        if not duration.startswith('PT'):
            return 0
            
        # Remove PT prefix
        duration = duration[2:]
        
        # Extract hours, minutes, seconds
        hours = 0
        minutes = 0
        seconds = 0
        
        # Match patterns like 1H, 23M, 45S
        hour_match = re.search(r'(\d+)H', duration)
        minute_match = re.search(r'(\d+)M', duration)
        second_match = re.search(r'(\d+)S', duration)
        
        if hour_match:
            hours = int(hour_match.group(1))
        if minute_match:
            minutes = int(minute_match.group(1))
        if second_match:
            seconds = int(second_match.group(1))
            
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    
    def _get_published_after_date(self) -> str:
        """Get RFC 3339 formatted date for 48 hours ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SEARCH_HOURS_BACK)
        return cutoff.isoformat()
    
    async def search_youtube(self, topic_title: str) -> Optional[Dict[str, Any]]:
        """
        Search YouTube Data API v3 for relevant videos.
        
        Args:
            topic_title: The trending topic title to search for
            
        Returns:
            Dict with video info if found, None otherwise
        """
        if not self.youtube_api_key:
            log.warning("YouTube API key not configured, skipping YouTube search")
            return None
            
        try:
            published_after = self._get_published_after_date()
            
            # Search for videos
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "part": "snippet",
                "q": topic_title,
                "type": "video",
                "order": "relevance",
                "maxResults": 5,
                "publishedAfter": published_after,
                "key": self.youtube_api_key
            }
            
            log.debug(f"YouTube search: {topic_title} (published after {published_after})")
            search_response = await self.http_client.get(search_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("items"):
                log.info(f"No YouTube videos found for topic: {topic_title}")
                return None
            
            # Get video details including statistics and duration
            video_ids = [item["id"]["videoId"] for item in search_data["items"]]
            
            details_url = "https://www.googleapis.com/youtube/v3/videos"
            details_params = {
                "part": "contentDetails,statistics,snippet",
                "id": ",".join(video_ids),
                "key": self.youtube_api_key
            }
            
            details_response = await self.http_client.get(details_url, params=details_params)
            details_response.raise_for_status()
            details_data = details_response.json()
            
            # Find first video that meets criteria
            for video in details_data.get("items", []):
                video_id = video["id"]
                statistics = video.get("statistics", {})
                content_details = video.get("contentDetails", {})
                snippet = video.get("snippet", {})
                
                # Check view count
                view_count = int(statistics.get("viewCount", 0))
                if view_count < MIN_VIEW_COUNT:
                    log.debug(f"YouTube video {video_id} has low views: {view_count}")
                    continue
                
                # Check duration
                duration_iso = content_details.get("duration", "")
                duration_seconds = self._parse_iso8601_duration(duration_iso)
                if not (MIN_DURATION_SECONDS <= duration_seconds <= MAX_DURATION_SECONDS):
                    log.debug(f"YouTube video {video_id} duration invalid: {duration_seconds}s")
                    continue
                
                # This video meets all criteria
                result = {
                    "video_type": "youtube",
                    "video_id": video_id,
                    "embed_url": f"https://www.youtube.com/embed/{video_id}",
                    "channel_name": snippet.get("channelTitle", ""),
                    "video_title": snippet.get("title", ""),
                    "view_count": view_count,
                    "duration_seconds": duration_seconds,
                    "published_at": snippet.get("publishedAt", "")
                }
                
                log.info(f"Found qualifying YouTube video: {video_id} ({view_count} views, {duration_seconds}s)")
                return result
                
            log.info(f"No qualifying YouTube videos found for: {topic_title}")
            return None
            
        except Exception as e:
            log.error(f"YouTube search error for '{topic_title}': {e}")
            return None
    
    async def search_vimeo(self, topic_title: str) -> Optional[Dict[str, Any]]:
        """
        Search Vimeo API for relevant videos.
        
        Args:
            topic_title: The trending topic title to search for
            
        Returns:
            Dict with video info if found, None otherwise
        """
        try:
            # Vimeo search doesn't require API key for public search
            # But has limited functionality without authentication
            search_url = "https://api.vimeo.com/videos"
            
            # Calculate date filter (Vimeo uses different format)
            cutoff_date = datetime.now(timezone.utc) - timedelta(hours=SEARCH_HOURS_BACK)
            
            params = {
                "query": topic_title,
                "sort": "relevant",
                "per_page": 5,
                "filter": "embeddable",
                "filter_created_time": f"{cutoff_date.strftime('%Y-%m-%d')}T00:00:00+00:00",
            }
            
            log.debug(f"Vimeo search: {topic_title}")
            response = await self.http_client.get(search_url, params=params)
            
            if response.status_code == 401:
                log.warning("Vimeo API requires authentication, skipping Vimeo search")
                return None
                
            response.raise_for_status()
            data = response.json()
            
            # Find first video that meets criteria
            for video in data.get("data", []):
                stats = video.get("stats", {})
                view_count = stats.get("plays", 0)
                
                if view_count < MIN_VIEW_COUNT:
                    continue
                
                duration_seconds = video.get("duration", 0)
                if not (MIN_DURATION_SECONDS <= duration_seconds <= MAX_DURATION_SECONDS):
                    continue
                
                video_id = video["uri"].split("/")[-1]  # Extract ID from URI
                
                result = {
                    "video_type": "vimeo",
                    "video_id": video_id,
                    "embed_url": f"https://player.vimeo.com/video/{video_id}",
                    "channel_name": video.get("user", {}).get("name", ""),
                    "video_title": video.get("name", ""),
                    "view_count": view_count,
                    "duration_seconds": duration_seconds,
                    "published_at": video.get("created_time", "")
                }
                
                log.info(f"Found qualifying Vimeo video: {video_id} ({view_count} views, {duration_seconds}s)")
                return result
                
            log.info(f"No qualifying Vimeo videos found for: {topic_title}")
            return None
            
        except Exception as e:
            log.error(f"Vimeo search error for '{topic_title}': {e}")
            return None
    
    async def find_video_for_topic(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find the best video source for a topic.
        
        Args:
            topic: Topic dictionary with title and viral_tier
            
        Returns:
            Updated topic dict with video sourcing info
        """
        topic_title = topic.get("title", "")
        viral_tier = topic.get("viral_tier", 3)
        
        log.info(f"Video sourcing for topic: {topic_title} (Tier {viral_tier})")
        
        # Try YouTube first
        youtube_result = await self.search_youtube(topic_title)
        if youtube_result:
            return {**topic, **youtube_result}
        
        # Try Vimeo as fallback
        vimeo_result = await self.search_vimeo(topic_title)
        if vimeo_result:
            return {**topic, **vimeo_result}
        
        # No videos found - set video_type based on viral tier
        if viral_tier == 1:
            video_type = "ai_needed"
            log.info(f"No existing videos found for Tier 1 topic '{topic_title}', marking for AI generation")
        else:
            video_type = "none"
            log.info(f"No existing videos found for Tier {viral_tier} topic '{topic_title}', no video needed")
        
        return {
            **topic,
            "video_type": video_type,
            "video_id": None,
            "embed_url": None,
            "channel_name": None,
            "video_title": None,
            "view_count": 0,
            "duration_seconds": 0
        }


async def source_videos_batch(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Source videos for multiple topics in parallel.
    
    Args:
        topics: List of topic dictionaries
        
    Returns:
        List of topics with video sourcing information added
    """
    if not topics:
        return []
    
    log.info(f"Video sourcing: processing {len(topics)} topics")
    
    async with VideoSourcingService() as service:
        # Process topics in parallel with some concurrency control
        semaphore = asyncio.Semaphore(3)  # Limit concurrent API calls
        
        async def process_topic(topic):
            async with semaphore:
                return await service.find_video_for_topic(topic)
        
        tasks = [process_topic(topic) for topic in topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"Video sourcing exception for topic {i}: {result}")
                # Return original topic with fallback video_type
                original_topic = topics[i]
                viral_tier = original_topic.get("viral_tier", 3)
                processed_results.append({
                    **original_topic,
                    "video_type": "ai_needed" if viral_tier == 1 else "none",
                    "video_id": None,
                    "embed_url": None,
                    "channel_name": None
                })
            else:
                processed_results.append(result)
    
    success_count = sum(1 for t in processed_results if t.get("video_type") in ["youtube", "vimeo"])
    log.info(f"Video sourcing complete: {success_count}/{len(topics)} topics found existing videos")
    
    return processed_results


def source_videos(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — source videos for topics from YouTube and Vimeo.
    
    Updates state keys:
      topics — each dict gains video sourcing fields
    """
    batch_id: str = state["batch_id"]
    topics: List[Dict[str, Any]] = state.get("topics", [])
    
    log.info(f"source_videos: processing {len(topics)} topics  batch_id={batch_id}")
    
    if not topics:
        return {"topics": topics}
    
    try:
        # Run async video sourcing
        enriched_topics = asyncio.run(source_videos_batch(topics))
        
        # Log video type distribution
        video_types = {}
        for topic in enriched_topics:
            vtype = topic.get("video_type", "unknown")
            video_types[vtype] = video_types.get(vtype, 0) + 1
        
        log.info(f"source_videos: video type distribution: {video_types}")
        
        return {"topics": enriched_topics}
        
    except Exception as e:
        log.error(f"source_videos: batch processing failed for batch {batch_id}: {e}")
        # Return original topics with fallback video types
        fallback_topics = []
        for topic in topics:
            viral_tier = topic.get("viral_tier", 3) 
            fallback_topics.append({
                **topic,
                "video_type": "ai_needed" if viral_tier == 1 else "none",
                "video_sourcing_error": str(e)
            })
        return {"topics": fallback_topics}