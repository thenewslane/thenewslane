#!/usr/bin/env python3
"""
Debug content generation pipeline to identify why topics are being skipped at publish.
"""

import sys
import asyncio
sys.path.insert(0, '.')

async def debug_content_generation():
    """Debug the content generation process."""
    print("🔍 Debugging Content Generation Pipeline")
    print("=" * 60)
    
    # Step 1: Test if Anthropic API is working
    print("1. 🔑 Testing Anthropic API...")
    try:
        from config.settings import settings
        from anthropic import Anthropic
        
        if settings.anthropic_api_key == "REPLACE_WITH_NEW_API_KEY":
            print("   ❌ API key still not updated!")
            return False
            
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        # Test basic call
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=[{"role": "user", "content": "Say 'Working' if you can read this."}],
            max_tokens=10,
            temperature=0.0
        )
        
        result = response.content[0].text.strip()
        print(f"   ✅ API working: '{result}'")
        
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        print("   Please update ANTHROPIC_API_KEY in .env file")
        return False
    
    # Step 2: Create a mock topic
    print("\n2. 📝 Creating mock topic...")
    mock_topic = {
        "id": "debug-topic-123",
        "title": "Debug Test Topic",
        "keyword": "debug test",
        "headline_cluster": "Testing headline cluster for debug purposes",
        "viral_tier": 2,
        "viral_score": 0.15,
        "category": "Technology"
    }
    print(f"   ✅ Mock topic created: '{mock_topic['title']}'")
    
    # Step 3: Test content generation directly
    print("\n3. 🤖 Testing content generation...")
    try:
        from nodes.content_generation_node import ContentGenerator
        
        generator = ContentGenerator()
        print("   ✅ Content generator initialized")
        
        # Generate content for single topic
        semaphore = asyncio.Semaphore(1)
        enriched_topic = await generator._generate_content_for_topic(mock_topic, semaphore)
        
        print(f"   📊 Result keys: {list(enriched_topic.keys())}")
        print(f"   📊 Content generated: {enriched_topic.get('content_generated', False)}")
        print(f"   📊 Has summary_16w: {bool(enriched_topic.get('summary_16w'))}")
        print(f"   📊 Has article_50w: {bool(enriched_topic.get('article_50w'))}")
        
        if enriched_topic.get('summary_16w'):
            summary_words = len(enriched_topic['summary_16w'].split())
            print(f"   📊 Summary word count: {summary_words}")
        
        if enriched_topic.get('article_50w'):
            article_words = len(enriched_topic['article_50w'].split())
            print(f"   📊 Article word count: {article_words}")
        
        # Check if it would pass publish validation
        would_skip = not enriched_topic.get("summary_16w") or not enriched_topic.get("article_50w")
        if would_skip:
            print("   ❌ Topic would be SKIPPED at publish!")
            print(f"       Missing fields: summary_16w={bool(enriched_topic.get('summary_16w'))}, article_50w={bool(enriched_topic.get('article_50w'))}")
        else:
            print("   ✅ Topic would PASS publish validation!")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Content generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the debug process."""
    try:
        success = asyncio.run(debug_content_generation())
        if success:
            print("\n🎉 Debug completed successfully!")
        else:
            print("\n❌ Debug failed - check errors above")
        return success
    except Exception as e:
        print(f"\n💥 Debug script failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)