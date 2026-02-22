#!/usr/bin/env python3
"""
check_categories_schema.py

Check if categories table has the required color field and other schema details.
"""

from utils.supabase_client import db
from utils.logger import get_logger

log = get_logger(__name__)

def check_categories_schema():
    """Check categories table schema and data"""
    
    print("🔍 Checking categories table schema and data")
    print("=" * 50)
    
    try:
        # Get all categories with all fields
        result = db.client.table("categories").select("*").execute()
        categories = result.data
        
        if not categories:
            print("❌ No categories found")
            return
        
        print(f"📊 Found {len(categories)} categories")
        
        # Check first category to see available fields
        sample_category = categories[0]
        available_fields = list(sample_category.keys())
        print(f"\n📋 Available fields: {available_fields}")
        
        # Check if color field exists
        has_color = 'color' in available_fields
        print(f"🎨 Color field exists: {'✓' if has_color else '❌'}")
        
        print("\n📂 Categories details:")
        for i, cat in enumerate(categories, 1):
            print(f"\n{i}. {cat.get('name', 'Unknown')}")
            print(f"   ID: {cat.get('id')}")
            print(f"   Description: {cat.get('description', 'None')[:50]}...")
            if has_color:
                print(f"   Color: {cat.get('color', 'None')}")
            else:
                print("   Color: ❌ Missing field")
        
        if not has_color:
            print("\n🔧 SQL to add missing color field:")
            print("ALTER TABLE categories ADD COLUMN color VARCHAR(7);")
            print("\nSample colors to update categories:")
            colors = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", 
                     "#06B6D4", "#F97316", "#84CC16", "#EC4899", "#6B7280"]
            for i, cat in enumerate(categories):
                color = colors[i % len(colors)]
                print(f"UPDATE categories SET color = '{color}' WHERE id = '{cat['id']}';")
    
    except Exception as e:
        print(f"❌ Categories schema check failed: {e}")

def check_classification_mapping():
    """Check if classification node is properly assigning category_id"""
    
    print("\n🔍 Checking classification logic")
    print("=" * 40)
    
    # Get categories for mapping
    try:
        result = db.client.table("categories").select("id, name").execute()
        categories = result.data
        
        category_map = {cat['name']: cat['id'] for cat in categories}
        print("📋 Available category mapping:")
        for name, cat_id in category_map.items():
            print(f"  '{name}' -> {cat_id}")
        
        print("\n🔧 Classification node should map these category names to IDs:")
        for name in category_map.keys():
            print(f"  - {name}")
    
    except Exception as e:
        print(f"❌ Classification mapping check failed: {e}")

if __name__ == "__main__":
    check_categories_schema()
    check_classification_mapping()