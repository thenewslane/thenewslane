#!/usr/bin/env python3
"""
Option 4: Direct HTTP API calls to Replicate (bypass Python library)

This completely bypasses the problematic Replicate Python library
and calls the Replicate API directly using HTTP requests.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional
import httpx
from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

class DirectReplicateClient:
    """Direct HTTP client for Replicate API - no Python library needed"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.replicate.com/v1"
        self.http_client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout
        self.headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json"
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    async def create_prediction(self, model: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a prediction (equivalent to replicate.run())"""
        
        payload = {
            "version": await self._get_model_version(model),
            "input": input_data
        }
        
        response = await self.http_client.post(
            f"{self.base_url}/predictions",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 201:
            raise Exception(f"Replicate API error: {response.status_code} - {response.text}")
        
        prediction = response.json()
        log.info(f"Created prediction: {prediction['id']}")
        
        return prediction
    
    async def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Get prediction status and results"""
        
        response = await self.http_client.get(
            f"{self.base_url}/predictions/{prediction_id}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get prediction: {response.status_code}")
        
        return response.json()
    
    async def wait_for_prediction(self, prediction_id: str, max_wait: int = 300) -> Dict[str, Any]:
        """Wait for prediction to complete (polling)"""
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            prediction = await self.get_prediction(prediction_id)
            status = prediction["status"]
            
            if status == "succeeded":
                log.info(f"Prediction {prediction_id} succeeded")
                return prediction
            elif status == "failed":
                error = prediction.get("error", "Unknown error")
                raise Exception(f"Prediction failed: {error}")
            elif status in ["starting", "processing"]:
                log.info(f"Prediction {prediction_id} status: {status}")
                await asyncio.sleep(5)  # Wait 5 seconds before next check
            else:
                log.warning(f"Unknown prediction status: {status}")
                await asyncio.sleep(5)
        
        raise Exception(f"Prediction timed out after {max_wait} seconds")
    
    async def _get_model_version(self, model: str) -> str:
        """Get the latest version hash for a model"""
        
        # For common models, we can hardcode known versions
        # This avoids an extra API call
        known_versions = {
            "black-forest-labs/flux-1.1-pro": "617bbfb1eaf09b9c8b0b2f01a01b05dd8a5b1b38f5b2e29e26a7b3d1f5a9c5c2",  # Example version
            "stability-ai/stable-diffusion-xl-base-1.0": "7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc"
        }
        
        if model in known_versions:
            return known_versions[model]
        
        # Otherwise, fetch from API
        response = await self.http_client.get(
            f"{self.base_url}/models/{model}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get model info: {response.status_code}")
        
        model_info = response.json()
        return model_info["latest_version"]["id"]
    
    async def generate_image(self, prompt: str, width: int = 1344, height: int = 768) -> str:
        """Generate image using Flux 1.1 Pro (direct HTTP API)"""
        
        input_data = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
            "output_format": "jpg",
            "output_quality": 90,
            "prompt_upsampling": True,
            "safety_tolerance": 2
        }
        
        # Create prediction
        prediction = await self.create_prediction("black-forest-labs/flux-1.1-pro", input_data)
        
        # Wait for completion
        completed = await self.wait_for_prediction(prediction["id"])
        
        # Extract image URL
        output = completed.get("output")
        if not output or not isinstance(output, list) or len(output) == 0:
            raise Exception("No image output from Replicate")
        
        image_url = output[0]  # First (and only) output image
        log.info(f"Generated image: {image_url}")
        
        return image_url


# Drop-in replacement for the broken media_generation_node.py
async def generate_thumbnail_direct_http(topic: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate thumbnail using direct HTTP calls to Replicate API
    This completely bypasses the broken Replicate Python library
    """
    
    image_prompt = topic.get("image_prompt", "")
    topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
    
    if not image_prompt:
        raise ValueError("No image_prompt found in topic")
    
    if not settings.replicate_api_key:
        raise ValueError("REPLICATE_API_KEY is required")
    
    log.info(f"Generating thumbnail for topic {topic_id} using direct HTTP API")
    
    try:
        async with DirectReplicateClient(settings.replicate_api_key) as client:
            # Generate image using Flux 1.1 Pro
            image_url = await client.generate_image(
                prompt=image_prompt,
                width=1344,
                height=768
            )
            
            # Download the generated image
            response = await client.http_client.get(image_url)
            if response.status_code != 200:
                raise Exception(f"Failed to download image: {response.status_code}")
            
            # Save to temporary file
            import tempfile
            import uuid
            from pathlib import Path
            
            temp_path = f"/tmp/thumbnail_{uuid.uuid4().hex[:8]}.jpg"
            with open(temp_path, "wb") as f:
                f.write(response.content)
            
            # Upload to Supabase Storage (use existing StorageManager)
            from nodes.media_generation_node import StorageManager
            storage = StorageManager()
            public_url = await storage.upload_file(temp_path, "thumbnails", f"{topic_id}.jpg")
            
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
            
            log.info(f"Thumbnail uploaded: {public_url}")
            return {"thumbnail_url": public_url}
            
    except Exception as e:
        log.error(f"Direct HTTP thumbnail generation failed: {e}")
        raise


# Updated MediaGenerator class for media_generation_node.py
class MediaGeneratorDirectHTTP:
    """MediaGenerator using direct HTTP API calls instead of Replicate library"""
    
    def __init__(self):
        if not settings.replicate_api_key:
            raise ValueError("REPLICATE_API_KEY is required for MediaGenerator")
        
        # No replicate library import needed!
        self.replicate_client = DirectReplicateClient(settings.replicate_api_key)
        self.storage = StorageManager()
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_thumbnail(self, topic: Dict[str, Any]) -> Dict[str, str]:
        """Generate thumbnail using direct HTTP (no Python library)"""
        return await generate_thumbnail_direct_http(topic)
    
    async def generate_ai_video(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI video using Kling via direct HTTP"""
        
        image_prompt = topic.get("image_prompt", "")
        topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
        
        if not image_prompt:
            raise ValueError("No image_prompt found in topic")
        
        log.info(f"Generating AI video for topic {topic_id} using direct HTTP API")
        
        try:
            async with DirectReplicateClient(settings.replicate_api_key) as client:
                
                # Generate 16:9 video
                video_input = {
                    "prompt": image_prompt,
                    "duration": 5,
                    "aspect_ratio": "16:9"
                }
                
                prediction = await client.create_prediction("kling-ai/kling-v1-6", video_input)
                completed = await client.wait_for_prediction(prediction["id"], max_wait=600)  # 10 min timeout
                
                video_url = completed["output"][0]
                
                # Also generate portrait version (9:16) for Instagram
                portrait_input = {
                    "prompt": image_prompt,
                    "duration": 5,
                    "aspect_ratio": "9:16"
                }
                
                portrait_prediction = await client.create_prediction("kling-ai/kling-v1-6", portrait_input)
                portrait_completed = await client.wait_for_prediction(portrait_prediction["id"], max_wait=600)
                
                portrait_url = portrait_completed["output"][0]
                
                return {
                    "video_url": video_url,
                    "video_url_portrait": portrait_url
                }
                
        except Exception as e:
            log.error(f"Direct HTTP video generation failed: {e}")
            return {"video_url": None, "video_url_portrait": None}


if __name__ == "__main__":
    # Test the direct HTTP client
    async def test_direct_http():
        if not settings.replicate_api_key:
            print("❌ Set REPLICATE_API_KEY in .env to test")
            return
        
        test_prompt = "A futuristic holographic interface in a tech workspace, photorealistic, 16:9 composition"
        
        try:
            async with DirectReplicateClient(settings.replicate_api_key) as client:
                print("🔍 Testing direct HTTP Replicate API...")
                
                image_url = await client.generate_image(test_prompt, 1344, 768)
                print(f"✅ Success! Generated image: {image_url}")
                
        except Exception as e:
            print(f"❌ Direct HTTP test failed: {e}")
    
    # asyncio.run(test_direct_http())
    print("Direct HTTP Replicate client ready!")
    print("This bypasses the Python library compatibility issue completely.")