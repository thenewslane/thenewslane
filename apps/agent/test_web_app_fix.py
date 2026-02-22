#!/usr/bin/env python3
"""
Test if the web app query works after fixing the categories table.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Test web app query after fix."""
    print("🧪 Testing Web App Query After Fix")
    print("=" * 50)
    
    try:
        from utils.supabase_client import db
        
        print("1. 🔍 Testing web app query...")
        
        # Test the exact query the web app uses
        try:
            result = db.client.table("trending_topics").select(
                "*, category:categories(id, name, slug, color, description)"
            ).eq("status", "published").order("published_at", desc=True).limit(5).execute()
            
            print(f"   ✅ Web app query successful: {len(result.data or [])} topics")
            
            if result.data:
                sample = result.data[0]
                print(f"   📋 Sample topic: '{sample.get('title', '')[:40]}...'")
                print(f"   📋 Has category: {bool(sample.get('category'))}")
                if sample.get('category'):
                    cat = sample['category']
                    print(f"   📋 Category: {cat.get('name', 'NO NAME')} (color: {cat.get('color', 'NO COLOR')})")
                
                return True
            else:
                print("   ❌ Query returned no data")
                return False
                
        except Exception as e:
            print(f"   ❌ Web app query still failing: {e}")
            
            # Test without color column
            print("\n   🔧 Testing query without color...")
            try:
                fallback_result = db.client.table("trending_topics").select(
                    "*, category:categories(id, name, slug, description)"
                ).eq("status", "published").order("published_at", desc=True).limit(5).execute()
                
                print(f"   ✅ Query without color works: {len(fallback_result.data or [])} topics")
                print("   💡 Update your web app to not require the color column")
                return False
                
            except Exception as e2:
                print(f"   ❌ Even fallback query failed: {e2}")
                return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 SUCCESS! Your web app should now display content!")
        print("\n🔗 Try visiting your website:")
        print("   https://thenewslane.com")
        print("\n💡 If still not showing:")
        print("   1. Hard refresh (Ctrl+Shift+R)")
        print("   2. Wait 2-3 minutes for cache")
        print("   3. Check Vercel deployment logs")
    else:
        print("\n🔧 Next steps:")
        print("1. Add 'color' column to categories table (see add_color_column_sql.sql)")
        print("2. OR update web app query to not require color")
        print("3. Run this test again")
    
    sys.exit(0 if success else 1)