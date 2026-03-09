#!/usr/bin/env python
"""Test script to verify browser launch"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService

print("🧪 Testing browser launch...")
print("=" * 50)

try:
    service = CartService()
    print("✅ CartService initialized")
    
    # Test browser start
    print("\n🚀 Starting browser...")
    service._start_browser()
    print("✅ Browser started successfully!")
    
    # Navigate to test page
    print("\n📍 Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
    print("✅ Page loaded!")
    
    # Take a screenshot
    print("\n📸 Taking screenshot...")
    service.page.screenshot(path="browser_test.png")
    print("✅ Screenshot saved to browser_test.png")
    
    # Wait a bit so you can see the browser
    print("\n⏳ Keeping browser open for 10 seconds...")
    import time
    time.sleep(10)
    
    print("\n✅ Test completed successfully!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\n🔒 Closing browser...")
    service._close_browser()
    print("✅ Browser closed")
