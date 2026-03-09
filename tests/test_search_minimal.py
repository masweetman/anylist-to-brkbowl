#!/usr/bin/env python
"""Minimal test to debug search box issues"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Minimal search test...")

try:
    service = CartService()
    service._start_browser()
    print("✅ Browser started")
    
    service.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded", timeout=10000)
    print("✅ Page loaded")
    time.sleep(2)
    
    search_inputs = service.page.locator('input[type="text"]')
    print(f"✅ Found {search_inputs.count()} text inputs")
    
    if search_inputs.count() > 0:
        search_box = search_inputs.first
        print("✅ Got search box element")
        
        # Try just typing without anything else
        print("📝 Typing 'Test'...")
        search_box.type("Test", delay=30)
        print("✅ Typed successfully")
        
        # Check the value
        value = search_box.input_value()
        print(f"   Input value: '{value}'")
    
    service._close_browser()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
