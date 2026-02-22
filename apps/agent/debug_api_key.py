#!/usr/bin/env python3
"""
Debug API key issues with detailed diagnostics.
"""

import sys
import os
sys.path.insert(0, '.')

def main():
    """Debug API key configuration."""
    print("🔍 API Key Debug Diagnostics")
    print("=" * 50)
    
    # Check 1: Raw .env file content
    print("1. 📁 Raw .env file check:")
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            if 'ANTHROPIC_API_KEY' in line:
                key_part = line.strip().split('=', 1)[1] if '=' in line else 'NO VALUE'
                key_preview = key_part[:20] + "..." if len(key_part) > 20 else key_part
                print(f"   Line {i}: ANTHROPIC_API_KEY={key_preview}")
                
                # Check for issues
                if key_part == "REPLACE_WITH_NEW_API_KEY":
                    print("   ❌ ISSUE: Still contains placeholder!")
                    print("   🔧 FIX: Replace with your actual API key from Anthropic Console")
                    return False
                elif not key_part.startswith('sk-ant-'):
                    print("   ❌ ISSUE: API key doesn't start with 'sk-ant-'")
                    print("   🔧 FIX: Get a valid API key from https://console.anthropic.com")
                    return False
                elif len(key_part) < 50:
                    print("   ❌ ISSUE: API key seems too short")
                    print("   🔧 FIX: Double-check you copied the complete key")
                    return False
                else:
                    print("   ✅ Format looks correct")
                
    except FileNotFoundError:
        print("   ❌ .env file not found!")
        return False
    except Exception as e:
        print(f"   ❌ Error reading .env file: {e}")
        return False
    
    # Check 2: Settings loading
    print("\n2. ⚙️  Settings loading check:")
    try:
        from config.settings import settings
        
        api_key = settings.anthropic_api_key
        if not api_key:
            print("   ❌ API key is empty in settings")
            return False
        
        key_preview = api_key[:20] + "..." if len(api_key) > 20 else api_key
        print(f"   Loaded key: {key_preview}")
        
        if api_key == "REPLACE_WITH_NEW_API_KEY":
            print("   ❌ ISSUE: Settings loaded placeholder instead of real key")
            print("   🔧 FIX: Update .env file and restart Python")
            return False
        
        print("   ✅ Settings loaded successfully")
        
    except Exception as e:
        print(f"   ❌ Settings loading failed: {e}")
        return False
    
    # Check 3: Anthropic client creation
    print("\n3. 🤖 Anthropic client test:")
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=settings.anthropic_api_key)
        print("   ✅ Client created successfully")
        
    except Exception as e:
        print(f"   ❌ Client creation failed: {e}")
        return False
    
    # Check 4: Model availability test
    print("\n4. 📡 API call test:")
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Use a more standard model name
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
            temperature=0.0
        )
        
        result = response.content[0].text.strip()
        print(f"   ✅ API call successful! Response: '{result}'")
        
        # Test the model used in classification
        print("\n   🔍 Testing classification model...")
        response2 = client.messages.create(
            model="claude-3-haiku-20240307",  # Standard Haiku model
            messages=[{"role": "user", "content": "Say 'OK' if you understand"}],
            max_tokens=5,
            temperature=0.0
        )
        
        result2 = response2.content[0].text.strip()
        print(f"   ✅ Classification model works! Response: '{result2}'")
        
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        print(f"   ❌ API call failed: {e}")
        
        if "401" in error_str or "authentication" in error_str:
            print("\n   🔧 POSSIBLE FIXES:")
            print("   1. Double-check your API key is correct")
            print("   2. Make sure you copied the COMPLETE key (no spaces/truncation)")
            print("   3. Generate a fresh API key at https://console.anthropic.com")
            print("   4. Check your Anthropic account status and billing")
        elif "model" in error_str:
            print("\n   🔧 MODEL ISSUE:")
            print("   1. The model 'claude-haiku-4-5-20251001' might not exist")
            print("   2. Try using 'claude-3-haiku-20240307' instead")
        
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n" + "=" * 50)
        print("❌ NEXT STEPS:")
        print("1. Get a NEW API key from: https://console.anthropic.com/")
        print("2. Copy the COMPLETE key (should be ~100 characters)")
        print("3. Edit .env file and replace REPLACE_WITH_NEW_API_KEY")
        print("4. Make sure there are no extra spaces or characters")
        print("5. Save the file and run this script again")
    else:
        print("\n🎉 API key is working! You can now run: python main.py")
    
    sys.exit(0 if success else 1)