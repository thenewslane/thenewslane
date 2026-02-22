#!/usr/bin/env python3
"""
fix_replicate_option3_alternatives.py

Replace Replicate with alternative image generation services that work with Python 3.14.
"""

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

class AlternativeImageGenerator:
    """Alternative image generation using OpenAI DALL-E, Stability AI, or other services"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    # Option 3A: OpenAI DALL-E 3 (Most reliable)
    async def generate_with_openai(self, prompt: str, size: str = "1792x1024") -> str:
        """Generate image using OpenAI DALL-E 3"""
        
        # Requires OPENAI_API_KEY in settings
        if not getattr(settings, 'openai_api_key', None):
            raise ValueError("OPENAI_API_KEY required for DALL-E image generation")
        
        payload = {
            "model": "dall-e-3",
            "prompt": prompt[:4000],  # DALL-E has prompt limits
            "size": size,  # "1024x1024", "1792x1024", or "1024x1792"
            "quality": "standard",  # or "hd" for higher quality
            "n": 1
        }
        
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        response = await self.http_client.post(
            "https://api.openai.com/v1/images/generations",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        data = response.json()
        image_url = data["data"][0]["url"]
        
        log.info(f"Generated image with OpenAI DALL-E: {image_url}")
        return image_url

    # Option 3B: Stability AI (Good alternative)
    async def generate_with_stability(self, prompt: str, width: int = 1344, height: int = 768) -> str:
        """Generate image using Stability AI"""
        
        if not getattr(settings, 'stability_api_key', None):
            raise ValueError("STABILITY_API_KEY required for Stability AI generation")
        
        payload = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30
        }
        
        headers = {
            "Authorization": f"Bearer {settings.stability_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        response = await self.http_client.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Stability AI error: {response.status_code} - {response.text}")
        
        data = response.json()
        # Stability returns base64 encoded images
        import base64
        image_base64 = data["artifacts"][0]["base64"]
        
        # Save to temp file and return path for upload
        temp_path = f"/tmp/stability_{uuid.uuid4().hex[:8]}.png"
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
        
        log.info(f"Generated image with Stability AI: {temp_path}")
        return temp_path

    # Option 3C: Hugging Face (Free alternative)
    async def generate_with_huggingface(self, prompt: str, model: str = "stabilityai/stable-diffusion-xl-base-1.0") -> str:
        """Generate image using Hugging Face Inference API"""
        
        if not getattr(settings, 'huggingface_api_key', None):
            raise ValueError("HUGGINGFACE_API_KEY required for HF generation")
        
        headers = {
            "Authorization": f"Bearer {settings.huggingface_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 25,
                "guidance_scale": 7.5
            }
        }
        
        response = await self.http_client.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Hugging Face error: {response.status_code} - {response.text}")
        
        # HF returns raw image bytes
        temp_path = f"/tmp/hf_{uuid.uuid4().hex[:8]}.jpg"
        with open(temp_path, "wb") as f:
            f.write(response.content)
        
        log.info(f"Generated image with Hugging Face: {temp_path}")
        return temp_path

    # Option 3D: Unsplash (Free stock photos - no generation)
    async def get_unsplash_photo(self, query: str) -> str:
        """Get relevant stock photo from Unsplash"""
        
        if not getattr(settings, 'unsplash_access_key', None):
            raise ValueError("UNSPLASH_ACCESS_KEY required")
        
        # Search for relevant photo
        search_url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query[:100],
            "per_page": 1,
            "orientation": "landscape"
        }
        headers = {
            "Authorization": f"Client-ID {settings.unsplash_access_key}"
        }
        
        response = await self.http_client.get(search_url, params=params, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Unsplash error: {response.status_code}")
        
        data = response.json()
        if not data.get("results"):
            raise Exception("No Unsplash photos found for query")
        
        photo = data["results"][0]
        image_url = photo["urls"]["regular"]  # 1080px width
        
        log.info(f"Found Unsplash photo: {image_url}")
        return image_url


# Example usage in media_generation_node.py
async def generate_thumbnail_alternative(topic: Dict[str, Any]) -> Dict[str, str]:
    """
    Drop-in replacement for the Replicate thumbnail generation
    """
    image_prompt = topic.get("image_prompt", "")
    topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
    
    if not image_prompt:
        raise ValueError("No image_prompt found in topic")
    
    log.info(f"Generating thumbnail for topic {topic_id} using alternative service")
    
    async with AlternativeImageGenerator() as generator:
        try:
            # Option A: Use OpenAI DALL-E (most reliable, ~$0.04 per image)
            image_url = await generator.generate_with_openai(
                prompt=image_prompt,
                size="1792x1024"  # Close to our 1344x768 requirement
            )
            
            # Download the image
            response = await generator.http_client.get(image_url)
            temp_path = f"/tmp/thumbnail_{topic_id}.jpg"
            with open(temp_path, "wb") as f:
                f.write(response.content)
            
            # Upload to Supabase Storage (existing code)
            from nodes.media_generation_node import StorageManager
            storage = StorageManager()
            public_url = await storage.upload_file(temp_path, "thumbnails", f"{topic_id}.jpg")
            
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
            
            return {"thumbnail_url": public_url}
            
        except Exception as e:
            log.error(f"Alternative thumbnail generation failed: {e}")
            
            # Fallback to Unsplash stock photo
            try:
                # Extract key terms from prompt for search
                search_terms = image_prompt.split()[:3]  # First 3 words
                query = " ".join(search_terms)
                
                stock_url = await generator.get_unsplash_photo(query)
                return {"thumbnail_url": stock_url}
                
            except Exception as fallback_error:
                log.error(f"Unsplash fallback failed: {fallback_error}")
                return {"thumbnail_url": None}


if __name__ == "__main__":
    # Test the alternatives
    async def test_alternatives():
        test_prompt = "A futuristic tech workspace with holographic displays and AI interfaces"
        
        generator = AlternativeImageGenerator()
        
        # Test each service (uncomment to test)
        # url = await generator.generate_with_openai(test_prompt)
        # print(f"OpenAI result: {url}")
        
        print("Alternative image generation services ready!")
        print("Update your .env file with API keys:")
        print("OPENAI_API_KEY=sk-...")
        print("STABILITY_API_KEY=sk-...")
        print("HUGGINGFACE_API_KEY=hf_...")
        print("UNSPLASH_ACCESS_KEY=...")
    
    # asyncio.run(test_alternatives())
    print("Run this script to test alternative image generation services")