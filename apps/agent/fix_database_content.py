#!/usr/bin/env python3
"""
Fix database content issues by cleaning incomplete topics and running a fresh pipeline.
"""

import sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, '.')

def main():
    """Fix database content issues."""
    print("🔧 Fixing database content issues...")
    print("=" * 60)
    
    try:
        from utils.supabase_client import db
        
        print("1. 🧹 Cleaning up incomplete topics...")
        
        # Count incomplete topics before cleanup
        try:
            result = db.client.table("trending_topics").select("id", count="exact").eq("status", "predicting").execute()
            predicting_count = result.count if hasattr(result, 'count') else len(result.data or [])
            print(f"   Found {predicting_count} topics stuck in 'predicting' status")
            
            # Delete old incomplete topics (older than 1 day)
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            delete_result = db.client.table("trending_topics").delete().eq("status", "predicting").lt("created_at", cutoff_date).execute()
            deleted_count = len(delete_result.data or [])
            print(f"   🗑️  Deleted {deleted_count} old incomplete topics")
            
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        
        print("\n2. 🔍 Checking keyword blocklist...")
        
        try:
            # Check current keyword blocklist
            blocklist = db.get_config_value("keyword_blocklist", default=[])
            if isinstance(blocklist, list):
                print(f"   Current blocklist has {len(blocklist)} keywords")
                if len(blocklist) > 20:
                    print(f"   ⚠️  Blocklist might be too restrictive with {len(blocklist)} keywords")
                    print(f"   Consider reducing to only extreme keywords")
                elif len(blocklist) == 0:
                    print("   ✅ No keyword blocklist - topics won't be blocked by keywords")
                else:
                    print(f"   ✅ Moderate blocklist size: {blocklist}")
            else:
                print(f"   ⚠️  Unexpected blocklist format: {type(blocklist)}")
                
        except Exception as e:
            print(f"   ⚠️  Blocklist check failed: {e}")
        
        print("\n3. 📊 Current database status:")
        
        try:
            # Get current status breakdown
            result = db.client.table("trending_topics").select("status", count="exact").execute()
            if result.data:
                from collections import Counter
                status_counts = Counter(row["status"] for row in result.data)
                for status, count in status_counts.items():
                    print(f"   {status}: {count} topics")
                    
                published_count = status_counts.get("published", 0)
                if published_count > 0:
                    print(f"   ✅ {published_count} published topics should appear on homepage")
                else:
                    print("   ❌ Still no published content")
            else:
                print("   📋 Database is empty - ready for fresh content")
                
        except Exception as e:
            print(f"   ❌ Status check failed: {e}")
        
        print("\n4. 🚀 Running fresh pipeline with new thresholds...")
        
        try:
            # Import and run the main pipeline
            print("   Starting pipeline execution...")
            from main import main as run_pipeline
            
            # Run the pipeline
            print("   ⏳ This may take a few minutes...")
            result = run_pipeline()
            
            if result:
                print("   ✅ Pipeline completed successfully!")
                
                # Check results
                result = db.client.table("trending_topics").select("status", count="exact").eq("status", "published").execute()
                new_published = result.count if hasattr(result, 'count') else len(result.data or [])
                print(f"   📈 Now have {new_published} published topics")
                
                if new_published > 0:
                    print("   🎉 Content should now appear on your website!")
                else:
                    print("   ⚠️  Pipeline ran but no content was published")
                    print("      Check logs for brand safety, content generation, or media generation failures")
            else:
                print("   ❌ Pipeline execution failed")
                print("      Check logs for specific error details")
                
        except Exception as e:
            print(f"   ❌ Pipeline execution failed: {e}")
            print("      Try running manually: python main.py")
        
        print("\n" + "=" * 60)
        print("🔧 Next steps if still no content:")
        print()
        print("1. Check Supabase logs for pipeline errors")
        print("2. Verify all API keys are set in .env file:")
        print("   - ANTHROPIC_API_KEY (for content generation)")
        print("   - NEWSAPI_KEY (for news data)")
        print("   - GROQ_API_KEY (for brand safety)")
        print("3. Check homepage at your website URL")
        print("4. Run: python main.py (to test pipeline manually)")
        print("5. Check individual node outputs for failures")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)