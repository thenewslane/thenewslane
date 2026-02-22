#!/usr/bin/env python3
"""
Diagnose why no content is showing on the site.
Check trending_topics table status and identify pipeline bottlenecks.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Diagnose content pipeline issues."""
    print("🔍 Diagnosing content pipeline issues...")
    print("=" * 60)
    
    try:
        from utils.supabase_client import db
        
        # Check if we can connect to database
        print("📊 Database Connection Test:")
        try:
            # Test basic query
            result = db.client.table("trending_topics").select("count", count="exact").execute()
            total_count = result.count if hasattr(result, 'count') else 0
            print(f"  ✅ Connected to Supabase - {total_count} total rows in trending_topics")
        except Exception as e:
            print(f"  ❌ Database connection failed: {e}")
            print("\n🔧 Fix: Check your .env file for correct SUPABASE_URL and SUPABASE_SERVICE_KEY")
            return False
        
        # Check content by status
        print("\n📈 Content Status Breakdown:")
        try:
            result = db.client.table("trending_topics").select("status", count="exact").execute()
            if result.data:
                from collections import Counter
                status_counts = Counter(row["status"] for row in result.data)
                for status, count in status_counts.items():
                    print(f"  {status}: {count} topics")
                
                if not status_counts:
                    print("  ❌ No topics found in database")
                elif status_counts.get("published", 0) == 0:
                    print(f"  ⚠️  NO PUBLISHED CONTENT - this is why your site is empty!")
                    if status_counts.get("predicting", 0) > 0:
                        print(f"     {status_counts['predicting']} topics stuck in 'predicting' status")
                else:
                    print(f"  ✅ {status_counts['published']} published topics should appear on site")
            else:
                print("  ❌ No data returned from status query")
        except Exception as e:
            print(f"  ❌ Status query failed: {e}")
        
        # Check NULL content fields
        print("\n🔍 Content Completeness Check:")
        try:
            # Check for NULL content fields in recent topics
            result = db.client.table("trending_topics").select(
                "id, status, title, seo_title, article_250w, viral_tier, created_at"
            ).order("created_at", desc=True).limit(10).execute()
            
            if result.data:
                print("  Recent topics (last 10):")
                for i, topic in enumerate(result.data, 1):
                    title = topic.get("title") or "NULL"
                    seo_title = topic.get("seo_title") or "NULL" 
                    article = "NULL" if not topic.get("article_250w") else "✓"
                    status = topic.get("status", "NULL")
                    tier = topic.get("viral_tier", "NULL")
                    
                    print(f"    {i}. [{status}] tier={tier} title='{title[:30]}...' seo={seo_title[:20]} article={article}")
                
                # Count NULL fields
                null_content_count = sum(1 for t in result.data if not t.get("seo_title") or not t.get("article_250w"))
                if null_content_count > 5:
                    print(f"  ⚠️  {null_content_count}/10 recent topics have NULL content fields")
                    print("     This indicates content generation is failing")
            else:
                print("  ❌ No recent topics found")
                
        except Exception as e:
            print(f"  ❌ Content check failed: {e}")
        
        # Check viral score distribution
        print("\n📊 Viral Score Analysis:")
        try:
            result = db.client.table("trending_topics").select(
                "viral_score, viral_tier"
            ).not_.is_("viral_score", "null").execute()
            
            if result.data:
                scores = [float(t["viral_score"]) * 100 for t in result.data if t.get("viral_score") is not None]
                if scores:
                    min_score = min(scores)
                    max_score = max(scores)  
                    avg_score = sum(scores) / len(scores)
                    
                    print(f"  Score range: {min_score:.1f} - {max_score:.1f} (avg: {avg_score:.1f})")
                    
                    # Check if any topics meet new threshold (≥10)
                    passing_scores = [s for s in scores if s >= 10.0]
                    print(f"  Topics ≥10 (new threshold): {len(passing_scores)}/{len(scores)}")
                    
                    if len(passing_scores) == 0:
                        print("  ❌ NO topics meet the new viral threshold of 10!")
                        print("     This suggests the pipeline is still using old thresholds")
                    else:
                        print("  ✅ Topics are passing viral threshold")
                else:
                    print("  ❌ No valid viral scores found")
            else:
                print("  ❌ No topics with viral scores found")
                
        except Exception as e:
            print(f"  ❌ Viral score analysis failed: {e}")
        
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("Make sure you're running from the correct directory with virtual environment activated")
        return False
    
    # Provide solutions
    print("\n" + "=" * 60)
    print("🔧 SOLUTIONS:")
    print()
    
    print("1. **Run the pipeline manually** to test new thresholds:")
    print("   cd /Users/admin/Desktop/platform/apps/agent")  
    print("   python main.py")
    print()
    
    print("2. **Clear stuck 'predicting' topics** (optional):")
    print("   -- Run this SQL in Supabase dashboard:")
    print("   DELETE FROM trending_topics WHERE status = 'predicting' AND created_at < NOW() - INTERVAL '1 day';")
    print()
    
    print("3. **Check for restrictive keyword blocklist:**")
    print("   SELECT * FROM config WHERE key = 'keyword_blocklist';")
    print("   -- If too many blocked keywords, update with:")
    print("   UPDATE config SET value = '[\"extreme-only\"]'::jsonb WHERE key = 'keyword_blocklist';")
    print()
    
    print("4. **Monitor pipeline logs** for errors:")
    print("   Check for brand safety, content generation, or media generation failures")
    print()
    
    print("5. **Force publish existing good topics** (if any exist):")
    print("   -- Find topics with content but not published:")
    print("   SELECT id, title, status FROM trending_topics") 
    print("   WHERE seo_title IS NOT NULL AND article_250w IS NOT NULL AND status != 'published';")
    print("   -- Manually set to published:")
    print("   UPDATE trending_topics SET status = 'published', published_at = NOW()")
    print("   WHERE id IN ('topic-id-1', 'topic-id-2');")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)