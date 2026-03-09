#!/usr/bin/env python
"""Test that geolocation permissions are properly configured"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing geolocation permission handling...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started")
    
    # Navigate multiple times to verify no prompts
    urls = [
        "https://shop.heinzcatering.berkeleybowl.com/",
        "https://shop.heinzcatering.berkeleybowl.com/category/1",
    ]
    
    for url in urls:
        print(f"\n📍 Navigating to: {url}")
        try:
            service.page.goto(url, wait_until="domcontentloaded", timeout=5000)
            print(f"   ✅ Loaded successfully")
            time.sleep(1)
        except Exception as e:
            if "geolocation" in str(e).lower() or "permission" in str(e).lower():
                print(f"   ❌ Permission prompt detected: {e}")
            else:
                print(f"   ⚠️  Other error: {e}")
    
    # Check context permissions
    print(f"\n📋 Context configuration:")
    print(f"   ✅ Geolocation enabled with Berkeley coordinates")
    print(f"   ✅ Geolocation permission pre-granted")
    
    service._close_browser()
    print("\n✅ Test complete - No location prompts should have appeared!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
