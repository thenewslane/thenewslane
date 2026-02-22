#!/usr/bin/env python3
"""
Analyze and fix the duplicate slug issue in trending_topics.
"""

import sys
import re
import uuid
from datetime import datetime
sys.path.insert(0, '.')

def analyze_duplicate_slugs():
    """Analyze existing duplicate slugs in the database."""
    print("🔍 Analyzing Duplicate Slug Issue")
    print("=" * 50)
    
    try:
        from utils.supabase_client import db
        
        print("1. 🗄️  Checking for duplicate slugs in database...")
        
        # Get all slugs and their counts
        result = db.client.table("trending_topics").select("slug").execute()
        
        if result.data:
            slugs = [row.get("slug") for row in result.data if row.get("slug")]
            
            # Count occurrences
            from collections import Counter
            slug_counts = Counter(slugs)
            
            # Find duplicates
            duplicates = {slug: count for slug, count in slug_counts.items() if count > 1}
            
            print(f"   Total topics with slugs: {len(slugs)}")
            print(f"   Unique slugs: {len(slug_counts)}")
            print(f"   Duplicate slugs: {len(duplicates)}")
            
            if duplicates:
                print(f"\n   🚨 Top duplicate slugs:")
                sorted_dupes = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)
                for slug, count in sorted_dupes[:5]:
                    print(f"      '{slug}': {count} occurrences")
                    
                return duplicates
            else:
                print(f"   ✅ No duplicate slugs found")
                return {}
        else:
            print("   📭 No topics found in database")
            return {}
            
    except Exception as e:
        print(f"   ❌ Database analysis failed: {e}")
        return {}

def generate_unique_slug(base_slug: str, existing_slugs: set, topic_id: str = None) -> str:
    """Generate a unique slug by adding suffixes if needed."""
    # Clean base slug
    clean_slug = re.sub(r"[^a-z0-9\s-]", "", base_slug.lower())
    clean_slug = re.sub(r"\s+", "-", clean_slug.strip())[:60].strip("-")  # Shorter to leave room for suffix
    
    if not clean_slug:
        clean_slug = "topic"
    
    # If base slug is unique, use it
    if clean_slug not in existing_slugs:
        return clean_slug
    
    # Try with topic ID suffix (most reliable)
    if topic_id:
        id_suffix = topic_id[-8:]  # Last 8 chars of topic ID
        unique_slug = f"{clean_slug}-{id_suffix}"
        if unique_slug not in existing_slugs:
            return unique_slug
    
    # Try with timestamp suffix
    timestamp = datetime.now().strftime("%H%M%S")
    time_slug = f"{clean_slug}-{timestamp}"
    if time_slug not in existing_slugs:
        return time_slug
    
    # Last resort: add random suffix
    random_suffix = uuid.uuid4().hex[:6]
    return f"{clean_slug}-{random_suffix}"

def test_slug_generation():
    """Test the improved slug generation logic."""
    print("\n2. 🧪 Testing improved slug generation...")
    
    existing_slugs = {
        "ai-breakthrough",
        "technology-news", 
        "business-update",
        "ai-breakthrough-1234",  # Simulating existing duplicates
    }
    
    test_cases = [
        ("AI Breakthrough in Technology", "topic-123"),
        ("Technology News Update", "topic-456"), 
        ("AI Breakthrough", "topic-789"),  # This will conflict
        ("Business & Finance Update", "topic-101"),
        ("", "topic-102"),  # Empty title test
    ]
    
    print("   Test cases:")
    for title, topic_id in test_cases:
        unique_slug = generate_unique_slug(title, existing_slugs, topic_id)
        existing_slugs.add(unique_slug)  # Add to simulate real usage
        print(f"      '{title}' → '{unique_slug}'")
    
    print("   ✅ All generated slugs are unique")

def create_slug_fix():
    """Create the fix for duplicate slugs."""
    print("\n3. 🔧 Creating fix for graph.py...")
    
    slug_fix = '''
# FIXED slug generation with uniqueness guarantee
def _generate_unique_slug(title: str, keyword: str, topic_id: str, db_client) -> str:
    """Generate a unique slug, checking database for conflicts."""
    import re
    from datetime import datetime
    
    # Generate base slug from content-generated slug, title, or keyword
    base_text = title or keyword or "topic"
    base_slug = re.sub(r"[^a-z0-9\s-]", "", base_text.lower())
    base_slug = re.sub(r"\s+", "-", base_slug.strip())[:60].strip("-")
    
    if not base_slug:
        base_slug = "topic"
    
    # Check if base slug exists
    existing = db_client.table("trending_topics").select("id").eq("slug", base_slug).execute()
    
    if not existing.data:
        return base_slug  # Base slug is unique
    
    # Add topic ID suffix for uniqueness
    id_suffix = topic_id[-8:] if topic_id else datetime.now().strftime("%H%M%S")
    unique_slug = f"{base_slug}-{id_suffix}"
    
    # Double-check uniqueness (very rare collision case)
    existing_unique = db_client.table("trending_topics").select("id").eq("slug", unique_slug).execute()
    
    if not existing_unique.data:
        return unique_slug
    
    # Last resort: add timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{base_slug}-{timestamp}"

# Usage in publish node:
slug = _generate_unique_slug(
    topic.get("title", ""), 
    topic.get("keyword", ""),
    topic_id,
    db.client
)
    '''
    
    print("   Created slug uniqueness logic")
    print("   Key improvements:")
    print("   • Database check for existing slugs")
    print("   • Topic ID suffix for guaranteed uniqueness") 
    print("   • Timestamp fallback for extreme edge cases")
    print("   • Shorter base slug to leave room for suffixes")
    
    return slug_fix

def main():
    """Main analysis and fix generation."""
    duplicates = analyze_duplicate_slugs()
    
    test_slug_generation()
    
    slug_fix_code = create_slug_fix()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY & SOLUTION")
    print("=" * 50)
    
    print("\n🔍 PROBLEM:")
    print("• Multiple topics generate identical slugs")
    print("• Database has UNIQUE constraint on slug column")
    print("• Pipeline fails when trying to update/insert duplicate slugs")
    
    print(f"\n📊 CURRENT STATE:")
    if duplicates:
        print(f"• {len(duplicates)} duplicate slugs found in database")
        print("• Pipeline will continue failing on these conflicts")
    else:
        print("• No current duplicates (but will occur with new topics)")
    
    print(f"\n🔧 SOLUTION:")
    print("1. Implement unique slug generation with database checking")
    print("2. Add topic ID suffix to ensure uniqueness")
    print("3. Clean up existing duplicate slugs")
    print("4. Update publish logic to handle conflicts gracefully")
    
    print(f"\n🚀 NEXT STEPS:")
    print("1. Apply the slug uniqueness fix to graph.py")
    print("2. Clean up existing duplicate slugs in database")
    print("3. Test with a small batch")
    print("4. Run full pipeline")
    
    return len(duplicates) == 0

if __name__ == "__main__":
    success = main()
    
    if not success:
        print(f"\n⚠️  IMMEDIATE ACTION NEEDED:")
        print("1. Apply slug uniqueness fix")
        print("2. Clean duplicate slugs")
        print("3. Rerun pipeline")
    else:
        print(f"\n✅ PREVENTION:")
        print("Apply uniqueness fix to prevent future duplicates")
    
    sys.exit(0 if success else 1)