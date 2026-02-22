#!/usr/bin/env python3
"""
Test different Claude model names to find which ones work.
"""

import sys
sys.path.insert(0, '.')

def test_model_names():
    """Test different Claude model names."""
    print("🔍 Testing Claude Model Names")
    print("=" * 50)
    
    try:
        from config.settings import settings
        from anthropic import Anthropic
        
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        # List of model names to test
        models_to_test = [
            "claude-3-5-sonnet-20241022",  # Original (failed)
            "claude-3-5-sonnet-20240620",  # First attempt (failed)
            "claude-3-5-sonnet-latest",    # Latest
            "claude-3-5-sonnet",           # Basic name
            "claude-3-sonnet-20240229",    # Claude 3 Sonnet
            "claude-3-opus-20240229",      # Claude 3 Opus
            "claude-3-haiku-20240307",     # Claude 3 Haiku (known to work)
        ]
        
        working_models = []
        
        for model_name in models_to_test:
            print(f"\n🧪 Testing model: {model_name}")
            try:
                response = client.messages.create(
                    model=model_name,
                    messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
                    max_tokens=5,
                    temperature=0.0
                )
                
                result = response.content[0].text.strip()
                print(f"   ✅ SUCCESS: '{result}'")
                working_models.append(model_name)
                
            except Exception as e:
                error_str = str(e)
                if "404" in error_str or "not_found" in error_str:
                    print(f"   ❌ NOT FOUND: Model doesn't exist")
                elif "401" in error_str or "authentication" in error_str:
                    print(f"   ❌ AUTH ERROR: {e}")
                elif "403" in error_str or "forbidden" in error_str:
                    print(f"   ❌ FORBIDDEN: No access to this model")
                else:
                    print(f"   ❌ ERROR: {e}")
        
        print(f"\n" + "=" * 50)
        if working_models:
            print(f"✅ WORKING MODELS:")
            for model in working_models:
                print(f"   - {model}")
            
            # Recommend the best one
            if "claude-3-5-sonnet" in working_models[0]:
                recommended = working_models[0]
            else:
                recommended = working_models[0]
            
            print(f"\n💡 RECOMMENDED: {recommended}")
            return recommended
        else:
            print("❌ NO WORKING MODELS FOUND")
            print("   Your account may not have access to Claude models")
            print("   Check your Anthropic account status and billing")
            return None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

if __name__ == "__main__":
    recommended_model = test_model_names()
    
    if recommended_model:
        print(f"\n🔧 NEXT STEP:")
        print(f"   Update content generation to use: {recommended_model}")
    else:
        print(f"\n🚨 ISSUE:")
        print(f"   No Claude models are accessible with your API key")
        print(f"   Check Anthropic Console for account status")
    
    sys.exit(0 if recommended_model else 1)