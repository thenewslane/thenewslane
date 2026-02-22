#!/usr/bin/env python3
"""
debug_thumbnail_generation.py

Debug why thumbnails aren't being generated for topics.
"""

from utils.supabase_client import db
from utils.logger import get_logger

log = get_logger(__name__)

def check_image_prompts():
    """Check if topics have image_prompt field required for thumbnail generation"""
    
    print("🔍 Checking image prompts in recent topics")
    print("=" * 50)
    
    try:
        # Get recent topics and check for image_prompt
        result = db.client.table("trending_topics").select(
            "id, title, schema_blocks, thumbnail_url"
        ).eq("status", "published").limit(10).order("created_at", desc=True).execute()
        
        topics = result.data
        print(f"📊 Checking {len(topics)} recent topics")
        
        topics_with_image_prompt = 0
        topics_with_thumbnail = 0
        
        for i, topic in enumerate(topics[:5], 1):
            title = topic.get("title", "Unknown")[:50]
            schema_blocks = topic.get("schema_blocks") or {}
            image_prompt = schema_blocks.get("image_prompt")
            thumbnail_url = topic.get("thumbnail_url")
            
            print(f"\n{i}. {title}...")
            print(f"   ID: {topic['id']}")
            print(f"   Image prompt: {'✓' if image_prompt else '❌'} ({len(image_prompt) if image_prompt else 0} chars)")
            if image_prompt:
                print(f"     Content: {image_prompt[:100]}...")
                topics_with_image_prompt += 1
            print(f"   Thumbnail URL: {'✓' if thumbnail_url else '❌'}")
            if thumbnail_url:
                topics_with_thumbnail += 1
        
        print(f"\n📊 Summary:")
        print(f"  Topics with image_prompt: {topics_with_image_prompt}/{len(topics[:5])}")
        print(f"  Topics with thumbnail_url: {topics_with_thumbnail}/{len(topics[:5])}")
        
        if topics_with_image_prompt == 0:
            print("\n❌ No topics have image_prompt - content generation may not be working")
        elif topics_with_thumbnail == 0:
            print("\n❌ Topics have image_prompt but no thumbnails - media generation not working")
        
    except Exception as e:
        print(f"❌ Image prompt check failed: {e}")

def check_media_generation_logs():
    """Look for media generation in pipeline logs"""
    print("\n🔍 Media Generation Analysis")
    print("=" * 40)
    
    print("Media generation should:")
    print("  1. Take topics with image_prompt from content generation")
    print("  2. Call Replicate API with black-forest-labs/flux-1.1-pro")
    print("  3. Upload generated image to Supabase Storage 'thumbnails' bucket")
    print("  4. Add thumbnail_url to topic")
    
    print("\nPossible issues:")
    print("  - Replicate API key missing or invalid")
    print("  - Supabase Storage bucket not accessible")
    print("  - Media generation node not being called in pipeline")
    print("  - Error in thumbnail generation that's being silently ignored")

def check_replicate_config():
    """Check if Replicate is properly configured"""
    print("\n🔍 Checking Replicate Configuration")
    print("=" * 40)
    
    try:
        import os
        replicate_token = os.getenv("REPLICATE_API_TOKEN")
        print(f"REPLICATE_API_TOKEN: {'✓ Set' if replicate_token else '❌ Missing'}")
        
        if replicate_token:
            print(f"  Length: {len(replicate_token)} chars")
            print(f"  Starts with: {replicate_token[:8]}...")
    
    except Exception as e:
        print(f"❌ Replicate config check failed: {e}")

if __name__ == "__main__":
    check_image_prompts()
    check_media_generation_logs()
    check_replicate_config()