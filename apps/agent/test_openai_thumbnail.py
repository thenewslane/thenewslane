#!/usr/bin/env python3
"""
test_openai_thumbnail.py

Test the OpenAI DALL-E thumbnail generation fix.
"""

import asyncio
from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

async def test_openai_thumbnail():
    """Test OpenAI DALL-E thumbnail generation"""
    
    print("🧪 Testing OpenAI DALL-E Thumbnail Generation")
    print("=" * 50)
    
    # Check if API key is configured
    if not getattr(settings, 'openai_api_key', None) or not settings.openai_api_key:
        print("❌ OPENAI_API_KEY not configured in .env file")
        print("🔑 Get your API key from: https://platform.openai.com/api-keys")
        return
    
    if "get-from-https" in settings.openai_api_key:
        print("❌ OPENAI_API_KEY is still placeholder - update .env with real key")
        return
    
    print(f"✅ OpenAI API key configured: {settings.openai_api_key[:8]}...")
    
    # Test the MediaGenerator
    try:
        from nodes.media_generation_node import MediaGenerator
        
        # Create test topic
        test_topic = {
            "id": "test-openai-123",
            "title": "AI Revolution in Technology",
            "image_prompt": "A futuristic AI workspace with holographic displays and advanced technology, photorealistic, professional lighting"
        }
        
        print(f"📋 Test topic: {test_topic['title']}")
        print(f"🎨 Image prompt: {test_topic['image_prompt'][:60]}...")
        
        # Initialize generator
        generator = MediaGenerator()
        print("✅ MediaGenerator initialized successfully")
        
        # Generate thumbnail
        print("🔄 Generating thumbnail with OpenAI DALL-E...")
        result = await generator.generate_thumbnail(test_topic)
        
        if result and result.get("thumbnail_url"):
            print(f"✅ SUCCESS! Thumbnail generated: {result['thumbnail_url']}")
            print("🎉 OpenAI DALL-E fix is working perfectly!")
            return True
        else:
            print("❌ Thumbnail generation returned None - check logs for errors")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("Check the implementation and API key configuration")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_thumbnail())
    
    if success:
        print("\n🚀 Next steps:")
        print("1. Run your pipeline: python main.py")
        print("2. Check that new topics get thumbnail URLs")
        print("3. Verify thumbnails display correctly in web app")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Verify OPENAI_API_KEY is correct in .env")
        print("2. Check OpenAI account has credits")
        print("3. Review logs for detailed error messages")
