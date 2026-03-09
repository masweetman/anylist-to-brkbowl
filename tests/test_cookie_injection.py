#!/usr/bin/env python
"""Quick test of cookie injection"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService

print("🧪 Testing cookie injection...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started with cookies injected")
    
    # Navigate to a page
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", timeout=5000)
    print("✅ Navigated to Berkeley Bowl")
    
    # Check if cookies were applied
    cookies = service.context.cookies()
    print(f"\n📋 Active cookies in context: {len(cookies)}")
    for cookie in cookies:
        print(f"   - {cookie['name']}")
    
    import time
    time.sleep(3)
    service._close_browser()
    print("\n✅ Test complete - cookies were properly injected!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
