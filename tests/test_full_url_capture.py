#!/usr/bin/env python
"""Test full flow: search, wait for cart increment, capture URL, return to search"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing complete URL capture flow...")
print("=" * 70)

service = CartService()
service._start_browser()

try:
    # Navigate to search results
    print("\n1️⃣  Navigating to Berkeley Bowl and searching...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(2)
    service._accept_cookies()
    
    # Search
    search_box = service.page.locator('input[type="text"]').first
    if search_box.count() > 0:
        search_box.click(click_count=3)
        time.sleep(0.3)
        search_box.type("Bread", delay=80)
        time.sleep(0.5)
        search_box.press("Enter")
        time.sleep(3)
        print("✅ Search results loaded")
        
        # Get initial cart count
        print("\n2️⃣  Getting initial cart count...")
        initial_count = service._get_cart_count()
        print(f"✅ Initial cart count: {initial_count}")
        
        # Simulate user clicking Add to cart by monitoring cart
        print("\n3️⃣  Watching for Add to cart button press (10 second wait for demo)...")
        print("   (In real usage, user would click Add to cart in the visible browser)")
        
        # For demo, simulate finding a product and clicking its Add to cart button
        print("\n4️⃣  Auto-clicking first Add to cart button (simulating user action)...")
        add_btns = service.page.locator('button[title="Add to cart"]')
        if add_btns.count() > 0:
            # In real scenario, user clicks this themselves
            # We're checking if we can find it
            print(f"✅ Found {add_btns.count()} 'Add to cart' buttons visible")
            print("   (User would click one in the real browser)")
            
            # Get current cart count
            current_count = service._get_cart_count()
            print(f"\n5️⃣  Current cart count: {current_count}")
            
            # Simulate cart increment
            if current_count == initial_count:
                print("   (No user interaction yet, simulating...)")
                # Click first button to simulate
                print("   Clicking first Add to cart button to simulate user action...")
                add_btns.first.click()
                time.sleep(2)
                new_count = service._get_cart_count()
                print(f"✅ Cart count after button: {new_count}")
            
            # Now capture the ProductTitle URL
            print("\n6️⃣  Capturing product URL via ProductTitle click...")
            product_url = service._capture_product_url_after_click()
            
            if product_url:
                print(f"✅ SUCCESS! Captured URL: {product_url}")
                
                # Verify we're back on search results
                print(f"\n7️⃣  Verifying we returned to search results...")
                current_page = service.page.url
                if 'search' in current_page:
                    print(f"✅ Back on search results: {current_page}")
                else:
                    print(f"⚠️  Not on search results page: {current_page}")
            else:
                print(f"⚠️  Could not capture product URL")
        else:
            print("❌ No Add to cart buttons found")
    else:
        print("❌ Search box not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    service._close_browser()

print("\n" + "=" * 70)
print("✅ Test complete!")
