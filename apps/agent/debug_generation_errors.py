#!/usr/bin/env python3
"""
Debug what's in the generation_errors field to identify the root cause.
"""

import sys
import asyncio
sys.path.insert(0, '.')

def main():
    """Debug content generation errors."""
    print("🔍 Debugging Content Generation Errors")
    print("=" * 60)
    
    # Check API key status first
    print("1. 🔑 Checking API key...")
    try:
        from config.settings import settings
        
        if "REPLACE_WITH_NEW_API_KEY" in settings.anthropic_api_key:
            print("   ❌ API key still contains placeholder!")
            print("   🔧 Update .env file with your actual Anthropic API key")
            return False
        
        api_key_preview = settings.anthropic_api_key[:20] + "..." if len(settings.anthropic_api_key) > 20 else settings.anthropic_api_key
        print(f"   ✅ API key loaded: {api_key_preview}")
        
    except Exception as e:
        print(f"   ❌ Settings error: {e}")
        return False
    
    # Test a simple content generation call
    print("\n2. 🧪 Testing content generation with mock topic...")
    
    mock_topic = {
        "id": "debug-test-123",
        "title": "Test Debug Topic",
        "keyword": "debug test",
        "headline_cluster": "Testing content generation for debugging purposes",
        "viral_tier": 2,
        "viral_score": 0.15,
        "category": "Technology"
    }
    
    try:
        # Import and test the content generator directly
        from nodes.content_generation_node import ContentGenerator
        
        print("   🔧 Creating content generator...")
        generator = ContentGenerator()
        
        print("   🔧 Testing content generation...")
        
        # Test the async function
        async def test_generation():
            semaphore = asyncio.Semaphore(1)
            try:
                result = await generator._generate_content_for_topic(mock_topic, semaphore)
                return result
            except Exception as e:
                print(f"   ❌ Content generation failed: {e}")
                print(f"   📝 Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                return {**mock_topic, "content_generated": False, "generation_errors": [str(e)]}
        
        # Run the test
        result = asyncio.run(test_generation())
        
        print(f"\n   📊 Result keys: {list(result.keys())}")
        print(f"   📊 content_generated: {result.get('content_generated', False)}")
        print(f"   📊 Has generation_errors: {bool(result.get('generation_errors'))}")
        
        if result.get('generation_errors'):
            print(f"   🚨 Generation errors found:")
            for i, error in enumerate(result.get('generation_errors', []), 1):
                print(f"      {i}. {error}")
        
        if result.get('content_generated'):
            print(f"   ✅ Content generation successful!")
            print(f"   📊 summary_16w: {bool(result.get('summary_16w'))}")
            print(f"   📊 article_50w: {bool(result.get('article_50w'))}")
        else:
            print(f"   ❌ Content generation failed!")
        
        return result.get('content_generated', False)
        
    except Exception as e:
        print(f"   💥 Content generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n" + "=" * 60)
        print("🔧 LIKELY ISSUES:")
        print("1. API key is invalid/expired (401 authentication error)")
        print("2. Model names are wrong (fixed in previous update)")
        print("3. API rate limits or quota exceeded")
        print("4. Network/connectivity issues")
        print("5. Malformed requests or invalid parameters")
        print("\n💡 SOLUTIONS:")
        print("1. Get new API key from: https://console.anthropic.com/")
        print("2. Check Anthropic account status and billing")
        print("3. Verify model names are correct")
        print("4. Check internet connectivity")
    
    sys.exit(0 if success else 1)