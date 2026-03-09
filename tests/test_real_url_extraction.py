#!/usr/bin/env python
"""Test actual product URL extraction from Berkeley Bowl"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing real product URL extraction...")
print("=" * 60)

service = CartService()
service._start_browser()
print("✅ Browser started")

try:
    # Navigate to Berkeley Bowl
    print("\n1️⃣  Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    time.sleep(2)
    service._accept_cookies()
    print("✅ Page loaded")
    
    # Search for an item to get to a product page
    print("\n2️⃣  Searching for 'Milk' to find a product...")
    search_box = service.page.locator('input[type="text"]').first
    if search_box.count() > 0:
        search_box.click(click_count=3)
        time.sleep(0.3)
        search_box.type("Milk", delay=80)
        time.sleep(0.5)
        search_box.press("Enter")
        time.sleep(3)
        print("✅ Search completed")
        
        # Click on first product (if available)
        print("\n3️⃣  Looking for product links...")
        product_links = service.page.locator('a[href*="/product/"]')
        
        print(f"   Found {product_links.count()} product links")
        
        if product_links.count() > 0:
            # Get first product link
            first_link = product_links.first
            product_url = first_link.get_attribute('href')
            print(f"   First product link: {product_url}")
            
            # Click it
            first_link.click()
            time.sleep(3)
            print("   ✅ Clicked first product")
            
            # Now try extraction
            print("\n4️⃣  Extracting product URL from current page...")
            current_url = service.page.url
            print(f"   Current page URL: {current_url}")
            
            extracted_url = service._extract_product_url()
            print(f"   Extracted URL: {extracted_url}")
            
            if '/product/' in extracted_url:
                print("   ✅ SUCCESS! Product URL extracted correctly")
            else:
                print("   ⚠️  URL extraction returned unexpected value")
        else:
            print("   ⚠️  No product links found")
    else:
        print("   ❌ Search box not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    service._close_browser()

print("\n" + "=" * 60)
print("✅ Real extraction test complete!")
