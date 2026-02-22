#!/usr/bin/env python3
"""
Update settings.py and .env for alternative image generation services
"""

# Add these to config/settings.py
SETTINGS_UPDATE = '''
class Settings(BaseSettings):
    # ... existing fields ...
    
    # ── Alternative Image Generation Services ────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key for DALL-E image generation")
    stability_api_key: str = Field(default="", description="Stability AI API key for image generation") 
    huggingface_api_key: str = Field(default="", description="Hugging Face API key for inference")
    unsplash_access_key: str = Field(default="", description="Unsplash API key for stock photos")
    
    # Image generation preferences
    image_service: str = Field(default="openai", description="Primary image service: openai, stability, huggingface, unsplash")
    image_fallback_service: str = Field(default="unsplash", description="Fallback if primary fails")
'''

# Add these to .env file
ENV_UPDATE = '''
# Alternative Image Generation (replace Replicate)
OPENAI_API_KEY=sk-proj-...  # Get from https://platform.openai.com/api-keys
STABILITY_API_KEY=sk-...    # Get from https://platform.stability.ai/account/keys
HUGGINGFACE_API_KEY=hf_...  # Get from https://huggingface.co/settings/tokens
UNSPLASH_ACCESS_KEY=...     # Get from https://unsplash.com/developers

# Service preferences
IMAGE_SERVICE=openai        # Primary: openai, stability, huggingface, unsplash
IMAGE_FALLBACK_SERVICE=unsplash  # Fallback service
'''

# Updated media_generation_node.py
MEDIA_NODE_UPDATE = '''
class MediaGenerator:
    def __init__(self):
        if not settings.replicate_api_key:
            log.warning("REPLICATE_API_KEY missing - using alternative image generation")
        
        # Initialize alternative services instead of Replicate
        self.use_alternatives = True
        self.storage = StorageManager()
        self.http_client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_thumbnail(self, topic: Dict[str, Any]) -> Dict[str, str]:
        """Generate thumbnail using alternative services (not Replicate)"""
        
        if self.use_alternatives:
            return await self.generate_thumbnail_alternative(topic)
        else:
            # Original Replicate code (if working)
            return await self.generate_thumbnail_replicate(topic)
    
    async def generate_thumbnail_alternative(self, topic: Dict[str, Any]) -> Dict[str, str]:
        """Use OpenAI/Stability/HuggingFace instead of Replicate"""
        
        image_prompt = topic.get("image_prompt", "")
        topic_id = topic.get("id", f"topic_{uuid.uuid4().hex[:8]}")
        
        if not image_prompt:
            return {"thumbnail_url": None}
        
        log.info(f"Generating thumbnail for {topic_id} using {settings.image_service}")
        
        try:
            # Try primary service
            if settings.image_service == "openai" and settings.openai_api_key:
                image_url = await self._generate_openai(image_prompt)
            elif settings.image_service == "stability" and settings.stability_api_key:
                image_url = await self._generate_stability(image_prompt)
            elif settings.image_service == "huggingface" and settings.huggingface_api_key:
                image_url = await self._generate_huggingface(image_prompt)
            else:
                raise ValueError(f"Service {settings.image_service} not configured")
            
            # Upload to Supabase Storage
            public_url = await self._upload_generated_image(image_url, topic_id)
            
            return {"thumbnail_url": public_url}
            
        except Exception as e:
            log.warning(f"Primary service failed: {e}, trying fallback")
            
            # Try fallback service (Unsplash stock photos)
            try:
                stock_url = await self._get_stock_photo(image_prompt)
                return {"thumbnail_url": stock_url}
            except Exception as fe:
                log.error(f"All image services failed: {fe}")
                return {"thumbnail_url": None}
'''

print("📋 Settings Update for Alternative Image Generation")
print("=" * 55)

print("\n1. Add to config/settings.py:")
print(SETTINGS_UPDATE)

print("\n2. Add to .env file:")
print(ENV_UPDATE)

print("\n3. API Key Setup Instructions:")
print("=" * 35)

services = [
    ("OpenAI DALL-E", "https://platform.openai.com/api-keys", "$0.04 per image", "Most reliable, high quality"),
    ("Stability AI", "https://platform.stability.ai/account/keys", "$0.05-0.10 per image", "Good quality, fast"),
    ("Hugging Face", "https://huggingface.co/settings/tokens", "Free tier available", "Good for testing"),
    ("Unsplash", "https://unsplash.com/developers", "Free", "Stock photos, no generation")
]

for service, url, cost, note in services:
    print(f"\n🔑 {service}:")
    print(f"   URL: {url}")
    print(f"   Cost: {cost}")
    print(f"   Note: {note}")

print(f"\n4. Recommended Setup:")
print("   - Primary: OpenAI DALL-E (most reliable)")
print("   - Fallback: Unsplash (free stock photos)")
print("   - Budget option: Hugging Face (free tier)")

print(f"\n5. Cost Comparison (per 1000 thumbnails):")
print("   - Replicate (Flux): ~$50-100")
print("   - OpenAI DALL-E: ~$40") 
print("   - Stability AI: ~$50-100")
print("   - Hugging Face: Free tier, then ~$20")
print("   - Unsplash: Free")