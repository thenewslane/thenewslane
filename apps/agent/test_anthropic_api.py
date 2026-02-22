#!/usr/bin/env python3
"""
Test the Anthropic API key to see if it's valid and working.
"""

import sys
sys.path.insert(0, '.')

def test_anthropic_api():
    """Test if the Anthropic API key is working."""
    print("🔑 Testing Anthropic API key...")
    print("=" * 50)
    
    try:
        from config.settings import settings
        from anthropic import Anthropic
        
        print(f"✅ Settings loaded successfully")
        print(f"   API key starts with: {settings.anthropic_api_key[:20]}...")
        
        # Initialize client
        client = Anthropic(api_key=settings.anthropic_api_key)
        print("✅ Anthropic client initialized")
        
        # Test simple API call
        print("\n🧪 Testing API call with a simple classification...")
        
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            messages=[{
                "role": "user",
                "content": "Classify this topic into one category: Technology, Politics, Business, Entertainment, Sports, Science, World News, Lifestyle, Environment, or Education. Topic: 'Apple releases new iPhone' - Return only the category name."
            }],
            max_tokens=20,
            temperature=0.0
        )
        
        result = response.content[0].text.strip()
        print(f"✅ API call successful!")
        print(f"   Response: '{result}'")
        
        if result in ["Technology", "Politics", "Business", "Entertainment", "Sports", "Science", "World News", "Lifestyle", "Environment", "Education"]:
            print("✅ Response format is correct")
        else:
            print(f"⚠️  Unexpected response format: '{result}'")
        
        print("\n🎉 Anthropic API key is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        
        # Check specific error types
        error_str = str(e).lower()
        if "401" in error_str or "authentication" in error_str or "api key" in error_str:
            print("\n🔧 FIX NEEDED: Invalid API key")
            print("   1. Check if your Anthropic API key has expired")
            print("   2. Generate a new API key at: https://console.anthropic.com/")
            print("   3. Update ANTHROPIC_API_KEY in your .env file")
            print("   4. Make sure you have sufficient credits in your Anthropic account")
            
        elif "403" in error_str or "forbidden" in error_str:
            print("\n🔧 FIX NEEDED: Access denied")
            print("   1. Check if your Anthropic account has access to Claude models")
            print("   2. Verify your account is in good standing")
            
        elif "model" in error_str:
            print("\n🔧 FIX NEEDED: Model access issue")
            print("   1. Check if 'claude-haiku-4-5-20251001' is the correct model name")
            print("   2. Your account might not have access to this model")
            
        elif "rate limit" in error_str or "429" in error_str:
            print("\n🔧 FIX NEEDED: Rate limit")
            print("   1. Wait a few minutes and try again")
            print("   2. Check if you've exceeded your API quota")
            
        else:
            print(f"\n🔧 UNKNOWN ERROR: {e}")
            print("   1. Check your internet connection")
            print("   2. Verify Anthropic service status")
            print("   3. Try regenerating your API key")
        
        return False

if __name__ == "__main__":
    success = test_anthropic_api()
    sys.exit(0 if success else 1)