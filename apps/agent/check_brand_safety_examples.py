#!/usr/bin/env python3
"""
Show real examples from brand_safety_log to demonstrate how filtering works.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Show real brand safety examples from logs."""
    print("📊 BRAND SAFETY FILTERING EXAMPLES")
    print("=" * 60)
    
    try:
        from utils.supabase_client import db
        
        print("1. 🔍 Recent Brand Safety Decisions:")
        
        # Get recent brand safety log entries
        logs = db.client.table("brand_safety_log").select(
            "topic_title, tier1_passed, tier1_blocked_keyword, tier2_passed, tier2_flagged_categories, tier3_passed, tier3_explanation, overall_passed, created_at"
        ).order("created_at", desc=True).limit(10).execute()
        
        if logs.data:
            for i, log in enumerate(logs.data, 1):
                title = log.get("topic_title", "NO TITLE")[:50]
                overall = "✅ PASSED" if log.get("overall_passed") else "❌ REJECTED"
                created = log.get("created_at", "")[:19] if log.get("created_at") else ""
                
                print(f"\n{i}. '{title}...' ({created})")
                print(f"   RESULT: {overall}")
                
                # Show tier results
                tier1 = "✅" if log.get("tier1_passed") else "❌"
                tier2 = "✅" if log.get("tier2_passed") else "❌"
                tier3 = "✅" if log.get("tier3_passed") else "❌"
                print(f"   TIERS: Keyword={tier1} | LlamaGuard={tier2} | BrandSafety={tier3}")
                
                # Show rejection reasons
                if not log.get("tier1_passed"):
                    keyword = log.get("tier1_blocked_keyword", "unknown")
                    print(f"   BLOCKED: Keyword '{keyword}'")
                elif not log.get("tier2_passed"):
                    categories = log.get("tier2_flagged_categories", [])
                    print(f"   FLAGGED: Llama Guard categories: {categories}")
                elif not log.get("tier3_passed"):
                    explanation = log.get("tier3_explanation", "No explanation")[:100]
                    print(f"   UNSAFE: {explanation}")
        else:
            print("   No brand safety logs found")
            
        print(f"\n2. 📈 Summary Statistics:")
        
        # Get statistics
        try:
            total_logs = db.client.table("brand_safety_log").select("id", count="exact").execute()
            total_count = total_logs.count if hasattr(total_logs, 'count') else 0
            
            passed_logs = db.client.table("brand_safety_log").select("id", count="exact").eq("overall_passed", True).execute()
            passed_count = passed_logs.count if hasattr(passed_logs, 'count') else 0
            
            rejection_rate = ((total_count - passed_count) / total_count * 100) if total_count > 0 else 0
            
            print(f"   Total topics processed: {total_count}")
            print(f"   Topics passed: {passed_count}")
            print(f"   Topics rejected: {total_count - passed_count}")
            print(f"   Rejection rate: {rejection_rate:.1f}%")
            
        except Exception as e:
            print(f"   Could not get statistics: {e}")
        
        print(f"\n3. 🚫 Common Rejection Reasons:")
        
        # Tier 1 rejections (keywords)
        try:
            tier1_rejects = db.client.table("brand_safety_log").select(
                "tier1_blocked_keyword", count="exact"
            ).eq("tier1_passed", False).not_.is_("tier1_blocked_keyword", "null").execute()
            
            if tier1_rejects.data:
                print("   Tier 1 (Keyword) blocks:")
                keyword_counts = {}
                for entry in tier1_rejects.data:
                    keyword = entry.get("tier1_blocked_keyword")
                    if keyword:
                        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                
                # Show top keywords
                sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for keyword, count in sorted_keywords:
                    print(f"     '{keyword}': {count} topics blocked")
                    
        except Exception as e:
            print(f"   Could not analyze Tier 1 rejections: {e}")
        
        # Tier 2 rejections (Llama Guard categories)
        try:
            tier2_rejects = db.client.table("brand_safety_log").select(
                "tier2_flagged_categories"
            ).eq("tier2_passed", False).execute()
            
            if tier2_rejects.data:
                print("   Tier 2 (Llama Guard) flags:")
                category_counts = {}
                for entry in tier2_rejects.data:
                    categories = entry.get("tier2_flagged_categories", [])
                    for category in categories:
                        category_counts[category] = category_counts.get(category, 0) + 1
                
                # Show top categories
                sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                for category, count in sorted_categories:
                    print(f"     {category}: {count} topics flagged")
                    
        except Exception as e:
            print(f"   Could not analyze Tier 2 rejections: {e}")
        
        print(f"\n4. 💡 Brand Safety Insights:")
        print("   • Most rejections happen at Tier 1 (keyword blocklist)")
        print("   • Llama Guard catches harmful content missed by keywords")
        print("   • Claude provides nuanced advertiser suitability assessment")
        print("   • Short-circuiting saves API costs on obviously unsafe content")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to analyze brand safety logs: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n🔧 To view brand safety examples:")
        print("1. Ensure the pipeline has run at least once")
        print("2. Check that brand_safety_log table exists")
        print("3. Verify Supabase connection")
    
    sys.exit(0 if success else 1)