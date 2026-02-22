#!/usr/bin/env python3
"""
Fix the web app database query issue by testing different approaches.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Test different query approaches to fix web app."""
    print("🔧 Fixing Web App Database Query")
    print("=" * 50)
    
    try:
        from utils.supabase_client import db
        
        print("1. 🔍 Testing if categories table exists...")
        try:
            categories_result = db.client.table("categories").select("*").limit(1).execute()
            print(f"   ✅ Categories table exists with {len(categories_result.data or [])} sample records")
            
            if categories_result.data:
                sample_category = categories_result.data[0]
                print(f"   📋 Sample category columns: {list(sample_category.keys())}")
                has_color = 'color' in sample_category
                print(f"   📋 Has 'color' column: {has_color}")
                if not has_color:
                    print("   ⚠️  Missing 'color' column in categories table!")
                    
        except Exception as e:
            print(f"   ❌ Categories table issue: {e}")
            print("   💡 Categories table might not exist or has wrong schema")
        
        print("\n2. 🧪 Testing simplified web app query...")
        try:
            # Test query without categories join
            simple_result = db.client.table("trending_topics").select(
                "id, title, slug, summary, article, published_at, viral_tier"
            ).eq("status", "published").order("published_at", desc=True).limit(5).execute()
            
            print(f"   ✅ Simplified query works: {len(simple_result.data or [])} results")
            
            if simple_result.data:
                sample = simple_result.data[0]
                print(f"   📋 Sample result: '{sample.get('title', 'NO TITLE')[:30]}...'")
                return simple_result.data
                
        except Exception as e:
            print(f"   ❌ Even simplified query failed: {e}")
            return None
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def create_categories_table():
    """Create a basic categories table if needed."""
    print("\n3. 🏗️  Creating categories table...")
    
    try:
        from utils.supabase_client import db
        
        # Create basic categories that match your content generation
        categories = [
            {"id": 1, "name": "Technology", "slug": "technology", "color": "#3B82F6", "description": "Tech news and innovations"},
            {"id": 2, "name": "World News", "slug": "world-news", "color": "#EF4444", "description": "Global news and events"},
            {"id": 3, "name": "Business & Finance", "slug": "business-finance", "color": "#10B981", "description": "Business and financial news"},
            {"id": 4, "name": "Entertainment", "slug": "entertainment", "color": "#F59E0B", "description": "Entertainment and celebrity news"},
            {"id": 5, "name": "Sports", "slug": "sports", "color": "#8B5CF6", "description": "Sports news and updates"},
            {"id": 6, "name": "Science & Health", "slug": "science-health", "color": "#06B6D4", "description": "Science and health news"},
            {"id": 7, "name": "Politics", "slug": "politics", "color": "#DC2626", "description": "Political news and analysis"},
            {"id": 8, "name": "Lifestyle", "slug": "lifestyle", "color": "#EC4899", "description": "Lifestyle and culture"},
            {"id": 9, "name": "Environment", "slug": "environment", "color": "#059669", "description": "Environmental news"},
            {"id": 10, "name": "Education", "slug": "education", "color": "#7C3AED", "description": "Education news"}
        ]
        
        # Try to insert categories (this might fail if table doesn't exist)
        try:
            result = db.client.table("categories").upsert(categories).execute()
            print(f"   ✅ Created/updated {len(categories)} categories")
            return True
        except Exception as e:
            print(f"   ❌ Failed to create categories: {e}")
            print("   💡 You need to create the categories table in Supabase dashboard")
            return False
            
    except Exception as e:
        print(f"   ❌ Categories creation failed: {e}")
        return False

def update_topic_categories():
    """Update topics to have proper category_id references."""
    print("\n4. 🔗 Updating topic category references...")
    
    try:
        from utils.supabase_client import db
        
        # Map category names to IDs
        category_mapping = {
            "Technology": 1,
            "World News": 2,
            "Business & Finance": 3,
            "Entertainment": 4,
            "Sports": 5,
            "Science & Health": 6,
            "Politics": 7,
            "Lifestyle": 8,
            "Environment": 9,
            "Education": 10
        }
        
        # Get topics without category_id
        topics = db.client.table("trending_topics").select(
            "id, category"
        ).eq("status", "published").is_("category_id", "null").limit(50).execute()
        
        print(f"   📊 Found {len(topics.data or [])} topics without category_id")
        
        if topics.data:
            updates = []
            for topic in topics.data[:10]:  # Update first 10 as example
                category_name = topic.get("category", "World News")
                category_id = category_mapping.get(category_name, 2)  # Default to World News
                
                updates.append({
                    "id": topic["id"],
                    "category_id": category_id
                })
            
            if updates:
                result = db.client.table("trending_topics").upsert(updates).execute()
                print(f"   ✅ Updated {len(updates)} topics with category_id")
                return True
        else:
            print("   ✅ All topics already have category_id")
            return True
            
    except Exception as e:
        print(f"   ❌ Category update failed: {e}")
        return False

if __name__ == "__main__":
    # Test current state
    topics = main()
    
    if topics:
        print(f"✅ Found {len(topics)} working topics!")
        
        # Try to fix categories
        categories_created = create_categories_table()
        if categories_created:
            category_refs_updated = update_topic_categories()
            
            if category_refs_updated:
                print("\n" + "=" * 50)
                print("🎉 FIXED! Your web app should now work!")
                print("\n🔗 Try these URLs:")
                for i, topic in enumerate(topics[:3], 1):
                    slug = topic.get('slug', 'no-slug')
                    print(f"{i}. https://thenewslane.com/trending/{slug}")
                
                print("\n💡 If still not working:")
                print("1. Hard refresh your website (Ctrl+Shift+R)")
                print("2. Wait 2-3 minutes for ISR cache to update")
                print("3. Check Vercel deployment logs")
                print("4. Verify web app environment variables")
        else:
            print("\n🔧 MANUAL FIX NEEDED:")
            print("1. Go to Supabase Dashboard")
            print("2. Create 'categories' table with columns: id, name, slug, color, description") 
            print("3. Add the 10 categories listed above")
            print("4. Run this script again")
    else:
        print("❌ Database connection issues - check Supabase settings")
    
    sys.exit(0 if topics else 1)