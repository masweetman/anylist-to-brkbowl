#!/usr/bin/env python
"""Test search using the actual cart automation"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from app import app, db, ShoppingItem

print("🧪 Testing actual cart search workflow...")
print("=" * 50)

# Add test items
with app.app_context():
    ShoppingItem.query.delete()
    db.session.commit()
    
    items = [
        ShoppingItem(name="Bread", complete=False, url=""),
        ShoppingItem(name="Milk", complete=False, url=""),
    ]
    for item in items:
        db.session.add(item)
    db.session.commit()
    
    print(f"✅ Created 2 test items")
    
    # Now test cart automation
    from cart_service import CartService
    import time
    
    item_data = [{'name': item.name, 'url': item.url} for item in items]
    
    service = CartService()
    
    try:
        service._start_browser()
        print("✅ Browser started")
        
        for item in item_data:
            item_name = item['name']
            print(f"\n📍 Testing: {item_name}")
            
            service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
            time.sleep(2)
            
            # Find search box
            search_box = None
            selectors = [
                'input[placeholder="Search product"]',
                'input[type="text"]',
                'input.search',
            ]
            
            for selector in selectors:
                try:
                    if service.page.locator(selector).count() > 0:
                        search_box = service.page.locator(selector).first
                        print(f"   ✅ Found search box with selector: {selector}")
                        break
                except:
                    continue
            
            if search_box:
                print(f"   🔎 Searching for: {item_name}")
                search_box.click()
                search_box.focus()
                time.sleep(0.3)
                search_box.press("Control+A")
                time.sleep(0.1)
                search_box.press("Delete")
                time.sleep(0.2)
                search_box.type(item_name, delay=30)
                print(f"   ✅ Typed: {item_name}")
                
                # Check value
                input_value = search_box.input_value()
                print(f"   📝 Input value: '{input_value}'")
                
                if item_name.lower() in input_value.lower() or input_value.lower() in item_name.lower():
                    print(f"   ✅ SUCCESS - Search term captured!")
                else:
                    print(f"   ⚠️  WARNING - Search term might have issues")
        
        service._close_browser()
        print("\n✅ Test complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        service._close_browser()
