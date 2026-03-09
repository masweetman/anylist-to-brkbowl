#!/usr/bin/env python
"""Test the new user-driven flow for URL capture"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing new user-driven URL capture flow...")
print("=" * 70)

service = CartService()
service._start_browser()

try:
    # Navigate and search
    print("\n1️⃣  Navigating to Berkeley Bowl and searching...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(2)
    service._accept_cookies()
    
    print("   Searching for 'Bread'...")
    search_box = service.page.locator('input[type="text"]').first
    if search_box.count() > 0:
        search_box.click(click_count=3)
        time.sleep(0.3)
        search_box.type("Bread", delay=80)
        time.sleep(0.5)
        search_box.press("Enter")
        time.sleep(3)
        print("   ✅ Search results loaded")
        
        # Get initial cart count
        initial_count = service._get_cart_count()
        print(f"\n2️⃣  Initial cart count: {initial_count}")
        
        # Simulate user action
        print(f"\n3️⃣  Simulating user clicking 'Add to cart'...")
        add_btns = service.page.locator('button[title="Add to cart"]')
        if add_btns.count() > 0:
            print(f"   Clicking first 'Add to cart' button...")
            add_btns.first.click()
            time.sleep(1)
            
            new_count = service._get_cart_count()
            print(f"   ✅ Cart count: {initial_count} → {new_count}")
            
            # Now test the popup and navigation wait
            print(f"\n4️⃣  Testing popup + navigation wait...")
            print(f"   The popup will appear in the browser")
            print(f"   You have 30 seconds to click a product title")
            
            product_url = service._wait_for_product_page_navigation(timeout_seconds=30)
            
            if product_url:
                print(f"\n5️⃣  Got product URL: {product_url}")
                
                # Test quantity check
                print(f"\n6️⃣  Checking InputWrap quantity...")
                quantity = service._get_input_wrap_quantity()
                print(f"   Quantity value: {quantity}")
                
                if quantity <= 0:
                    print(f"   Would click 'Add to cart' button")
                else:
                    print(f"   Quantity > 0, would NOT click 'Add to cart'")
                
                # Test return to search
                print(f"\n7️⃣  Returning to search results...")
                service.page.go_back()
                time.sleep(2)
                current_url = service.page.url
                
                if 'search' in current_url:
                    print(f"   ✅ Back on search results: {current_url}")
                else:
                    print(f"   ⚠️  Not on search page: {current_url}")
                    
            else:
                print(f"\n❌ Timeout: No product page navigation detected")
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
print("\nFlow summary:")
print("  1. Search for product")
print("  2. User clicks 'Add to cart' button")
print("  3. App detects cart count increase")
print("  4. Popup asks user to click product title")
print("  5. User navigates to product page") 
print("  6. App captures URL from product page")
print("  7. App checks quantity in InputWrap")
print("  8. If quantity <= 0, clicks 'Add to cart' on product page")
print("  9. App returns to search results to continue")
