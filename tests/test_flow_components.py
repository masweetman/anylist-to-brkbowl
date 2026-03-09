#!/usr/bin/env python
"""Test individual components of the new flow"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing new flow components...")
print("=" * 70)

service = CartService()
service._start_browser()

try:
    # Test 1: Navigate and search
    print("\n1️⃣  Testing search...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(2)
    service._accept_cookies()
    
    search_box = service.page.locator('input[type="text"]').first
    search_box.click(click_count=3)
    time.sleep(0.3)
    search_box.type("Milk", delay=80)
    time.sleep(0.5)
    search_box.press("Enter")
    time.sleep(3)
    print("   ✅ Search completed")
    
    # Test 2: Cart count detection
    print("\n2️⃣  Testing cart count detection...")
    initial = service._get_cart_count()
    print(f"   Initial cart count: {initial}")
    
    # Click Add to cart
    add_btn = service.page.locator('button[title="Add to cart"]').first
    add_btn.click()
    time.sleep(1)
    
    after_click = service._get_cart_count()
    print(f"   After Add to cart click: {after_click}")
    
    if after_click > initial:
        print(f"   ✅ Cart count increase detected!")
    else:
        print(f"   ⚠️  Cart count did not increase")
    
    # Test 3: Navigate to product page
    print("\n3️⃣  Testing product page navigation...")
    product_titles = service.page.locator('[class*="ProductTitle"]')
    if product_titles.count() > 0:
        print(f"   Found {product_titles.count()} ProductTitle elements")
        print(f"   Clicking first ProductTitle...")
        product_titles.first.click()
        time.sleep(3)
        
        current_url = service.page.url
        print(f"   Current URL: {current_url}")
        
        if '/product/' in current_url:
            print(f"   ✅ Successfully navigated to product page!")
            
            # Test 4: Check quantity
            print(f"\n4️⃣  Testing InputWrap quantity detection...")
            quantity = service._get_input_wrap_quantity()
            print(f"   Quantity from InputWrap: {quantity}")
            print(f"   ✅ Quantity detection working!")
            
            # Test 5: Check Add to cart button
            print(f"\n5️⃣  Testing Add to cart button...")
            add_to_cart = service.page.locator('button[title="Add to cart"]')
            if add_to_cart.count() > 0:
                print(f"   ✅ Add to cart button found on product page")
            else:
                print(f"   ⚠️  Add to cart button not found")
            
            # Test 6: Return to search
            print(f"\n6️⃣  Testing return to search...")
            service.page.go_back()
            time.sleep(2)
            
            back_url = service.page.url
            if 'search' in back_url:
                print(f"   ✅ Successfully returned to search results!")
                print(f"   URL: {back_url}")
            else:
                print(f"   ⚠️  Not on search page: {back_url}")
        else:
            print(f"   ⚠️  Not on product page: {current_url}")
    else:
        print(f"   ⚠️  No ProductTitle elements found")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    service._close_browser()

print("\n" + "=" * 70)
print("✅ Component testing complete!")
