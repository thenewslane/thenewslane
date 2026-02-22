#!/usr/bin/env python3
"""
Clean up trending_topics table by removing or fixing topics that were published without content.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Clean up empty published topics."""
    print("🧹 Cleaning up empty published topics...")
    print("=" * 60)
    
    try:
        from utils.supabase_client import db
        
        print("1. 🔍 Finding empty published topics...")
        
        # Find topics marked as published but with no content
        try:
            result = db.client.table("trending_topics").select(
                "id, title, status, summary, article, created_at"
            ).eq("status", "published").execute()
            
            if result.data:
                empty_topics = []
                valid_topics = []
                
                for topic in result.data:
                    has_summary = topic.get("summary") is not None and topic.get("summary").strip()
                    has_article = topic.get("article") is not None and topic.get("article").strip()
                    
                    if not has_summary or not has_article:
                        empty_topics.append(topic)
                    else:
                        valid_topics.append(topic)
                
                print(f"   Found {len(empty_topics)} empty published topics")
                print(f"   Found {len(valid_topics)} topics with valid content")
                
                if empty_topics:
                    print("\n   Sample empty topics:")
                    for i, topic in enumerate(empty_topics[:5], 1):
                        title = (topic.get("title") or "NO TITLE")[:40]
                        created = topic.get("created_at", "")[:10]  # Just date part
                        summary_status = "✓" if topic.get("summary") else "❌"
                        article_status = "✓" if topic.get("article") else "❌"
                        print(f"     {i}. '{title}' ({created}) summary={summary_status} article={article_status}")
                
                if valid_topics:
                    print(f"\n   ✅ {len(valid_topics)} topics have proper content and should show on website")
                    
                    if len(valid_topics) > 0 and len(empty_topics) > 0:
                        print("   🤔 If content still isn't showing, check:")
                        print("      - Web app deployment and build")
                        print("      - Vercel ISR revalidation")
                        print("      - Database connection in web app")
            else:
                print("   📋 No published topics found")
                
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            return False
        
        if empty_topics:
            print(f"\n2. 🗑️  Cleaning up {len(empty_topics)} empty topics...")
            
            try:
                # Method 1: Delete empty published topics (recommended)
                empty_ids = [t["id"] for t in empty_topics]
                
                # Delete in batches of 50 to avoid query limits
                deleted_count = 0
                for i in range(0, len(empty_ids), 50):
                    batch_ids = empty_ids[i:i+50]
                    delete_result = db.client.table("trending_topics").delete().in_("id", batch_ids).execute()
                    batch_deleted = len(delete_result.data or [])
                    deleted_count += batch_deleted
                    print(f"   Deleted batch {i//50 + 1}: {batch_deleted} topics")
                
                print(f"   ✅ Successfully deleted {deleted_count} empty published topics")
                
                # Alternative Method 2: Set status back to 'predicting' (commented out)
                # This would keep the topics but mark them as incomplete
                # update_result = db.client.table("trending_topics").update({
                #     "status": "predicting",
                #     "published_at": None
                # }).in_("id", empty_ids).execute()
                # print(f"   ✅ Reset {len(update_result.data)} topics to 'predicting' status")
                
            except Exception as e:
                print(f"   ❌ Cleanup failed: {e}")
                return False
        else:
            print("\n2. ✅ No empty topics to clean up")
        
        print("\n3. 📊 Final status check...")
        
        try:
            # Check final counts
            from collections import Counter
            result = db.client.table("trending_topics").select("status").execute()
            
            if result.data:
                status_counts = Counter(row["status"] for row in result.data)
                print("   Current status breakdown:")
                for status, count in sorted(status_counts.items()):
                    print(f"     {status}: {count} topics")
                
                published_count = status_counts.get("published", 0)
                if published_count > 0:
                    print(f"\n   🎉 {published_count} properly published topics should now appear on website!")
                    
                    # Check if these are actually populated
                    content_check = db.client.table("trending_topics").select("id").eq("status", "published").not_.is_("summary", "null").not_.is_("article", "null").execute()
                    content_count = len(content_check.data or [])
                    
                    if content_count == published_count:
                        print(f"   ✅ All {content_count} published topics have content!")
                    else:
                        print(f"   ⚠️  Only {content_count}/{published_count} published topics have content")
                else:
                    print("\n   📭 No published topics remain - run pipeline to generate fresh content")
            else:
                print("   📋 Database is empty")
                
        except Exception as e:
            print(f"   ❌ Final status check failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Cleanup complete!")
        print()
        print("Next steps:")
        print("1. Check your website homepage - it should now show only topics with actual content")
        print("2. If still no content, run: python main.py (to generate fresh content)")
        print("3. Monitor pipeline logs for content generation failures")
        print()
        print("The publish node has been fixed to prevent future empty topics from being published.")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup script failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)