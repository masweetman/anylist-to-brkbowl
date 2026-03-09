#!/usr/bin/env python
"""Test the cart endpoint - minimal version"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing CartService with manual steps...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started")
    
    print("\n📍 Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", timeout=10000)
    print("✅ Page loaded")
    time.sleep(2)
    
    # Try to find search box
    print("\n🔎 Looking for search box...")
    search_inputs = service.page.locator('input[type="text"]')
    count = search_inputs.count()
    print(f"   Found {count} text inputs")
    
    if count > 0:
        search_box = search_inputs.first
        print("✅ Found search box")
        
        print("\n🔍 Searching for 'Milk'...")
        search_box.fill("Milk")
        print("✅ Entered search term")
        
        search_box.press("Enter")
        print("✅ Pressed Enter")
        
        time.sleep(3)
        print("✅ Waited 3 seconds for results to load")
        
        # Take screenshot
        service.page.screenshot(path="search_results.png")
        print("✅ Screenshot saved to search_results.png")
        
        print("\n⏳ Keeping browser open for 15 seconds...")
        time.sleep(15)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    service._close_browser()
    print("✅ Browser closed")
