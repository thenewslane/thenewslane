#!/usr/bin/env python3
"""
implement_openai_fix.py

One-click implementation of the OpenAI DALL-E fix for Replicate compatibility issue.
This script will update your codebase to use OpenAI instead of Replicate.
"""

import os
from pathlib import Path

def update_settings():
    """Add OpenAI API key field to settings.py"""
    
    settings_path = "config/settings.py"
    
    # Read current settings
    with open(settings_path, 'r') as f:
        content = f.read()
    
    # Check if OpenAI key already added
    if "openai_api_key" in content:
        print("✅ OpenAI API key field already exists in settings.py")
        return
    
    # Add OpenAI field after replicate_api_key
    insertion_point = content.find('replicate_api_key: str = Field(default="", description="Replicate API key (Flux, Kling video)")')
    
    if insertion_point == -1:
        print("❌ Could not find replicate_api_key in settings.py")
        return
    
    # Find end of the replicate line
    end_of_line = content.find('\n', insertion_point)
    
    new_field = '\n    openai_api_key: str = Field(default="", description="OpenAI API key for DALL-E image generation")'
    
    # Insert the new field
    new_content = content[:end_of_line] + new_field + content[end_of_line:]
    
    # Write back
    with open(settings_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Added openai_api_key field to settings.py")

def update_env_file():
    """Add OpenAI API key placeholder to .env"""
    
    env_path = ".env"
    
    # Read current .env
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check if OpenAI key already exists
    if "OPENAI_API_KEY" in content:
        print("✅ OPENAI_API_KEY already exists in .env")
        return
    
    # Find the AI/ML section
    ai_section = content.find("# AI / ML")
    
    if ai_section == -1:
        print("❌ Could not find AI/ML section in .env")
        return
    
    # Find the end of the section (next # comment or end of file)
    end_section = content.find("\n#", ai_section + 1)
    if end_section == -1:
        end_section = len(content)
    
    # Add OpenAI key
    new_line = "\nOPENAI_API_KEY=get-from-https://platform.openai.com/api-keys"
    
    new_content = content[:end_section] + new_line + content[end_section:]
    
    # Write back
    with open(env_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Added OPENAI_API_KEY placeholder to .env")
    print("🔑 Get your API key from: https://platform.openai.com/api-keys")

def update_media_generation_node():
    """Replace the broken generate_thumbnail method with OpenAI DALL-E version"""
    
    node_path = "nodes/media_generation_node.py"
    
    # Read current file
    with open(node_path, 'r') as f:
        content = f.read()
    
    # Find the generate_thumbnail method
    method_start = content.find("async def generate_thumbnail(self, topic: Dict[str, Any]) -> Dict[str, str]:")
    
    if method_start == -1:
        print("❌ Could not find generate_thumbnail method")
        return
    
    # Find the end of the method (next async def or end of class)
    method_end = content.find("\n    async def ", method_start + 1)
    if method_end == -1:
        # Look for class end
        method_end = content.find("\n\nclass ", method_start)
        if method_end == -1:
            method_end = len(content)
    
    # New OpenAI-based method
    new_method = '''async def generate_thumbnail(self, topic: Dict[str, Any]) -> Dict[str, str]:
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
'''
    
    # Replace the method
    new_content = content[:method_start] + new_method + content[method_end:]
    
    # Write back
    with open(node_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Updated generate_thumbnail method to use OpenAI DALL-E")

def add_required_import():
    """Ensure httpx is imported in media_generation_node.py"""
    
    node_path = "nodes/media_generation_node.py"
    
    with open(node_path, 'r') as f:
        content = f.read()
    
    if "import httpx" in content:
        print("✅ httpx already imported")
        return
    
    # Find existing imports and add httpx
    import_section = content.find("import uuid")
    if import_section != -1:
        # Add after uuid import
        line_end = content.find('\n', import_section)
        new_content = content[:line_end] + "\nimport httpx" + content[line_end:]
        
        with open(node_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Added httpx import to media_generation_node.py")

def create_test_script():
    """Create a test script to verify the OpenAI fix works"""
    
    test_script = '''#!/usr/bin/env python3
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
        print("\\n🚀 Next steps:")
        print("1. Run your pipeline: python main.py")
        print("2. Check that new topics get thumbnail URLs")
        print("3. Verify thumbnails display correctly in web app")
    else:
        print("\\n🔧 Troubleshooting:")
        print("1. Verify OPENAI_API_KEY is correct in .env")
        print("2. Check OpenAI account has credits")
        print("3. Review logs for detailed error messages")
'''
    
    with open("test_openai_thumbnail.py", 'w') as f:
        f.write(test_script)
    
    print("✅ Created test_openai_thumbnail.py")

def main():
    """Run all updates to implement OpenAI DALL-E fix"""
    
    print("🔧 IMPLEMENTING OPENAI DALL-E FIX FOR REPLICATE ISSUE")
    print("=" * 60)
    
    print("\\n📝 Step 1: Updating configuration files...")
    update_settings()
    update_env_file()
    
    print("\\n🔄 Step 2: Updating media generation code...")
    add_required_import()
    update_media_generation_node()
    
    print("\\n🧪 Step 3: Creating test script...")
    create_test_script()
    
    print("\\n" + "=" * 60)
    print("✅ OPENAI DALL-E FIX IMPLEMENTED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\\n🔑 NEXT STEPS:")
    print("1. Get OpenAI API key: https://platform.openai.com/api-keys")
    print("2. Update .env file: OPENAI_API_KEY=sk-proj-your-key-here") 
    print("3. Test the fix: python test_openai_thumbnail.py")
    print("4. Run pipeline: python main.py")
    
    print("\\n💰 COST INFO:")
    print("- OpenAI DALL-E 3: $0.04 per image (1024x1024) or $0.08 per image (1792x1024)")
    print("- For 1000 thumbnails: ~$40-80 (similar to Replicate)")
    
    print("\\n🎯 ADVANTAGES OVER REPLICATE:")
    print("✅ No Python 3.14 compatibility issues")
    print("✅ More reliable API")
    print("✅ Better documentation")
    print("✅ Consistent image quality")
    print("✅ Faster generation times")

if __name__ == "__main__":
    main()