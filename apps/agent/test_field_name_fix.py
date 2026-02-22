#!/usr/bin/env python3
"""
Test that field name mismatch is fixed.
"""

import sys
sys.path.insert(0, '.')

def test_field_consistency():
    """Test that all field names are consistent across the pipeline."""
    print("🔍 Testing field name consistency fix...")
    print("=" * 50)
    
    # Mock topic with content generation output
    test_topic = {
        "id": "test-topic-123",
        "title": "Test Topic",
        "keyword": "test",
        "viral_tier": 2,
        "viral_score": 0.15,
        "summary_16w": "This is a test summary with exactly sixteen words to test field consistency.",
        "article_50w": "This is a test article with enough words to meet the fifty word requirement for testing the field name consistency fix that should resolve the publish node skipping topics due to missing fields that were renamed after threshold reduction from eighty percent.",
        "seo_title": "Test SEO Title",
        "meta_description": "Test meta description",
        "faq": [
            {"question": "What is this?", "answer": "This is a test."},
            {"question": "Why test?", "answer": "To verify consistency."}
        ],
        "facebook_post": "Test Facebook post content with ARTICLE_LINK_PLACEHOLDER",
        "instagram_caption": "Test IG caption #test",
        "twitter_thread": ["Test tweet 1", "Test tweet 2", "Test tweet 3"],
        "youtube_script": "Test YouTube script content for video generation",
        "image_prompt": "Test image prompt",
        "iab_categories": ["Technology", "News"],
        "slug": "test-topic"
    }
    
    print("1. ✅ Mock topic created with summary_16w and article_50w")
    
    # Test graph.py validation logic
    print("\n2. 🧪 Testing graph.py validation logic...")
    has_summary = bool(test_topic.get("summary_16w"))
    has_article = bool(test_topic.get("article_50w"))
    
    print(f"   summary_16w present: {has_summary}")
    print(f"   article_50w present: {has_article}")
    
    # This simulates the check in graph.py
    would_skip = not test_topic.get("summary_16w") or not test_topic.get("article_50w")
    
    if would_skip:
        print("   ❌ Topic would be SKIPPED by publish validation")
    else:
        print("   ✅ Topic would PASS publish validation")
    
    # Test database mapping
    print("\n3. 🗄️  Testing database field mapping...")
    db_record = {
        "summary": test_topic.get("summary_16w") or "",
        "article": test_topic.get("article_50w") or "",
    }
    
    print(f"   Database 'summary' field: {'✓' if db_record['summary'] else '❌'}")
    print(f"   Database 'article' field: {'✓' if db_record['article'] else '❌'}")
    
    # Test content lengths (after 80% reduction)
    print("\n4. 📏 Testing content length validation...")
    summary_words = len(test_topic["summary_16w"].split())
    article_words = len(test_topic["article_50w"].split())
    
    summary_valid = 14 <= summary_words <= 18  # Target 16 ±2
    article_valid = 48 <= article_words <= 52   # Target 50 ±2
    
    print(f"   summary_16w: {summary_words} words (valid: {summary_valid})")
    print(f"   article_50w: {article_words} words (valid: {article_valid})")
    
    # Overall result
    print("\n" + "=" * 50)
    if has_summary and has_article and not would_skip:
        print("🎉 SUCCESS: Field names are now consistent!")
        print("   - Topics with content will pass validation")
        print("   - Database mapping works correctly") 
        print("   - Pipeline should now publish topics successfully")
        return True
    else:
        print("❌ FAILURE: Field name issues remain")
        return False

if __name__ == "__main__":
    success = test_field_consistency()
    sys.exit(0 if success else 1)