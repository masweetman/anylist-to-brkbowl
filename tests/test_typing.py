#!/usr/bin/env python
"""Test click and fill on search box"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing click + fill on search box...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started")
    
    print("\n📍 Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", timeout=10000)
    print("✅ Page loaded")
    time.sleep(2)
    
    # Get first text input
    search_inputs = service.page.locator('input[type="text"]')
    if search_inputs.count() > 0:
        search_box = search_inputs.first
        print("✅ Found search box")
        
        # Try typing instead of fill
        print("\n⌨️ Typing in search box...")
        search_box.click()
        print("✅ Clicked search box")
        
        # Use type() instead of fill()
        search_box.type("Milk", delay=100)
        print("✅ Typed search term")
        
        time.sleep(2)
        
        # Take screenshot
        service.page.screenshot(path="after_typing.png")
        print("✅ Screenshot saved")
        
        print("\n⏳ Keeping browser open for 10 seconds...")
        time.sleep(10)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    service._close_browser()
    print("✅ Browser closed")
