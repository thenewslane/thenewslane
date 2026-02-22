#!/usr/bin/env python3
"""
Verify the API key fix and test the pipeline.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Verify API fix and test pipeline."""
    print("🔧 Verifying API key fix...")
    print("=" * 50)
    
    # Step 1: Test API key
    print("1. 🔑 Testing new API key...")
    try:
        from config.settings import settings
        from anthropic import Anthropic
        
        if settings.anthropic_api_key == "YOUR_NEW_API_KEY_HERE":
            print("❌ You need to replace YOUR_NEW_API_KEY_HERE with your actual API key!")
            print("   Edit .env file and set: ANTHROPIC_API_KEY=sk-ant-api03-...")
            return False
        
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        # Quick test
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            messages=[{"role": "user", "content": "Say 'API working' if you can read this."}],
            max_tokens=10,
            temperature=0.0
        )
        
        result = response.content[0].text.strip()
        print(f"   ✅ API key working! Response: '{result}'")
        
    except Exception as e:
        print(f"   ❌ API key still not working: {e}")
        if "YOUR_NEW_API_KEY_HERE" in str(e):
            print("   Please update .env with your actual API key from Anthropic Console")
        return False
    
    # Step 2: Test classification node specifically
    print("\n2. 🏷️  Testing classification node...")
    try:
        from nodes.classification_node import ClassificationNode
        
        classifier = ClassificationNode()
        
        # Test with a simple topic
        test_topics = [{
            "keyword": "Apple iPhone",
            "title": "Apple releases new iPhone 15",
            "headline_cluster": "Apple unveils latest iPhone with new features"
        }]
        
        result = classifier.classify_topics_batch(test_topics)
        
        if result and len(result) > 0 and "category" in result[0]:
            category = result[0]["category"]
            print(f"   ✅ Classification working! Test topic classified as: '{category}'")
        else:
            print("   ❌ Classification failed - no category returned")
            return False
            
    except Exception as e:
        print(f"   ❌ Classification node failed: {e}")
        return False
    
    # Step 3: Suggest next steps
    print("\n3. 🚀 Ready to run pipeline!")
    print("   Your API key is now working. You can run:")
    print("   python main.py")
    print()
    print("   This will:")
    print("   - Collect trending topics")
    print("   - Score them for virality") 
    print("   - Filter for brand safety")
    print("   - Classify into categories ✅ (now working)")
    print("   - Generate content")
    print("   - Create media assets")
    print("   - Publish to your site")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)