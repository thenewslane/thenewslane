#!/usr/bin/env python3
"""
Explain the brand safety check logic with examples and current configuration.
"""

import sys
sys.path.insert(0, '.')

def main():
    """Explain brand safety logic."""
    print("🛡️  BRAND SAFETY CHECK LOGIC EXPLAINED")
    print("=" * 70)
    
    print("\n🔍 OVERVIEW:")
    print("Three-tier filtering system that processes topics sequentially.")
    print("Each tier can reject a topic, stopping further processing (short-circuiting).")
    print("Only topics that pass ALL three tiers are marked as 'brand_safe'.")
    
    print("\n" + "─" * 70)
    print("⚡ TIER 1: KEYWORD FILTER (Instant)")
    print("─" * 70)
    print("• PURPOSE: Fast blocklist filtering")
    print("• DATA SOURCE: Supabase config table ('keyword_blocklist')")
    print("• LOGIC: Case-insensitive keyword matching")
    print("• INPUT: topic_title + headline_cluster (combined text)")
    print("• PROCESS:")
    print("  1. Load blocked keywords from database")
    print("  2. Check if ANY keyword appears in topic text")
    print("  3. FAIL immediately if match found")
    print("• PERFORMANCE: <1ms (no API calls)")
    print("• SHORT-CIRCUIT: ✅ Stops processing if blocked")
    
    try:
        from utils.supabase_client import db
        keywords = db.get_config_value("keyword_blocklist", default=[])
        print(f"\n• CURRENT BLOCKLIST: {len(keywords)} keywords")
        if keywords:
            sample_keywords = keywords[:5] if len(keywords) >= 5 else keywords
            print(f"  Sample keywords: {sample_keywords}")
        else:
            print("  No blocked keywords configured")
    except Exception as e:
        print(f"  (Could not load current keywords: {e})")
    
    print("\n" + "─" * 70)
    print("🤖 TIER 2: LLAMA GUARD FILTER (~2 seconds)")
    print("─" * 70)
    print("• PURPOSE: AI-powered harm detection")
    print("• API: Groq with 'meta-llama/Llama-Guard-3-11B-Vision-Turbo'")
    print("• PROCESS:")
    print("  1. Format content: 'Topic: {title}\\nHeadlines: {headlines}'")
    print("  2. Send to Llama Guard model")
    print("  3. Parse response: 'safe' or 'unsafe\\nS1,S3' (category codes)")
    print("  4. FAIL if response starts with 'unsafe'")
    print("• CATEGORIES (14 total):")
    
    categories = [
        "S1: Violent Crimes", "S2: Non-Violent Crimes", "S3: Sex Crimes",
        "S4: Child Exploitation", "S5: Defamation", "S6: Specialized Advice",
        "S7: Privacy", "S8: Intellectual Property", "S9: Indiscriminate Weapons",
        "S10: Hate", "S11: Self-Harm", "S12: Sexual Content",
        "S13: Elections", "S14: Code Interpreter Abuse"
    ]
    
    for i, cat in enumerate(categories, 1):
        print(f"  {i:2}. {cat}")
    
    print("• PERFORMANCE: ~1-2 seconds per topic")
    print("• SHORT-CIRCUIT: ✅ Stops processing if flagged")
    print("• FALLBACK: Defaults to SAFE on API errors")
    
    print("\n" + "─" * 70)
    print("🎯 TIER 3: BRAND SAFETY LLM FILTER (~2 seconds)")
    print("─" * 70)
    print("• PURPOSE: Advertiser suitability assessment")
    print("• API: Anthropic Claude Haiku ('claude-3-haiku-20240307')")
    print("• LOGIC: Would Toyota/P&G advertise next to this content?")
    print("• PROCESS:")
    print("  1. Send prompt asking about advertiser comfort")
    print("  2. Parse response for 'SAFE' or 'UNSAFE' + explanation")
    print("  3. FAIL if response starts with 'UNSAFE'")
    print("• EXAMPLE PROMPT:")
    
    example_prompt = '''You are a brand safety reviewer. A mainstream advertiser like Toyota or 
Procter and Gamble needs to decide if their ad should appear next to content 
about this topic.

Topic: AI Innovation Breakthrough
Headlines: New chatbot capabilities announced by major tech companies

Would a major advertiser be comfortable? Answer: SAFE or UNSAFE and one 
sentence explanation.'''
    
    for line in example_prompt.split('\n'):
        print(f"    {line}")
    
    print("• PERFORMANCE: ~1-2 seconds per topic")
    print("• FALLBACK: Defaults to SAFE on API errors")
    
    print("\n" + "─" * 70)
    print("📊 PROCESSING FLOW")
    print("─" * 70)
    print("1. Topic enters brand safety check")
    print("2. ⚡ Tier 1 (Keyword): INSTANT screening")
    print("   └── ❌ BLOCKED → Log & reject (skip Tier 2 & 3)")
    print("   └── ✅ PASSED → Continue to Tier 2")
    print("3. 🤖 Tier 2 (Llama Guard): AI harm detection")
    print("   └── ❌ FLAGGED → Log & reject (skip Tier 3)")
    print("   └── ✅ PASSED → Continue to Tier 3")
    print("4. 🎯 Tier 3 (Brand Safety): Advertiser suitability")
    print("   └── ❌ UNSAFE → Log & reject")
    print("   └── ✅ SAFE → Mark as 'brand_safe' & continue pipeline")
    
    print("\n" + "─" * 70)
    print("📝 LOGGING & AUDIT TRAIL")
    print("─" * 70)
    print("• ALL decisions logged to 'brand_safety_log' table")
    print("• Log entry contains:")
    print("  - batch_id, topic_id, topic_title")
    print("  - tier1_passed, tier1_blocked_keyword")
    print("  - tier2_passed, tier2_flagged_categories")
    print("  - tier3_passed, tier3_explanation")
    print("  - overall_passed (final decision)")
    print("• Enables compliance auditing and filter tuning")
    
    print("\n" + "─" * 70)
    print("🚀 PERFORMANCE & OPTIMIZATION")
    print("─" * 70)
    print("• SHORT-CIRCUITING: Early exit saves API costs")
    print("  - If Tier 1 blocks: 0 API calls needed")
    print("  - If Tier 2 blocks: Only 1 API call needed")
    print("  - Only safe topics use all 3 tiers")
    print("• PARALLEL PROCESSING: Topics processed independently")
    print("• ERROR HANDLING: API failures default to SAFE")
    print("• RATE LIMITING: Handled by underlying HTTP clients")
    
    print("\n" + "─" * 70)
    print("⚙️ CONFIGURATION")
    print("─" * 70)
    print("• Keyword blocklist: Supabase config table")
    print("• API keys required: GROQ_API_KEY, ANTHROPIC_API_KEY")
    print("• Models used:")
    print("  - Llama Guard: 'meta-llama/Llama-Guard-3-11B-Vision-Turbo'")
    print("  - Claude: 'claude-3-haiku-20240307'")
    
    print("\n🎯 RESULT: Only topics marked 'brand_safe=True' proceed to classification")

if __name__ == "__main__":
    main()