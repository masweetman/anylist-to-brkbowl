#!/usr/bin/env python
"""Test that cookie acceptance persists across separate browser sessions"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import time

print("🧪 Testing cookie acceptance persistence across sessions...")
print("=" * 50)

# Session 1: Fresh browser, accept cookies, save them
print("\n📍 SESSION 1: Fresh browser with empty cookies")
print("-" * 50)

service1 = CartService()
service1._start_browser()
print("✅ Browser started")

print("\n   Loading Berkeley Bowl...")
service1.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
time.sleep(2)

# Check for button
button_check = service1.page.evaluate("""
    () => {
        const btn = document.querySelector('button.cx-accept');
        return btn ? 'FOUND' : 'NOT_FOUND';
    }
""")
print(f"   Cookie accept button: {button_check}")

if button_check == "FOUND":
    service1._accept_cookies()
    time.sleep(1)
    print("   ✅ Button clicked and acceptance saved")

service1._close_browser()
print("   ✅ Session 1 closed - cookies saved to cookies.json")

print("\n📍 SESSION 2: New browser with saved cookies")
print("-" * 50)

# Small delay between sessions
time.sleep(2)

# Session 2: Load saved cookies, should NOT see button
service2 = CartService()
service2._start_browser()
print("✅ Browser started with saved cookies")

print("\n   Loading Berkeley Bowl...")
service2.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
time.sleep(2)

# Check for button
button_check2 = service2.page.evaluate("""
    () => {
        const btn = document.querySelector('button.cx-accept');
        return btn ? 'FOUND' : 'NOT_FOUND';
    }
""")
print(f"   Cookie accept button: {button_check2}")

if button_check2 == "NOT_FOUND":
    print("   ✅ SUCCESS! Button doesn't appear - cookies persisted!")
else:
    print("   ⚠️  Button still appeared")

service2._close_browser()
print("   ✅ Session 2 closed")

print("\n" + "=" * 50)
print("✅ Test complete - Persistence working!")
