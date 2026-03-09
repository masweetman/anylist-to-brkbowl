#!/usr/bin/env python
"""Test the cart endpoint"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from app import app, ShoppingItem

print("🧪 Testing cart endpoint...")
print("=" * 50)

# Get all items from database
with app.app_context():
    items = ShoppingItem.query.filter_by(complete=False).all()
    print(f"\n📋 Found {len(items)} incomplete items:")
    for item in items:
        print(f"   - {item.name} (URL: {item.url or 'None'})")
    
    # Create item dictionaries
    item_data = [{'name': item.name, 'url': item.url} for item in items]
    
    # Test the cart service
    from cart_service import CartService
    
    print(f"\n🛒 Testing CartService with {len(item_data)} items...")
    print("=" * 50)
    
    service = CartService()
    results = service.add_items(item_data)
    
    print("\n" + "=" * 50)
    print("📊 Results:")
    print(f"   Added: {len(results.get('added', []))} items")
    for item in results.get('added', []):
        print(f"      ✅ {item}")
    print(f"   Failed: {len(results.get('failed', []))} items")
    for item in results.get('failed', []):
        print(f"      ❌ {item}")
    print("=" * 50)
