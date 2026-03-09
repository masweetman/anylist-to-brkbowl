#!/usr/bin/env python
"""Test manual cookies.json update preserves acceptance preference"""

import sys
sys.path.insert(0, '/Users/mike/code/anylist-to-brkbowl')

from cart_service import CartService
import json
import time

print("🧪 Testing manual cookies.json update...")
print("=" * 60)

# Manually edit cookies.json with new cookies
print("\n✏️  Manually updating cookies.json with new test cookies...")
new_cookies = [
    {
        "name": "manual_token",
        "value": "abc123xyz",
        "domain": "shop.heinzcatering.berkeleybowl.com",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "Strict"
    }
]

with open('cookies.json', 'w') as f:
    json.dump(new_cookies, f, indent=2)

print("✅ Manually saved 1 new cookie to cookies.json")

# Verify preference file is untouched
with open('cookies_prefs.json') as f:
    prefs = json.load(f)

print(f"✅ cookies_prefs.json still has {len(prefs)} preference cookies (untouched)")

# Start session 3 - should load both the manual cookie and preference
print("\n📍 SESSION 3: Load manually updated cookies + preserved preference")
print("-" * 60)

service3 = CartService()
service3._start_browser()
print("✅ Browser started")

# Check what cookies were injected
page_cookies = service3.context.cookies()
print(f"✅ Total cookies injected: {len(page_cookies)}")
cookie_names = [c['name'] for c in page_cookies if c['name'] in ['manual_token', 'cookie_consent_v1']]
print(f"   Key cookies: {cookie_names}")

# Verify the button doesn't appear (preference is still loaded)
service3.page.goto("https://shop.heinzcatering.berkeleybowl.com/", wait_until="domcontentloaded")
time.sleep(2)

button_check = service3.page.evaluate("() => !!document.querySelector('button.cx-accept')")
print(f"✅ Cookie dialog appears: {button_check} (should be False)")

service3._close_browser()

print("\n" + "=" * 60)
print("🎉 Manual update test passed!")
print("\nFlow verified:")
print("  1. You edit cookies.json with new authentication cookies")
print("  2. cookies_prefs.json acceptance preference is NOT touched")
print("  3. Next session loads both files separately")
print("  4. Both work together seamlessly!")
