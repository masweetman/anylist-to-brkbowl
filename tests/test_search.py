#!/usr/bin/env python
"""Test the search functionality to verify the fix"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing search functionality...")
print("=" * 50)

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started")
    
    # Navigate to Berkeley Bowl
    print("\n📍 Navigating to Berkeley Bowl...")
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded", timeout=10000)
    print("✅ Page loaded")
    time.sleep(2)
    
    # Try searching for one item to test
    item_name = "Bread"
    print(f"\n🔎 Testing search for: {item_name}")
    
    # Find search box
    search_inputs = service.page.locator('input[type="text"]')
    print(f"   Found {search_inputs.count()} text inputs")
    
    if search_inputs.count() > 0:
        search_box = search_inputs.first
        print("   ✅ Located search box")
        
        # Click and wait for focus
        search_box.click()
        print("   ✅ Clicked search box")
        
        time.sleep(0.3)
        
        # Clear any existing content
        search_box.fill("")
        print("   ✅ Cleared input field")
        
        time.sleep(0.2)
        
        # Type the search term
        search_box.type(item_name, delay=50)
        print(f"   ✅ Typed: {item_name}")
        
        # Check what was actually typed
        input_value = search_box.input_value()
        print(f"   📝 Input value: '{input_value}'")
        
        if input_value == item_name:
            print(f"   ✅✅✅ Search term entered correctly!")
        else:
            print(f"   ❌ ERROR: Expected '{item_name}' but got '{input_value}'")
    else:
        print(f"   ❌ Could not find search box")
    
    service._close_browser()
    print("\n✅ Test complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
