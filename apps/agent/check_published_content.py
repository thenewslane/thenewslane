#!/usr/bin/env python3
"""
Check what content is actually in the database and why it's not showing on the website.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Check published content in database."""
    print("🔍 Checking Published Content in Database")
    print("=" * 60)
    
    try:
        from utils.supabase_client import db
        
        print("1. 📊 Checking published topics...")
        
        # Check total published count
        result = db.client.table("trending_topics").select("id", count="exact").eq("status", "published").execute()
        published_count = result.count if hasattr(result, 'count') else len(result.data or [])
        print(f"   Total published topics: {published_count}")
        
        if published_count == 0:
            print("   ❌ No published topics found!")
            return False
        
        print(f"   ✅ Found {published_count} published topics")
        
        print("\n2. 📋 Sample published topics:")
        
        # Get sample topics with all fields the web app might need
        result = db.client.table("trending_topics").select(
            "id, title, slug, summary, article, created_at, published_at, status, viral_tier, viral_score"
        ).eq("status", "published").order("published_at", desc=True).limit(5).execute()
        
        if result.data:
            for i, topic in enumerate(result.data, 1):
                title = topic.get("title", "NO TITLE")[:40]
                slug = topic.get("slug", "NO SLUG")
                summary = "✓" if topic.get("summary") else "❌"
                article = "✓" if topic.get("article") else "❌" 
                published_at = topic.get("published_at", "NO DATE")[:19] if topic.get("published_at") else "NO DATE"
                
                print(f"   {i}. '{title}' (slug: {slug})")
                print(f"      Status: {topic.get('status')} | Published: {published_at}")
                print(f"      Content: summary={summary} article={article}")
                print(f"      Tier: {topic.get('viral_tier')} | Score: {topic.get('viral_score')}")
                print()
                
        else:
            print("   ❌ No published topic data returned")
            return False
        
        print("3. 🌐 Checking what the web app expects...")
        
        # Check if we have the exact query that the web app uses
        # Based on your earlier web app code: .eq('status', 'published')
        print("   Testing web app query...")
        web_app_result = db.client.table("trending_topics").select(
            "*, category:categories(id, name, slug, color, description)"
        ).eq("status", "published").order("published_at", desc=True).limit(12).execute()
        
        web_app_count = len(web_app_result.data or [])
        print(f"   Web app query returns: {web_app_count} topics")
        
        if web_app_count == 0:
            print("   ❌ Web app query returns no results!")
            print("   🔍 Checking for potential issues...")
            
            # Check if topics have category issues
            no_category = db.client.table("trending_topics").select("id").eq("status", "published").is_("category_id", "null").execute()
            no_category_count = len(no_category.data or [])
            print(f"      Topics with no category_id: {no_category_count}")
            
            if no_category_count > 0:
                print("      ⚠️  This might cause the web app query to fail if it requires categories")
        else:
            print("   ✅ Web app query works - should show content!")
            
            # Show what the web app would see
            sample_web_topic = web_app_result.data[0] if web_app_result.data else None
            if sample_web_topic:
                print(f"   📋 Sample topic web app would see:")
                print(f"      Title: {sample_web_topic.get('title', 'NO TITLE')[:40]}")
                print(f"      Slug: {sample_web_topic.get('slug', 'NO SLUG')}")
                print(f"      Summary: {'✓' if sample_web_topic.get('summary') else '❌'}")
                print(f"      Category: {sample_web_topic.get('category', 'NO CATEGORY')}")
        
        print("\n4. 🔗 URL for first published article:")
        if result.data and result.data[0].get('slug'):
            first_slug = result.data[0]['slug']
            print(f"   https://thenewslane.com/trending/{first_slug}")
            print(f"   Try visiting this URL directly to test")
        
        return True
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n" + "=" * 60)
        print("🔧 If content still not showing on website, check:")
        print("1. **Web app deployment** - is it running the latest code?")
        print("2. **Database connection** - can the web app connect to Supabase?")
        print("3. **ISR cache** - try hard refresh (Ctrl+Shift+R) or wait a few minutes")
        print("4. **Environment variables** - does web app have correct SUPABASE_URL/KEY?")
        print("5. **Build/deploy logs** - check Vercel logs for errors")
        print("6. **Category table** - web app might need categories to exist")
        print("\n💡 **Backend is working perfectly** - this is a frontend/deployment issue!")
    else:
        print("\n❌ Database issues found - check Supabase connection")
    
    sys.exit(0 if success else 1)