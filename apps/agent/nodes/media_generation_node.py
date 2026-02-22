"""
nodes/media_generation_node.py — AI media generation using Replicate APIs.

Generates thumbnails and videos for topics using:
1. Flux 1.1 Pro for thumbnail images (16:9 aspect ratio)
2. Kling AI for video generation (16:9 and 9:16 aspect ratios)
3. Supabase Storage for media hosting

Runs thumbnail and video generation tasks in parallel for efficiency.
"""

from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

try:
    import replicate
except Exception:
    # replicate may be unavailable or incompatible with this Python version
    replicate = None  # type: ignore[assignment]

from config.settings import settings
from utils.logger import get_logger
from utils.supabase_client import db

log = get_logger(__name__)

# Media generation settings
THUMBNAIL_WIDTH = 1344
THUMBNAIL_HEIGHT = 768
VIDEO_DURATION = 5
POLL_INTERVAL = 10  # seconds
MAX_WAIT_TIME = 300  # 5 minutes


class StorageManager:
    """Utility for uploading files to Supabase Storage."""
    
    def __init__(self):
        self.client = db.client
    
    async def upload_file(self, file_path: str, bucket: str, object_name: str) -> str:
        """
        Upload a file to Supabase Storage and return public URL.
        
        Args:
            file_path: Local file path to upload
            bucket: Storage bucket name
            object_name: Object key/name in storage
            
        Returns:
            str: Public URL of uploaded file
        """
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            # Upload to Supabase Storage
            response = self.client.storage.from_(bucket).upload(
                path=object_name,
                file=file_data,
                file_options={"content-type": self._get_content_type(file_path)}
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
            
            # Get public URL
            public_url = self.client.storage.from_(bucket).get_public_url(object_name)
            
            log.debug(f"Uploaded {file_path} to {bucket}/{object_name}")
            return public_url
            
        except Exception as e:
            log.error(f"Storage upload failed for {file_path}: {e}")
            raise
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type from file extension."""
        suffix = Path(file_path).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm'
        }
        return content_types.get(suffix, 'application/octet-stream')


class MediaGenerator:
    """AI media generation service using Replicate APIs."""
    
    def __init__(self):
        if not settings.replicate_api_key:
            raise ValueError("REPLICATE_API_KEY is required for MediaGenerator")
        
        if replicate is None:
            log.warning("replicate package unavailable - thumbnails will be skipped due to Python 3.14 compatibility issues")
            self.replicate_client = None
            
        if replicate is not None:
            self.replicate_client = replicate.Client(api_token=settings.replicate_api_key)
        self.storage = StorageManager()
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    async def download_file(self, url: str, local_path: str) -> None:
        """Download a file from URL to local path."""
        try:
            async with self.http_client.stream('GET', url) as response:
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
                        
            log.debug(f"Downloaded {url} to {local_path}")
            
        except Exception as e:
            log.error(f"Download failed for {url}: {e}")
            raise
    
    async def generate_thumbnail(self, topic: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate thumbnail image using OpenAI DALL-E 3 (replaces Replicate Flux).
        
        Args:
            topic: Topic dict containing image_prompt
            
        Returns:
            Dict with thumbnail_url
        """
        image_prompt = topic.get("image_prompt", "")
        topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
        
        if not image_prompt:
            log.warning(f"No image_prompt for topic {topic_id} - skipping thumbnail")
            return {"thumbnail_url": None}
        
        # Check if OpenAI API key is configured
        if not getattr(settings, 'openai_api_key', None) or not settings.openai_api_key:
            log.warning(f"OPENAI_API_KEY not configured - skipping thumbnail for {topic_id}")
            return {"thumbnail_url": None}
        
        log.info(f"Generating thumbnail for topic {topic_id} using OpenAI DALL-E 3")
        
        try:
            # Call OpenAI DALL-E 3 API
            payload = {
                "model": "dall-e-3",
                "prompt": image_prompt[:4000],  # DALL-E has 4000 char limit
                "size": "1792x1024",  # Closest to our 1344x768 requirement
                "quality": "standard",  # or "hd" for higher quality
                "n": 1
            }
            
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
                
                data = response.json()
                generated_url = data["data"][0]["url"]
                
                log.info(f"OpenAI generated image URL: {generated_url}")
                
                # Download the generated image
                img_response = await client.get(generated_url)
                if img_response.status_code != 200:
                    raise Exception(f"Failed to download generated image: {img_response.status_code}")
                
                # Save to temporary file
                import tempfile
                tmp_path = f"/tmp/dall_e_thumbnail_{topic_id}.jpg"
                with open(tmp_path, "wb") as f:
                    f.write(img_response.content)
                
                # Upload to Supabase Storage
                public_url = await self.storage.upload_file(tmp_path, "thumbnails", f"{topic_id}.jpg")
                
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)
                
                log.info(f"Thumbnail uploaded to Supabase: {public_url}")
                return {"thumbnail_url": public_url}
                
        except Exception as e:
            log.error(f"OpenAI thumbnail generation failed for topic {topic_id}: {e}")
            log.error(f"  Image prompt: {image_prompt[:100]}...")
            
            # Return None instead of crashing
            return {"thumbnail_url": None}

    async def generate_ai_video(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI video using Kling AI model.
        
        Args:
            topic: Topic dict containing image_prompt
            
        Returns:
            Dict with video_url and potentially video_url_portrait
        """
        image_prompt = topic.get("image_prompt", "")
        topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
        
        if not image_prompt:
            raise ValueError("No image_prompt found in topic")
        
        # Check if Replicate is available (Python 3.14 compatibility issue)
        if self.replicate_client is None:
            log.warning(f"Skipping AI video generation for topic {topic_id} - Replicate unavailable (Python 3.14 compatibility)")
            return {"video_url": None, "video_url_portrait": None}
        
        log.info(f"Generating AI video for topic {topic_id}")
        
        results = {}
        
        try:
            # Generate 16:9 video
            log.debug(f"Generating 16:9 video for topic {topic_id}")
            video_16_9 = await self._generate_video_aspect_ratio(
                image_prompt, topic_id, "16:9", "landscape"
            )
            results.update(video_16_9)
            
            # Generate 9:16 video for Instagram Reels
            log.debug(f"Generating 9:16 video for topic {topic_id}")
            video_9_16 = await self._generate_video_aspect_ratio(
                image_prompt, topic_id, "9:16", "portrait"
            )
            # Add portrait video with different key
            if "video_url" in video_9_16:
                results["video_url_portrait"] = video_9_16["video_url"]
            
            log.info(f"AI video generation completed for topic {topic_id}")
            return results
            
        except Exception as e:
            log.error(f"AI video generation failed for topic {topic_id}: {e}")
            raise
    
    async def _generate_video_aspect_ratio(
        self, 
        prompt: str, 
        topic_id: str, 
        aspect_ratio: str,
        orientation: str
    ) -> Dict[str, str]:
        """Generate video for specific aspect ratio."""
        try:
            # Call Replicate Kling AI
            prediction = self.replicate_client.predictions.create(
                model="kling-ai/kling-v1-6",
                input={
                    "prompt": prompt,
                    "duration": VIDEO_DURATION,
                    "aspect_ratio": aspect_ratio
                }
            )
            
            # Poll for completion (video generation takes longer)
            prediction = await self._poll_prediction(prediction.id, max_wait=MAX_WAIT_TIME)
            
            if prediction.status != "succeeded":
                raise Exception(f"Video generation failed: {prediction.status}")
            
            # Download generated video
            video_url = prediction.output[0] if prediction.output else None
            if not video_url:
                raise Exception("No video output from Replicate")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            await self.download_file(video_url, tmp_path)
            
            # Upload to Supabase Storage
            object_name = f"{topic_id}/video_{orientation}_{uuid.uuid4().hex[:8]}.mp4"
            public_url = await self.storage.upload_file(
                tmp_path,
                "videos", 
                object_name
            )
            
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
            log.debug(f"Video {aspect_ratio} generated: {public_url}")
            return {"video_url": public_url}
            
        except Exception as e:
            log.error(f"Video generation failed for {aspect_ratio}: {e}")
            raise
    
    async def _poll_prediction(self, prediction_id: str, max_wait: int = 120) -> Any:
        """Poll Replicate prediction until completion."""
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                prediction = self.replicate_client.predictions.get(prediction_id)
                
                if prediction.status == "succeeded":
                    return prediction
                elif prediction.status == "failed":
                    raise Exception(f"Prediction failed: {prediction.error}")
                elif prediction.status in ["canceled", "cancelled"]:
                    raise Exception("Prediction was canceled")
                
                # Still processing, wait and retry
                log.debug(f"Prediction {prediction_id} status: {prediction.status}")
                await asyncio.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL
                
            except Exception as e:
                if "failed" in str(e).lower() or "canceled" in str(e).lower():
                    raise
                log.warning(f"Error polling prediction {prediction_id}: {e}")
                await asyncio.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL
        
        raise Exception(f"Prediction {prediction_id} timed out after {max_wait}s")
    
    async def process_topic_media(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all media generation for a single topic.
        
        Args:
            topic: Topic dict with image_prompt and video_type
            
        Returns:
            Updated topic dict with media URLs
        """
        topic_id = topic.get("id", "unknown")
        video_type = topic.get("video_type", "none")
        
        log.info(f"Processing media for topic {topic_id} (video_type: {video_type})")
        
        # Prepare tasks to run in parallel
        tasks = []
        
        # Task 1: Always generate thumbnail
        thumbnail_task = self.generate_thumbnail(topic)
        tasks.append(("thumbnail", thumbnail_task))
        
        # Task 2: Generate AI video only if needed
        if video_type == "ai_needed":
            video_task = self.generate_ai_video(topic)
            tasks.append(("video", video_task))
        
        # Run tasks in parallel
        results = {}
        exceptions = []
        
        if tasks:
            task_names, task_coroutines = zip(*tasks)
            completed_tasks = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            for task_name, result in zip(task_names, completed_tasks):
                if isinstance(result, Exception):
                    log.error(f"Media task '{task_name}' failed for topic {topic_id}: {result}")
                    exceptions.append(f"{task_name}: {result}")
                else:
                    results.update(result)
        
        # Add error info if any tasks failed
        if exceptions:
            results["media_generation_errors"] = exceptions
        
        # Mark media generation as completed (even with partial failures)
        results["media_generated"] = len(exceptions) == 0
        
        final_topic = {**topic, **results}
        
        log.info(f"Media processing completed for topic {topic_id} (success: {results.get('media_generated', False)})")
        return final_topic


async def generate_media_batch(topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate media for multiple topics with concurrency control.
    
    Args:
        topics: List of topic dictionaries
        
    Returns:
        List of topics with media generation results
    """
    if not topics:
        return []
    
    log.info(f"Media generation: processing {len(topics)} topics")
    
    async with MediaGenerator() as generator:
        # Process topics with limited concurrency to avoid overwhelming APIs
        semaphore = asyncio.Semaphore(2)  # Limit concurrent media generation
        
        async def process_topic_with_limit(topic):
            async with semaphore:
                return await generator.process_topic_media(topic)
        
        tasks = [process_topic_with_limit(topic) for topic in topics]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions at topic level
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"Media generation exception for topic {i}: {result}")
                original_topic = topics[i]
                processed_results.append({
                    **original_topic,
                    "media_generated": False,
                    "media_generation_errors": [str(result)]
                })
            else:
                processed_results.append(result)
    
    success_count = sum(1 for t in processed_results if t.get("media_generated", False))
    log.info(f"Media generation complete: {success_count}/{len(topics)} topics successful")
    
    return processed_results


def generate_media(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — generate thumbnails and AI videos for topics.
    
    Updates state keys:
      topics — each dict gains media URLs and generation status
    """
    batch_id: str = state["batch_id"]
    topics: List[Dict[str, Any]] = state.get("topics", [])
    
    log.info(f"generate_media: processing {len(topics)} topics  batch_id={batch_id}")
    
    if not topics:
        return {"topics": topics}
    
    try:
        # Run async media generation
        enriched_topics = asyncio.run(generate_media_batch(topics))
        
        # Log generation statistics
        thumbnail_count = sum(1 for t in enriched_topics if "thumbnail_url" in t)
        video_count = sum(1 for t in enriched_topics if "video_url" in t)
        portrait_count = sum(1 for t in enriched_topics if "video_url_portrait" in t)
        
        log.info(f"generate_media: generated {thumbnail_count} thumbnails, {video_count} videos, {portrait_count} portrait videos")
        
        return {"topics": enriched_topics}
        
    except Exception as e:
        log.error(f"generate_media: batch processing failed for batch {batch_id}: {e}")
        # Return original topics with error markers
        error_topics = [
            {**topic, "media_generated": False, "media_generation_errors": [str(e)]}
            for topic in topics
        ]
        return {"topics": error_topics}