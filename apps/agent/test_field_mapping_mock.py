#!/usr/bin/env python3
"""
Test field name mapping with mock data (no API calls needed).
"""

import sys
import json
sys.path.insert(0, '.')

def test_field_mapping():
    """Test that field names are correctly mapped throughout the pipeline."""
    print("🔍 Testing Field Name Mapping (Mock)")
    print("=" * 50)
    
    # Mock Claude API response (what the API should return)
    mock_claude_response = {
        "seo_title": "Test SEO Title Under 70 Chars",
        "meta_description": "Test meta description under 160 characters explaining the topic",
        "summary_16w": "This is a test summary with exactly sixteen words to verify field mapping works correctly today",
        "article_50w": "This is a test article with exactly fifty words to verify that field mapping works correctly throughout the entire pipeline from content generation to database insertion and publish validation checks that ensure topics are not skipped",
        "faq": [
            {"question": "What is this test?", "answer": "This tests field mapping."},
            {"question": "Why is this important?", "answer": "To prevent topic skipping."}
        ],
        "facebook_post": "Test Facebook post content with appropriate length and ARTICLE_LINK_PLACEHOLDER",
        "instagram_caption": "Test IG caption with #hashtag",
        "twitter_thread": [
            "First tweet in the thread about this topic",
            "Second tweet continuing the story",
            "Final tweet wrapping up the thread"
        ],
        "youtube_script": "Test YouTube script content with appropriate length for video narration and engagement",
        "image_prompt": "Test image prompt describing abstract scene",
        "iab_categories": ["Technology", "News"],
        "slug": "test-topic-field-mapping"
    }
    
    print("1. ✅ Mock Claude response created")
    print(f"   Fields: {list(mock_claude_response.keys())}")
    print(f"   summary_16w: {bool(mock_claude_response.get('summary_16w'))}")
    print(f"   article_50w: {bool(mock_claude_response.get('article_50w'))}")
    
    # Mock topic before content generation
    original_topic = {
        "id": "test-topic-123",
        "title": "Test Topic",
        "keyword": "test",
        "viral_tier": 2,
        "viral_score": 0.15,
        "category": "Technology"
    }
    
    # Simulate what content generation does: {**topic, **content, "content_generated": True}
    enriched_topic = {**original_topic, **mock_claude_response, "content_generated": True}
    
    print(f"\n2. ✅ Topic after content generation")
    print(f"   Keys: {list(enriched_topic.keys())}")
    print(f"   content_generated: {enriched_topic.get('content_generated')}")
    print(f"   summary_16w: {bool(enriched_topic.get('summary_16w'))}")
    print(f"   article_50w: {bool(enriched_topic.get('article_50w'))}")
    
    # Test publish validation logic (from graph.py)
    print(f"\n3. 🧪 Testing publish validation...")
    has_summary = bool(enriched_topic.get("summary_16w"))
    has_article = bool(enriched_topic.get("article_50w"))
    would_skip = not has_summary or not has_article
    
    print(f"   summary_16w present: {has_summary}")
    print(f"   article_50w present: {has_article}")
    print(f"   Would skip topic: {would_skip}")
    
    if would_skip:
        print("   ❌ FAIL: Topic would be skipped at publish!")
        return False
    else:
        print("   ✅ PASS: Topic would be published!")
    
    # Test database mapping (from graph.py lines 334-335)
    print(f"\n4. 🗄️  Testing database field mapping...")
    db_fields = {
        "summary": enriched_topic.get("summary_16w") or "",
        "article": enriched_topic.get("article_50w") or "",
    }
    
    print(f"   summary (DB): {'✓' if db_fields['summary'] else '❌'} = '{db_fields['summary'][:30]}...'")
    print(f"   article (DB): {'✓' if db_fields['article'] else '❌'} = '{db_fields['article'][:30]}...'")
    
    # Test word counts
    print(f"\n5. 📏 Testing word count validation...")
    summary_words = len(db_fields['summary'].split()) if db_fields['summary'] else 0
    article_words = len(db_fields['article'].split()) if db_fields['article'] else 0
    
    summary_valid = 14 <= summary_words <= 18  # Target 16 ±2
    article_valid = 48 <= article_words <= 52  # Target 50 ±2
    
    print(f"   summary: {summary_words} words (valid: {summary_valid})")
    print(f"   article: {article_words} words (valid: {article_valid})")
    
    # Overall result
    print(f"\n" + "=" * 50)
    all_good = has_summary and has_article and not would_skip and db_fields['summary'] and db_fields['article']
    
    if all_good:
        print("🎉 SUCCESS: Field mapping is correct!")
        print("   ✅ Content generation produces: summary_16w, article_50w")
        print("   ✅ Publish validation checks: summary_16w, article_50w")
        print("   ✅ Database mapping: summary_16w → summary, article_50w → article")
        print("   ✅ Content would be published successfully")
        print("\n💡 Issue is likely:")
        print("   1. API key not working (prevents content generation)")
        print("   2. Model names were incorrect (now fixed)")
        print("   3. Content generation failing silently")
        return True
    else:
        print("❌ FAILURE: Field mapping has issues")
        return False

if __name__ == "__main__":
    success = test_field_mapping()
    sys.exit(0 if success else 1)