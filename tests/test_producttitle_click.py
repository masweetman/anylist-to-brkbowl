#!/usr/bin/env python
"""Test product URL capture by clicking ProductTitle after Add to cart"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing ProductTitle click and URL capture...")
print("=" * 70)

service = CartService()
service._start_browser()

try:
    # Navigate to search results
    print("\n1️⃣  Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(2)
    service._accept_cookies()
    print("✅ Home page loaded")
    
    # Search for item
    print("\n2️⃣  Searching for 'Milk'...")
    search_box = service.page.locator('input[type="text"]').first
    if search_box.count() > 0:
        search_box.click(click_count=3)
        time.sleep(0.3)
        search_box.type("Milk", delay=80)
        time.sleep(0.5)
        search_box.press("Enter")
        time.sleep(3)
        print("✅ Search completed")
        
        # Show current page
        print(f"\n3️⃣  Current page: {service.page.url}")
        
        # Check for ProductTitle elements
        print("\n4️⃣  Looking for ProductTitle elements...")
        product_titles = service.page.locator('[class*="ProductTitle"]')
        title_count = product_titles.count()
        print(f"✅ Found {title_count} ProductTitle element(s)")
        
        if title_count > 0:
            # Click first ProductTitle
            print("\n5️⃣  Clicking first ProductTitle...")
            product_titles.first.click()
            time.sleep(3)
            
            # Capture URL
            current_url = service.page.url
            print(f"✅ Navigated to: {current_url}")
            
            # Verify it's a product page
            if '/product/' in current_url:
                print(f"✅ SUCCESS! Product URL captured: {current_url}")
            else:
                print(f"⚠️  URL doesn't contain /product/: {current_url}")
        else:
            print("⚠️  No ProductTitle elements found on page")
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
