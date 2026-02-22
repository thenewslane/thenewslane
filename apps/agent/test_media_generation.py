#!/usr/bin/env python3
"""
test_media_generation.py

Test the media generation system to identify why thumbnails aren't being generated.
"""

import asyncio
from config.settings import settings
from utils.logger import get_logger

log = get_logger(__name__)

def test_replicate_config():
    """Test if Replicate API key is loaded correctly"""
    print("🔍 Testing Replicate Configuration")
    print("=" * 40)
    
    print(f"REPLICATE_API_KEY loaded: {'✓' if settings.replicate_api_key else '❌'}")
    if settings.replicate_api_key:
        print(f"  Length: {len(settings.replicate_api_key)} chars")
        print(f"  Starts with: {settings.replicate_api_key[:8]}...")
    
    # Test replicate import
    try:
        import replicate
        print("Replicate library import: ✓")
        
        # Test if client can be created
        client = replicate.Client(api_token=settings.replicate_api_key)
        print("Replicate client creation: ✓")
        
    except Exception as e:
        print(f"Replicate library/client error: ❌ {e}")

async def test_thumbnail_generation():
    """Test thumbnail generation with a simple example"""
    print("\n🔍 Testing Thumbnail Generation")
    print("=" * 40)
    
    try:
        from nodes.media_generation_node import MediaGenerator
        
        # Test MediaGenerator initialization
        try:
            generator = MediaGenerator()
            print("MediaGenerator initialization: ✓")
        except Exception as e:
            print(f"MediaGenerator initialization: ❌ {e}")
            return
        
        # Create a test topic
        test_topic = {
            "id": "test-topic-123",
            "title": "Test Topic",
            "image_prompt": "A photorealistic cinematic scene of a modern tech workspace with computers and coding"
        }
        
        print(f"Test topic created with image_prompt: {len(test_topic['image_prompt'])} chars")
        print("Attempting thumbnail generation...")
        
        try:
            result = await generator.generate_thumbnail(test_topic)
            print(f"Thumbnail generation: ✓")
            print(f"Result: {result}")
        except Exception as e:
            print(f"Thumbnail generation: ❌ {e}")
            print(f"Error type: {type(e).__name__}")
    
    except Exception as e:
        print(f"Media generation test setup failed: ❌ {e}")

def check_pipeline_flow():
    """Check if media generation is called in the pipeline"""
    print("\n🔍 Checking Pipeline Flow")
    print("=" * 40)
    
    # Check if media generation is included in the graph
    try:
        from graph import AgentState
        print("Graph import: ✓")
        
        # The pipeline should have: content_generated_topics -> media_generated_topics
        print("\nPipeline flow should be:")
        print("  classify_topics -> brand_safe_topics")
        print("  generate_content -> content_generated_topics") 
        print("  generate_media -> media_generated_topics  <- CHECK THIS")
        print("  publish -> published_topic_ids")
        
        print("\nIf topics reach publish without media_generated_topics,")
        print("then generate_media node is not being called or is failing.")
    
    except Exception as e:
        print(f"Pipeline flow check failed: ❌ {e}")

async def main():
    test_replicate_config()
    await test_thumbnail_generation()
    check_pipeline_flow()

if __name__ == "__main__":
    asyncio.run(main())