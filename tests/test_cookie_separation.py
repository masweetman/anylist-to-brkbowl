#!/usr/bin/env python
"""Test that cookies are separated into two files"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import json
import os
import time

print("🧪 Testing cookie separation...")
print("=" * 60)

# Clear both files first
try:
    os.remove('cookies.json')
    os.remove('cookies_prefs.json')
except:
    pass

# Session 1: Fresh browser, accept cookies
print("\n📍 SESSION 1: Fresh browser, accept cookies")
print("-" * 60)

service1 = CartService()
service1._start_browser()
print("✅ Browser started (empty cookies)")

print("\n   Loading Berkeley Bowl...")
service1.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
time.sleep(2)

# Accept cookies
print("   Accepting cookies...")
service1._accept_cookies()
time.sleep(1)

service1._close_browser()
print("✅ Session 1 closed - cookies saved")

# Check what was saved
print("\n📊 Files after Session 1:")
print("-" * 60)

cookies_count = 0
prefs_count = 0

if os.path.exists('cookies.json'):
    with open('cookies.json') as f:
        cookies = json.load(f)
        cookies_count = len(cookies)
        print(f"✅ cookies.json: {cookies_count} cookies")
        if cookies:
            print(f"   First cookie: {cookies[0]['name']}")

if os.path.exists('cookies_prefs.json'):
    with open('cookies_prefs.json') as f:
        prefs = json.load(f)
        prefs_count = len(prefs)
        print(f"✅ cookies_prefs.json: {prefs_count} preference cookies")
        if prefs:
            for pref in prefs:
                print(f"   - {pref['name']}")

print(f"\n📈 Total: {cookies_count} main + {prefs_count} preference = {cookies_count + prefs_count} cookies")

# Session 2: Load both files
print("\n📍 SESSION 2: Load both files separately")
print("-" * 60)

service2 = CartService()
service2._start_browser()
print("✅ Browser started (both files loaded)")

print("\n   Loading Berkeley Bowl...")
service2.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
time.sleep(2)

# Check if button appears (it shouldn't if preference was loaded)
button_check = service2.page.evaluate("""
    () => {
        const btn = document.querySelector('button.cx-accept');
        return btn ? 'FOUND' : 'NOT_FOUND';
    }
""")
print(f"   Cookie accept button: {button_check}")

if button_check == "NOT_FOUND":
    print("   ✅ SUCCESS! Preference cookie loaded - button didn't appear")
else:
    print("   ⚠️  Button appeared (preference not loaded)")

service2._close_browser()

print("\n" + "=" * 60)
print("✅ Separation test complete!")
print("\nℹ️  You can now manually edit cookies.json without affecting")
print("   the cookie acceptance preference stored in cookies_prefs.json")
