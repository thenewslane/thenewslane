#!/usr/bin/env python3
"""
fix_category_colors.py

Fix the categories to have different colors for visual distinction.
"""

from utils.supabase_client import db
from utils.logger import get_logger

log = get_logger(__name__)

def update_category_colors():
    """Update categories with distinct colors"""
    
    print("🎨 Updating Category Colors")
    print("=" * 30)
    
    # Define distinct colors for each category
    category_colors = {
        1: "#3B82F6",   # Technology - Blue
        2: "#EF4444",   # Entertainment - Red
        3: "#10B981",   # Sports - Green
        4: "#F59E0B",   # Politics - Amber
        5: "#8B5CF6",   # Business & Finance - Purple
        6: "#06B6D4",   # Health & Science - Cyan
        7: "#F97316",   # Lifestyle - Orange
        8: "#84CC16",   # World News - Lime
        9: "#EC4899",   # Culture & Arts - Pink
        10: "#6B7280"   # Environment - Gray
    }
    
    try:
        # Get all categories
        result = db.client.table("categories").select("id, name, color").execute()
        categories = result.data
        
        print(f"📊 Found {len(categories)} categories")
        
        # Update each category with its new color
        updates_made = 0
        for category in categories:
            cat_id = category['id']
            current_color = category.get('color')
            new_color = category_colors.get(cat_id)
            
            if new_color and current_color != new_color:
                # Update the color
                update_result = db.client.table("categories").update({
                    "color": new_color
                }).eq("id", cat_id).execute()
                
                print(f"✓ Updated {category['name']}: {current_color} → {new_color}")
                updates_made += 1
            else:
                print(f"- {category['name']}: already {current_color or new_color}")
        
        print(f"\n🎨 Updated {updates_made} category colors")
        
        if updates_made > 0:
            print("\n✅ Category tabs should now have distinct colors!")
            print("   Each category will be visually distinguishable in the web app.")
        
    except Exception as e:
        print(f"❌ Failed to update category colors: {e}")

def show_updated_categories():
    """Show the updated category colors"""
    print("\n📋 Updated Category Colors:")
    print("-" * 40)
    
    try:
        result = db.client.table("categories").select("id, name, color").order("id").execute()
        categories = result.data
        
        for cat in categories:
            print(f"{cat['id']:2}. {cat['name']:<18} {cat.get('color', 'None')}")
    
    except Exception as e:
        print(f"❌ Failed to show categories: {e}")

if __name__ == "__main__":
    update_category_colors()
    show_updated_categories()