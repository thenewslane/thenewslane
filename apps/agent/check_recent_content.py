#!/usr/bin/env python3
"""
check_recent_content.py

Diagnostic script to check content generated in the last 24 hours
and identify issues with homepage display, thumbnails, and article access.
"""

from datetime import datetime, timedelta
from utils.supabase_client import db
from utils.logger import get_logger

log = get_logger(__name__)

def analyze_recent_content():
    """Analyze content from the last 24 hours"""
    
    # Calculate 24 hours ago
    twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
    
    print(f"🔍 Checking content published in last 24 hours (since {twenty_four_hours_ago})")
    print("=" * 80)
    
    try:
        # Query recent published content
        result = db.client.table("trending_topics").select(
            "id, slug, title, summary, article, thumbnail_url, video_url, category_id, "
            "viral_score, viral_tier, status, created_at, updated_at"
        ).eq("status", "published").gte("created_at", twenty_four_hours_ago).order("created_at", desc=True).execute()
        
        topics = result.data
        print(f"📊 Found {len(topics)} published topics in last 24 hours")
        
        if not topics:
            print("❌ No content found in last 24 hours - this explains why homepage is empty")
            return
        
        # Analyze content quality
        content_with_summary = sum(1 for t in topics if t.get("summary"))
        content_with_article = sum(1 for t in topics if t.get("article"))
        content_with_thumbnail = sum(1 for t in topics if t.get("thumbnail_url"))
        content_with_video = sum(1 for t in topics if t.get("video_url"))
        
        print("\n📈 Content Quality Analysis:")
        print(f"  ✓ With summary: {content_with_summary}/{len(topics)} ({100*content_with_summary/len(topics):.1f}%)")
        print(f"  ✓ With article: {content_with_article}/{len(topics)} ({100*content_with_article/len(topics):.1f}%)")
        print(f"  ✓ With thumbnail: {content_with_thumbnail}/{len(topics)} ({100*content_with_thumbnail/len(topics):.1f}%)")
        print(f"  ✓ With video: {content_with_video}/{len(topics)} ({100*content_with_video/len(topics):.1f}%)")
        
        print("\n📋 Recent Content Sample:")
        for i, topic in enumerate(topics[:5]):  # Show first 5
            print(f"\n{i+1}. {topic['title'][:60]}...")
            print(f"   ID: {topic['id']}")
            print(f"   Slug: {topic['slug']}")
            print(f"   Category ID: {topic.get('category_id', 'None')}")
            print(f"   Summary: {'✓' if topic.get('summary') else '❌'} ({len(topic.get('summary', ''))} chars)")
            print(f"   Article: {'✓' if topic.get('article') else '❌'} ({len(topic.get('article', ''))} chars)")
            print(f"   Thumbnail: {'✓' if topic.get('thumbnail_url') else '❌'}")
            if topic.get('thumbnail_url'):
                print(f"     URL: {topic['thumbnail_url'][:80]}...")
            print(f"   Created: {topic['created_at']}")
        
        # Check for 500 error potential causes
        print("\n🔧 Article Page Issues Analysis:")
        missing_content = [t for t in topics if not t.get('summary') or not t.get('article')]
        if missing_content:
            print(f"  ❌ {len(missing_content)} topics missing essential content (could cause 500 errors)")
            for topic in missing_content[:3]:
                print(f"     - {topic['slug']}: summary={'✓' if topic.get('summary') else '❌'}, article={'✓' if topic.get('article') else '❌'}")
        
        # Check thumbnail issues
        print("\n🖼️ Thumbnail Issues Analysis:")
        missing_thumbnails = [t for t in topics if not t.get('thumbnail_url')]
        if missing_thumbnails:
            print(f"  ❌ {len(missing_thumbnails)} topics missing thumbnails")
            for topic in missing_thumbnails[:3]:
                print(f"     - {topic['slug']}: {topic['title'][:40]}...")
        
        broken_thumbnails = [t for t in topics if t.get('thumbnail_url') and 'null' in str(t.get('thumbnail_url')).lower()]
        if broken_thumbnails:
            print(f"  ❌ {len(broken_thumbnails)} topics with broken thumbnail URLs")
        
    except Exception as e:
        print(f"❌ Database query failed: {e}")

def check_categories():
    """Check if categories table has proper data"""
    print("\n📂 Categories Analysis:")
    print("=" * 40)
    
    try:
        result = db.client.table("categories").select("*").execute()
        categories = result.data
        
        print(f"📊 Found {len(categories)} categories")
        for cat in categories:
            print(f"  - {cat.get('name', 'Unknown')}: {cat.get('description', 'No description')[:50]}...")
            if not cat.get('color'):
                print(f"    ⚠️ Missing color field")
    
    except Exception as e:
        print(f"❌ Categories query failed: {e}")

def suggest_fixes():
    """Suggest fixes for identified issues"""
    print("\n🔧 Suggested Fixes:")
    print("=" * 40)
    
    print("1. Homepage showing no content:")
    print("   - Check if web app query filters by last 24 hours correctly")
    print("   - Verify web app is querying 'published' status correctly")
    print("   - Check if web app handles thumbnail_url field properly")
    
    print("\n2. Article pages return 500 errors:")
    print("   - Check if web app expects specific fields that might be null")
    print("   - Verify slug-based routing works in web app")
    print("   - Check if article content parsing handles new field names")
    
    print("\n3. Category tabs not working:")
    print("   - Verify categories table has color field")
    print("   - Check if web app category filtering works")
    print("   - Ensure category names match between database and web app")
    
    print("\n4. Thumbnails not displayed:")
    print("   - Verify Supabase Storage bucket 'thumbnails' is public")
    print("   - Check if thumbnail URLs are accessible")
    print("   - Ensure web app displays thumbnail_url field correctly")
    
    print("\n5. Article summary word count:")
    print("   - Updated backend to generate 30-word summaries (summary_30w)")
    print("   - Web app may need to adjust display logic for new field structure")

if __name__ == "__main__":
    analyze_recent_content()
    check_categories()
    suggest_fixes()